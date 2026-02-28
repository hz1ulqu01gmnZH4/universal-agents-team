"""4-layer resource awareness stack.
Spec reference: Section 18 (Resource Awareness & Self-Budgeting)."""
from __future__ import annotations

import re
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

from ..models.resource import (
    BudgetPressureLevel,
    ComputeMetrics,
    CostApproval,
    RateLimitBucket,
    RateLimitMirror,
    SpendLevel,
    TokenBudget,
)
from ..state.yaml_store import YamlStore


# Cold-start seeds for token estimation (Section 18.2)
COLD_SEEDS: dict[str, int] = {
    "simple_fix": 2_000,
    "feature_small": 8_000,
    "feature_medium": 25_000,
    "feature_large": 80_000,
    "research": 15_000,
    "review": 5_000,
}


class ResourceTracker:
    """4-layer resource awareness: compute, rate limits, token budget, cost decisions.

    Token estimation strategy:
    - Primary: parse /usage output from a secondary Claude Code shell (I8)
    - Fallback: character-ratio estimation (3.5 chars/token English)
    - Rolling average replaces cold seeds after 10 samples (P4)
    """

    def __init__(self, yaml_store: YamlStore, state_dir: Path):
        self.yaml_store = yaml_store
        self.state_dir = state_dir
        self._token_history: deque[tuple[str, int]] = deque(maxlen=100)
        self._chars_per_token: float = 3.5  # Calibrated over time

    # ── Layer 1: Compute ──

    def check_compute(self) -> ComputeMetrics:
        """Read CPU/memory/disk via psutil. No fallbacks."""
        import psutil

        return ComputeMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage("/").percent,
            active_agents=self._count_active_agents(),
            max_agents=5,  # From framework.yaml
        )

    def can_spawn_agent(self) -> tuple[bool, str]:
        """Pre-spawn resource check with 20% headroom (G1)."""
        metrics = self.check_compute()
        if metrics.cpu_percent > 80:
            return False, f"CPU too high: {metrics.cpu_percent}%"
        if metrics.memory_percent > 80:
            return False, f"Memory too high: {metrics.memory_percent}%"
        if metrics.disk_percent > 90:
            return False, f"Disk too high: {metrics.disk_percent}%"
        if metrics.active_agents >= metrics.max_agents:
            return False, f"At agent cap: {metrics.active_agents}/{metrics.max_agents}"
        return True, "Resources available"

    # ── Layer 2: Rate Limits ──

    def update_rate_mirror(self, tokens_consumed: int) -> None:
        """Update local rate limit mirror after API call."""
        # Reads from state/resources/rate-limits.yaml, updates counts
        pass  # Full implementation in Phase 1

    def get_backpressure_level(self) -> float:
        """0.0 = no pressure, 1.0 = at limit."""
        return 0.0  # Phase 0: no rate tracking

    # ── Layer 3: Token Budget ──

    def estimate_task_cost(self, task_type: str, complexity: str = "medium") -> int:
        """Estimate token cost for a task type.
        Uses rolling average if available, cold seeds otherwise."""
        key = f"{task_type}_{complexity}" if complexity else task_type
        # Check history for this task type
        matching = [t for label, t in self._token_history if label == key]
        if len(matching) >= 3:
            return int(sum(matching) / len(matching))
        # Fall back to cold seeds
        return COLD_SEEDS.get(key, COLD_SEEDS.get(task_type, 10_000))

    def record_actual_usage(self, task_type: str, tokens_used: int) -> None:
        """Record actual token usage for calibration."""
        self._token_history.append((task_type, tokens_used))
        # Recalibrate chars_per_token if we have /usage data
        self._maybe_recalibrate()

    def parse_usage_output(self) -> dict | None:
        """Parse /usage command output from Claude Code shell.
        Primary token tracking method (user-discovered).
        Returns dict with token counts or None if parsing fails (I8)."""
        try:
            result = subprocess.run(
                ["claude", "-p", "/usage"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None
            return self._parse_usage_text(result.stdout)
        except Exception:
            return None  # Fall back to estimation

    @staticmethod
    def _parse_usage_text(text: str) -> dict | None:
        """Parse /usage output text into structured data.
        Format may change between Claude Code versions (I8)."""
        data: dict = {}
        # Look for common patterns in /usage output
        patterns = {
            "input_tokens": r"[Ii]nput\s+tokens?:\s*([0-9,]+)",
            "output_tokens": r"[Oo]utput\s+tokens?:\s*([0-9,]+)",
            "total_cost": r"[Cc]ost:\s*\$([0-9.]+)",
            "cache_read": r"[Cc]ache\s+read:\s*([0-9,]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                val = match.group(1).replace(",", "")
                data[key] = float(val) if "." in val else int(val)
        return data if data else None

    # ── Layer 4: Cost Decisions ──

    def check_spend_level(self, estimated_cost: float) -> SpendLevel:
        """Classify cost into spend levels."""
        if estimated_cost <= 0:
            return SpendLevel.FREE
        if estimated_cost < 0.10:
            return SpendLevel.LOW
        if estimated_cost < 10.0:
            return SpendLevel.MEDIUM
        return SpendLevel.HIGH

    # ── Internal ──

    def _count_active_agents(self) -> int:
        """Count active agents from registry files."""
        agents_dir = self.state_dir / "agents"
        if not agents_dir.exists():
            return 0
        return sum(1 for _ in agents_dir.glob("*/status.yaml"))

    def _maybe_recalibrate(self) -> None:
        """Recalibrate chars_per_token ratio against /usage data (P4)."""
        usage = self.parse_usage_output()
        if usage and "input_tokens" in usage:
            # We'd need to correlate with known text lengths
            # Full implementation deferred to Phase 1
            pass
