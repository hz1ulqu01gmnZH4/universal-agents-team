"""Task topology analysis and routing.
Spec reference: Section 5 (Topology & Coordination Patterns)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import StrEnum

from ..models.audit import DecisionLogEntry, LogStream
from ..models.base import FrameworkModel, generate_id
from ..models.task import Task

logger = logging.getLogger("uagents.topology_router")


class Decomposability(StrEnum):
    MONOLITHIC = "monolithic"
    PARTIALLY_DECOMPOSABLE = "partially_decomposable"
    FULLY_DECOMPOSABLE = "fully_decomposable"


class Interdependency(StrEnum):
    INDEPENDENT = "independent"
    LOOSELY_COUPLED = "loosely_coupled"
    TIGHTLY_COUPLED = "tightly_coupled"


class ExplorationExecution(StrEnum):
    PURE_EXPLORATION = "pure_exploration"
    MIXED = "mixed"
    PURE_EXECUTION = "pure_execution"


class QualityCriticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Scale(StrEnum):
    SMALL = "small"       # < 1 hour
    MEDIUM = "medium"     # 1-4 hours
    LARGE = "large"       # 4+ hours


class Novelty(StrEnum):
    ROUTINE = "routine"
    MODERATE = "moderate"
    NOVEL = "novel"
    UNPRECEDENTED = "unprecedented"


class TaskAnalysis(FrameworkModel):
    """6-dimension task analysis result."""

    decomposability: Decomposability
    interdependency: Interdependency
    exploration_vs_execution: ExplorationExecution
    quality_criticality: QualityCriticality
    scale: Scale
    novelty: Novelty


class RoutingResult(FrameworkModel):
    """Topology routing decision."""

    pattern: str  # solo, pipeline, parallel_swarm, hierarchical_team, hybrid, debate
    agent_count: int
    role_assignments: list[dict]
    inject_scout: bool
    rationale: str


# Pattern selection matrix (simplified for Phase 0)
# Full version uses MAP-Elites archive lookup
PATTERN_RULES: dict[str, dict] = {
    "solo": {
        "conditions": "monolithic AND small AND routine",
        "agents": 1,
    },
    "pipeline": {
        "conditions": "partially_decomposable AND loosely_coupled",
        "agents": 2,
    },
    "hierarchical_team": {
        "conditions": "fully_decomposable OR large OR critical",
        "agents": 4,
    },
    "parallel_swarm": {
        "conditions": "fully_decomposable AND independent",
        "agents": 3,
    },
    "debate": {
        "conditions": "novel AND critical AND exploration",
        "agents": 3,
    },
}


class TopologyRouter:
    """Task analysis and topology routing.

    Phase 0: Hardcoded defaults, stateless class.
    Phase 1: Heuristic-enhanced analysis with keyword extraction, resource awareness.
             Constructor requires yaml_store and resource_tracker.
    Phase 2+: LLM judgment + MAP-Elites archive lookup.

    BREAKING CHANGES from Phase 0:
    - __init__ now requires (yaml_store, resource_tracker, domain, audit_logger)
    - analyze() signature: (task: Task) instead of (task_description: str, hints: dict | None)
    - route() signature: (analysis: TaskAnalysis) instead of (analysis, available_capacity)
      Resource checking moved to instance's resource_tracker.
    - Phase 0 test updates required: test_topology_router.py
    """

    def __init__(
        self,
        yaml_store: "YamlStore",
        resource_tracker: "ResourceTracker | None" = None,
        domain: str = "meta",
        audit_logger: "AuditLogger | None" = None,
        map_elites_archive: "MAPElitesArchive | None" = None,
    ):
        from ..audit.logger import AuditLogger
        from ..engine.resource_tracker import ResourceTracker
        from ..state.yaml_store import YamlStore

        self.yaml_store = yaml_store
        self.resource_tracker = resource_tracker
        self._tasks_base = f"instances/{domain}/state/tasks"
        self.audit_logger = audit_logger
        self._archive = map_elites_archive

    def analyze(self, task: Task) -> TaskAnalysis:
        """Analyze task along 6 dimensions using structured heuristics.

        Phase 1 heuristic strategy:
        - Decomposability: keyword-based (list/multiple/each -> decomposable)
        - Interdependency: keyword-based (depends/after/then -> coupled)
        - Exploration vs Execution: keyword-based (research/explore vs implement/fix)
        - Quality Criticality: keyword-based (critical/safety/production vs quick/draft)
        - Scale: description length + keyword count heuristic
        - Novelty: check task history for similar titles (Jaccard similarity)
        """
        text = f"{task.title} {task.description}".lower()
        # Use word set for matching (prevents substring false positives)
        words = set(text.split())

        # Decomposability
        decomp_keywords = {"parallel", "independent", "each", "multiple", "all", "every", "batch"}
        mono_keywords = {"single", "one", "specific"}
        decomp_score = len(decomp_keywords & words)
        mono_score = len(mono_keywords & words)
        if decomp_score >= 2:
            decomposability = Decomposability.FULLY_DECOMPOSABLE
        elif decomp_score >= 1:
            decomposability = Decomposability.PARTIALLY_DECOMPOSABLE
        else:
            decomposability = Decomposability.MONOLITHIC

        # Interdependency
        coupled_keywords = {"depends", "after", "then", "requires", "blocking", "sequential"}
        independent_keywords = {"independent", "parallel", "concurrent", "separate"}
        coupled_score = len(coupled_keywords & words)
        indep_score = len(independent_keywords & words)
        if coupled_score >= 2:
            interdependency = Interdependency.TIGHTLY_COUPLED
        elif indep_score >= 1:
            interdependency = Interdependency.INDEPENDENT
        else:
            interdependency = Interdependency.LOOSELY_COUPLED

        # Exploration vs Execution
        explore_keywords = {"research", "explore", "investigate", "analyze", "discover", "design", "plan"}
        execute_keywords = {"implement", "fix", "build", "deploy", "create", "write", "code"}
        explore_score = len(explore_keywords & words)
        execute_score = len(execute_keywords & words)
        if explore_score > execute_score + 1:
            expl_exec = ExplorationExecution.PURE_EXPLORATION
        elif execute_score > explore_score + 1:
            expl_exec = ExplorationExecution.PURE_EXECUTION
        else:
            expl_exec = ExplorationExecution.MIXED

        # Quality Criticality
        critical_keywords = {"critical", "safety", "production", "security", "correctness"}
        speed_keywords = {"quick", "draft", "prototype", "rough", "fast", "hack"}
        crit_score = len(critical_keywords & words)
        speed_score = len(speed_keywords & words)
        # Also check multi-word phrases via substring (only for specific known phrases)
        if "must not fail" in text:
            crit_score += 1
        if crit_score >= 2:
            quality = QualityCriticality.CRITICAL
        elif crit_score >= 1:
            quality = QualityCriticality.HIGH
        elif speed_score >= 1:
            quality = QualityCriticality.LOW
        else:
            quality = QualityCriticality.MEDIUM

        # Scale (based on description length and complexity indicators)
        word_count = len(text.split())
        if word_count > 200 or "large" in words or "major" in words or "comprehensive" in words:
            scale = Scale.LARGE
        elif word_count > 50 or decomp_score >= 1:
            scale = Scale.MEDIUM
        else:
            scale = Scale.SMALL

        # Novelty (check recent task history)
        novelty = self._assess_novelty(task.title)

        return TaskAnalysis(
            decomposability=decomposability,
            interdependency=interdependency,
            exploration_vs_execution=expl_exec,
            quality_criticality=quality,
            scale=scale,
            novelty=novelty,
        )

    def _assess_novelty(self, title: str) -> Novelty:
        """Check task history for similar tasks using word overlap."""
        title_words = set(title.lower().split())
        try:
            # Use domain-scoped path: instances/{domain}/state/tasks/completed
            completed_dir = f"{self._tasks_base}/completed"
            completed_tasks = self.yaml_store.list_dir(completed_dir)
        except (NotADirectoryError, FileNotFoundError):
            return Novelty.NOVEL  # No history -> novel

        max_similarity = 0.0
        yaml_tasks = [f for f in completed_tasks if f.endswith((".yaml", ".yml"))]
        for task_file in yaml_tasks[:50]:  # Check last 50 completed
            try:
                data = self.yaml_store.read_raw(f"{completed_dir}/{task_file}")
                # IFM-N53: fail-loud — task files must have a title field
                past_title = data["title"]
                past_words = set(past_title.lower().split())
                if title_words and past_words:
                    intersection = title_words & past_words
                    union = title_words | past_words
                    similarity = len(intersection) / len(union)  # Jaccard
                    max_similarity = max(max_similarity, similarity)
            except (FileNotFoundError, OSError) as e:
                logger.warning(
                    f"Skipping unreadable task file {task_file} in novelty check: {e}"
                )
                continue

        if max_similarity > 0.7:
            return Novelty.ROUTINE
        elif max_similarity > 0.4:
            return Novelty.MODERATE
        else:
            return Novelty.NOVEL

    def route(self, analysis: TaskAnalysis, task: "Task | None" = None) -> RoutingResult:
        """Select topology pattern based on 6-dimension analysis.

        Phase 1 implements 3 patterns:
        - solo: monolithic + small + routine
        - parallel_swarm: fully_decomposable + independent
        - hierarchical_team: everything else (default)

        All topologies include a mandatory reviewer agent.

        Phase 7: Optionally consults MAP-Elites archive for topology hint.
        """
        # Phase 7: Archive consultation (advisory only)
        if task is not None:
            archive_hint = self._consult_archive(task)
            if archive_hint:
                logger.info(f"Archive suggests topology: {archive_hint}")
                # Advisory logging only in Phase 7 — full integration in Phase 8

        # Check available resources for topology downgrade decisions
        can_spawn, spawn_reason = self.resource_tracker.can_spawn_agent()
        metrics = self.resource_tracker.check_compute()

        # Resource-constrained: force solo if unable to spawn
        if not can_spawn:
            return RoutingResult(
                pattern="solo",
                agent_count=2,
                role_assignments=[
                    {"role": "implementer", "model": "sonnet", "purpose": "execute task"},
                    {"role": "reviewer", "model": "sonnet", "purpose": "mandatory review"},
                ],
                inject_scout=False,
                rationale=f"Resource-constrained ({spawn_reason}) -> forced solo with mandatory review",
            )

        # Solo: simple, small, monolithic tasks that aren't tightly coupled
        # Novel but monolithic+small tasks still go solo — they don't benefit from
        # multi-agent decomposition. Tightly coupled tasks need coordination even if small.
        if (analysis.decomposability == Decomposability.MONOLITHIC
                and analysis.scale == Scale.SMALL
                and analysis.interdependency != Interdependency.TIGHTLY_COUPLED
                and analysis.novelty in (Novelty.ROUTINE, Novelty.MODERATE, Novelty.NOVEL)):
            return RoutingResult(
                pattern="solo",
                agent_count=2,  # worker + reviewer (A7: review always mandatory)
                # role_assignments include both 'model' (Phase 0 format) and 'purpose' (Phase 1)
                role_assignments=[
                    {"role": "implementer", "model": "sonnet", "purpose": "execute task"},
                    {"role": "reviewer", "model": "sonnet", "purpose": "mandatory review"},
                ],
                inject_scout=False,
                # Use str() not .value — Pydantic use_enum_values=True may store raw string
                rationale=f"Monolithic + small + {str(analysis.novelty)} -> solo with mandatory review",
            )

        # Parallel swarm: decomposable + independent subtasks
        if (analysis.decomposability == Decomposability.FULLY_DECOMPOSABLE
                and analysis.interdependency == Interdependency.INDEPENDENT):
            # Scale agent count based on resources
            base_count = 3 if analysis.scale == Scale.SMALL else 4
            if analysis.scale == Scale.LARGE:
                base_count = 5
            # Cap by resources: max_concurrent (10) - active_agents - 2 (orchestrator + reviewer)
            resource_cap = max(1, 10 - metrics.active_agents - 2)
            actual_count = min(base_count, 6, resource_cap)  # Hard cap at 6, resource cap

            roles = [{"role": "orchestrator", "model": "opus", "purpose": "decompose and aggregate"}]
            for i in range(actual_count):
                roles.append({"role": "implementer", "model": "sonnet", "purpose": f"parallel worker {i+1}"})
            roles.append({"role": "reviewer", "model": "sonnet", "purpose": "mandatory review"})

            return RoutingResult(
                pattern="parallel_swarm",
                agent_count=len(roles),
                role_assignments=roles,
                inject_scout=analysis.novelty == Novelty.NOVEL,
                rationale=f"Fully decomposable + independent -> parallel swarm ({actual_count} workers)",
            )

        # Phase 6: Creative/novel tasks use debate topology
        # Note: UNPRECEDENTED is excluded from solo routing (line 287), and
        # this check comes after parallel_swarm, so debate only fires for
        # tasks that are NOT fully_decomposable+independent (correct: debate
        # tasks inherently involve coupled reasoning).
        if (analysis.novelty == Novelty.UNPRECEDENTED
                and analysis.exploration_vs_execution == ExplorationExecution.PURE_EXPLORATION
                and analysis.quality_criticality in (QualityCriticality.HIGH, QualityCriticality.CRITICAL)):
            # FM-P6-IMP-017-FIX: Include mandatory reviewer (invariant: all topologies
            # include a reviewer agent)
            return RoutingResult(
                pattern="debate",
                agent_count=4,
                role_assignments=[
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative exploration (advocate)"},
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative exploration (challenger)"},
                    {"role": "researcher", "model": "sonnet", "purpose": "Creative synthesis (judge)"},
                    {"role": "reviewer", "model": "sonnet", "purpose": "mandatory review"},
                ],
                inject_scout=False,  # Debate handles novelty internally
                rationale="Unprecedented + pure exploration + high/critical -> debate topology",
            )

        # Hierarchical team: default for complex/coupled tasks
        team_size = 3  # orchestrator + worker + reviewer
        if analysis.scale == Scale.LARGE or analysis.quality_criticality in (
            QualityCriticality.HIGH, QualityCriticality.CRITICAL
        ):
            team_size = 4  # orchestrator + 2 workers + reviewer
        if analysis.scale == Scale.LARGE and analysis.quality_criticality == QualityCriticality.CRITICAL:
            team_size = 5  # orchestrator + 3 workers + reviewer

        roles = [{"role": "orchestrator", "model": "opus", "purpose": "strategic coordination"}]
        worker_count = team_size - 2  # minus orchestrator and reviewer
        for i in range(worker_count):
            role_name = self._select_worker_role(analysis, i)
            roles.append({"role": role_name, "model": "sonnet", "purpose": f"worker {i+1}"})
        roles.append({"role": "reviewer", "model": "sonnet", "purpose": "mandatory review"})

        result = RoutingResult(
            pattern="hierarchical_team",
            agent_count=len(roles),
            role_assignments=roles,
            inject_scout=analysis.novelty == Novelty.NOVEL,
            rationale=f"Complex/coupled task -> hierarchical team ({team_size} agents)",
        )
        return result

    def _select_worker_role(self, analysis: TaskAnalysis, index: int) -> str:
        """Select appropriate worker role based on task analysis."""
        if analysis.exploration_vs_execution == ExplorationExecution.PURE_EXPLORATION:
            return "researcher" if index == 0 else "scout"
        elif analysis.exploration_vs_execution == ExplorationExecution.PURE_EXECUTION:
            return "implementer"
        else:
            # Mixed: first worker implements, second researches
            return "implementer" if index == 0 else "researcher"

    def _consult_archive(self, task: "Task") -> str | None:
        """Consult MAP-Elites archive for topology hint.

        Returns topology pattern name if archive has a mature entry,
        None otherwise (caller should fall back to heuristics).

        DR-Issue-6-FIX: Method name is _consult_archive (consistent with call site).
        FM-P7-061-FIX: Task type vocabulary matches archive vocabulary.

        NOTE: Currently returns None in practice because _extract_config()
        in MAPElitesArchive does not store a "topology" key. This method
        provides the integration point for Phase 8, where archive entries
        will include topology metadata from successful evolution records.
        """
        if self._archive is None:
            return None

        # Map task to archive coordinates
        task_type = self._infer_task_type(task)
        complexity = self._infer_complexity(task)

        config = self._archive.get_best_config(task_type, complexity)
        if config is None:
            return None

        # DR-Issue-6-FIX: Extract topology from config's "topology" key
        topology = config.get("topology")
        if topology is None:
            return None

        # Only accept known patterns (FM-P7-08)
        known_patterns = {"solo", "pipeline", "parallel_swarm", "hierarchical_team", "debate"}
        if topology not in known_patterns:
            logger.warning(
                f"Archive returned unknown topology '{topology}' for "
                f"task_type={task_type}, complexity={complexity} — ignoring"
            )
            return None
        return topology

    def _infer_task_type(self, task: "Task") -> str:
        """Infer task type from task metadata for archive lookup.

        FM-P7-061-FIX: Returns values from the archive's task_type vocabulary.
        The archive vocabulary is defined in core/evolution.yaml under
        archive.task_types. The default vocabulary is:
        ["research", "feature", "bugfix", "refactor", "creative", "meta"]

        Note: "engineering" from v0.1.0 is replaced with "feature" to match
        the archive vocabulary. Unmapped tasks default to "feature".
        """
        text = f"{task.title} {task.description}".lower()
        words = set(text.split())

        research_keywords = {"research", "analyze", "investigate", "review", "literature"}
        creative_keywords = {"creative", "brainstorm", "novel", "innovative", "design"}
        meta_keywords = {"framework", "evolve", "improve", "optimize"}
        refactor_keywords = {"refactor", "cleanup", "reorganize", "restructure"}
        bugfix_keywords = {"bug", "fix", "error", "broken", "crash", "regression"}

        if research_keywords & words:
            return "research"
        if creative_keywords & words:
            return "creative"
        if meta_keywords & words:
            return "meta"
        if refactor_keywords & words:
            return "refactor"
        if bugfix_keywords & words:
            return "bugfix"
        return "feature"  # FM-P7-061-FIX: "feature" not "engineering"

    def _infer_complexity(self, task: "Task") -> str:
        """Infer complexity from task for archive lookup.

        FM-P7-062-FIX: Returns archive vocabulary values
        ("simple", "moderate", "complex"). "extreme" requires explicit tagging.
        """
        text = f"{task.title} {task.description}".lower()
        word_count = len(text.split())

        if word_count > 200:
            return "complex"
        elif word_count > 50:
            return "moderate"
        return "simple"

    def _log_routing_decision(
        self, task: Task, analysis: TaskAnalysis, result: RoutingResult
    ) -> None:
        """Log topology routing decision for audit trail.

        DecisionLogEntry fields: decision_type, actor, options_considered, selected, rationale
        (NOT inputs/output — those don't exist on the model).
        """
        if not self.audit_logger:
            return
        entry = DecisionLogEntry(
            id=generate_id("dec"),
            timestamp=datetime.now(timezone.utc),
            stream=LogStream.DECISIONS,
            decision_type="topology_routing",
            actor="topology_router",
            options_considered=[
                {"pattern": "solo", "analysis": analysis.model_dump()},
                {"pattern": "parallel_swarm", "analysis": analysis.model_dump()},
                {"pattern": "hierarchical_team", "analysis": analysis.model_dump()},
            ],
            selected=result.pattern,
            rationale=result.rationale,
        )
        self.audit_logger.log_decision(entry)
