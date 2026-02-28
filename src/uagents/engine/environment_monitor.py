"""Model fingerprinting and drift detection.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking)."""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from ..models.environment import CanaryResult, DriftDetection, ModelFingerprint
from ..state.yaml_store import YamlStore


class EnvironmentMonitor:
    """Canary suite runner, model fingerprinting, drift detection.

    Phase 0: basic canary suite with 5 micro-benchmarks.
    Phase 1+: full fingerprinting with 20+ tasks, behavioral probes.
    """

    DRIFT_THRESHOLD = 0.15  # 15% deviation triggers investigation

    def __init__(self, yaml_store: YamlStore, canary_dir: Path):
        self.yaml_store = yaml_store
        self.canary_dir = canary_dir

    def should_run_canary(self) -> bool:
        """Skip if last fingerprint < 5 hours old AND Claude version unchanged."""
        try:
            data = self.yaml_store.read_raw("core/last-fingerprint.yaml")
            last_run = datetime.fromisoformat(data.get("timestamp", ""))
            elapsed = (datetime.utcnow() - last_run).total_seconds()
            if elapsed < 5 * 3600:  # 5 hours
                stored_version = data.get("claude_version", "")
                current_version = self.check_claude_version()
                if stored_version == current_version:
                    return False
        except (FileNotFoundError, ValueError, KeyError):
            pass
        return True

    def run_canary_suite(self) -> list[CanaryResult]:
        """Execute fixed micro-benchmark tasks."""
        # Phase 0: placeholder canary tasks
        # Each task is a known-answer prompt
        results: list[CanaryResult] = []
        canary_tasks = [
            ("arithmetic", "What is 7 * 8?", "56"),
            ("logic", "If all A are B and all B are C, are all A C?", "yes"),
            ("code", "Write a Python function to reverse a string", "def"),
            ("reasoning", "What comes next: 2, 4, 8, 16, ?", "32"),
            ("instruction", "Reply with exactly the word: ACKNOWLEDGED", "ACKNOWLEDGED"),
        ]
        for name, prompt, expected in canary_tasks:
            results.append(CanaryResult(
                task_name=name,
                expected=expected,
                actual="",  # Filled by actual execution
                score=0.0,
                tokens_used=0,
                latency_ms=0,
            ))
        return results

    def compute_fingerprint(self, results: list[CanaryResult]) -> ModelFingerprint:
        """Build fingerprint from canary results."""
        scores = {r.task_name: r.score for r in results}
        return ModelFingerprint(
            created_at=datetime.utcnow(),
            model_id="claude-opus-4-6",
            reasoning_score=scores.get("reasoning", 0.0),
            instruction_score=scores.get("instruction", 0.0),
            code_score=scores.get("code", 0.0),
            creative_score=0.5,  # No creative canary in Phase 0
            tool_score=0.5,      # No tool canary in Phase 0
            avg_latency_ms=int(sum(r.latency_ms for r in results) / max(len(results), 1)),
            avg_output_tokens=int(sum(r.tokens_used for r in results) / max(len(results), 1)),
        )

    def detect_drift(self, current: ModelFingerprint) -> DriftDetection:
        """Compare current fingerprint against stored baselines."""
        # Load last 5 fingerprints for comparison
        baseline = current  # Phase 0: compare against self
        distance = current.distance_to(baseline)
        affected: list[str] = []

        return DriftDetection(
            current=current,
            baseline=baseline,
            distance=distance,
            threshold=self.DRIFT_THRESHOLD,
            drift_detected=distance > self.DRIFT_THRESHOLD,
            affected_dimensions=affected,
        )

    @staticmethod
    def check_claude_version() -> str:
        """Get Claude Code version string."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
