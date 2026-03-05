"""Multi-level stagnation detection.
Spec reference: Section 10.2 (Stagnation Detection).

Monitors 4 levels:
- Agent: single agent repeating itself (cosine > 0.9 for 3 outputs)
- Voice: all agents using same tone for 5+ tasks; VDI < 0.2 for 3 tasks
- Team: SRD < 0.4 for 3 consecutive tasks
- Framework: no Tier 2+ evolution in 10 tasks; same topology for 10 tasks

Literature basis:
- DoT problem: LLMs cannot self-correct once confident (Liang et al. 2023)
- Content homogenization: multi-agent interaction paradoxically reduces diversity (Li et al. 2026)
- k-means + entropy for quantitative diversity detection (Yang et al. 2025)
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone

from ..models.diversity import (
    SRDMeasurement,
    StagnationLevel,
    StagnationSignal,
    VDIMeasurement,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.stagnation_detector")

# Thresholds from Section 10.2
AGENT_SIMILARITY_THRESHOLD = 0.9   # Cosine > this = too similar
AGENT_CONSECUTIVE_THRESHOLD = 3    # 3 consecutive similar outputs
VOICE_SAME_TONE_THRESHOLD = 5      # 5+ tasks with identical tones
VDI_FLOOR = 0.2                    # VDI below this for 3 tasks
VDI_CONSECUTIVE_THRESHOLD = 3
SRD_STAGNATION_THRESHOLD = 0.4     # SRD below this for 3 tasks
SRD_CONSECUTIVE_THRESHOLD = 3
FRAMEWORK_EVOLUTION_THRESHOLD = 10  # No Tier 2+ evo in this many tasks
FRAMEWORK_TOPOLOGY_THRESHOLD = 10   # Same topology for this many tasks
ARCHIVE_STALENESS_THRESHOLD = 20    # No MAP-Elites cell replacement in this many tasks
# Phase 8: Single-fork evolution stall detection
SINGLE_FORK_STALL_THRESHOLD = 3     # N consecutive rejected evolutions → suggest population mode


class StagnationDetector:
    """Multi-level stagnation monitoring system.

    Maintains sliding windows of measurements and fires StagnationSignal
    objects when thresholds are breached. Signals are informational in
    Phase 2 — autonomous intervention is Phase 4+.

    Usage:
        detector = StagnationDetector(yaml_store)
        signals = detector.check_all(srd_measurement, topology_used)
        # signals is a list of StagnationSignal objects
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._stagnation_base = f"instances/{domain}/state/diversity/stagnation"
        yaml_store.ensure_dir(self._stagnation_base)

        # In-memory sliding windows (persisted to YAML for crash recovery)
        self._srd_history: deque[float] = deque(maxlen=20)
        self._vdi_history: deque[float] = deque(maxlen=20)
        self._topology_history: deque[str] = deque(maxlen=20)
        self._tone_history: deque[set[str]] = deque(maxlen=20)
        self._tasks_since_evolution: int = 0
        self._tasks_since_archive_update: int = 0
        # Phase 8: consecutive evolution rejections counter
        self._consecutive_rejections: int = 0

        # Load persisted state
        self._load_state()

    def check_all(
        self,
        srd: SRDMeasurement,
        topology_used: str | None = None,
        agent_tones: set[str] | None = None,
    ) -> list[StagnationSignal]:
        """Run all stagnation checks and return signals.

        Args:
            srd: The SRD measurement for the just-completed task.
            topology_used: The topology pattern selected for this task.
            agent_tones: Set of tone atom names used by agents on this task.

        Returns:
            List of StagnationSignal objects (may be empty).
        """
        signals: list[StagnationSignal] = []

        # Update histories
        self._srd_history.append(srd.composite_srd)
        if srd.vdi is not None:
            self._vdi_history.append(srd.vdi.vdi_score)
        if topology_used is not None:
            self._topology_history.append(topology_used)
        if agent_tones is not None:
            self._tone_history.append(agent_tones)
        self._tasks_since_evolution += 1
        self._tasks_since_archive_update += 1

        # Check team-level SRD stagnation
        team_signal = self._check_team_srd()
        if team_signal is not None:
            signals.append(team_signal)

        # Check voice-level stagnation
        voice_signals = self._check_voice_stagnation()
        signals.extend(voice_signals)

        # Check framework-level stagnation
        fw_signals = self._check_framework_stagnation()
        signals.extend(fw_signals)

        # Persist state
        self._save_state()

        if signals:
            for s in signals:
                logger.warning(
                    f"Stagnation detected [{s.level}]: {s.description} "
                    f"({s.metric_name}={s.metric_value:.3f}, threshold={s.threshold:.3f})"
                )

        return signals

    def check_agent_output_similarity(
        self,
        agent_id: str,
        current_output: str,
        recent_outputs: list[str],
    ) -> StagnationSignal | None:
        """Check if an agent is repeating itself (cosine > 0.9 for 3 outputs).

        This is called separately per-agent, not as part of check_all().
        Uses the same TF-IDF cosine distance as DiversityEngine.
        """
        if len(recent_outputs) < AGENT_CONSECUTIVE_THRESHOLD - 1:
            return None

        # S-5: Import public functions (no underscore prefix)
        from .diversity_engine import compute_idf, cosine_distance, tf_idf_vector, tokenize

        all_texts = recent_outputs[-(AGENT_CONSECUTIVE_THRESHOLD - 1):] + [current_output]
        tokenized = [tokenize(t) for t in all_texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tokens, idf) for tokens in tokenized]

        # Check current output against each recent output
        current_vec = vectors[-1]
        similarities = []
        for vec in vectors[:-1]:
            dist = cosine_distance(current_vec, vec)
            similarities.append(1.0 - dist)  # Convert distance to similarity

        high_similarity_count = sum(1 for s in similarities if s > AGENT_SIMILARITY_THRESHOLD)

        if high_similarity_count >= AGENT_CONSECUTIVE_THRESHOLD - 1:
            avg_sim = sum(similarities) / len(similarities)
            return StagnationSignal(
                level=StagnationLevel.AGENT,
                description=f"Agent {agent_id} producing semantically similar outputs "
                            f"(avg similarity {avg_sim:.3f} > {AGENT_SIMILARITY_THRESHOLD})",
                metric_name="output_similarity",
                metric_value=avg_sim,
                threshold=AGENT_SIMILARITY_THRESHOLD,
                agent_id=agent_id,
                consecutive_count=high_similarity_count + 1,
            )
        return None

    def check_framework_stagnation(self) -> list[StagnationSignal]:
        """Public wrapper for framework-level stagnation checks.

        Used by orchestrator to check framework stagnation independently
        of the full check_all() flow (e.g., for solo tasks that don't
        produce diversity measurements).
        """
        return self._check_framework_stagnation()

    def record_evolution(self, tier: int) -> None:
        """Record that an evolution occurred. Resets framework counter if Tier >= 2."""
        if tier >= 2:
            self._tasks_since_evolution = 0
            self._save_state()

    def record_archive_update(self) -> None:
        """Record that a MAP-Elites archive cell was replaced. Resets counter."""
        self._tasks_since_archive_update = 0
        self._save_state()

    def record_evolution_outcome(self, promoted: bool) -> None:
        """Record evolution outcome for stall detection (Phase 8).

        If promoted, reset consecutive_rejections counter.
        If rejected, increment counter.
        """
        if promoted:
            self._consecutive_rejections = 0
        else:
            self._consecutive_rejections += 1
        self._save_state()

    def _check_team_srd(self) -> StagnationSignal | None:
        """SRD < 0.4 for 3 consecutive tasks → team-level stagnation."""
        recent = list(self._srd_history)[-SRD_CONSECUTIVE_THRESHOLD:]
        if len(recent) < SRD_CONSECUTIVE_THRESHOLD:
            return None

        if all(v < SRD_STAGNATION_THRESHOLD for v in recent):
            avg = sum(recent) / len(recent)
            return StagnationSignal(
                level=StagnationLevel.TEAM,
                description=f"SRD below {SRD_STAGNATION_THRESHOLD} for "
                            f"{SRD_CONSECUTIVE_THRESHOLD} consecutive tasks "
                            f"(avg={avg:.3f})",
                metric_name="srd",
                metric_value=avg,
                threshold=SRD_STAGNATION_THRESHOLD,
                consecutive_count=SRD_CONSECUTIVE_THRESHOLD,
            )
        return None

    def _check_voice_stagnation(self) -> list[StagnationSignal]:
        """Check voice-level stagnation signals."""
        signals: list[StagnationSignal] = []

        # VDI < 0.2 for 3 consecutive tasks
        recent_vdi = list(self._vdi_history)[-VDI_CONSECUTIVE_THRESHOLD:]
        if len(recent_vdi) >= VDI_CONSECUTIVE_THRESHOLD:
            if all(v < VDI_FLOOR for v in recent_vdi):
                avg = sum(recent_vdi) / len(recent_vdi)
                signals.append(StagnationSignal(
                    level=StagnationLevel.VOICE,
                    description=f"VDI below {VDI_FLOOR} for "
                                f"{VDI_CONSECUTIVE_THRESHOLD} consecutive tasks "
                                f"(avg={avg:.3f})",
                    metric_name="vdi",
                    metric_value=avg,
                    threshold=VDI_FLOOR,
                    consecutive_count=VDI_CONSECUTIVE_THRESHOLD,
                ))

        # All agents using same tone for 5+ tasks
        recent_tones = list(self._tone_history)[-VOICE_SAME_TONE_THRESHOLD:]
        if len(recent_tones) >= VOICE_SAME_TONE_THRESHOLD:
            # Check if all tone sets are identical (single tone used)
            first = recent_tones[0]
            if all(t == first for t in recent_tones) and len(first) <= 1:
                tone_name = next(iter(first)) if first else "none"
                signals.append(StagnationSignal(
                    level=StagnationLevel.VOICE,
                    description=f"All agents using same tone atom '{tone_name}' "
                                f"for {VOICE_SAME_TONE_THRESHOLD}+ consecutive tasks",
                    metric_name="tone_uniformity",
                    metric_value=1.0,
                    threshold=0.0,
                    consecutive_count=VOICE_SAME_TONE_THRESHOLD,
                ))

        return signals

    def _check_framework_stagnation(self) -> list[StagnationSignal]:
        """Check framework-level stagnation signals.

        FM-104: Signal suppression — only fire the evolution stagnation signal
        once when first crossing the threshold, then every 10 tasks after that.
        In Phase 2 there is no evolution engine, so this prevents perpetual
        log noise. The signal fires at task 10, 20, 30... not on every task.
        """
        signals: list[StagnationSignal] = []

        # No Tier 2+ evolution in 10 tasks
        # FM-104: Only fire at threshold crossings (every 10 tasks), not continuously
        if (
            self._tasks_since_evolution >= FRAMEWORK_EVOLUTION_THRESHOLD
            and self._tasks_since_evolution % FRAMEWORK_EVOLUTION_THRESHOLD == 0
        ):
            signals.append(StagnationSignal(
                level=StagnationLevel.FRAMEWORK,
                description=f"No Tier 2+ evolution in "
                            f"{self._tasks_since_evolution} tasks",
                metric_name="tasks_since_evolution",
                metric_value=float(self._tasks_since_evolution),
                threshold=float(FRAMEWORK_EVOLUTION_THRESHOLD),
                consecutive_count=self._tasks_since_evolution,
            ))

        # MAP-Elites archive staleness: no cell replacement in N tasks
        # FM-P7-057-FIX: Only fire at multiples of threshold (FM-104 pattern)
        if (
            self._tasks_since_archive_update >= ARCHIVE_STALENESS_THRESHOLD
            and self._tasks_since_archive_update % ARCHIVE_STALENESS_THRESHOLD == 0
        ):
            signals.append(StagnationSignal(
                level=StagnationLevel.FRAMEWORK,
                description=(
                    f"MAP-Elites archive stale: no cell replacement in "
                    f"{self._tasks_since_archive_update} tasks"
                ),
                metric_name="tasks_since_archive_update",
                metric_value=float(self._tasks_since_archive_update),
                threshold=float(ARCHIVE_STALENESS_THRESHOLD),
                consecutive_count=self._tasks_since_archive_update,
            ))

        # Phase 8: Single-fork evolution stall
        # FM-104: Only fire at multiples of threshold
        if (
            self._consecutive_rejections >= SINGLE_FORK_STALL_THRESHOLD
            and self._consecutive_rejections % SINGLE_FORK_STALL_THRESHOLD == 0
        ):
            signals.append(StagnationSignal(
                level=StagnationLevel.FRAMEWORK,
                description=(
                    f"Single-fork evolution stalled: {self._consecutive_rejections} "
                    f"consecutive_rejections. Consider population mode."
                ),
                metric_name="consecutive_rejections",
                metric_value=float(self._consecutive_rejections),
                threshold=float(SINGLE_FORK_STALL_THRESHOLD),
                consecutive_count=self._consecutive_rejections,
            ))

        # Same topology for 10 consecutive tasks
        recent_topo = list(self._topology_history)[-FRAMEWORK_TOPOLOGY_THRESHOLD:]
        if len(recent_topo) >= FRAMEWORK_TOPOLOGY_THRESHOLD:
            if len(set(recent_topo)) == 1:
                signals.append(StagnationSignal(
                    level=StagnationLevel.FRAMEWORK,
                    description=f"Same topology '{recent_topo[0]}' selected for "
                                f"{FRAMEWORK_TOPOLOGY_THRESHOLD} consecutive tasks",
                    metric_name="topology_uniformity",
                    metric_value=1.0,
                    threshold=0.0,
                    consecutive_count=FRAMEWORK_TOPOLOGY_THRESHOLD,
                ))

        return signals

    def _save_state(self) -> None:
        """Persist sliding window state to YAML."""
        state = {
            "srd_history": list(self._srd_history),
            "vdi_history": list(self._vdi_history),
            "topology_history": list(self._topology_history),
            "tone_history": [list(s) for s in self._tone_history],
            "tasks_since_evolution": self._tasks_since_evolution,
            "tasks_since_archive_update": self._tasks_since_archive_update,
            "consecutive_rejections": self._consecutive_rejections,
        }
        self.yaml_store.write_raw(f"{self._stagnation_base}/state.yaml", state)

    def _load_state(self) -> None:
        """Load persisted sliding window state.

        FM-119: Catches all exceptions (FileNotFoundError on first run,
        yaml.ScannerError on corrupt YAML, ValueError/TypeError/KeyError
        on invalid data). Resets to empty state on any failure.
        """
        try:
            state = self.yaml_store.read_raw(f"{self._stagnation_base}/state.yaml")
            for v in state.get("srd_history", []):
                self._srd_history.append(float(v))
            for v in state.get("vdi_history", []):
                self._vdi_history.append(float(v))
            for v in state.get("topology_history", []):
                self._topology_history.append(str(v))
            for v in state.get("tone_history", []):
                self._tone_history.append(set(v))
            self._tasks_since_evolution = int(state.get("tasks_since_evolution", 0))
            # FM-P7-056-FIX: FM-119 backward-compat pattern — .get() with default
            # is acceptable for state loading (older state files won't have this key)
            self._tasks_since_archive_update = int(state.get("tasks_since_archive_update", 0))
            # Phase 8: FM-119 backward-compat — older state files won't have this
            self._consecutive_rejections = int(state.get("consecutive_rejections", 0))
        except Exception as e:
            # FM-119: Corrupt/missing YAML — start with empty state
            if not isinstance(e, FileNotFoundError):
                logger.warning(
                    f"Corrupt stagnation state, resetting to empty: {e}"
                )
