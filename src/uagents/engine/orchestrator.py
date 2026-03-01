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
    from .budget_tracker import BudgetTracker
    from .cache_manager import CacheManager
    from .capability_tracker import CapabilityTracker
    from .context_pressure_monitor import ContextPressureMonitor
    from .cost_gate import CostGate
    from .diversity_engine import DiversityEngine
    from .prompt_composer import PromptComposer
    from .rate_limiter import RateLimiter
    from .ring_enforcer import RingEnforcer
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
                    model=ModelPreference(a.get("model", "sonnet")),
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
            except Exception as e:
                logger.warning(
                    f"Phase 2 metric recording failed for {task_id}: {e}",
                    exc_info=True,
                )
                # Non-fatal: metrics are valuable but not critical path

            # Dissolve team
            if task.team_id:
                self.team_manager.dissolve_team(task.team_id, "Task complete")
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

        return results

    def _load_agent(self, agent_id: str) -> AgentRegistryEntry | None:
        """Load agent registry entry by ID. Returns None if not found."""
        from ..models.agent import AgentRegistryEntry
        # Use the same base path convention as AgentSpawner
        agents_base = f"instances/{self.task_lifecycle.domain}/state/agents"
        path = f"{agents_base}/{agent_id}/status.yaml"
        try:
            return self.yaml_store.read(path, AgentRegistryEntry)
        except (FileNotFoundError, ValueError):
            return None

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
