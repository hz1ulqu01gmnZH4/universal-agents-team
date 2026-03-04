# Phase 6: Creativity Engine — Detailed Design

**Version:** 0.2.0
**Date:** 2026-03-04
**Status:** Review-hardened (Step 3-4 findings applied)
**Spec reference:** Unified Design v1.1, Section 11 (Creativity Engine), Section 4.6 (Voice System), Section 10 (Diversity & Stagnation)
**Literature:** research/creativity-in-multi-agent-systems.md (43 papers)
**Dependencies:** Phase 2 (diversity_engine, stagnation_detector), Phase 3 (skill_library), Phase 4 (evolution_engine), Phase 5 (governance)

---

## Part 1: Architecture Overview

### What Phase 6 Adds

Phase 6 implements the **Creativity Engine** — a structured creative problem-solving subsystem that activates when conventional approaches stagnate or when tasks require novel solutions. Key principle from literature: **structure > individual capability** (FilmAgent 2025: GPT-4o multi-agent with good structure beats single o1).

**New components:**
1. `CreativityEngine` — orchestrates the 4-phase Separate-Then-Together protocol
2. `CreativeSession` model — tracks a single creative problem-solving session
3. `GuilfordMetrics` — measures fluency, flexibility, originality, elaboration
4. `PersonaAssigner` — selects and assigns creative voice atoms to agents

**Modified components:**
1. `Orchestrator` — new optional `creativity_engine` dependency, activation triggers
2. `TopologyRouter` — enables `debate` topology selection for creative tasks
3. `StagnationDetector` — emits creativity-trigger signals consumed by orchestrator
4. `DiversityEngine` — no code changes, but Phase 6 is a primary consumer of VDI/SRD

### What Phase 6 Does NOT Include

- No new LLM calls (agents are simulated via existing team/orchestrator infrastructure)
- No MAP-Elites archive (Phase 7)
- No population-based evolution (Phase 8)
- No domain switching (Phase 7)
- No Elo tournament ranking (deferred to Phase 8)
- No textual backpropagation (requires Phase 8 population evolution)

### Key Design Decisions

1. **Voice atoms as creativity primitives.** Creative personas are composed from existing `VoiceAtom` objects with `creativity_mode: true`, not hardcoded. This makes the creativity engine extensible via Tier 2 evolution.

2. **4-phase protocol is synchronous.** Each phase completes before the next begins. This avoids the "problem drift" identified by Becker 2024 where extended discussion loses focus.

3. **Blind cross-pollination.** During Phase 2, agents review others' outputs without knowing the author. This prevents authority bias (Straub et al. 2025).

4. **Creativity metrics are separate from quality metrics.** Guilford dimensions (fluency, flexibility, originality, elaboration) are tracked independently from task success rate.

5. **Anti-stagnation is reactive, not proactive.** Creativity engine activates in response to stagnation signals or explicit triggers, not on every task. This prevents unnecessary token expenditure (BATS finding: agents without budget tracking waste 50-95% tokens).

---

## Part 2: Data Models

### File: `src/uagents/models/creativity.py`

```python
"""Creativity engine data models — Phase 6.
Spec reference: Section 11 (Creativity Engine), Section 4.6 (Voice System)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, generate_id


class CreativePhase(IntEnum):
    """Phases of the Separate-Then-Together protocol."""
    DIVERGE = 1
    CROSS_POLLINATE = 2
    SYNTHESIZE = 3
    EVALUATE = 4


class CreativeActivationTrigger(FrameworkModel):
    """Why the creativity engine was activated."""
    trigger_type: Literal[
        "stagnation_detected",
        "task_tagged_novel",
        "conventional_approach_failed",
        "human_requested",
        "evolution_needs_novel_solution",
    ]
    detail: str
    task_id: str
    stagnation_signals: list[dict] = Field(default_factory=list)


class CreativeAgentAssignment(FrameworkModel):
    """A single agent's creative role assignment."""
    agent_slot: int  # 0-indexed position in the creative session
    persona_atom: str  # e.g., "persona_analogist"
    tone_atom: str  # e.g., "tone_assertive"
    style_atom: str | None = None
    temperature_offset: float = Field(default=0.0, ge=-0.3, le=0.3)  # FM-P6-45-FIX


class DivergentIdea(FrameworkModel):
    """A single idea produced during the diverge phase."""
    id: str = Field(default_factory=lambda: generate_id("idea"))
    agent_slot: int
    content: str
    category: str = ""  # Assigned during evaluation (for flexibility metric)
    originality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class CrossPollinationResult(FrameworkModel):
    """Result of one agent reviewing another's idea (blind)."""
    reviewer_slot: int
    original_idea_id: str
    combined_output: str  # "yes, and..." combination
    build_on_elements: list[str] = Field(default_factory=list)


class SynthesisResult(FrameworkModel):
    """Orchestrator's synthesis of best ideas."""
    selected_idea_ids: list[str]
    synthesis_text: str
    diversity_preserved: bool  # Did synthesis preserve minority ideas?
    minority_ideas: list[str] = Field(default_factory=list)  # IDs of preserved minority ideas


class GuilfordScores(FrameworkModel):
    """Creativity metrics based on Guilford dimensions."""
    fluency: int = Field(ge=0)  # Number of distinct ideas
    flexibility: int = Field(ge=0)  # Number of distinct categories/approaches
    originality: float = Field(ge=0.0, le=1.0)  # Mean semantic distance from common solutions
    elaboration: float = Field(ge=0.0, le=1.0)  # Detail and development of ideas


class CreativeEvaluation(FrameworkModel):
    """Evaluation of a creative session's output."""
    id: str = Field(default_factory=lambda: generate_id("ceval"))
    created_at: datetime
    guilford: GuilfordScores
    novelty: float = Field(ge=0.0, le=1.0)  # Genuinely new?
    quality: float = Field(ge=0.0, le=1.0)  # Solves the problem?
    diversity: float = Field(ge=0.0, le=1.0)  # Differs from other solutions?
    feasibility: float = Field(ge=0.0, le=1.0)  # Can be implemented?
    vdi_score: float = Field(ge=0.0, le=1.0)  # Voice diversity during session


class CreativeSession(FrameworkModel):
    """Tracks a complete creative problem-solving session."""
    id: str = Field(default_factory=lambda: generate_id("csess"))
    created_at: datetime
    task_id: str
    trigger: CreativeActivationTrigger
    agent_count: int = Field(ge=3, le=5)
    assignments: list[CreativeAgentAssignment] = Field(default_factory=list)
    current_phase: CreativePhase = CreativePhase.DIVERGE

    # Phase outputs (populated as session progresses)
    divergent_ideas: list[DivergentIdea] = Field(default_factory=list)
    cross_pollinations: list[CrossPollinationResult] = Field(default_factory=list)
    synthesis: SynthesisResult | None = None
    evaluation: CreativeEvaluation | None = None

    # Anti-stagnation tracking
    persona_history_hash: str = ""  # SHA-256 of sorted persona+tone combo, for rotation check
```

---

## Part 3: Configuration

### File: `core/creativity.yaml`

