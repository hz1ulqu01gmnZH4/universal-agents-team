"""Framework factory — one-call Orchestrator construction.
Spec reference: Phase 9 (Integration & Wiring).

Constructs all engine dependencies in dependency order and returns
a fully-wired Orchestrator. Phase-gated: missing config files disable
the corresponding phase, they don't crash.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from ..audit.logger import AuditLogger
from ..state.directory import DirectoryManager
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.factory")


class FrameworkFactory:
    """Constructs a fully-wired Orchestrator from a bootstrapped framework root.

    Usage:
        factory = FrameworkFactory(root=Path("/path/to/framework"), domain="meta")
        orchestrator = factory.build()
    """

    # Config file → phase mapping for phase-gating
    PHASE_CONFIGS: dict[str, str] = {
        "core/resource-awareness.yaml": "1.5",
        "core/environment-awareness.yaml": "2.5",
        "core/canary-expectations.yaml": "2.5",
        "core/skill-system.yaml": "3",
        "core/context-pressure.yaml": "3.5",
        "core/tool-taxonomy.yaml": "3.5",
        "core/evolution.yaml": "4",
        "core/self-governance.yaml": "5",
        "core/creativity.yaml": "6",
        "core/scout.yaml": "7",
    }

    def __init__(self, root: Path, domain: str = "meta") -> None:
        self.root = root.resolve()
        self.domain = domain
        self._enabled_phases: set[str] = set()
        self._detect_phases()

    def _detect_phases(self) -> None:
        """Detect which phases are enabled by checking for config files.

        A phase is enabled only when ALL of its config files are present and
        non-empty. If any config file for a phase is missing or empty, the
        entire phase is disabled. This prevents partial-config crashes where
        one config exists but a sibling config (e.g. Phase 2.5 requires both
        environment-awareness.yaml AND canary-expectations.yaml) is absent.
        """
        # Group configs by phase
        phase_configs: dict[str, list[str]] = defaultdict(list)
        for config_path, phase in self.PHASE_CONFIGS.items():
            phase_configs[phase].append(config_path)

        for phase, config_paths in phase_configs.items():
            all_present = True
            for config_path in config_paths:
                full_path = self.root / config_path
                if full_path.exists() and full_path.stat().st_size > 0:
                    logger.info("Phase %s config found: %s", phase, config_path)
                else:
                    logger.info("Phase %s disabled (missing %s)", phase, config_path)
                    all_present = False
                    break
            if all_present:
                self._enabled_phases.add(phase)
                logger.info("Phase %s enabled (all config files present)", phase)

    def _phase_enabled(self, phase: str) -> bool:
        return phase in self._enabled_phases

    def build(self) -> "Orchestrator":
        """Construct and return a fully-wired Orchestrator.

        Construction order follows the dependency tree:
        Tier 0: YamlStore, AuditLogger, paths
        Tier 1: TaskLifecycle, ResourceTracker
        Tier 2: BudgetTracker, RateLimiter, CostGate (Phase 1.5)
        Tier 3: PromptComposer, AgentSpawner
        Tier 4: TopologyRouter, ReviewEngine, TeamManager
        Tier 5: Self-awareness engines (Phase 2)
        Tier 6: Environment engines (Phase 2.5)
        Tier 7: Skill engines (Phase 3)
        Tier 8: Protection engines (Phase 3.5)
        Tier 9: Evolution & governance (Phases 4-5)
        Tier 10: Creativity & expansion (Phases 6-7)
        Tier 11: Orchestrator assembly
        """
        # ── Tier 0: Foundation ──
        yaml_store = YamlStore(self.root)
        instance_root = self.root / "instances" / self.domain
        log_root = instance_root / "logs"
        audit_logger = AuditLogger(log_root)
        constitution_path = self.root / "CONSTITUTION.md"

        # ── Tier 1: Core state ──
        from .task_lifecycle import TaskLifecycle

        task_lifecycle = TaskLifecycle(yaml_store, self.domain)

        # ── Tier 2: Budget & resource (Phase 1.5) ──
        budget_tracker = None
        rate_limiter = None
        cost_gate = None

        if self._phase_enabled("1.5"):
            from .budget_tracker import BudgetTracker
            from .rate_limiter import RateLimiter
            from .cost_gate import CostGate

            ra_config = yaml_store.read_raw("core/resource-awareness.yaml")
            ra = ra_config["resource_awareness"]

            budget_tracker = BudgetTracker(
                yaml_store, self.domain,
                plan=ra["claude_max_plan"],
            )
            rl_cfg = ra["rate_limits"]
            rate_limiter = RateLimiter(
                yaml_store, self.domain,
                rpm_estimate=int(rl_cfg["rpm_estimate"]),
                itpm_estimate=int(rl_cfg["itpm_estimate"]),
                otpm_estimate=int(rl_cfg["otpm_estimate"]),
            )
            cc_cfg = ra["cost_caps"]
            cost_gate = CostGate(
                yaml_store, self.domain,
                daily_cap=float(cc_cfg["daily"]),
                weekly_cap=float(cc_cfg["weekly"]),
            )
            logger.info("Phase 1.5 (Budget): BudgetTracker, RateLimiter, CostGate")

        # ResourceTracker (Tier 1 continued — needs budget/rate from Tier 2)
        from .resource_tracker import ResourceTracker

        state_dir = instance_root / "state"
        resource_tracker = ResourceTracker(
            yaml_store, state_dir,
            budget_tracker=budget_tracker,
            rate_limiter=rate_limiter,
        )

        # ── Tier 3: Prompt & agent composition ──
        from .prompt_composer import PromptComposer
        from .agent_spawner import AgentSpawner

        prompt_composer = PromptComposer(yaml_store, constitution_path)
        agent_spawner = AgentSpawner(
            prompt_composer, resource_tracker, yaml_store,
            self.domain, budget_tracker, rate_limiter,
        )

        # ── Tier 4: Topology, review, teams ──
        from .topology_router import TopologyRouter
        from .review_engine import ReviewEngine
        from .team_manager import TeamManager

        capabilities = self._load_capabilities(yaml_store)
        voice_atoms = self._load_voice_atoms(yaml_store)

        topology_router = TopologyRouter(
            yaml_store, resource_tracker, self.domain, audit_logger,
        )
        review_engine = ReviewEngine(yaml_store, task_lifecycle, audit_logger)
        team_manager = TeamManager(
            yaml_store, agent_spawner, capabilities, voice_atoms,
            self.domain, audit_logger,
        )

        # ── Tier 5: Self-awareness (Phase 2 — always on) ──
        from .capability_tracker import CapabilityTracker
        from .diversity_engine import DiversityEngine
        from .stagnation_detector import StagnationDetector

        capability_tracker = CapabilityTracker(yaml_store, self.domain)
        diversity_engine = DiversityEngine(yaml_store, self.domain)
        stagnation_detector = StagnationDetector(yaml_store, self.domain)

        # ── Tier 6: Environment (Phase 2.5) ──
        if self._phase_enabled("2.5"):
            if budget_tracker is None:
                raise RuntimeError(
                    "Phase 2.5 (Environment) requires Phase 1.5 (budget_tracker). "
                    "Enable Phase 1.5 by creating core/resource-awareness.yaml."
                )
            from .environment_monitor import EnvironmentMonitor
            from .performance_monitor import PerformanceMonitor
            from .canary_runner import CanaryRunner

            environment_monitor = EnvironmentMonitor(
                yaml_store, budget_tracker, audit_logger,
                capability_tracker, self.domain,
            )
            performance_monitor = PerformanceMonitor(yaml_store, self.domain, audit_logger)
            canary_runner = CanaryRunner(yaml_store, self.domain)
            logger.info("Phase 2.5 (Environment): monitors created")

        # ── Tier 7: Skills (Phase 3) ──
        skill_library = None
        if self._phase_enabled("3"):
            from .skill_library import SkillLibrary

            skill_library = SkillLibrary(yaml_store, self.domain, audit_logger)
            logger.info("Phase 3 (Skills): SkillLibrary")

        # ── Tier 8: Protection (Phase 3.5) ──
        context_pressure_monitor = None
        tool_loader = None
        ring_enforcer = None
        self_reconfigurer = None

        if self._phase_enabled("3.5"):
            from .context_pressure_monitor import ContextPressureMonitor
            from .tool_loader import ToolLoader
            from .ring_enforcer import RingEnforcer
            from .self_reconfigurer import SelfReconfigurer

            context_pressure_monitor = ContextPressureMonitor(yaml_store)
            tool_loader = ToolLoader(yaml_store, self.domain, budget_tracker)
            ring_enforcer = RingEnforcer(
                yaml_store, constitution_path, self.domain, audit_logger,
            )
            self_reconfigurer = SelfReconfigurer(
                yaml_store, self.domain, audit_logger, tool_loader,
            )
            logger.info("Phase 3.5 (Protection): CPM, ToolLoader, RingEnforcer, SelfReconfigurer")

        # ── Tier 9: Evolution (Phase 4) ──
        evolution_engine = None
        map_elites_archive = None

        if self._phase_enabled("4"):
            from .map_elites_archive import MAPElitesArchive
            from .evolution_validator import EvolutionValidator
            from .dual_copy_manager import DualCopyManager
            from .constitution_guard import ConstitutionGuard
            from .gap_monitor import GapMonitor
            from .population_evolver import PopulationEvolver
            from .evolution_engine import EvolutionEngine
            from ..state.git_ops import GitOps

            map_elites_archive = MAPElitesArchive(yaml_store, self.domain)
            evolution_validator = EvolutionValidator(yaml_store)
            git_ops = GitOps(self.root)
            dual_copy_manager = DualCopyManager(yaml_store, self.domain)
            hash_path = self.root / "core" / "constitution-hash.txt"
            constitution_guard = ConstitutionGuard(constitution_path, hash_path)
            gap_monitor = GapMonitor(yaml_store, self.domain)

            population_evolver = PopulationEvolver(
                yaml_store, dual_copy_manager, evolution_validator,
                constitution_guard, map_elites_archive,
                self.domain, budget_tracker,
            )

            if ring_enforcer is None:
                raise RuntimeError(
                    "Phase 4 (Evolution) requires Phase 3.5 (ring_enforcer). "
                    "Enable Phase 3.5 by creating core/context-pressure.yaml "
                    "and core/tool-taxonomy.yaml."
                )

            evolution_engine = EvolutionEngine(
                yaml_store,
                git_ops,
                constitution_guard,
                dual_copy_manager,
                evolution_validator,
                map_elites_archive,
                audit_logger,
                ring_enforcer,
                self.domain,
                quorum_manager=None,
                objective_anchor=None,
                risk_scorecard=None,
                alignment_verifier=None,
                population_evolver=population_evolver,
                gap_monitor=gap_monitor,
                stagnation_detector=stagnation_detector,
            )

            topology_router._archive = map_elites_archive
            logger.info("Phase 4 (Evolution): full evolution pipeline wired")

        # ── Tier 10: Governance (Phase 5) ──
        quorum_manager = None
        objective_anchor = None
        risk_scorecard = None
        alignment_verifier = None

        if self._phase_enabled("5"):
            from .quorum_manager import QuorumManager
            from .risk_scorecard import RiskScorecard
            from .objective_anchor import ObjectiveAnchor
            from .alignment_verifier import AlignmentVerifier

            quorum_manager = QuorumManager(yaml_store, self.domain, audit_logger)
            risk_scorecard = RiskScorecard(yaml_store, self.domain, audit_logger)
            objective_anchor = ObjectiveAnchor(yaml_store, self.domain, audit_logger)
            alignment_verifier = AlignmentVerifier(yaml_store, self.domain, audit_logger)

            if evolution_engine is not None:
                evolution_engine._quorum_manager = quorum_manager
                evolution_engine._objective_anchor = objective_anchor
                evolution_engine._risk_scorecard = risk_scorecard
                evolution_engine._alignment_verifier = alignment_verifier

            logger.info("Phase 5 (Governance): quorum, risk, anchor, alignment")

        # ── Tier 11: Creativity (Phase 6) ──
        creativity_engine = None
        if self._phase_enabled("6"):
            from .creativity_engine import CreativityEngine
            from .persona_assigner import PersonaAssigner
            from .guilford_metrics import GuilfordMetrics

            persona_assigner = PersonaAssigner(yaml_store)
            guilford_metrics = GuilfordMetrics()
            creativity_engine = CreativityEngine(
                yaml_store, diversity_engine, persona_assigner,
                guilford_metrics, audit_logger,
            )
            logger.info("Phase 6 (Creativity): CreativityEngine")

        # ── Tier 12: Self-expansion (Phase 7) ──
        scout_spawner = None
        pressure_field_coordinator = None
        domain_manager = None

        if self._phase_enabled("7"):
            from .scout_spawner import ScoutSpawner
            from .pressure_field import PressureFieldCoordinator
            from .domain_manager import DomainManager

            scout_spawner = ScoutSpawner(yaml_store, map_elites_archive, self.domain)
            pressure_field_coordinator = PressureFieldCoordinator(yaml_store, self.domain)
            directory_manager = DirectoryManager()
            domain_manager = DomainManager(yaml_store, directory_manager)
            logger.info("Phase 7 (Expansion): ScoutSpawner, PressureField, DomainManager")

        # ── Tier 13: Orchestrator assembly ──
        from .orchestrator import Orchestrator

        orchestrator = Orchestrator(
            yaml_store=yaml_store,
            topology_router=topology_router,
            team_manager=team_manager,
            task_lifecycle=task_lifecycle,
            review_engine=review_engine,
            audit_logger=audit_logger,
            budget_tracker=budget_tracker,
            rate_limiter=rate_limiter,
            cost_gate=cost_gate,
            capability_tracker=capability_tracker,
            constitution_path=constitution_path,
            prompt_composer=prompt_composer,
            cache_manager=None,
            skill_library=skill_library,
            context_pressure_monitor=context_pressure_monitor,
            tool_loader=tool_loader,
            ring_enforcer=ring_enforcer,
            self_reconfigurer=self_reconfigurer,
            evolution_engine=evolution_engine,
            quorum_manager=quorum_manager,
            objective_anchor=objective_anchor,
            risk_scorecard=risk_scorecard,
            alignment_verifier=alignment_verifier,
            creativity_engine=creativity_engine,
            scout_spawner=scout_spawner,
            pressure_field_coordinator=pressure_field_coordinator,
            domain_manager=domain_manager,
        )

        orchestrator.diversity_engine = diversity_engine
        orchestrator.stagnation_detector = stagnation_detector

        logger.info(
            "Orchestrator assembled with phases: %s",
            sorted(self._enabled_phases) if self._enabled_phases else ["0 (core only)"],
        )

        return orchestrator

    def _load_capabilities(self, yaml_store: YamlStore) -> dict:
        """Load capability atoms from roles/capabilities.yaml."""
        try:
            return yaml_store.read_raw("roles/capabilities.yaml")
        except FileNotFoundError:
            raise FileNotFoundError(
                "roles/capabilities.yaml not found. Run bootstrap first."
            )

    def _load_voice_atoms(self, yaml_store: YamlStore) -> dict:
        """Load voice atoms from roles/voice.yaml."""
        try:
            return yaml_store.read_raw("roles/voice.yaml")
        except FileNotFoundError:
            raise FileNotFoundError(
                "roles/voice.yaml not found. Run bootstrap first."
            )
