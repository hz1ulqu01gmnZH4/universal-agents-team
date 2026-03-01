"""Fingerprint storage, comparison, and drift detection.
Spec reference: Section 19.1 (Model Fingerprinting — drift_detection).

Stores fingerprint history, computes Euclidean distance between current
and baseline (median of last N), flags drift when distance > threshold.
Also tracks Claude Code version changes.

Key design decisions:
- Baseline is median of last N fingerprints (not just last one) — smooths noise
- Per-dimension delta reported for targeted revalidation
- Version comparison is zero-cost (subprocess, no tokens)
"""
from __future__ import annotations

import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.environment import (
    DriftDetection,
    ModelFingerprint,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.drift_detector")


class DriftDetector:
    """Detects model capability drift and version changes.

    Design invariants:
    - Fingerprint history limited to `history_size` entries (bounded storage)
    - Baseline computed as per-dimension median of last `baseline_window` fingerprints
    - Version info persisted and compared at every session start
    - All state persisted to YAML via YamlStore
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)
        self.yaml_store.ensure_dir(f"{self._state_base}/fingerprints")

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        dd = ea.get("drift_detection", {})
        self._threshold = float(dd.get("threshold", 0.15))
        self._history_size = int(dd.get("history_size", 10))
        self._baseline_window = int(dd.get("baseline_window", 5))
        self._per_dim_alert = float(dd.get("per_dimension_alert", 0.10))

        vt = ea.get("version_tracking", {})
        self._version_command = str(vt.get("version_command", "claude --version"))
        self._version_timeout = int(vt.get("version_timeout_seconds", 5))

    def store_fingerprint(self, fingerprint: ModelFingerprint) -> None:
        """Store a fingerprint to history. Trims to history_size.

        IFM-01: Appends generate_id() suffix for collision avoidance.
        MF-6/IFM-02: last-fingerprint.yaml stored in state dir, not core/.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("fp").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/fingerprints/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, fingerprint)

        # Trim old fingerprints if exceeding history_size
        self._trim_history()

        # MF-6/IFM-02: Write to state dir, not core/ (which is read-only config)
        self.yaml_store.write_raw(
            f"{self._state_base}/last-fingerprint.yaml",
            {
                "timestamp": fingerprint.created_at.isoformat(),
                "claude_version": self.check_claude_version(),
                "path": path,
            },
        )

    def load_fingerprint_history(self) -> list[ModelFingerprint]:
        """Load all stored fingerprints, sorted chronologically (oldest first)."""
        fp_dir = f"{self._state_base}/fingerprints"
        try:
            files = self.yaml_store.list_dir(fp_dir)
        except (NotADirectoryError, FileNotFoundError):
            return []
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        fingerprints: list[ModelFingerprint] = []
        for fname in yaml_files:
            try:
                fp = self.yaml_store.read(f"{fp_dir}/{fname}", ModelFingerprint)
                fingerprints.append(fp)
            except Exception as e:
                logger.warning(f"Skipping corrupt fingerprint {fname}: {e}")
        return fingerprints

    def compute_baseline(self, history: list[ModelFingerprint]) -> ModelFingerprint | None:
        """Compute baseline fingerprint as per-dimension median of last N.

        Returns None if history is empty.
        """
        if not history:
            return None

        window = history[-self._baseline_window:]
        if not window:
            return None

        # Compute median for each dimension
        def median(values: list[float]) -> float:
            s = sorted(values)
            n = len(s)
            if n % 2 == 1:
                return s[n // 2]
            return (s[n // 2 - 1] + s[n // 2]) / 2

        reasoning_scores = [fp.reasoning_score for fp in window]
        instruction_scores = [fp.instruction_score for fp in window]
        code_scores = [fp.code_score for fp in window]
        creative_scores = [fp.creative_score for fp in window]
        tool_scores = [fp.tool_score for fp in window]
        latencies = [fp.avg_latency_ms for fp in window]
        output_tokens = [fp.avg_output_tokens for fp in window]

        return ModelFingerprint(
            created_at=datetime.now(timezone.utc),
            model_id=window[-1].model_id,  # Use most recent model_id
            reasoning_score=median(reasoning_scores),
            instruction_score=median(instruction_scores),
            code_score=median(code_scores),
            creative_score=median(creative_scores),
            tool_score=median(tool_scores),
            avg_latency_ms=int(median([float(x) for x in latencies])),
            avg_output_tokens=int(median([float(x) for x in output_tokens])),
        )

    def detect_drift(self, current: ModelFingerprint) -> DriftDetection:
        """Compare current fingerprint against stored baseline.

        If no history exists, baseline is the current fingerprint itself
        (distance = 0, no drift detected).

        IFM-10: Suppresses drift detection when history has fewer entries
        than baseline_window to prevent false alarms on early sessions.
        """
        history = self.load_fingerprint_history()
        baseline = self.compute_baseline(history)

        if baseline is None:
            # First run — no baseline, no drift
            return DriftDetection(
                current=current,
                baseline=current,
                distance=0.0,
                threshold=self._threshold,
                drift_detected=False,
                affected_dimensions=[],
            )

        distance = current.distance_to(baseline)
        deltas = current.per_dimension_delta(baseline)

        # Identify affected dimensions
        affected: list[str] = []
        for dim_name, delta in deltas.items():
            if abs(delta) > self._per_dim_alert:
                affected.append(dim_name)

        drift_detected = distance > self._threshold

        # IFM-10: Suppress false drift alarms when insufficient history.
        # With fewer than baseline_window fingerprints, the baseline is
        # statistically unreliable and would cause false alarms on the
        # second session.
        if len(history) < self._baseline_window:
            drift_detected = False

        if drift_detected:
            logger.warning(
                f"Model drift detected: distance={distance:.4f} "
                f"(threshold={self._threshold}), "
                f"affected_dimensions={affected}"
            )
        else:
            logger.info(
                f"No drift: distance={distance:.4f} "
                f"(threshold={self._threshold})"
            )

        return DriftDetection(
            current=current,
            baseline=baseline,
            distance=distance,
            threshold=self._threshold,
            drift_detected=drift_detected,
            affected_dimensions=affected,
        )

    def check_version(self) -> tuple[VersionInfo, list[str]]:
        """Check current environment version and compare to stored version.

        Returns:
            Tuple of (current VersionInfo, list of changed fields).
            Changed fields is empty if no previous version stored.
        """
        current = VersionInfo(
            claude_code_version=self.check_claude_version(),
            python_version=platform.python_version(),
            os_info=f"{platform.system()} {platform.release()}",
            timestamp=datetime.now(timezone.utc),
        )

        # Load previous version
        # IFM-19: Catch all exceptions (FileNotFoundError on first run,
        # ValidationError on schema change, yaml.ScannerError on corruption).
        version_path = f"{self._state_base}/version-info.yaml"
        changes: list[str] = []
        try:
            previous = self.yaml_store.read(version_path, VersionInfo)
            changes = current.differs_from(previous)
            if changes:
                logger.warning(
                    f"Version changes detected: {changes}. "
                    f"Previous: {previous.claude_code_version}, "
                    f"Current: {current.claude_code_version}"
                )
        except FileNotFoundError:
            logger.info("No previous version info — first run")
        except Exception as e:
            logger.warning(
                f"Could not load previous version info, treating as first run: "
                f"{type(e).__name__}: {e}"
            )

        # Store current version
        self.yaml_store.write(version_path, current)

        return current, changes

    def check_claude_version(self) -> str:
        """Get Claude Code version string via subprocess."""
        parts = self._version_command.split()
        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=self._version_timeout,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _trim_history(self) -> None:
        """Remove oldest fingerprints exceeding history_size."""
        fp_dir = f"{self._state_base}/fingerprints"
        try:
            files = self.yaml_store.list_dir(fp_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > self._history_size:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{fp_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)
