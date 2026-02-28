"""Task topology analysis and routing.
Spec reference: Section 5 (Topology & Coordination Patterns)."""
from __future__ import annotations

from enum import StrEnum

from ..models.base import FrameworkModel
from ..models.resource import ComputeMetrics


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
    """Analyzes tasks and selects topology patterns.

    Phase 0: heuristic-based routing.
    Phase 1+: MAP-Elites archive lookup with reinforcement learning.
    """

    def analyze(self, task_description: str, hints: dict | None = None) -> TaskAnalysis:
        """Analyze task along 6 dimensions.
        Phase 0: uses heuristics from task description keywords.
        Phase 1+: uses LLM judgment + historical data."""
        # Default analysis — overridden by hints or LLM in later phases
        return TaskAnalysis(
            decomposability=Decomposability.PARTIALLY_DECOMPOSABLE,
            interdependency=Interdependency.LOOSELY_COUPLED,
            exploration_vs_execution=ExplorationExecution.MIXED,
            quality_criticality=QualityCriticality.MEDIUM,
            scale=Scale.MEDIUM,
            novelty=Novelty.MODERATE,
        )

    def route(
        self,
        analysis: TaskAnalysis,
        available_capacity: ComputeMetrics | None = None,
    ) -> RoutingResult:
        """Select topology pattern based on analysis and resource constraints."""
        # Phase 0: simplified routing
        if analysis.scale == Scale.SMALL and analysis.novelty == Novelty.ROUTINE:
            return RoutingResult(
                pattern="solo",
                agent_count=1,
                role_assignments=[{"role": "implementer", "model": "sonnet"}],
                inject_scout=False,
                rationale="Small routine task — solo execution sufficient",
            )

        if analysis.quality_criticality == QualityCriticality.CRITICAL:
            return RoutingResult(
                pattern="hierarchical_team",
                agent_count=4,
                role_assignments=[
                    {"role": "orchestrator", "model": "opus"},
                    {"role": "researcher", "model": "opus"},
                    {"role": "implementer", "model": "sonnet"},
                    {"role": "reviewer", "model": "opus"},
                ],
                inject_scout=analysis.novelty in (Novelty.NOVEL, Novelty.UNPRECEDENTED),
                rationale="Critical quality task — full team with dedicated reviewer",
            )

        # Default: hierarchical team
        return RoutingResult(
            pattern="hierarchical_team",
            agent_count=3,
            role_assignments=[
                {"role": "orchestrator", "model": "opus"},
                {"role": "implementer", "model": "sonnet"},
                {"role": "reviewer", "model": "opus"},
            ],
            inject_scout=False,
            rationale="Standard task — orchestrator + worker + reviewer",
        )
