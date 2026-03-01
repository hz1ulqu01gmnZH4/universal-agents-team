"""Self-capability assessment and knowledge boundary mapping.
Spec reference: Section 13 (Self-Capability Awareness).

Maintains a persistent map of {task_type → performance record} updated
after each task completion. Identifies blind spots (task types never
attempted) and tracks success rates for self-awareness.

Literature basis:
- Knowledge boundary awareness (Li et al. 2024, arXiv:2412.12472)
- LLMs lack stable self-knowledge (arXiv:2503.02233)
- "Know Your Limits" — abstention as safety mechanism (TACL)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.self_assessment import CapabilityMap, CapabilityMapEntry
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.capability_tracker")

# All known task types from Orchestrator._classify_task_type()
ALL_KNOWN_TASK_TYPES = [
    "canary_suite",
    "evolution_proposal",
    "decomposition",
    "skill_validation",
    "review",
    "simple_fix",
    "research",
    "feature",
]


class CapabilityTracker:
    """Tracks framework capabilities via empirical task outcomes.

    Responsibilities:
    1. Record task outcomes (success/failure, tokens used, review scores)
    2. Maintain capability map (task_type → performance stats)
    3. Identify blind spots (task types never attempted)
    4. Provide capability queries for orchestration decisions

    Persisted at: state/self-assessment/capability-map.yaml
    Updated: after every task reaches COMPLETE or VERDICT(fail) status.
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._assessment_base = f"instances/{domain}/state/self-assessment"
        yaml_store.ensure_dir(self._assessment_base)
        self._capability_map = self._load_map()

    def record_outcome(
        self,
        task_type: str,
        success: bool,
        tokens_used: int,
        review_confidence: float = 0.0,
    ) -> CapabilityMapEntry:
        """Record a task outcome and update the capability map.

        Args:
            task_type: From Orchestrator._classify_task_type().
            success: True if review verdict was "pass" or "pass_with_notes".
            tokens_used: Total tokens consumed by the task.
            review_confidence: Reviewer's confidence score (0-1).

        Returns:
            Updated CapabilityMapEntry for this task type.
        """
        entry = self._capability_map.get_entry(task_type)
        entry.attempts += 1

        if success:
            entry.successes += 1
        else:
            entry.failures += 1

        # FM-87: Only update token average when tokens_used > 0
        # (tokens_used may be 0 if not populated by caller)
        if tokens_used > 0:
            entry.token_count += 1
            n_tok = entry.token_count
            entry.avg_tokens = (
                (entry.avg_tokens * (n_tok - 1) + tokens_used) / n_tok
            )

        # FM-93: Only update confidence average when confidence > 0,
        # using separate confidence_count to avoid denominator dilution.
        if review_confidence > 0:
            entry.confidence_count += 1
            n_conf = entry.confidence_count
            entry.avg_review_confidence = (
                (entry.avg_review_confidence * (n_conf - 1) + review_confidence) / n_conf
            )
        entry.last_updated = datetime.now(timezone.utc)

        # Update blind spots
        self._update_blind_spots()

        # Persist
        self._save_map()

        logger.info(
            f"Capability updated: {task_type} — "
            f"success_rate={entry.success_rate:.2f} "
            f"({entry.successes}/{entry.attempts}), "
            f"avg_tokens={entry.avg_tokens:.0f}"
        )

        return entry

    def get_capability(self, task_type: str) -> CapabilityMapEntry:
        """Get capability data for a task type."""
        return self._capability_map.get_entry(task_type)

    def get_success_rate(self, task_type: str) -> float:
        """Get success rate for a task type. Returns 0.0 if never attempted."""
        entry = self._capability_map.entries.get(task_type)
        if entry is None:
            return 0.0
        return entry.success_rate

    def get_blind_spots(self) -> list[str]:
        """Return task types that have never been attempted."""
        return list(self._capability_map.blind_spots)

    def get_weak_areas(self, threshold: float = 0.5) -> list[CapabilityMapEntry]:
        """Return task types with success rate below threshold.

        Only includes types with at least 3 attempts (avoid noise).
        """
        weak: list[CapabilityMapEntry] = []
        for entry in self._capability_map.entries.values():
            if entry.attempts >= 3 and entry.success_rate < threshold:
                weak.append(entry)
        return sorted(weak, key=lambda e: e.success_rate)

    def get_full_map(self) -> CapabilityMap:
        """Return the complete capability map."""
        return self._capability_map

    def get_estimated_complexity(self, task_type: str) -> str | None:
        """FM-41 Phase 2: Classify complexity based on historical token data.

        If we have enough data (10+ samples for this task type), use the
        average token consumption to classify complexity:
        - avg_tokens < 5000: "small"
        - avg_tokens < 20000: "medium"
        - avg_tokens >= 20000: "large"

        Returns None if insufficient data (caller should fall back to heuristic).
        FM-109: Returns None (not empty string) for consistent API behavior.
        """
        entry = self._capability_map.entries.get(task_type)
        if entry is None or entry.token_count < 10:
            return None  # FM-109: None, not "" — consistent with docstring
        if entry.avg_tokens < 5000:
            return "small"
        if entry.avg_tokens < 20000:
            return "medium"
        return "large"

    def _update_blind_spots(self) -> None:
        """Recalculate blind spots list."""
        attempted = set(self._capability_map.entries.keys())
        self._capability_map.blind_spots = [
            t for t in ALL_KNOWN_TASK_TYPES if t not in attempted
        ]

    def _load_map(self) -> CapabilityMap:
        """Load capability map from YAML or create new.

        FM-119: Catches all exceptions (FileNotFoundError on first run,
        yaml.ScannerError on corrupt YAML, ValidationError on schema mismatch).
        """
        path = f"{self._assessment_base}/capability-map.yaml"
        try:
            return self.yaml_store.read(path, CapabilityMap)
        except Exception as e:
            # FM-119: Corrupt/missing YAML — start fresh
            if not isinstance(e, FileNotFoundError):
                logger.warning(f"Corrupt capability map, resetting to empty: {e}")
            cap_map = CapabilityMap()
            cap_map.blind_spots = list(ALL_KNOWN_TASK_TYPES)
            return cap_map

    def _save_map(self) -> None:
        """Persist capability map to YAML."""
        self._capability_map.last_analysis = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._assessment_base}/capability-map.yaml",
            self._capability_map,
        )