```yaml
# core/creativity.yaml — Creativity Engine configuration
# Spec reference: Section 11 (Creativity Engine)
creativity_engine:

  creative_protocol:
    min_agents: 3
    max_agents: 5
    default_agents: 3

    phases:
      diverge:
        description: "Persona-conditioned agents brainstorm independently"
        rules:
          - "No convergence pressure — agents cannot see others' outputs"
          - "Quantity over quality — fluency first"
          - "Each agent gets unique persona + tone combination"

      cross_pollinate:
        description: "Agents share outputs via blind review"
        rules:
          - "Blind: agents don't know whose idea they're reviewing"
          - "Build on, don't judge — yes-and not no-but"
          - "Reviewer must combine reviewed idea with own"

      synthesize:
        description: "Orchestrator integrates best ideas"
        rules:
          - "Select for diversity of approach, not just quality"
          - "Preserve minority ideas that challenge consensus"

      evaluate:
        criteria:
          novelty: "Genuinely new, not a reformulation?"
          quality: "Actually solves the problem?"
          diversity: "Differs from other solutions found?"
          feasibility: "Can it be implemented?"

  persona_assignment:
    method: "Select from voice atoms with creativity_mode: true"
    constraint: "No two agents may share a persona atom"
    tone_variation: "Each creative agent gets a unique tone atom"
    temperature_offsets:
      - 0.0
      - 0.1
      - -0.1
      - 0.2
      - -0.2

  anti_stagnation:
    persona_rotation:
      enabled: true
      description: "Never same persona + tone combination twice in a row"
    entropy_injection:
      enabled: true
      entropy_threshold: 0.3  # Below this, inject adversarial agent
    adversarial_agent:
      persona: "persona_inverter"
      tone: "tone_assertive"

  activation:
    triggers:
      - "stagnation_detected"
      - "task_tagged_novel"
      - "conventional_approach_failed"
      - "human_requested"
      - "evolution_needs_novel_solution"
    topology: "debate"  # Creative tasks use debate topology
    srd_floor_trigger: 0.4  # SRD below this for 3+ tasks triggers creativity
    consecutive_stagnation_threshold: 2  # N stagnation signals before activation

  metrics:
    guilford_tracking: true
    originality_method: "cosine_distance_from_corpus"
    flexibility_method: "category_count"
    history_size: 50  # Keep last 50 session evaluations
```

---

## Part 4: PersonaAssigner

### File: `src/uagents/engine/persona_assigner.py`

```python
"""Assigns creative voice profiles to agents in creative sessions.
Spec reference: Section 11.1 (persona_assignment), Section 4.6 (Voice Atoms).

Key constraints:
- No two agents may share the same persona atom
- Each agent gets a unique tone atom
- Never repeat the same persona+tone combo as the previous session
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from ..models.creativity import CreativeAgentAssignment
from ..models.voice import VoiceAtom
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.persona_assigner")


class PersonaAssignmentError(Exception):
    """Raised when persona assignment fails."""


class PersonaAssigner:
    """Assigns diverse creative voice profiles to agents.

    Loads voice atoms from roles/voice.yaml, filters by creativity_mode,
    and produces unique assignments per session with rotation enforcement.
    """

    def __init__(self, yaml_store: YamlStore) -> None:
        self.yaml_store = yaml_store
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load creativity engine config (fail-loud)."""
        raw = self.yaml_store.read_raw("core/creativity.yaml")
        return raw["creativity_engine"]

    def assign(
        self,
        agent_count: int,
        previous_session_hash: str = "",
    ) -> list[CreativeAgentAssignment]:
        """Assign unique persona + tone combinations to N agents.

        Args:
            agent_count: Number of agents (3-5).
            previous_session_hash: Hash of previous session's assignments
                for rotation enforcement.

        Returns:
            List of CreativeAgentAssignment, one per agent slot.

        Raises:
            PersonaAssignmentError: If not enough creative personas or tones.
        """
        atoms = self._load_voice_atoms()

        # use_enum_values=True: .category is already a str, not an enum
        creative_personas = [
            a for a in atoms.values()
            if a.creativity_mode and a.category == "persona"
        ]
        tone_atoms = [
            a for a in atoms.values()
            if a.category == "tone"
        ]

        if len(creative_personas) < agent_count:
            raise PersonaAssignmentError(
                f"Need {agent_count} creative personas but only "
                f"{len(creative_personas)} available (creativity_mode=true). "
                f"Available: {[p.name for p in creative_personas]}"
            )
        if len(tone_atoms) < agent_count:
            raise PersonaAssignmentError(
                f"Need {agent_count} unique tone atoms but only "
                f"{len(tone_atoms)} available. "
                f"Available: {[t.name for t in tone_atoms]}"
            )

        temp_offsets = self._config.get("persona_assignment", {}).get(
            "temperature_offsets", [0.0, 0.1, -0.1, 0.2, -0.2]
        )

        # Build assignments with unique persona + tone per agent
        assignments = self._build_assignments(
            agent_count, creative_personas, tone_atoms,
            temp_offsets, previous_session_hash,
        )
        return assignments

    def _build_assignments(
        self,
        agent_count: int,
        personas: list[VoiceAtom],
        tones: list[VoiceAtom],
        temp_offsets: list[float],
        previous_hash: str,
    ) -> list[CreativeAgentAssignment]:
        """Build assignments, enforcing rotation constraint.

        FM-P6-01: If first candidate combo matches previous_hash,
        rotate by shifting persona order by 1.
        """
        # Sort for determinism
        personas = sorted(personas, key=lambda a: a.name)
        tones = sorted(tones, key=lambda a: a.name)

        # Initial assignment: persona[i] + tone[i]
        assignments: list[CreativeAgentAssignment] = []
        for i in range(agent_count):
            assignments.append(CreativeAgentAssignment(
                agent_slot=i,
                persona_atom=personas[i].name,
                tone_atom=tones[i].name,
                temperature_offset=temp_offsets[i] if i < len(temp_offsets) else 0.0,
            ))

        # Check rotation constraint
        combo_hash = self._compute_combo_hash(assignments)
        if combo_hash == previous_hash and previous_hash != "":
            # Rotate: shift personas by 1 position
            logger.info("Rotating persona assignments to avoid repetition")
            for i, a in enumerate(assignments):
                shifted_idx = (i + 1) % len(personas)
                a.persona_atom = personas[shifted_idx].name
            combo_hash = self._compute_combo_hash(assignments)

        return assignments

    def _load_voice_atoms(self) -> dict[str, VoiceAtom]:
        """Load all voice atoms from roles/voice.yaml."""
        raw = self.yaml_store.read_raw("roles/voice.yaml")
        atoms_raw = raw["voice_atoms"]
        atoms: dict[str, VoiceAtom] = {}
        for name, data in atoms_raw.items():
            data = dict(data)  # FM-P6-29-FIX: copy before mutation
            data["name"] = name
            # Infer category from name prefix
            for cat in ("language", "tone", "style", "persona"):
                if name.startswith(f"{cat}_"):
                    data["category"] = cat
                    break
            else:
                raise PersonaAssignmentError(
                    f"Voice atom '{name}' does not match any known "
                    f"category prefix (language_, tone_, style_, persona_)"
                )
            atoms[name] = VoiceAtom(**data)
        return atoms

    @staticmethod
    def _compute_combo_hash(assignments: list[CreativeAgentAssignment]) -> str:
        """Compute deterministic hash of persona+tone combos for rotation tracking."""
        combos = sorted(f"{a.persona_atom}:{a.tone_atom}" for a in assignments)
        return hashlib.sha256("|".join(combos).encode()).hexdigest()[:16]
```

---

