"""Generation-verification gap monitor.
Spec reference: Section 13.3 (Metacognitive Monitoring — gap_monitoring).

Tracks whether evolution approvals are actually reliable:
- False positive rate: approved changes that turned out worse
- False negative rate: rejected changes that would have been beneficial

Auto-calibrates evaluation thresholds:
- FP rate > configured threshold: tighten (raise promote_threshold)
- FN rate > configured threshold: loosen (lower promote_threshold)

Key constraints:
- Thresholds loaded from YAML config (M-07 fix), not hardcoded
- Threshold changes are bounded (promote_threshold in [min, max])
- promote_threshold must stay > hold_threshold (FM-P8-024)
- Each calibration action is logged
- Metrics are persisted for continuity across sessions
- Calibration only triggers after minimum sample size
- Corrupted metrics file recovery (FM-P8-016)

Literature basis:
- Song et al. 2024: Generation-verification gap
- Huang 2025: Iterative calibration
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import yaml
from pydantic import ValidationError

from ..models.population import GapCalibrationAction, GapMetrics
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.gap_monitor")


class GapMonitor:
    """Generation-verification gap tracker and auto-calibrator.

    Design invariants:
    - Metrics are persisted to YAML for cross-session continuity
    - Calibration only fires after min_sample_size promotions
    - Threshold adjustments are bounded by [min, max]
    - promote_threshold must stay > hold_threshold (FM-P8-024)
    - Each calibration action is logged with full context
    - FP/FN rates computed lazily (avoid division by zero)

    Usage:
        monitor = GapMonitor(yaml_store, domain)
        monitor.record_promotion()
        monitor.record_rejection()
        monitor.record_false_positive()
        monitor.record_false_negative()
        action = monitor.check_calibration()
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._metrics_path = f"instances/{domain}/state/evolution/gap_metrics.yaml"

        # M-07 fix: Load thresholds from YAML config (IFM-N53 fail-loud)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        gap_cfg = config_raw["evolution"]["gap_monitoring"]
        self._fp_tighten: float = float(gap_cfg["fp_tighten_threshold"])
        self._fn_loosen: float = float(gap_cfg["fn_loosen_threshold"])
        self._threshold_step: float = float(gap_cfg["threshold_step"])
        self._min_promote: float = float(gap_cfg["min_promote_threshold"])
        self._max_promote: float = float(gap_cfg["max_promote_threshold"])
        self._min_sample: int = int(gap_cfg["min_sample_size"])

        self._metrics = self._load_metrics()

    def record_promotion(self) -> None:
        """Record that an evolution was promoted."""
        self._metrics.total_promotions += 1
        self._update_rates()
        self._persist()

    def record_rejection(self) -> None:
        """Record that an evolution was rejected."""
        self._metrics.total_rejections += 1
        self._update_rates()
        self._persist()

    def record_false_positive(self) -> None:
        """Record that a promoted evolution turned out worse."""
        self._metrics.false_positives += 1
        self._update_rates()
        self._persist()

    def record_false_negative(self) -> None:
        """Record that a rejected evolution would have been beneficial."""
        self._metrics.false_negatives += 1
        self._update_rates()
        self._persist()

    def check_calibration(self) -> GapCalibrationAction:
        """Check if evaluation thresholds need recalibration.

        Only triggers after min_sample_size promotions.
        """
        if self._metrics.total_promotions < self._min_sample:
            return GapCalibrationAction.HOLD

        action = GapCalibrationAction.HOLD

        if self._metrics.fp_rate > self._fp_tighten:
            action = GapCalibrationAction.TIGHTEN
        elif self._metrics.fn_rate > self._fn_loosen:
            action = GapCalibrationAction.LOOSEN

        if action != GapCalibrationAction.HOLD:
            self._metrics.last_calibration_action = action
            self._metrics.threshold_adjustments += 1
            self._persist()
            logger.info(
                f"Gap calibration: {action} "
                f"(FP rate={self._metrics.fp_rate:.2f}, "
                f"FN rate={self._metrics.fn_rate:.2f})"
            )

        return action

    def apply_calibration(self, action: GapCalibrationAction) -> float:
        """Apply a calibration action to the promote_threshold.

        FM-P8-024: Enforces promote_threshold > hold_threshold.

        Args:
            action: TIGHTEN or LOOSEN.

        Returns:
            The new promote_threshold value.

        Raises:
            ValueError: If action is HOLD (no-op).
        """
        if action == GapCalibrationAction.HOLD:
            raise ValueError("Cannot apply HOLD action — it's a no-op")

        config_raw = self.yaml_store.read_raw("core/evolution.yaml")
        current = float(config_raw["evolution"]["evaluation"]["promote_threshold"])

        if action == GapCalibrationAction.TIGHTEN:
            new_threshold = min(current + self._threshold_step, self._max_promote)
        else:  # LOOSEN
            new_threshold = max(current - self._threshold_step, self._min_promote)

        # FM-P8-024: Enforce promote_threshold > hold_threshold
        hold_threshold = float(
            config_raw["evolution"]["evaluation"]["hold_threshold"]
        )
        if new_threshold <= hold_threshold:
            logger.warning(
                f"Calibrated promote_threshold {new_threshold:.2f} would be "
                f"<= hold_threshold {hold_threshold:.2f}. Clamping to "
                f"hold_threshold + {self._threshold_step}"
            )
            new_threshold = hold_threshold + self._threshold_step

        config_raw["evolution"]["evaluation"]["promote_threshold"] = new_threshold
        self.yaml_store.write_raw("core/evolution.yaml", config_raw)

        logger.info(
            f"Threshold adjusted: {current:.2f} → {new_threshold:.2f} ({action})"
        )
        return new_threshold

    def get_metrics(self) -> GapMetrics:
        """Return current gap metrics (copy)."""
        return self._metrics.model_copy()

    def _update_rates(self) -> None:
        """Recompute FP/FN rates from counts."""
        if self._metrics.total_promotions > 0:
            self._metrics.fp_rate = (
                self._metrics.false_positives / self._metrics.total_promotions
            )
        else:
            self._metrics.fp_rate = 0.0

        if self._metrics.total_rejections > 0:
            self._metrics.fn_rate = (
                self._metrics.false_negatives / self._metrics.total_rejections
            )
        else:
            self._metrics.fn_rate = 0.0

    def _persist(self) -> None:
        """Persist metrics to YAML."""
        self.yaml_store.write(self._metrics_path, self._metrics)

    def _load_metrics(self) -> GapMetrics:
        """Load metrics from YAML or create fresh.

        FM-119 pattern: broad exception acceptable for STATE loading.
        FM-P8-016: Catches corruption in addition to FileNotFoundError.
        """
        try:
            data = self.yaml_store.read_raw(self._metrics_path)
            return GapMetrics.model_validate(data, strict=False)
        except FileNotFoundError:
            return GapMetrics()
        except (yaml.YAMLError, ValidationError, TypeError, KeyError) as e:
            logger.error(
                f"Gap metrics file corrupted at {self._metrics_path}: {e}. "
                f"Starting with fresh metrics. Old file will be overwritten "
                f"on next persist."
            )
            return GapMetrics()
