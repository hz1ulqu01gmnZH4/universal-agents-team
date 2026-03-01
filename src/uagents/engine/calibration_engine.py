"""Confidence calibration and generation-verification gap monitoring.
Spec reference: Section 13.2 (Confidence Calibration), Section 13.3 (Gap Monitoring).

Tracks predicted vs actual improvement for each evolution cycle.
Computes rolling ECE. Triggers overcalibration response when ECE > 0.15.

Literature basis:
- Huang et al. 2025 (arXiv:2504.02902): ECE rises without iterative calibration
- Song et al. 2024 (arXiv:2412.02674): generation-verification gap bounds improvement
- Anthropic 2025 (arXiv:2601.01828): LLM introspection ~20% reliable
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.self_assessment import CalibrationRecord, CalibrationState, GapAssessment
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.calibration_engine")

# Calibration thresholds
ECE_ALERT_THRESHOLD = 0.15          # Rolling ECE above this triggers response
ECE_WINDOW_SIZE = 10                # Rolling window for ECE computation
GAP_MINIMUM_THRESHOLD = 0.05        # Min gap for reliable self-improvement
CONFIDENCE_DEFLATION_RATE = 0.05    # How much to deflate per overcalibrated cycle
FALSE_POSITIVE_THRESHOLD = 0.10     # > 10% false positives → tighten criteria
FALSE_NEGATIVE_THRESHOLD = 0.30     # > 30% false negatives → loosen criteria


class CalibrationEngine:
    """Tracks confidence calibration across evolution cycles.

    Phase 2 is read-only: it records and measures but does not block evolutions.
    Phase 4+ will use calibration data to gate evolution proposals.

    Usage:
        engine = CalibrationEngine(yaml_store)
        engine.record_prediction(evolution_id, confidence=0.8)
        # ... after evaluation ...
        engine.record_outcome(evolution_id, actual_improvement=0.3)
        state = engine.get_state()
        # state.ece_alert → True if systematic overconfidence
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._assessment_base = f"instances/{domain}/state/self-assessment"
        yaml_store.ensure_dir(self._assessment_base)
        self._state = self._load_state()

    def record_prediction(
        self, evolution_id: str, confidence: float
    ) -> CalibrationRecord:
        """Record predicted confidence before an evolution is applied.

        Args:
            evolution_id: ID of the evolution proposal.
            confidence: Predicted confidence that this improves things (0-1).
                        Deflated by current confidence_deflation factor.
        """
        # Apply deflation to the raw confidence
        deflated = max(0.0, confidence - self._state.confidence_deflation)

        record = CalibrationRecord(
            evolution_id=evolution_id,
            predicted_confidence=deflated,
            timestamp=datetime.now(timezone.utc),
        )
        self._state.records.append(record)
        self._save_state()

        logger.info(
            f"Calibration prediction: evo={evolution_id}, "
            f"raw_confidence={confidence:.3f}, "
            f"deflated={deflated:.3f} "
            f"(deflation={self._state.confidence_deflation:.3f})"
        )

        return record

    def record_outcome(
        self, evolution_id: str, actual_improvement: float
    ) -> CalibrationRecord | None:
        """Record actual improvement after evaluation.

        Args:
            evolution_id: ID of the evolution proposal.
            actual_improvement: Measured delta on benchmark (can be negative).

        Returns:
            Updated CalibrationRecord, or None if evolution_id not found.
        """
        # Find the matching record
        record = None
        for r in reversed(self._state.records):
            if r.evolution_id == evolution_id:
                record = r
                break

        if record is None:
            logger.warning(
                f"No prediction found for evolution {evolution_id}. "
                f"Cannot compute calibration error."
            )
            return None

        record.actual_improvement = actual_improvement

        # M-7/FM-95: ECE uses binary success comparison, not raw magnitude.
        # Standard ECE: |predicted_probability - observed_frequency|
        # predicted_confidence = P(improvement > 0)
        # actual_outcome = 1.0 if improvement > 0 else 0.0
        actual_success = 1.0 if actual_improvement > 0 else 0.0
        record.calibration_error = record.predicted_confidence - actual_success

        # Update overcalibration tracking
        if record.calibration_error > 0:
            self._state.overcalibration_streak += 1
            self._state.undercalibration_streak = 0  # FM-108: reset opposite
        elif record.calibration_error < 0:
            self._state.undercalibration_streak += 1  # FM-108: track undercalibration
            self._state.overcalibration_streak = 0
        else:
            self._state.overcalibration_streak = 0
            self._state.undercalibration_streak = 0

        # Recompute rolling ECE
        self._recompute_ece()

        # Check if overcalibration response needed
        if self._state.ece_alert:
            self._apply_overcalibration_response()

        self._save_state()

        logger.info(
            f"Calibration outcome: evo={evolution_id}, "
            f"predicted={record.predicted_confidence:.3f}, "
            f"actual={actual_improvement:.3f}, "
            f"error={record.calibration_error:.3f}, "
            f"running_ECE={self._state.running_ece:.3f}"
        )

        return record

    def get_state(self) -> CalibrationState:
        """Get current calibration state."""
        return self._state

    def compute_gap_assessment(
        self,
        verifier_accuracy: float,
        generator_accuracy: float,
        benchmark_task_count: int,
    ) -> GapAssessment:
        """Compute generation-verification gap assessment.

        Song et al. 2024: self-improvement is bounded by this gap.
        If gap < 0.05, self-improvement from this source is unreliable.
        """
        assessment = GapAssessment(
            verifier_accuracy=verifier_accuracy,
            generator_accuracy=generator_accuracy,
            assessment_date=datetime.now(timezone.utc),
            benchmark_task_count=benchmark_task_count,
        )

        # Persist latest assessment
        self.yaml_store.write(
            f"{self._assessment_base}/gap-assessment.yaml",
            assessment,
        )

        if not assessment.self_improvement_reliable:
            logger.warning(
                f"Generation-verification gap too small: "
                f"{assessment.gap_score:.3f} < {GAP_MINIMUM_THRESHOLD}. "
                f"Self-improvement from this capability source is unreliable."
            )

        return assessment

    def get_false_positive_rate(self) -> float:
        """Compute false positive rate: approved changes that turned out worse.

        A false positive is a record where predicted_confidence > evidence_threshold
        but actual_improvement <= 0.
        """
        completed = [r for r in self._state.records if r.actual_improvement is not None]
        if not completed:
            return 0.0

        approved = [
            r for r in completed
            if r.predicted_confidence >= self._state.evidence_threshold
        ]
        if not approved:
            return 0.0

        false_positives = sum(
            1 for r in approved if r.actual_improvement <= 0
        )
        return false_positives / len(approved)

    def get_false_negative_rate(self) -> float:
        """Compute false negative rate: rejected changes that would have helped.

        A false negative is a record where predicted_confidence < evidence_threshold
        but actual_improvement > 0.
        """
        completed = [r for r in self._state.records if r.actual_improvement is not None]
        if not completed:
            return 0.0

        rejected = [
            r for r in completed
            if r.predicted_confidence < self._state.evidence_threshold
        ]
        if not rejected:
            return 0.0

        false_negatives = sum(
            1 for r in rejected if r.actual_improvement > 0
        )
        return false_negatives / len(rejected)

    def _recompute_ece(self) -> None:
        """Recompute rolling ECE from the last ECE_WINDOW_SIZE completed records."""
        completed = [
            r for r in self._state.records
            if r.calibration_error is not None
        ]
        recent = completed[-ECE_WINDOW_SIZE:]
        if not recent:
            self._state.running_ece = 0.0
            return

        # ECE = mean of absolute calibration errors
        self._state.running_ece = sum(
            abs(r.calibration_error) for r in recent
        ) / len(recent)

    def _apply_overcalibration_response(self) -> None:
        """Respond to systematic overconfidence (Section 13.2).

        M-9/FM-94: Removed unconditional evidence_threshold increment.
        Threshold adjustment is now SOLELY based on FP/FN rate analysis,
        preventing the double-increment ratcheting problem.

        FM-108: Also checks for systematic undercalibration and can
        decrease confidence_deflation to allow recovery from over-correction.
        """
        self._state.overcalibrated = True
        self._state.confidence_deflation += CONFIDENCE_DEFLATION_RATE

        logger.warning(
            f"Overcalibration response triggered: "
            f"ECE={self._state.running_ece:.3f} > {ECE_ALERT_THRESHOLD}. "
            f"Deflation now={self._state.confidence_deflation:.3f}, "
            f"evidence_threshold={self._state.evidence_threshold:.3f}"
        )

        # M-9: FP/FN rate checks are the SOLE mechanism for threshold adjustment
        fp_rate = self.get_false_positive_rate()
        fn_rate = self.get_false_negative_rate()

        if fp_rate > FALSE_POSITIVE_THRESHOLD:
            self._state.evidence_threshold = min(
                0.9, self._state.evidence_threshold + 0.05
            )
            logger.warning(
                f"False positive rate {fp_rate:.2f} > {FALSE_POSITIVE_THRESHOLD}. "
                f"Tightening evidence threshold to {self._state.evidence_threshold:.2f}."
            )
        elif fn_rate > FALSE_NEGATIVE_THRESHOLD:
            # M-9: elif, not if — FP and FN adjustments are mutually exclusive
            self._state.evidence_threshold = max(
                0.3, self._state.evidence_threshold - 0.05
            )
            # FM-108: Also reduce confidence_deflation to allow recovery
            self._state.confidence_deflation = max(
                0.0, self._state.confidence_deflation - CONFIDENCE_DEFLATION_RATE
            )
            logger.info(
                f"False negative rate {fn_rate:.2f} > {FALSE_NEGATIVE_THRESHOLD}. "
                f"Loosening evidence threshold to {self._state.evidence_threshold:.2f}, "
                f"deflation to {self._state.confidence_deflation:.3f}."
            )

    def _load_state(self) -> CalibrationState:
        """Load calibration state from YAML or create new.

        FM-119: Catches all exceptions (FileNotFoundError on first run,
        yaml.ScannerError on corrupt YAML, ValidationError on schema mismatch).
        """
        path = f"{self._assessment_base}/calibration.yaml"
        try:
            return self.yaml_store.read(path, CalibrationState)
        except Exception as e:
            # FM-119: Corrupt/missing YAML — start fresh
            if not isinstance(e, FileNotFoundError):
                logger.warning(f"Corrupt calibration state, resetting: {e}")
            return CalibrationState()

    def _save_state(self) -> None:
        """Persist calibration state to YAML.

        FM-86: Trims records to last 100 entries before saving to prevent
        unbounded growth that would crash at YamlStore's 1MB size cap.
        """
        # FM-86: Cap records to prevent unbounded growth
        if len(self._state.records) > 100:
            self._state.records = self._state.records[-100:]

        self.yaml_store.write(
            f"{self._assessment_base}/calibration.yaml",
            self._state,
        )