## Part 5: GuilfordMetrics

### File: `src/uagents/engine/guilford_metrics.py`

```python
"""Creativity metrics based on Guilford's divergent thinking dimensions.
Spec reference: Section 11.3 (metrics.guilford_dimensions).

Measures:
- Fluency: number of distinct ideas
- Flexibility: number of distinct categories/approaches
- Originality: semantic distance from common solutions (TF-IDF cosine)
- Elaboration: detail level of ideas (word count heuristic)
"""
from __future__ import annotations

import logging

from ..models.creativity import DivergentIdea, GuilfordScores
from .diversity_engine import (
    compute_idf,
    cosine_distance,
    tf_idf_vector,
    tokenize,
)

logger = logging.getLogger("uagents.guilford_metrics")


class GuilfordMetrics:
    """Computes Guilford divergent thinking scores for creative sessions.

    Uses TF-IDF cosine distance (reused from diversity_engine) for
    originality measurement. Category assignment for flexibility is
    done via content clustering heuristic.
    """

    # Minimum word count for an idea to be considered "elaborated"
    ELABORATION_THRESHOLD = 50

    def compute(
        self,
        ideas: list[DivergentIdea],
        corpus: list[str] | None = None,
    ) -> GuilfordScores:
        """Compute all 4 Guilford dimensions for a set of ideas.

        Args:
            ideas: List of divergent ideas from a creative session.
            corpus: Optional list of prior solutions for originality baseline.
                If None, originality is computed as mean pairwise distance.

        Returns:
            GuilfordScores with all 4 dimensions.

        Raises:
            ValueError: If ideas list is empty.
        """
        if not ideas:
            raise ValueError("Cannot compute Guilford metrics on empty ideas list")

        fluency = self._compute_fluency(ideas)
        flexibility = self._compute_flexibility(ideas)
        originality = self._compute_originality(ideas, corpus)
        elaboration = self._compute_elaboration(ideas)

        return GuilfordScores(
            fluency=fluency,
            flexibility=flexibility,
            originality=originality,
            elaboration=elaboration,
        )

    def _compute_fluency(self, ideas: list[DivergentIdea]) -> int:
        """Fluency = number of distinct non-empty ideas."""
        seen: set[str] = set()
        count = 0
        for idea in ideas:
            # Deduplicate by normalized content
            normalized = idea.content.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                count += 1
        return count

    def _compute_flexibility(self, ideas: list[DivergentIdea]) -> int:
        """Flexibility = number of distinct categories/approaches.

        Uses TF-IDF clustering heuristic: ideas with cosine distance < 0.3
        are considered same category. Counts resulting clusters.
        """
        if len(ideas) < 2:
            return len(ideas)

        texts = [idea.content for idea in ideas if idea.content.strip()]
        if len(texts) < 2:
            return len(texts)

        tokenized = [tokenize(t) for t in texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tok, idf) for tok in tokenized]

        # Greedy clustering: assign each idea to first cluster within threshold
        clusters: list[list[int]] = []
        cluster_threshold = 0.3  # cosine distance below this = same category

        for i, vec in enumerate(vectors):
            assigned = False
            for cluster in clusters:
                representative = vectors[cluster[0]]
                dist = cosine_distance(vec, representative)
                if dist < cluster_threshold:
                    cluster.append(i)
                    assigned = True
                    break
            if not assigned:
                clusters.append([i])

        # Update idea categories for transparency
        for cluster_idx, cluster in enumerate(clusters):
            category_label = f"approach_{cluster_idx + 1}"
            for idea_idx in cluster:
                ideas[idea_idx].category = category_label

        return len(clusters)

    def _compute_originality(
        self,
        ideas: list[DivergentIdea],
        corpus: list[str] | None,
    ) -> float:
        """Originality = mean semantic distance from baseline.

        If corpus provided: distance from corpus centroid.
        If no corpus: mean pairwise distance between ideas.
        """
        texts = [idea.content for idea in ideas if idea.content.strip()]
        if len(texts) < 1:
            return 0.0

        if corpus and len(corpus) > 0:
            return self._distance_from_corpus(texts, corpus)
        return self._mean_pairwise_distance(texts)

    def _distance_from_corpus(
        self, texts: list[str], corpus: list[str]
    ) -> float:
        """Mean distance of ideas from corpus (common solutions)."""
        all_docs = [tokenize(t) for t in texts + corpus]
        idf = compute_idf(all_docs)

        idea_vectors = [tf_idf_vector(tokenize(t), idf) for t in texts]
        corpus_vectors = [tf_idf_vector(tokenize(t), idf) for t in corpus]

        total_dist = 0.0
        count = 0
        for iv in idea_vectors:
            for cv in corpus_vectors:
                total_dist += cosine_distance(iv, cv)
                count += 1

        return total_dist / count if count > 0 else 0.0

    def _mean_pairwise_distance(self, texts: list[str]) -> float:
        """Mean pairwise cosine distance between ideas."""
        if len(texts) < 2:
            return 0.0

        tokenized = [tokenize(t) for t in texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tok, idf) for tok in tokenized]

        total_dist = 0.0
        pair_count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                total_dist += cosine_distance(vectors[i], vectors[j])
                pair_count += 1

        return total_dist / pair_count if pair_count > 0 else 0.0

    def _compute_elaboration(self, ideas: list[DivergentIdea]) -> float:
        """Elaboration = proportion of ideas that are well-developed.

        Heuristic: ideas with >= ELABORATION_THRESHOLD words are "elaborated".
        Returns ratio of elaborated ideas to total.
        """
        if not ideas:
            return 0.0

        elaborated = sum(
            1 for idea in ideas
            if len(idea.content.split()) >= self.ELABORATION_THRESHOLD
        )
        return elaborated / len(ideas)
```

---

## Part 6: CreativityEngine

### File: `src/uagents/engine/creativity_engine.py`

