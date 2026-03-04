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
            try:
                return state["last_session_hash"]  # IFM-N53: no .get() fallback
            except KeyError:
                raise CreativityError(
                    "state/creativity/engine_state.yaml exists but missing "
                    "'last_session_hash' key. File may be corrupted."
                )
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

        # FM-P6-IMP-007-FIX: Update rotation state BEFORE session file
        # so if session write fails, the hash is already updated (safe side:
        # worst case we skip a combo, but don't repeat one)
        self._last_session_hash = combo_hash
        self._save_last_session_hash(combo_hash)

        # Persist session
        self.yaml_store.write(
            f"state/creativity/sessions/{session.id}.yaml", session,
        )

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

        # FM-P6-IMP-012-FIX: Cross-pollination must produce at least 1 result
        if not results:
            raise CreativityError(
                f"No cross-pollination results provided for session {session_id}. "
                f"Cross-pollination phase must produce at least 1 result."
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

        # FM-P6-IMP-003-FIX: Validate selected_idea_ids reference existing ideas
        idea_ids = {idea.id for idea in session.divergent_ideas}
        invalid = set(synthesis.selected_idea_ids) - idea_ids
        if invalid:
            raise CreativityError(
                f"Synthesis references non-existent ideas: {sorted(invalid)} "
                f"in session {session_id}. Valid IDs: {sorted(idea_ids)}"
            )

        # FM-P6-IMP-013-FIX: Synthesis must select at least 1 idea
        if not synthesis.selected_idea_ids:
            raise CreativityError(
                f"Synthesis must select at least 1 idea for session {session_id}."
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
        profiles = self._assignments_to_profiles(session.assignments)
        # FM-P6-IMP-006-FIX: Fail-loud if assignments are empty when agent_count >= 3
        if len(profiles) < 2 and session.agent_count >= 3:
            raise CreativityError(
                f"Session {session_id} has {len(profiles)} profiles but "
                f"agent_count={session.agent_count}. Data corruption suspected."
            )
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
    ) -> list[VoiceProfile]:
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
            return 0.0  # Cannot compute pairwise distance with < 2 texts
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
