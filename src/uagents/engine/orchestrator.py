"""Orchestrator decision logic for multi-agent coordination.
Spec reference: Section 4.3 (Orchestrator Role), Section 5 (Topology).

Phase 1.5: Budget-aware orchestration (Section 18).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..audit.logger import AuditLogger
from ..models.base import generate_id
from ..models.capability import ModelPreference
from ..models.resource import BudgetPressureLevel
from ..models.task import Task, TaskStatus, TaskTopology, TopologyAssignment
from ..models.team import SubTask, Team, TeamStatus
from ..models.voice import VoiceProfile
from ..state.yaml_store import YamlStore
from .review_engine import ReviewEngine
from .task_lifecycle import TaskLifecycle
from .team_manager import TeamManager, TeamCreationError
from .topology_router import TopologyRouter

if TYPE_CHECKING:
    from .alignment_verifier import AlignmentVerifier
    from .budget_tracker import BudgetTracker
    from .cache_manager import CacheManager
    from .capability_tracker import CapabilityTracker
    from .context_pressure_monitor import ContextPressureMonitor
    from .cost_gate import CostGate
    from .creativity_engine import CreativityEngine
    from .diversity_engine import DiversityEngine
    from .domain_manager import DomainManager
    from .evolution_engine import EvolutionEngine
    from .objective_anchor import ObjectiveAnchor
    from .pressure_field import PressureFieldCoordinator
    from .prompt_composer import PromptComposer
    from .quorum_manager import QuorumManager
    from .rate_limiter import RateLimiter
    from .ring_enforcer import RingEnforcer
    from .risk_scorecard import RiskScorecard
    from .scout_spawner import ScoutSpawner
    from .self_reconfigurer import SelfReconfigurer
    from .skill_library import SkillLibrary
    from .stagnation_detector import StagnationDetector
    from .tool_loader import ToolLoader

logger = logging.getLogger("uagents.orchestrator")


class ResourceConstrainedError(RuntimeError):
    """Raised when resource constraints prevent task processing."""


class Orchestrator:
    """Central orchestration logic for task processing.

    The orchestrator is NOT an agent itself -- it's the decision engine
    that the orchestrator agent (or the framework in solo mode) invokes.

    Orchestration pipeline:
    1. Receive task
    2. Analyze via TopologyRouter
    3. Select topology and create team
    4. Decompose task into subtasks
    5. Assign subtasks to team members
    6. Monitor progress
    7. Trigger review when workers complete
    8. Handle review verdict (complete or re-plan)
    9. Dissolve team on completion
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        topology_router: TopologyRouter,
        team_manager: TeamManager,
        task_lifecycle: TaskLifecycle,
        review_engine: ReviewEngine,
        audit_logger: AuditLogger | None = None,
        budget_tracker: BudgetTracker | None = None,
        rate_limiter: RateLimiter | None = None,
        cost_gate: CostGate | None = None,
        capability_tracker: CapabilityTracker | None = None,
        # Phase 3.5 (IFM-N51): All optional, stored as self._X attributes
        constitution_path: Path | None = None,
        prompt_composer: PromptComposer | None = None,
        cache_manager: CacheManager | None = None,
        skill_library: SkillLibrary | None = None,
        context_pressure_monitor: ContextPressureMonitor | None = None,
        tool_loader: ToolLoader | None = None,
        ring_enforcer: RingEnforcer | None = None,
        self_reconfigurer: SelfReconfigurer | None = None,
        # Phase 4: Evolution engine (optional)
        evolution_engine: EvolutionEngine | None = None,
        # Phase 5: Governance components
        quorum_manager: QuorumManager | None = None,
        objective_anchor: ObjectiveAnchor | None = None,
        risk_scorecard: RiskScorecard | None = None,
        alignment_verifier: AlignmentVerifier | None = None,
        # Phase 6: Creativity engine
        creativity_engine: CreativityEngine | None = None,
        # Phase 7: Self-expansion
        scout_spawner: ScoutSpawner | None = None,
        pressure_field_coordinator: PressureFieldCoordinator | None = None,
        domain_manager: DomainManager | None = None,
    ):
        self.yaml_store = yaml_store
        self.topology_router = topology_router
        self.team_manager = team_manager
        self.task_lifecycle = task_lifecycle
        self.review_engine = review_engine
        self.audit_logger = audit_logger
        self.budget_tracker = budget_tracker
        self.rate_limiter = rate_limiter
        self.cost_gate = cost_gate
        self.diversity_engine: DiversityEngine | None = None
        self.stagnation_detector: StagnationDetector | None = None
        self.capability_tracker = capability_tracker

        # Phase 3.5 (IFM-N51): Optional components stored with underscore prefix
        self._constitution_path = constitution_path
        self._prompt_composer = prompt_composer
        self._cache_manager = cache_manager
        self._skill_library = skill_library
        self._context_pressure_monitor = context_pressure_monitor
        self._tool_loader = tool_loader
        self._ring_enforcer = ring_enforcer
        self._self_reconfigurer = self_reconfigurer
        self._evolution_engine = evolution_engine
        # Phase 5: Governance
        self._quorum_manager = quorum_manager
        self._objective_anchor = objective_anchor
        self._risk_scorecard = risk_scorecard
        self._alignment_verifier = alignment_verifier
        self._creativity_engine = creativity_engine
        # Phase 7: Self-expansion
        self._scout_spawner = scout_spawner
        self._pressure_field_coordinator = pressure_field_coordinator
        self._domain_manager = domain_manager

        # Phase 3.5: Verify Ring 0 integrity at boot (if enforcer provided)
        if self._ring_enforcer is not None:
            self._ring_enforcer.verify_ring_0_integrity()

    def process_task(
        self, task_id: str, domain_config, actor: str = "orchestrator"
    ) -> dict:
        """Full orchestration pipeline for a task.

        Returns dict with:
        - task: Final task state
        - team: Team record (or None for solo)
        - analysis: TaskAnalysis
        - routing: RoutingResult

        Phase 1.5 additions:
        - Budget pressure check before processing (RED = critical-only)
        - Task budget allocation via BudgetTracker
        - Efficiency recording on completion
        """
        # 0. Budget pressure check (RED = critical-only)
        task = self.task_lifecycle._load_task(task_id)
        if self.budget_tracker is not None:
            pressure = self.budget_tracker.get_pressure()
            if pressure == BudgetPressureLevel.RED:
                if task.priority not in ("high", "critical"):
                    if task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                        self.task_lifecycle.transition(
                            task_id, TaskStatus.PARKED, actor,
                            "Budget RED — non-critical deferred",
                        )
                    raise ResourceConstrainedError(
                        f"Budget pressure RED. Task {task_id} deferred. "
                        f"Window: {self.budget_tracker.get_window().remaining_tokens} tokens remaining."
                    )

        # 0b. Allocate task budget
        budget_annotation = None
        if self.budget_tracker is not None:
            budget_annotation = self.budget_tracker.allocate_task_budget(
                task_type=self._classify_task_type(task),
                complexity=self._classify_complexity(task),
            )

        # 1. Transition to ANALYSIS (was step 2)
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.ANALYSIS, actor, "Starting orchestration"
        )

        # 3. Analyze task
        analysis = self.topology_router.analyze(task)

        # 4. Route to topology
        routing = self.topology_router.route(analysis)

        # 5. Transition to PLANNING
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.PLANNING, actor,
            f"Topology: {routing.pattern} ({routing.agent_count} agents)"
        )

        # 6. Store topology assignment on task
        # TaskTopology fields: pattern (str), analysis (dict), agents (list[TopologyAssignment])
        # TopologyAssignment fields: role (str), agent_id (str), model (ModelPreference)
        task.topology = TaskTopology(
            pattern=routing.pattern,
            analysis=analysis.model_dump(),
            agents=[
                TopologyAssignment(
                    role=a["role"],
                    agent_id="pending",  # Filled when team spawns agents
                    model=ModelPreference(a["model"]),  # IFM-N53: router guarantees this
                )
                for a in routing.role_assignments
            ],
        )

        # 7. Create team — with rollback to PARKED on failure
        try:
            team = self.team_manager.create_team(task, routing, domain_config)
        except TeamCreationError as e:
            logger.error(f"Team creation failed for task {task_id}: {e}")
            self.task_lifecycle.transition(
                task_id, TaskStatus.PARKED, actor,
                f"Team creation failed: {e}"
            )
            raise

        task.team_id = team.id

        # Persist topology and team_id to disk before transition
        # (transition() reloads the task from disk, so in-memory changes must be persisted first)
        current_path = f"{self.task_lifecycle._tasks_base}/active/{task_id}.yaml"
        self.yaml_store.write(current_path, task)

        # 8. Transition to EXECUTING
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.EXECUTING, actor,
            f"Team {team.id} executing with {len(team.members)} agents"
        )

        return {
            "task": task,
            "team": team,
            "analysis": analysis,
            "routing": routing,
        }

    def complete_execution(self, task_id: str, actor: str = "orchestrator") -> Task:
        """Transition task from EXECUTING to REVIEWING.

        Called when all workers have completed their subtasks.
        Phase 1.5: Records actual token usage for rolling average calibration.
        """
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.REVIEWING, actor,
            "All workers complete -- entering mandatory review"
        )

        # Record actual usage for rolling average calibration
        if self.budget_tracker is not None and task.metrics.budget_allocated > 0:
            self.budget_tracker.record_actual_usage(
                task_type=self._classify_task_type(task),
                complexity=self._classify_complexity(task),
                tokens_used=task.metrics.budget_allocated,
            )

        return task

    def handle_verdict(
        self, task_id: str, actor: str = "orchestrator"
    ) -> Task:
        """Handle review verdict and transition appropriately.

        ReviewEngine always transitions REVIEWING -> VERDICT first.
        If review verdict is "pass" or "pass_with_notes":
          VERDICT -> COMPLETE (handled here)
        If review verdict is "fail":
          VERDICT -> PLANNING (already handled by ReviewEngine.submit_review)

        FM-115: After COMPLETE transition, records Phase 2 metrics
        (diversity, stagnation, capability) before team dissolution.
        """
        task = self.task_lifecycle._load_task(task_id)
        if task.review and task.review.verdict in ("pass", "pass_with_notes"):
            task = self.task_lifecycle.transition(
                task_id, TaskStatus.COMPLETE, actor,
                f"Review passed: {task.review.verdict}"
            )

            # FM-115: Record Phase 2 metrics after successful completion
            try:
                topology_used = task.topology.pattern if task.topology else None
                agent_tones: set[str] | None = None
                voice_profiles: list[VoiceProfile] | None = None
                # Collect voice profiles from agent registry if available
                if task.topology and task.topology.agents:
                    agent_tones = set()
                    voice_profiles = []
                    for assignment in task.topology.agents:
                        agent = self._load_agent(assignment.agent_id)
                        if agent and hasattr(agent, "voice") and agent.voice:
                            voice_profiles.append(agent.voice)
                            if agent.voice.tone:
                                agent_tones.add(agent.voice.tone)

                self.record_task_outcome(
                    task_id=task_id,
                    voice_profiles=voice_profiles if voice_profiles else None,
                    topology_used=topology_used,
                    agent_tones=agent_tones if agent_tones else None,
                )
            except OSError as e:
                logger.error(
                    f"Phase 2 metric recording I/O failed for {task_id}: {e}",
                    exc_info=True,
                )
                # I/O failures are retriable — allow task to complete.
                # ValueError/TypeError/etc. propagate as programming bugs.

            # Dissolve team
            if task.team_id:
                self.team_manager.dissolve_team(task.team_id, "Task complete")

        # FM-P4-46: Notify evolution engine on ALL verdicts (pass, fail, partial).
        # Evolution cooldown counts total completed tasks, not just successful ones.
        if self._evolution_engine is not None:
            self._evolution_engine.record_task_completion()

        # Phase 5: Governance checks after task completion
        self._check_governance_after_task()

        return task

    def record_task_outcome(
        self,
        task_id: str,
        agent_outputs: list[str] | None = None,
        voice_profiles: list[VoiceProfile] | None = None,
        topology_used: str | None = None,
        agent_tones: set[str] | None = None,
    ) -> dict:
        """Phase 2: Record task outcome for self-awareness metrics.

        Called after task reaches COMPLETE or VERDICT(fail) status.
        Triggers diversity measurement, stagnation detection, and
        capability tracking.

        FM-87: Uses task.metrics.tokens_used only if > 0.
        FM-96: Handles task.review being None (manual completion).
        FM-115: Called from handle_verdict() — see integration point above.
        FM-116: Falls back to collecting output_text from SubTask records
                when agent_outputs is not explicitly provided.

        Returns dict with measurement results.
        """
        task = self.task_lifecycle._load_task(task_id)
        results: dict = {}

        # FM-96: Determine success and confidence with null guards
        if task.review is not None:
            success = task.review.verdict in ("pass", "pass_with_notes")
            confidence = task.review.reviewer_confidence
        elif task.status == TaskStatus.COMPLETE:
            # FM-96: Manual completion without review — assume success, low confidence
            success = True
            confidence = 0.0
        else:
            # VERDICT(fail) without review — should not happen, but safe default
            success = False
            confidence = 0.0

        # FM-87: Only pass tokens_used when actually populated (> 0)
        tokens_used = task.metrics.tokens_used if task.metrics.tokens_used > 0 else 0

        # Capability tracking
        if self.capability_tracker is not None:
            task_type = self._classify_task_type(task)
            entry = self.capability_tracker.record_outcome(
                task_type=task_type,
                success=success,
                tokens_used=tokens_used,
                review_confidence=confidence,
            )
            results["capability"] = entry.model_dump()

        # FM-116: Collect agent outputs from subtasks if not explicitly provided
        if agent_outputs is None and task.subtasks and task.team_id:
            collected = []
            domain = self.task_lifecycle.domain
            teams_base = f"instances/{domain}/state/teams"
            for subtask_id in task.subtasks:
                try:
                    st_data = self.yaml_store.read_raw(
                        f"{teams_base}/{task.team_id}/subtasks/{subtask_id}.yaml"
                    )
                    output_text = st_data.get("output_text")
                    if output_text:
                        collected.append(output_text)
                except FileNotFoundError:
                    continue
            if len(collected) >= 2:
                agent_outputs = collected

        # Diversity measurement (only for multi-agent tasks)
        if (
            self.diversity_engine is not None
            and agent_outputs is not None
            and len(agent_outputs) >= 2
        ):
            srd = self.diversity_engine.compute_srd(
                task_id, agent_outputs, voice_profiles
            )
            if srd is None:
                # FM-85: All outputs empty → no diversity to measure
                logger.info(f"SRD skipped for task {task_id}: insufficient non-empty outputs")
                return results
            results["srd"] = srd.model_dump()

            # Stagnation detection
            stagnation_signals: list = []
            if self.stagnation_detector is not None:
                stagnation_signals = self.stagnation_detector.check_all(
                    srd=srd,
                    topology_used=topology_used,
                    agent_tones=agent_tones,
                )
                results["stagnation_signals"] = [
                    s.model_dump() for s in stagnation_signals
                ]

            # Create and persist diversity snapshot
            snapshot = self.diversity_engine.create_snapshot(
                task_id, srd, stagnation_signals, agent_outputs
            )
            self.diversity_engine.append_srd_history(srd.composite_srd)
            results["diversity_snapshot"] = snapshot.model_dump()

            # Log to diversity audit stream
            if self.audit_logger is not None:
                from ..models.audit import DiversityLogEntry
                self.audit_logger.log_diversity(DiversityLogEntry(
                    id=generate_id("div"),
                    timestamp=snapshot.timestamp,
                    task_id=task_id,
                    srd_composite=srd.composite_srd,
                    text_diversity=srd.text_diversity,
                    vdi_score=srd.vdi.vdi_score if srd.vdi else None,
                    agent_count=srd.agent_count,
                    stagnation_signals=[s.model_dump() for s in stagnation_signals],
                    health_status=srd.health_status,
                ))

            # Phase 6: Check creativity trigger
            # FM-P6-48-FIX: scoped inside diversity_engine block for stagnation_signals access.
            # FM-P6-17-FIX: Use `results` (the dict defined at top of method).
            # FM-P6-IMP-010/011-FIX: Always check creativity trigger when engine is
            # available — stagnation is only one activation path; task tags, conventional
            # failure, and human requests should also be checked.
            if self._creativity_engine is not None:
                creativity_info = self._check_creativity_trigger(
                    task_id=task_id,
                    stagnation_signals=stagnation_signals,
                )
                if creativity_info is not None:
                    results["creativity_session"] = creativity_info

        # Phase 7: Scout spawning check — OUTSIDE diversity block so solo
        # tasks can trigger scouts via framework-level stagnation.
        # FM-P7-067-FIX / DR-Issue-15-FIX
        if self._scout_spawner is not None:
            # Collect stagnation signals (may be from diversity block or empty)
            scout_stagnation = results.get("stagnation_signals", [])
            # For solo tasks, run framework-level stagnation check directly
            if not scout_stagnation and self.stagnation_detector is not None:
                fw_signals = self.stagnation_detector.check_framework_stagnation()
                scout_stagnation = [s.model_dump() for s in fw_signals]

            # DR-Issue-22-FIX: Budget pressure check for scout spawning
            skip_scout = False
            if self.budget_tracker is not None:
                pressure = self.budget_tracker.get_pressure()
                if pressure in (BudgetPressureLevel.RED, BudgetPressureLevel.ORANGE):
                    logger.info(
                        f"Skipping scout spawn for task {task_id}: "
                        f"budget pressure is {pressure}"
                    )
                    skip_scout = True

            if not skip_scout and scout_stagnation:
                # FM-P7-IMP-019-FIX: Check metric_name, not just level.
                # Team-level signals include VDI stagnation too — only SRD
                # signals should trigger the diversity floor scout.
                srd_below_floor = any(
                    s.get("metric_name") == "srd" for s in scout_stagnation
                )
                targets = self._scout_spawner.generate_targets(
                    stagnation_signals=scout_stagnation,
                    srd_below_floor=srd_below_floor,
                )
                if targets:
                    # Save the highest-priority target
                    self._scout_spawner.save_target(targets[0])
                    results["scout_target"] = {
                        "target_id": targets[0].id,
                        "target_type": str(targets[0].target_type),
                        "description": targets[0].description,
                        "priority": targets[0].priority,
                    }

        return results

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
            if pressure in (BudgetPressureLevel.RED, BudgetPressureLevel.ORANGE):
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

    def _load_agent(self, agent_id: str) -> AgentRegistryEntry | None:
        """Load agent registry entry by ID. Returns None if not found."""
        from ..models.agent import AgentRegistryEntry
        # Use the same base path convention as AgentSpawner
        agents_base = f"instances/{self.task_lifecycle.domain}/state/agents"
        path = f"{agents_base}/{agent_id}/status.yaml"
        try:
            return self.yaml_store.read(path, AgentRegistryEntry)
        except FileNotFoundError:
            return None
        # ValueError = corrupt YAML — let it propagate as a bug

    def generate_decomposition_prompt(self, task: Task) -> str:
        """Generate a prompt for the orchestrator agent to decompose a task.

        The orchestrator agent (Claude Code) uses this to decide how to
        break down the task into subtasks.
        """
        return f"""## Task Decomposition

Decompose this task into subtasks for your team:

**Task:** {task.title}
**Description:** {task.description}

**Team size:** {len(task.topology.agents) if task.topology else 'unknown'} agents
**Topology:** {task.topology.pattern if task.topology else 'unknown'}

### Instructions:
1. Break the task into 2-5 independent subtasks
2. Each subtask should be completable by one agent
3. Minimize dependencies between subtasks
4. Include clear acceptance criteria for each subtask

### Output Format:
For each subtask, provide:
- title: Brief title
- description: What the agent should do
- acceptance_criteria: How to know it's done
"""

    # ── Phase 1.5: Task classification helpers (FM-40, FM-41) ──

    @staticmethod
    def _classify_task_type(task: Task) -> str:
        """Classify task into type for budget estimation.

        FM-40: Priority-ordered matching — most specific patterns first,
        then general. Returns a key matching cold_seeds in resource-awareness.yaml.
        """
        title_lower = task.title.lower()
        desc_lower = (task.description or "").lower()
        combined = title_lower + " " + desc_lower

        # Specific Phase 1.5 task types (most specific first)
        if "canary" in combined:
            return "canary_suite"
        if "evolution" in combined or "evolve" in combined:
            return "evolution_proposal"
        if "decompos" in combined or "subtask" in combined:
            return "decomposition"
        if "skill" in combined and ("valid" in combined or "crystal" in combined):
            return "skill_validation"
        if "review" in combined:
            return "review"
        # General patterns (less specific)
        if any(w in combined for w in ("fix", "typo", "bug", "patch")):
            return "simple_fix"
        if any(w in combined for w in ("research", "analyze", "investigat", "survey")):
            return "research"
        if any(w in combined for w in ("implement", "add", "create", "build")):
            return "feature"
        return "feature"

    def _classify_complexity(self, task: Task) -> str:
        """Classify task complexity for budget estimation.

        FM-41 Phase 2: Uses historical data from CapabilityTracker when
        available (>= 10 samples). Falls back to keyword + length heuristic.
        """
        # Phase 2: Try learned classification first
        if self.capability_tracker is not None:
            task_type = self._classify_task_type(task)
            learned = self.capability_tracker.get_estimated_complexity(task_type)
            if learned is not None:
                return learned

        # Fallback: keyword + length heuristic (Phase 1.5)
        desc = task.description or ""
        desc_lower = desc.lower()
        if any(w in desc_lower for w in ("trivial", "simple", "quick", "minor")):
            return "small"
        if any(w in desc_lower for w in ("complex", "large", "extensive", "major", "refactor")):
            return "large"

        desc_len = len(desc)
        if desc_len < 100:
            return "small"
        if desc_len < 400:
            return "medium"
        return "large"

    # ── Phase 4: Evolution integration ──

    def trigger_evolution_if_ready(
        self,
        trigger: str,
        trigger_detail: str,
        component: str,
        diff: str,
        rationale: str,
    ) -> EvolutionRecord | None:
        """Check if evolution cooldown has elapsed and run if ready.

        Called by the autonomous run loop (Phase 5) or manually.
        Returns EvolutionRecord if evolution was run, None if cooldown active.

        DR-10: Validates trigger is a valid ObservationTrigger value before
        constructing the proposal. Invalid triggers raise ValueError.
        """
        if self._evolution_engine is None:
            return None
        if not self._evolution_engine.can_evolve():
            return None

        from ..models.evolution import EvolutionRecord, ObservationTrigger

        # DR-10: Validate trigger value — fail loud on invalid trigger
        try:
            trigger_enum = ObservationTrigger(trigger)
        except ValueError:
            raise ValueError(
                f"Invalid evolution trigger '{trigger}'. "
                f"Valid triggers: {[t.value for t in ObservationTrigger]}"
            )

        proposal = self._evolution_engine.create_proposal(
            component=component,
            diff=diff,
            rationale=rationale,
            trigger=trigger_enum,
            trigger_detail=trigger_detail,
        )
        return self._evolution_engine.run_evolution(proposal)

    # ── Phase 5: Governance integration ──

    _task_completion_count: int = 0

    def _check_governance_after_task(self) -> None:
        """Run governance checks after task completion.

        S-CR-01/02: CRITICAL risk and alignment failures raise errors
        (not just logged). Governance controls must actually enforce.
        """
        self._task_completion_count += 1
        task_count = self._task_completion_count

        # AlignmentVerifier: periodic or post-Tier 2
        if self._alignment_verifier is not None:
            tier2_just_completed = self._last_evolution_was_tier2()
            if self._alignment_verifier.should_check(
                task_count, tier2_just_completed
            ):
                agent_data = self._collect_agent_alignment_data()
                trigger = "post_tier2_evolution" if tier2_just_completed else "periodic"
                report = self._alignment_verifier.run_checks(
                    trigger=trigger,
                    task_count=task_count,
                    agent_data=agent_data,
                )
                if not report.overall_passed:
                    # S-CR-02-FIX: Alignment failure must be enforced, not just logged
                    logger.error(
                        f"Alignment verification FAILED: {report.recommendations}"
                    )
                    from ..models.governance import HumanDecision
                    from ..models.base import generate_id
                    from datetime import datetime, timezone
                    decision = HumanDecision(
                        id=generate_id("hd"),
                        created_at=datetime.now(timezone.utc),
                        decision_type="alignment_failure",
                        summary=(
                            f"Alignment check failed ({trigger}). "
                            f"Recommendations: {report.recommendations}"
                        ),
                        proposed_by="orchestrator",
                        urgency="high",
                        blocking=True,
                    )
                    self.yaml_store.write(
                        f"state/governance/pending_human_decisions/{decision.id}.yaml",
                        decision,
                    )
                    raise RuntimeError(
                        f"Alignment verification FAILED. "
                        f"Human decision queued: {decision.id}. "
                        f"Recommendations: {report.recommendations}"
                    )

        # RiskScorecard: periodic (every 10 tasks)
        if self._risk_scorecard is not None and task_count > 0 and task_count % 10 == 0:
            metrics = self._collect_risk_metrics()
            assessment = self._risk_scorecard.compute(metrics)
            from ..models.governance import RiskLevel
            if assessment.aggregate_level == RiskLevel.CRITICAL:
                # S-CR-01-FIX: CRITICAL risk must halt, not just log
                logger.error(
                    f"Risk assessment CRITICAL: {assessment.aggregate_score:.2f}. "
                    f"Halting: {assessment.halted_operations}"
                )
                if self._evolution_engine is not None:
                    self._evolution_engine.pause(
                        f"CRITICAL risk: {assessment.aggregate_score:.2f}. "
                        f"Actions: {assessment.actions_required}"
                    )
                raise RuntimeError(
                    f"CRITICAL risk assessment ({assessment.aggregate_score:.2f}). "
                    f"Halted: {assessment.halted_operations}. "
                    f"Actions: {assessment.actions_required}"
                )
            elif assessment.aggregate_level == RiskLevel.WARNING:
                logger.warning(
                    f"Risk assessment WARNING: {assessment.aggregate_score:.2f}"
                )

    def _last_evolution_was_tier2(self) -> bool:
        """Check if the most recent evolution was Tier 2+.

        S-CR-06-FIX: Read last evolution record instead of returning False.
        """
        if self._evolution_engine is None:
            return False
        records_dir = self.yaml_store.base_dir / "state/evolution/records"
        if not records_dir.exists():
            return False
        record_files = sorted(
            f for f in records_dir.iterdir()
            if f.suffix in (".yaml", ".yml")
        )
        if not record_files:
            return False
        last_file = record_files[-1]
        rel_path = str(last_file.relative_to(self.yaml_store.base_dir))
        try:
            data = self.yaml_store.read_raw(rel_path)
        except FileNotFoundError:
            return False
        # IFM-N53: fail-loud — evolution records must have proposal.tier
        proposal = data["proposal"]
        tier = proposal["tier"]
        # Tier 2 = organizational, also catch higher tiers
        if isinstance(tier, int):
            return tier >= 2
        if isinstance(tier, str):
            try:
                return int(tier) >= 2
            except ValueError:
                return tier in ("organizational", "framework", "constitutional")
        return False

    def _collect_agent_alignment_data(self) -> list[dict]:
        """Collect alignment-relevant data for all registered agents.

        S-CR-07/NFR-04-FIX: Marks incomplete metrics explicitly so
        alignment checks can distinguish "no data" from "clean data".
        """
        agents_base = f"instances/{self.task_lifecycle.domain}/state/agents"
        agents_dir = self.yaml_store.base_dir / agents_base
        if not agents_dir.exists():
            return []

        agent_data: list[dict] = []
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            status_path = f"{agents_base}/{agent_dir.name}/status.yaml"
            try:
                data = self.yaml_store.read_raw(status_path)
                agent_id = data["id"]  # KeyError = fail-loud (NFR-05)
                role = data["role"]    # KeyError = fail-loud (NFR-05)
                agent_data.append({
                    "agent_id": agent_id,
                    "role": role,
                    "capabilities": data["capabilities"],  # IFM-N53: fail-loud
                    # Phase 5: behavioral metrics not yet collected.
                    # Marked absent so checks can skip vs. false-pass.
                    "_metrics_available": False,
                })
            except FileNotFoundError:
                continue
            except KeyError as e:
                raise RuntimeError(
                    f"Agent status file {status_path} missing required "
                    f"field: {e}. Cannot build alignment data."
                )

        return agent_data

    def _collect_risk_metrics(self) -> dict[str, dict]:
        """Collect risk metrics for all 10 dimensions.

        S-CR-08/NFR-06-FIX: Marks metrics as unavailable rather than
        providing empty dicts that score as "healthy".
        """
        dimensions = [
            "operational", "evolutionary", "diversity", "knowledge",
            "resource", "governance", "alignment", "calibration",
            "environment", "complexity",
        ]
        # Phase 5: real metric collection deferred. Mark all as
        # explicitly unavailable so RiskScorecard can score
        # conservatively rather than defaulting to "healthy".
        return {
            dim: {"_metrics_available": False}
            for dim in dimensions
        }