```python
"""Creativity Engine — Separate-Then-Together creative protocol.
Spec reference: Section 11 (Creativity Engine).

Implements the 4-phase evidence-based brainstorming protocol:
1. DIVERGE: persona-conditioned agents brainstorm independently
2. CROSS_POLLINATE: blind review and "yes, and..." building
3. SYNTHESIZE: orchestrator integrates best ideas
4. EVALUATE: multi-criteria evaluation with Guilford metrics

Key literature:
- Straub et al. 2025: persona-based multi-agent brainstorming
- Liang et al. 2023: Degeneration-of-Thought prevention
- Imasato et al. 2024: Csikszentmihalyi systems model
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..audit.logger import AuditLogger
from ..models.base import generate_id
from ..models.creativity import (
    CreativeActivationTrigger,
    CreativeAgentAssignment,
    CreativeEvaluation,
    CreativePhase,
    CreativeSession,
    CrossPollinationResult,
    DivergentIdea,
    SynthesisResult,
)
from ..state.yaml_store import YamlStore
from .diversity_engine import DiversityEngine, cosine_distance, tokenize, compute_idf, tf_idf_vector
from .guilford_metrics import GuilfordMetrics
from .persona_assigner import PersonaAssigner, PersonaAssignmentError

logger = logging.getLogger("uagents.creativity_engine")


class CreativityError(Exception):
    """Raised when the creativity engine encounters an unrecoverable error."""


class CreativityEngine:
    """Orchestrates the Separate-Then-Together creative protocol.

    The creativity engine is activated by the Orchestrator when:
    - Stagnation is detected (SRD/VDI below floor)
    - A task is tagged as novel/exploratory
    - Conventional approaches have failed
    - Human explicitly requests creative exploration
    - Evolution proposal requires novel solution

    The engine manages a CreativeSession through 4 phases, producing
    evaluated creative output with Guilford metrics.
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        diversity_engine: DiversityEngine,
        persona_assigner: PersonaAssigner,
        guilford_metrics: GuilfordMetrics,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.yaml_store = yaml_store
        self.diversity_engine = diversity_engine
        self.persona_assigner = persona_assigner
        self.guilford_metrics = guilford_metrics
        self.audit_logger = audit_logger

        self._config = self._load_config()
        self._last_session_hash: str = self._load_last_session_hash()

    def _load_config(self) -> dict:
        """Load creativity engine config (fail-loud)."""
        raw = self.yaml_store.read_raw("core/creativity.yaml")
        return raw["creativity_engine"]

    def _load_last_session_hash(self) -> str:
        """Load the hash of the last creative session's persona assignments."""
        try:
            state = self.yaml_store.read_raw("state/creativity/engine_state.yaml")
            return state["last_session_hash"]  # IFM-N53: no .get() fallback
        except FileNotFoundError:
            return ""

    def _save_last_session_hash(self, hash_val: str) -> None:
        """Persist the session hash for rotation enforcement."""
        self.yaml_store.write_raw(
            "state/creativity/engine_state.yaml",
            {"last_session_hash": hash_val},
        )

    def should_activate(
        self,
        stagnation_signals: list[dict],
        task_tags: list[str] | None = None,
        conventional_failed: bool = False,
        human_requested: bool = False,
    ) -> CreativeActivationTrigger | None:
        """Determine if the creativity engine should activate.

        Args:
            stagnation_signals: Signals from StagnationDetector.check_all().
            task_tags: Tags on the current task (e.g., ["novel", "exploratory"]).
            conventional_failed: True if standard approaches already failed.
            human_requested: True if human explicitly asked for creative mode.

        Returns:
            CreativeActivationTrigger if should activate, None otherwise.
        """
        task_tags = task_tags or []
        activation_config = self._config["activation"]

        # Human request always activates
        if human_requested:
            return CreativeActivationTrigger(
                trigger_type="human_requested",
                detail="Human explicitly requested creative exploration",
                task_id="",
                stagnation_signals=stagnation_signals,
            )

        # Conventional failure activates
        if conventional_failed:
            return CreativeActivationTrigger(
                trigger_type="conventional_approach_failed",
                detail="Standard approaches failed, switching to creative protocol",
                task_id="",
                stagnation_signals=stagnation_signals,
            )

        # Task tagged as novel
        if any(tag in ("novel", "exploratory", "creative") for tag in task_tags):
            return CreativeActivationTrigger(
                trigger_type="task_tagged_novel",
                detail=f"Task tagged with: {[t for t in task_tags if t in ('novel', 'exploratory', 'creative')]}",
                task_id="",
                stagnation_signals=stagnation_signals,
            )

        # Stagnation-based activation
        threshold = activation_config["consecutive_stagnation_threshold"]
        if len(stagnation_signals) >= threshold:
            return CreativeActivationTrigger(
                trigger_type="stagnation_detected",
                detail=f"{len(stagnation_signals)} stagnation signals detected",
                task_id="",
                stagnation_signals=stagnation_signals,
            )

        return None

    def create_session(
        self,
        task_id: str,
        trigger: CreativeActivationTrigger,
        agent_count: int | None = None,
    ) -> CreativeSession:
        """Create a new creative session with persona assignments.

        Args:
            task_id: The task that triggered creativity.
            trigger: Why the creativity engine was activated.
            agent_count: Override agent count (default from config).

        Returns:
            Initialized CreativeSession with agent assignments.

        Raises:
            PersonaAssignmentError: If not enough creative voice atoms.
            CreativityError: If agent_count is out of range.
        """
        now = datetime.now(timezone.utc)
        min_agents = self._config["creative_protocol"]["min_agents"]
        max_agents = self._config["creative_protocol"]["max_agents"]
        default_agents = self._config["creative_protocol"]["default_agents"]

        count = agent_count if agent_count is not None else default_agents
        if count < min_agents or count > max_agents:
            raise CreativityError(
                f"Agent count {count} out of range [{min_agents}, {max_agents}]"
            )

        # Assign personas with rotation enforcement
        # FM-P6-26-FIX: task_id is set by caller (_check_creativity_trigger);
        # don't mutate trigger here — it's already set or will be set upstream.
        assignments = self.persona_assigner.assign(
            count, self._last_session_hash,
        )
        combo_hash = self.persona_assigner._compute_combo_hash(assignments)

        session = CreativeSession(
            id=generate_id("csess"),
            created_at=now,
            task_id=task_id,
            trigger=trigger,
            agent_count=count,
            assignments=assignments,
            current_phase=CreativePhase.DIVERGE,
            persona_history_hash=combo_hash,
        )

        # Persist session
        self.yaml_store.write(
            f"state/creativity/sessions/{session.id}.yaml", session,
        )

        # Update rotation state
        self._last_session_hash = combo_hash
        self._save_last_session_hash(combo_hash)

        logger.info(
            f"Creative session {session.id} created for task {task_id}: "
            f"{count} agents, trigger={trigger.trigger_type}"
        )

        # FM-P6-24-FIX: Use log_creativity() not log_governance()
        if self.audit_logger is not None:
            from ..models.audit import CreativityLogEntry
            self.audit_logger.log_creativity(CreativityLogEntry(
                id=generate_id("clog"),
                timestamp=now,
                event_type="creative_session_created",
                session_id=session.id,
                task_id=task_id,
                trigger_type=trigger.trigger_type,
                agent_count=count,
                detail=f"trigger={trigger.trigger_type}",
            ))

        return session

    def record_divergent_ideas(
        self,
        session_id: str,
        ideas: list[DivergentIdea],
    ) -> CreativeSession:
        """Record ideas from the diverge phase and advance to cross-pollination.

        Args:
            session_id: The creative session ID.
            ideas: Ideas produced by all agents during diverge phase.

        Returns:
            Updated session in CROSS_POLLINATE phase.

        Raises:
            CreativityError: If session not found or wrong phase.
        """
        session = self._load_session(session_id)
        if session.current_phase != CreativePhase.DIVERGE:
            raise CreativityError(
                f"Session {session_id} is in phase {CreativePhase(session.current_phase).name}, "
                f"expected DIVERGE"
            )

        if not ideas:
            raise CreativityError(
                f"No ideas provided for session {session_id}. "
                f"Diverge phase must produce at least 1 idea."
            )

        session.divergent_ideas = ideas
        session.current_phase = CreativePhase.CROSS_POLLINATE
        self._save_session(session)

        logger.info(
            f"Session {session_id}: {len(ideas)} ideas recorded, "
            f"advancing to CROSS_POLLINATE"
        )
        return session

    def record_cross_pollinations(
        self,
        session_id: str,
        results: list[CrossPollinationResult],
    ) -> CreativeSession:
        """Record cross-pollination results and advance to synthesis.

        Args:
            session_id: The creative session ID.
            results: Cross-pollination outputs from blind review.

        Returns:
            Updated session in SYNTHESIZE phase.

        Raises:
            CreativityError: If session not found or wrong phase.
        """
        session = self._load_session(session_id)
        if session.current_phase != CreativePhase.CROSS_POLLINATE:
            raise CreativityError(
                f"Session {session_id} is in phase {CreativePhase(session.current_phase).name}, "
                f"expected CROSS_POLLINATE"
            )

        # FM-P6-31-FIX: Validate all original_idea_ids reference existing ideas
        idea_ids = {idea.id for idea in session.divergent_ideas}
        for r in results:
            if r.original_idea_id not in idea_ids:
                raise CreativityError(
                    f"Cross-pollination references non-existent idea "
                    f"'{r.original_idea_id}' in session {session_id}. "
                    f"Valid IDs: {sorted(idea_ids)}"
                )

        # FM-P6-32-FIX: Prevent self-review (violates blind protocol)
        idea_author: dict[str, int] = {
            idea.id: idea.agent_slot for idea in session.divergent_ideas
        }
        for r in results:
            author_slot = idea_author[r.original_idea_id]
            if r.reviewer_slot == author_slot:
                raise CreativityError(
                    f"Agent slot {r.reviewer_slot} cannot review own idea "
                    f"'{r.original_idea_id}' (blind cross-pollination violated)"
                )

        session.cross_pollinations = results
        session.current_phase = CreativePhase.SYNTHESIZE
        self._save_session(session)

        logger.info(
            f"Session {session_id}: {len(results)} cross-pollinations recorded, "
            f"advancing to SYNTHESIZE"
        )
        return session

    def record_synthesis(
        self,
        session_id: str,
        synthesis: SynthesisResult,
    ) -> CreativeSession:
        """Record synthesis result and advance to evaluation.

        Args:
            session_id: The creative session ID.
            synthesis: Orchestrator's synthesis of best ideas.

        Returns:
            Updated session in EVALUATE phase.

        Raises:
            CreativityError: If session not found or wrong phase.
        """
        session = self._load_session(session_id)
        if session.current_phase != CreativePhase.SYNTHESIZE:
            raise CreativityError(
                f"Session {session_id} is in phase {CreativePhase(session.current_phase).name}, "
                f"expected SYNTHESIZE"
            )

        session.synthesis = synthesis
        session.current_phase = CreativePhase.EVALUATE
        self._save_session(session)

        logger.info(
            f"Session {session_id}: synthesis recorded ({len(synthesis.selected_idea_ids)} "
            f"ideas selected), advancing to EVALUATE"
        )
        return session

    def evaluate_session(
        self,
        session_id: str,
        corpus: list[str] | None = None,
    ) -> CreativeSession:
        """Run evaluation on a complete creative session.

        Computes Guilford metrics, novelty/quality/diversity/feasibility
        scores, and VDI measurement.

        Args:
            session_id: The creative session ID.
            corpus: Prior solutions for originality baseline.

        Returns:
            Completed session with evaluation.

        Raises:
            CreativityError: If session not found or wrong phase.
        """
        session = self._load_session(session_id)
        if session.current_phase != CreativePhase.EVALUATE:
            raise CreativityError(
                f"Session {session_id} is in phase {CreativePhase(session.current_phase).name}, "
                f"expected EVALUATE"
            )

        now = datetime.now(timezone.utc)

        # Compute Guilford metrics on divergent ideas
        guilford = self.guilford_metrics.compute(
            session.divergent_ideas, corpus
        )

        # Compute VDI for the session's voice profiles
        from ..models.voice import VoiceProfile
        profiles = self._assignments_to_profiles(session.assignments)
        vdi_measurement = self.diversity_engine.compute_vdi(
            task_id=session.task_id,
            profiles=profiles,
        )
        vdi_score = vdi_measurement.vdi_score if vdi_measurement else 0.0

        # Compute session-level scores
        idea_texts = [idea.content for idea in session.divergent_ideas]
        novelty = self._compute_novelty(idea_texts, corpus)
        quality = self._compute_quality_proxy(session)
        diversity_score = self._compute_idea_diversity(idea_texts)
        feasibility = self._compute_feasibility_proxy(session)

        evaluation = CreativeEvaluation(
            id=generate_id("ceval"),
            created_at=now,
            guilford=guilford,
            novelty=novelty,
            quality=quality,
            diversity=diversity_score,
            feasibility=feasibility,
            vdi_score=vdi_score,
        )

        session.evaluation = evaluation
        self._save_session(session)

        # Persist evaluation separately for history tracking
        self.yaml_store.write(
            f"state/creativity/evaluations/{evaluation.id}.yaml",
            evaluation,
        )

        # FM-P6-24-FIX: Use log_creativity() not log_governance()
        if self.audit_logger is not None:
            from ..models.audit import CreativityLogEntry
            self.audit_logger.log_creativity(CreativityLogEntry(
                id=generate_id("clog"),
                timestamp=now,
                event_type="creative_session_evaluated",
                session_id=session.id,
                task_id=session.task_id,
                guilford_fluency=guilford.fluency,
                guilford_flexibility=guilford.flexibility,
                guilford_originality=guilford.originality,
                guilford_elaboration=guilford.elaboration,
                vdi_score=vdi_score,
                detail=f"Session {session_id} evaluation complete",
            ))

        logger.info(
            f"Session {session_id} evaluated: guilford=({guilford.fluency}, "
            f"{guilford.flexibility}, {guilford.originality:.2f}, "
            f"{guilford.elaboration:.2f}), VDI={vdi_score:.2f}"
        )
        return session

    def get_session_history(self, limit: int = 50) -> list[CreativeEvaluation]:
        """Load recent creative session evaluations.

        Returns:
            List of evaluations sorted by created_at descending.
        """
        evals_dir = self.yaml_store.base_dir / "state/creativity/evaluations"
        if not evals_dir.exists():
            return []

        evaluations: list[CreativeEvaluation] = []
        eval_files = sorted(
            (f for f in evals_dir.iterdir() if f.suffix in (".yaml", ".yml")),
            reverse=True,
        )

        for ef in eval_files[:limit]:
            rel_path = str(ef.relative_to(self.yaml_store.base_dir))
            evaluations.append(
                self.yaml_store.read(rel_path, CreativeEvaluation)
            )
        return evaluations

    # ── Private helpers ──

    def _load_session(self, session_id: str) -> CreativeSession:
        """Load a creative session (fail-loud)."""
        path = f"state/creativity/sessions/{session_id}.yaml"
        try:
            return self.yaml_store.read(path, CreativeSession)
        except FileNotFoundError:
            raise CreativityError(
                f"Creative session '{session_id}' not found at {path}"
            )

    def _save_session(self, session: CreativeSession) -> None:
        """Persist a creative session."""
        self.yaml_store.write(
            f"state/creativity/sessions/{session.id}.yaml", session,
        )

    def _assignments_to_profiles(
        self, assignments: list[CreativeAgentAssignment]
    ) -> list:
        """Convert assignments to VoiceProfile objects for VDI computation."""
        from ..models.voice import VoiceProfile
        return [
            VoiceProfile(
                language="language_english",  # Creative sessions default to English
                tone=a.tone_atom,
                persona=a.persona_atom,
            )
            for a in assignments
        ]

    def _compute_novelty(
        self, idea_texts: list[str], corpus: list[str] | None,
    ) -> float:
        """Novelty = mean cosine distance from corpus (or pairwise if no corpus)."""
        if not idea_texts:
            return 0.0
        if corpus:
            all_texts = idea_texts + corpus
            tokenized = [tokenize(t) for t in all_texts]
            idf = compute_idf(tokenized)
            idea_vecs = [tf_idf_vector(tokenize(t), idf) for t in idea_texts]
            corpus_vecs = [tf_idf_vector(tokenize(t), idf) for t in corpus]
            total = 0.0
            count = 0
            for iv in idea_vecs:
                for cv in corpus_vecs:
                    total += cosine_distance(iv, cv)
                    count += 1
            return total / count if count > 0 else 0.0
        # No corpus: use pairwise distance
        if len(idea_texts) < 2:
            return 0.5  # Single idea, moderate novelty assumed
        tokenized = [tokenize(t) for t in idea_texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tok, idf) for tok in tokenized]
        total = 0.0
        count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                total += cosine_distance(vectors[i], vectors[j])
                count += 1
        return total / count if count > 0 else 0.0

    def _compute_idea_diversity(self, idea_texts: list[str]) -> float:
        """Diversity of ideas = text diversity via DiversityEngine."""
        result = self.diversity_engine.compute_text_diversity(idea_texts)
        return result if result is not None else 0.0

    def _compute_quality_proxy(self, session: CreativeSession) -> float:
        """Quality proxy: ratio of ideas that survived synthesis selection."""
        if not session.synthesis or not session.divergent_ideas:
            return 0.0
        selected = len(session.synthesis.selected_idea_ids)
        total = len(session.divergent_ideas)
        return min(selected / max(total, 1), 1.0)

    def _compute_feasibility_proxy(self, session: CreativeSession) -> float:
        """Feasibility proxy: based on synthesis completeness.

        If synthesis produced a result with diversity preserved, higher score.
        Proper feasibility requires execution (Phase 7+).
        """
        if session.synthesis is None:
            return 0.0
        base = 0.5  # Synthesis exists = baseline feasibility
        if session.synthesis.diversity_preserved:
            base += 0.2
        if session.synthesis.minority_ideas:
            base += 0.1
        if len(session.synthesis.synthesis_text) > 100:
            base += 0.2
        return min(base, 1.0)
```

