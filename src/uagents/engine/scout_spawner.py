"""Scout agent spawning and lifecycle management.
Spec reference: Section 10 (Diversity/Stagnation), Section 7.4 (MAP-Elites).

Scout agents explore unexplored regions of the design space:
- Archive gaps (MAP-Elites cells with no occupant)
- Stagnation responses (triggered by stagnation signals)
- Diversity floor breaches (SRD/VDI below floor)

Key constraints:
- Maximum 1 active scout at a time (resource conservation)
- Scouts operate at Ring 2-3 (no Ring 0 access)
- Scout reports are advisory — orchestrator decides action
- Budget pressure RED/ORANGE suppresses scout spawning

Review fixes applied:
- DR-Issue-3/FM-P7-016: Error class inherits RuntimeError (codebase convention).
- DR-Issue-18: Use public accessors for archive dimensions (not private _task_types/_complexities).
- DR-Issue-25: Use typed read for target validation in record_report().
- DR-Issue-22/FM-P7-080: max_active_scouts enforced in generate_targets().
- FM-P7-025: Config file creation documented in implementation sequence.
- FM-P7-034: Deduplication check against existing pending targets.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.expansion import (
    ScoutReport,
    ScoutTarget,
    ScoutTargetType,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.scout_spawner")


class ScoutSpawnError(RuntimeError):
    """Raised when scout spawning fails.

    DR-Issue-3-FIX: Inherits RuntimeError per codebase convention
    (see EvolutionError, QuorumError, DomainError, etc.).
    """


class ScoutSpawner:
    """Manages scout agent lifecycle.

    Determines WHAT to explore (targeting) and tracks scout results.
    Does NOT actually spawn Claude Code subprocesses — produces ScoutTarget
    models consumed by the orchestrator's agent spawning infrastructure.

    Usage:
        spawner = ScoutSpawner(yaml_store, map_elites_archive)
        targets = spawner.generate_targets(stagnation_signals)
        # Orchestrator spawns scout agent for targets[0]
        spawner.record_report(report)
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        map_elites_archive: "MAPElitesArchive | None" = None,
        domain: str = "meta",
    ) -> None:
        self.yaml_store = yaml_store
        self.archive = map_elites_archive
        self._domain = domain
        self._scouts_base = f"instances/{domain}/state/scouts"
        yaml_store.ensure_dir(self._scouts_base)
        yaml_store.ensure_dir(f"{self._scouts_base}/targets")
        yaml_store.ensure_dir(f"{self._scouts_base}/reports")

        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load scout configuration from core/scout.yaml (fail-loud)."""
        raw = self.yaml_store.read_raw("core/scout.yaml")
        return raw["scout"]

    def generate_targets(
        self,
        stagnation_signals: list[dict] | None = None,
        srd_below_floor: bool = False,
        manual_description: str | None = None,
    ) -> list[ScoutTarget]:
        """Generate scout exploration targets based on current state.

        Priority order:
        1. Manual requests (highest priority)
        2. Stagnation responses
        3. Diversity floor breaches
        4. Archive gaps (lowest priority, continuous background)

        Args:
            stagnation_signals: Signals from StagnationDetector.check_all().
            srd_below_floor: True if SRD is below the diversity floor.
            manual_description: Human-provided exploration target.

        Returns:
            List of ScoutTarget objects, sorted by priority descending.
            Empty list if max_active_scouts already reached.
        """
        # FM-P7-080-FIX: Enforce max_active_scouts from config
        max_active = self._config["max_active_scouts"]
        if self.get_active_scout_count() >= max_active:
            logger.info(
                f"Scout limit reached ({max_active} active) — "
                f"skipping target generation"
            )
            return []

        targets: list[ScoutTarget] = []

        # 1. Manual request
        if manual_description:
            targets.append(ScoutTarget(
                target_type=ScoutTargetType.MANUAL,
                description=manual_description,
                priority=1.0,
            ))

        # 2. Stagnation-triggered targets
        # FM-P7-080-FIX: Read priorities from config (no dead config keys)
        stagnation_priority = float(self._config["stagnation_priority"])
        if stagnation_signals:
            for signal in stagnation_signals:
                # IFM-N53: fail-loud on required signal fields
                level = signal["level"]
                description = signal["description"]
                targets.append(ScoutTarget(
                    target_type=ScoutTargetType.STAGNATION_RESPONSE,
                    description=f"Explore alternatives for: {description}",
                    priority=min(stagnation_priority + 0.1, 1.0) if level == "framework" else stagnation_priority - 0.1,
                ))

        # 3. Diversity floor breach
        diversity_floor_priority = float(self._config["diversity_floor_priority"])
        if srd_below_floor:
            targets.append(ScoutTarget(
                target_type=ScoutTargetType.DIVERSITY_FLOOR,
                description="SRD below diversity floor — explore divergent approaches",
                priority=diversity_floor_priority,
            ))

        # 4. Archive gap targets
        if self.archive is not None:
            gap_targets = self._find_archive_gaps()
            targets.extend(gap_targets)

        # Sort by priority descending
        targets.sort(key=lambda t: t.priority, reverse=True)

        # Cap at max_targets from config (IFM-N53: direct dict access)
        max_targets = self._config["max_pending_targets"]
        return targets[:max_targets]

    def record_report(self, report: ScoutReport) -> None:
        """Persist a scout report.

        Args:
            report: Completed scout report.

        Raises:
            ScoutSpawnError: If referenced target does not exist.
        """
        # DR-Issue-25-FIX: Use typed read for target validation
        target_path = f"{self._scouts_base}/targets/{report.target_id}.yaml"
        try:
            self.yaml_store.read(target_path, ScoutTarget)
        except FileNotFoundError:
            raise ScoutSpawnError(
                f"Scout report references non-existent target '{report.target_id}'"
            )

        self.yaml_store.write(
            f"{self._scouts_base}/reports/{report.id}.yaml", report,
        )
        logger.info(
            f"Scout report {report.id} recorded for target {report.target_id}: "
            f"status={report.status}"
        )

    def save_target(self, target: ScoutTarget) -> None:
        """Persist a scout target to disk."""
        self.yaml_store.write(
            f"{self._scouts_base}/targets/{target.id}.yaml", target,
        )

    def get_active_scout_count(self) -> int:
        """Count targets without corresponding reports (i.e., still active).

        Note: O(targets * reports). Acceptable for Phase 7 volumes
        (max_pending_targets=5, max_active_scouts=1). See FM-P7-030.
        """
        targets_dir = self.yaml_store.base_dir / self._scouts_base / "targets"
        if not targets_dir.exists():
            return 0
        count = 0
        for f in targets_dir.iterdir():
            if f.suffix in (".yaml", ".yml"):
                data = self.yaml_store.read_raw(
                    f"{self._scouts_base}/targets/{f.name}"
                )
                # A target is "active" if it has no corresponding report yet
                target_id = data["id"]  # IFM-N53: fail-loud
                if not self._has_report(target_id):
                    count += 1
        return count

    def get_recent_reports(self, limit: int = 20) -> list[ScoutReport]:
        """Load recent scout reports, sorted by ID descending (approximate creation order)."""
        reports_dir = self.yaml_store.base_dir / self._scouts_base / "reports"
        if not reports_dir.exists():
            return []

        report_files = sorted(
            (f for f in reports_dir.iterdir() if f.suffix in (".yaml", ".yml")),
            reverse=True,
        )
        results: list[ScoutReport] = []
        for rf in report_files[:limit]:
            rel_path = f"{self._scouts_base}/reports/{rf.name}"
            results.append(self.yaml_store.read(rel_path, ScoutReport))
        return results

    def _find_archive_gaps(self) -> list[ScoutTarget]:
        """Identify unoccupied MAP-Elites cells as exploration targets.

        DR-Issue-18-FIX: Uses public accessors (task_types, complexities)
        instead of private attributes (_task_types, _complexities).
        """
        if self.archive is None:
            return []

        targets: list[ScoutTarget] = []
        # DR-Issue-18-FIX: Use public accessor properties
        unoccupied = self.archive.get_unoccupied_cells()

        # FM-P7-034-FIX: Deduplicate against existing pending targets
        existing_coords = self._get_pending_target_coords()

        for task_type, complexity in unoccupied:
            if (task_type, complexity) in existing_coords:
                continue  # Already have a pending target for this cell
            targets.append(ScoutTarget(
                target_type=ScoutTargetType.ARCHIVE_GAP,
                description=(
                    f"Unexplored archive cell: task_type={task_type}, "
                    f"complexity={complexity}"
                ),
                task_type=task_type,
                complexity=complexity,
                priority=float(self._config["archive_gap_priority"]),
            ))

        return targets

    def _get_pending_target_coords(self) -> set[tuple[str, str]]:
        """Get (task_type, complexity) coords of existing pending targets."""
        targets_dir = self.yaml_store.base_dir / self._scouts_base / "targets"
        if not targets_dir.exists():
            return set()
        coords: set[tuple[str, str]] = set()
        for f in targets_dir.iterdir():
            if f.suffix in (".yaml", ".yml"):
                data = self.yaml_store.read_raw(
                    f"{self._scouts_base}/targets/{f.name}"
                )
                tt = data.get("task_type", "")
                cx = data.get("complexity", "")
                if tt and cx:
                    coords.add((tt, cx))
        return coords

    def _has_report(self, target_id: str) -> bool:
        """Check if a target has a corresponding report."""
        reports_dir = self.yaml_store.base_dir / self._scouts_base / "reports"
        if not reports_dir.exists():
            return False
        for f in reports_dir.iterdir():
            if f.suffix in (".yaml", ".yml"):
                data = self.yaml_store.read_raw(
                    f"{self._scouts_base}/reports/{f.name}"
                )
                if data["target_id"] == target_id:  # IFM-N53: fail-loud
                    return True
        return False