---

## Part 7: Orchestrator Integration

### Modified file: `src/uagents/engine/orchestrator.py`

#### 7.1 Constructor changes

Add `creativity_engine` as an optional parameter:

```python
# In Orchestrator.__init__ — add after alignment_verifier:
        # Phase 6: Creativity engine
        creativity_engine: CreativityEngine | None = None,
```

Store it:
```python
        self._creativity_engine = creativity_engine
```

Add TYPE_CHECKING import:
```python
if TYPE_CHECKING:
    from .creativity_engine import CreativityEngine
```

#### 7.2 New method: `_check_creativity_trigger`

```python
    def _check_creativity_trigger(
        self,
        task_id: str,
        stagnation_signals: list,
        task_tags: list[str] | None = None,
        conventional_failed: bool = False,
    ) -> dict | None:
        """Check if creativity engine should activate and create session.

        Called from record_task_outcome() when stagnation signals are present,
        or from process_task() for tagged-novel tasks.

        Returns:
            Dict with session info if activated, None otherwise.
        """
        if self._creativity_engine is None:
            return None

        # FM-P6-40-FIX: Skip creativity under RED/ORANGE budget pressure
        if self.budget_tracker is not None:
            pressure = self.budget_tracker.get_pressure()
            if str(pressure) in ("red", "orange"):
                logger.info(
                    f"Skipping creativity trigger for task {task_id}: "
                    f"budget pressure is {pressure}"
                )
                return None

        # FM-P6-25-FIX: Lossless conversion via model_dump() preserves all fields
        signal_dicts = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in stagnation_signals
        ] if stagnation_signals else []

        trigger = self._creativity_engine.should_activate(
            stagnation_signals=signal_dicts,
            task_tags=task_tags,
            conventional_failed=conventional_failed,
        )

        if trigger is None:
            return None

        trigger.task_id = task_id
        session = self._creativity_engine.create_session(
            task_id=task_id,
            trigger=trigger,
        )

        logger.info(
            f"Creativity engine activated for task {task_id}: "
            f"session {session.id}, trigger={trigger.trigger_type}"
        )
        return {
            "session_id": session.id,
            "trigger_type": trigger.trigger_type,
            "agent_count": session.agent_count,
            "assignments": [
                {"persona": a.persona_atom, "tone": a.tone_atom}
                for a in session.assignments
            ],
        }
```

#### 7.3 Integration point in `record_task_outcome`

Add at the end of `record_task_outcome()`, after stagnation check:

```python
        # Phase 6: Check creativity trigger based on stagnation signals
        # FM-P6-48-FIX: stagnation_signals is scoped inside the diversity_engine
        # block above; this code must be placed INSIDE that block (after the
        # diversity snapshot persistence) so stagnation_signals is in scope.
        # FM-P6-17-FIX: Use `results` (the dict defined at line 346), not `result`.
            creativity_info = None
            if stagnation_signals:
                creativity_info = self._check_creativity_trigger(
                    task_id=task_id,
                    stagnation_signals=stagnation_signals,
                )
            if creativity_info is not None:
                results["creativity_session"] = creativity_info
```

---

## Part 8: TopologyRouter Integration

### Modified file: `src/uagents/engine/topology_router.py`

#### 8.1 Enable `debate` topology for creative/novel tasks

In `TopologyRouter.route()`, add debate selection **before** the hierarchical_team
default case and **after** the parallel_swarm check. Must return `RoutingResult`
inline (matching existing code style) with string literal model names
(FM-P6-18-FIX, FM-P6-19-FIX, FM-P6-42-FIX):

```python
        # Phase 6: Creative/novel tasks use debate topology
        # Note: UNPRECEDENTED is excluded from solo routing (line 287), and
        # this check comes after parallel_swarm, so debate only fires for
        # tasks that are NOT fully_decomposable+independent (correct: debate
        # tasks inherently involve coupled reasoning).
        if (analysis.novelty == Novelty.UNPRECEDENTED
                and analysis.exploration_vs_execution == ExplorationExecution.PURE_EXPLORATION
                and analysis.quality_criticality in (QualityCriticality.HIGH, QualityCriticality.CRITICAL)):
            return RoutingResult(
                pattern="debate",
                agent_count=3,
                role_assignments=[
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative exploration (advocate)"},
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative exploration (challenger)"},
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative synthesis (judge)"},
                ],
                inject_scout=False,  # Debate handles novelty internally
                rationale="Unprecedented + pure exploration + high/critical -> debate topology",
            )
```

---

## Part 9: Directory Scaffold

### Modified file: `src/uagents/state/directory.py`

Add creativity directories to `INSTANCE_DIRS` (FM-P6-35-FIX: the class uses `INSTANCE_DIRS`, not `REQUIRED_DIRS`):

```python
        # Phase 6: Creativity directories
        "state/creativity/",
        "state/creativity/sessions/",
        "state/creativity/evaluations/",
```

---

## Part 9.5: Audit Integration (FM-P6-24-FIX, FM-P6-36-FIX)

### Modified file: `src/uagents/models/audit.py`

Add `CreativityLogEntry` model (writes to the `CREATIVITY` stream, not `EVOLUTION`):

```python
class CreativityLogEntry(BaseLogEntry):
    """Creativity engine audit log entry — Phase 6.

    Tracks creative session lifecycle: creation, evaluation, metrics.
    Uses the CREATIVITY log stream (not EVOLUTION/governance).
    """

    stream: Literal[LogStream.CREATIVITY] = LogStream.CREATIVITY
    event_type: str  # "creative_session_created", "creative_session_evaluated"
    session_id: str = ""
    task_id: str = ""
    trigger_type: str = ""
    agent_count: int = 0
    guilford_fluency: int = 0
    guilford_flexibility: int = 0
    guilford_originality: float = 0.0
    guilford_elaboration: float = 0.0
    vdi_score: float = 0.0
    detail: str = ""
```

### Modified file: `src/uagents/audit/logger.py`

Add import and `log_creativity()` method:

```python
# Add to imports:
from ..models.audit import CreativityLogEntry

# Add method to AuditLogger class:
    def log_creativity(self, entry: CreativityLogEntry) -> None:
        self.writers[LogStream.CREATIVITY].append(entry)
```

### Modified code in `src/uagents/engine/creativity_engine.py`

Replace `log_governance()` calls with `log_creativity()`:

```python
# In create_session(), replace the audit_logger block with:
        if self.audit_logger is not None:
            from ..models.audit import CreativityLogEntry
            self.audit_logger.log_creativity(CreativityLogEntry(
                id=generate_id("clog"),
                timestamp=now,
                event_type="creative_session_created",
                session_id=session.id,
                task_id=task_id,
                trigger_type=trigger.trigger_type,
                agent_count=count,
                detail=f"trigger={trigger.trigger_type}",
            ))

# In evaluate_session(), replace the audit_logger block with:
        if self.audit_logger is not None:
            from ..models.audit import CreativityLogEntry
            self.audit_logger.log_creativity(CreativityLogEntry(
                id=generate_id("clog"),
                timestamp=now,
                event_type="creative_session_evaluated",
                session_id=session.id,
                task_id=session.task_id,
                guilford_fluency=guilford.fluency,
                guilford_flexibility=guilford.flexibility,
                guilford_originality=guilford.originality,
                guilford_elaboration=guilford.elaboration,
                vdi_score=vdi_score,
                detail=f"Session {session_id} evaluation complete",
            ))
```

---

## Part 10: Implementation Sequence

```
Step 1: Models — src/uagents/models/creativity.py + src/uagents/models/audit.py (CreativityLogEntry)
        Dependencies: models/base.py (FrameworkModel, generate_id)

Step 2: Config — core/creativity.yaml
        Dependencies: None (pure YAML)

Step 3: Directory scaffold — modify src/uagents/state/directory.py
        Dependencies: None (add lines to INSTANCE_DIRS)

Step 4: PersonaAssigner — src/uagents/engine/persona_assigner.py
        Dependencies: models/creativity.py, models/voice.py, state/yaml_store.py

Step 5: GuilfordMetrics — src/uagents/engine/guilford_metrics.py
        Dependencies: models/creativity.py, diversity_engine.py (TF-IDF functions)

Step 6: AuditLogger integration — modify src/uagents/audit/logger.py (add log_creativity)
        Dependencies: Step 1 (CreativityLogEntry in audit.py)

Step 7: CreativityEngine — src/uagents/engine/creativity_engine.py
        Dependencies: PersonaAssigner, GuilfordMetrics, DiversityEngine, AuditLogger (log_creativity)

Step 8: Orchestrator integration — modify src/uagents/engine/orchestrator.py
        Dependencies: CreativityEngine

Step 9: TopologyRouter integration — modify src/uagents/engine/topology_router.py
        Dependencies: None (add condition to existing route() method)
```

Dependency graph:
```
Step 1 ──→ Step 4 ──→ Step 7 ──→ Step 8
Step 1 ──→ Step 5 ──→ Step 7
Step 1 ──→ Step 6 ──→ Step 7
Step 2 (parallel with 1)
Step 3 (parallel with 1-2)
Step 9 (parallel with 8)
```

---

## Part 11: Failure Modes

### Original (design-time) failure modes

| ID | Severity | Location | Description | Mitigation | Status |
|---|---|---|---|---|---|
| FM-P6-01 | MEDIUM | PersonaAssigner._build_assignments | Same persona+tone combo as previous session | Rotation check via hash comparison, shift by 1 | DOCUMENTED |
| FM-P6-02 | HIGH | PersonaAssigner.assign | Fewer creative personas than requested agents | Fail-loud with PersonaAssignmentError | DOCUMENTED |
| FM-P6-03 | HIGH | PersonaAssigner.assign | Fewer tone atoms than requested agents | Fail-loud with PersonaAssignmentError | DOCUMENTED |
| FM-P6-04 | MEDIUM | CreativityEngine.create_session | agent_count outside [min, max] range | Fail-loud with CreativityError | DOCUMENTED |
| FM-P6-05 | LOW | GuilfordMetrics._compute_flexibility | All ideas in one cluster (no flexibility) | Returns 1 (single cluster is valid) | DOCUMENTED |
| FM-P6-06 | MEDIUM | GuilfordMetrics._compute_originality | Empty corpus → fallback to pairwise distance | Documented behavior, not an error | DOCUMENTED |
| FM-P6-07 | HIGH | CreativityEngine phase transitions | Wrong phase for recorded data | Fail-loud with CreativityError on phase mismatch | DOCUMENTED |
| FM-P6-08 | MEDIUM | CreativityEngine._assignments_to_profiles | Hardcoded language_english for VDI profiles | Acceptable for Phase 6; domain language integration deferred | DOCUMENTED |
| FM-P6-09 | LOW | GuilfordMetrics._compute_elaboration | ELABORATION_THRESHOLD arbitrary at 50 words | Configurable threshold deferred; 50 is reasonable default | DOCUMENTED |
| FM-P6-10 | HIGH | CreativityEngine.evaluate_session | Session not found | Fail-loud with CreativityError | DOCUMENTED |
| FM-P6-11 | MEDIUM | TopologyRouter.route | Debate topology conditions narrow (UNPRECEDENTED+PURE_EXPLORATION+HIGH/CRITICAL) | Only fires for non-decomposable tasks; correct for debate semantics | DOCUMENTED |
| FM-P6-12 | LOW | CreativityEngine._compute_feasibility_proxy | Feasibility is a proxy, not real execution | Documented; real feasibility requires Phase 7+ | DOCUMENTED |
| FM-P6-13 | MEDIUM | PersonaAssigner._load_voice_atoms | roles/voice.yaml missing or malformed | FileNotFoundError propagates (fail-loud) | DOCUMENTED |
| FM-P6-14 | LOW | CreativityEngine.get_session_history | No evaluations directory yet | Returns empty list | DOCUMENTED |
| FM-P6-15 | MEDIUM | Orchestrator._check_creativity_trigger | Stagnation signals have varying attribute formats | Defensive getattr() with defaults for signal conversion | DOCUMENTED |

### Review-identified failure modes (Step 3-4)

| ID | Severity | Location | Description | Mitigation | Status |
|---|---|---|---|---|---|
| FM-P6-16 | CRITICAL | creativity_engine._save_last_session_hash | dict passed to YamlStore.write() which requires FrameworkModel | Use write_raw() instead | FIXED |
| FM-P6-17 | CRITICAL | orchestrator.record_task_outcome (Part 7.3) | `result` vs `results` variable name mismatch | Changed to `results` | FIXED |
| FM-P6-18 | CRITICAL | topology_router.route (Part 8.1) | Undefined `model` variable in debate role_assignments | Use string literal `"sonnet"` | FIXED |
| FM-P6-19 | HIGH | topology_router.route (Part 8.1) | Debate block has no return statement, code is dead | Added `return RoutingResult(...)` | FIXED |
| FM-P6-20 | HIGH | persona_assigner.assign | `.category.value` fails because `use_enum_values=True` stores raw string | Compare directly to string | FIXED |
| FM-P6-21 | MEDIUM | creativity_engine._load_session/_save_session | TOCTOU: load-modify-save without locking allows concurrent corruption | YamlStore.write() uses flock; document single-threaded assumption | DOCUMENTED |
| FM-P6-22 | MEDIUM | creativity_engine phase transitions | No monotonicity check; phase can regress via YAML editing | Per-method checks are sufficient; YAML editing is out of scope | DOCUMENTED |
| FM-P6-23 | MEDIUM | guilford_metrics._compute_flexibility | Mutates caller's DivergentIdea.category in-place | Intentional: assigns cluster labels for transparency; document in docstring | DOCUMENTED |
| FM-P6-24 | MEDIUM | creativity_engine audit logging | GovernanceLogEntry goes to EVOLUTION stream, not CREATIVITY | Added CreativityLogEntry + log_creativity() | FIXED |
| FM-P6-25 | MEDIUM | orchestrator._check_creativity_trigger | Lossy signal conversion: only 3 of 8 StagnationSignal fields preserved | Use model_dump() for lossless conversion (see FM-P6-25-FIX below) | FIXED |
| FM-P6-26 | LOW | creativity_engine.should_activate/create_session | task_id="" then mutated twice (redundant) | Remove mutation in create_session; only set in _check_creativity_trigger | FIXED |
| FM-P6-27 | MEDIUM | creativity_engine._assignments_to_profiles | style_atom ignored, VDI artificially low | Include style in VoiceProfile; acceptable VDI limitation for Phase 6 | DOCUMENTED |
| FM-P6-28 | LOW | persona_assigner._build_assignments | Rotation only checks previous session; degenerates for small pools | Acceptable for Phase 6; richer history deferred to Phase 8 | DOCUMENTED |
| FM-P6-29 | LOW | persona_assigner._load_voice_atoms | Mutates raw dict from read_raw() in-place | Copy dict before mutation | FIXED |
| FM-P6-30 | LOW | creativity_engine._compute_quality_proxy | selected_idea_ids not validated against divergent_ideas | Clamped to [0, 1.0]; validation deferred | DOCUMENTED |
| FM-P6-31 | MEDIUM | creativity_engine.record_cross_pollinations | original_idea_id not validated against existing ideas | Add validation check | FIXED |
| FM-P6-32 | MEDIUM | creativity_engine.record_cross_pollinations | No check preventing self-review (violates blind protocol) | Add reviewer_slot != author_slot check | FIXED |
| FM-P6-33 | LOW | creativity_engine.evaluate_session | Empty ideas after YAML roundtrip hits ValueError without session context | GuilfordMetrics raises ValueError; acceptable fail-loud | DOCUMENTED |
| FM-P6-34 | HIGH | models/creativity.py CreativePhase | IntEnum + use_enum_values causes .name AttributeError on error messages | Use `CreativePhase(val).name` | FIXED |
| FM-P6-35 | HIGH | directory.py (Part 9) | Design says REQUIRED_DIRS which doesn't exist; should be INSTANCE_DIRS | Changed to INSTANCE_DIRS | FIXED |
| FM-P6-36 | MEDIUM | audit/logger.py | No log_creativity() method; CREATIVITY stream permanently empty | Added CreativityLogEntry + log_creativity() (Part 9.5) | FIXED |
| FM-P6-37 | MEDIUM | creativity_engine.get_session_history | Bypasses YamlStore path validation by directly accessing base_dir | Pre-existing pattern in codebase; acceptable | DOCUMENTED |
| FM-P6-38 | LOW | creativity_engine vs guilford_metrics | Duplicated TF-IDF novelty/originality computation | Intentional: originality=Guilford dimension, novelty=session metric | DOCUMENTED |
| FM-P6-39 | LOW | orchestrator._check_creativity_trigger | Redundant str() wrapping on already-string values | Removed via FM-P6-25 fix (use model_dump()) | FIXED |
| FM-P6-40 | MEDIUM | creativity_engine.create_session | No budget/cost gate check before token-intensive creative sessions | Add budget pressure check; see FM-P6-40-FIX below | FIXED |
| FM-P6-41 | LOW | models/creativity.py CreativeSession | default_factory on id is redundant (always explicitly set) | Cosmetic; keep for safety if model is constructed without explicit id | DOCUMENTED |
| FM-P6-42 | HIGH | topology_router.route (Part 8.1) | Local variables don't match existing RoutingResult inline construction | Rewritten to inline RoutingResult (merged with FM-P6-18/19 fix) | FIXED |
| FM-P6-43 | LOW | persona_assigner._build_assignments | Rotation shift by 1 is predictable for larger pools | Acceptable; advanced rotation deferred to Phase 8 | DOCUMENTED |
| FM-P6-44 | LOW | creativity_engine._compute_idea_diversity | None → 0.0 conflates "can't compute" with "zero diversity" | Document that 0.0 means "zero or not computable"; sentinel value deferred | DOCUMENTED |
| FM-P6-45 | LOW | models/creativity.py CreativeAgentAssignment | temperature_offset has no ge/le constraint despite +-0.3 limit | Add `Field(default=0.0, ge=-0.3, le=0.3)` | FIXED |
| FM-P6-46 | LOW | models/creativity.py CreativePhase | IntEnum serializes to opaque integers in YAML | Acceptable; consistent with existing IntEnum usage (e.g., EvolutionTier) | DOCUMENTED |
| FM-P6-47 | MEDIUM | creativity_engine lifecycle | No cleanup for abandoned/stuck sessions | Add note for Phase 7; no cleanup in Phase 6 | DEFERRED |
| FM-P6-48 | HIGH | orchestrator.record_task_outcome (Part 7.3) | stagnation_signals variable scope: NameError or incomplete coverage | Place creativity check inside diversity_engine block | FIXED |
| FM-P6-49 | LOW | orchestrator.__init__ (Part 7.1) | Parameter ordering must be after alignment_verifier | Document: add as last keyword-only param | DOCUMENTED |

---

## Part 12: Verification Checklist

1. `uv run pytest tests/test_engine/test_creativity_phase6.py -v` — all Phase 6 tests pass
2. `uv run pytest --tb=short -q` — full suite (1238+ tests) passes, no regressions
3. Models serialize/deserialize correctly through YamlStore
4. PersonaAssigner rejects insufficient voice atoms (fail-loud)
5. Phase transition enforcement: recording ideas in wrong phase raises CreativityError
6. Rotation constraint: consecutive sessions never repeat the same persona+tone combo
7. Guilford metrics: fluency counts distinct ideas, flexibility counts clusters, originality uses TF-IDF
8. Orchestrator creates creativity session when stagnation threshold met
9. TopologyRouter selects debate for unprecedented + pure exploration + high/critical tasks
10. Audit logging for session creation and evaluation
11. Directory scaffold includes creativity directories
12. No TODOs, no fallback defaults, all errors fail-loud
