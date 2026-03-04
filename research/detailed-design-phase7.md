# Phase 7: Self-Expansion — Detailed Design

**Version:** 0.2.0
**Date:** 2026-03-04
**Status:** Post-review (v0.2.0 — addresses 25 HIGH + 1 CRITICAL from Steps 3-4)
**Spec reference:** Unified Design v1.1, Sections 7.4 (MAP-Elites), 9.2 (Stigmergic Coordination), 10 (Diversity/Stagnation), 22 (Domain Instantiation & Switching), 25 (Meta Bootstrap)
**Literature:** research/swarm-intelligence-problem-discovery.md (47 papers), research/agent-teams-vs-swarms-literature-review.md (32 papers)
**Dependencies:** Phase 4 (map_elites_archive, evolution_engine), Phase 5 (governance), Phase 2 (stagnation_detector, diversity_engine), Phase 1.5 (budget_tracker, resource_tracker), Phase 3.5 (ring_enforcer)

---

## Part 1: Architecture Overview

### What Phase 7 Adds

Phase 7 implements **Self-Expansion** — the framework discovers what it's missing through continuous exploration, learns from behavioral diversity archives, coordinates via stigmergic traces, and manages multiple domain workspaces. Key principle from literature: **scout bees convert from workers when stagnation is detected** (ABC algorithm: forced exploration through stagnation).

**New components:**
1. `ScoutSpawner` — manages scout agent lifecycle: spawning, targeting, result collection
2. `PressureFieldCoordinator` — stigmergic coordination via shared YAML pressure fields
3. `DomainManager` — domain creation, switching, cross-domain learning

**Modified components:**
1. `Orchestrator` — wire scout spawner, pressure fields, domain manager; auto-scout on stagnation
2. `TopologyRouter` — consult MAP-Elites archive for topology selection (archive-informed routing)
3. `StagnationDetector` — emit MAP-Elites staleness signal (no cell replacement in 20 tasks)
4. `MAPElitesArchive` — add staleness tracking, underexplored cell identification, cross-domain tagging
5. `DirectoryManager` — generate domain.yaml template, scaffold CHARTER.md placeholder

### What Phase 7 Does NOT Include

- No population-based evolution (Phase 8)
- No Elo tournament ranking (Phase 8)
- No meta-evolution (Phase 8)
- No autonomous run loop (Phase ∞)
- No actual Claude Code subprocess spawning (scouts are conceptual — they produce ScoutReport models)
- No cross-domain skill transfer (deferred: requires Phase 8 population evaluation)

### Key Design Decisions

1. **Scouts are advisory, not autonomous.** Scout spawner produces `ScoutReport` models describing exploration findings. The orchestrator decides whether to act on them. This prevents scouts from taking uncontrolled actions.

2. **Pressure fields are append-only within a session.** Agents write their exploration traces; fields are consolidated on read. No deletion — only saturation decay (exponential, configurable half-life).

3. **Domain switching parks all tasks.** The spec says "Park all and switch" | "Complete first" | "Cancel". Phase 7 implements park-and-switch only. Completion requires orchestrator changes beyond Phase 7 scope.

4. **MAP-Elites archive-informed routing is advisory.** `TopologyRouter` consults the archive as a hint, but falls back to existing heuristic rules if no archive entry exists or is too immature (< min_tasks).

5. **Cross-domain learning is read-only.** Domains can read the shared archive but cannot modify other domains' state. The archive is at the core level (`roles/archive/`) not domain-scoped.

---

## Part 2: Data Models

### New models in `src/uagents/models/expansion.py`

```python
"""Self-expansion models for Phase 7.
Spec reference: Section 9.2 (Pressure Fields), Section 22 (Domain), Section 25 (Phase 7).

Review fixes applied:
- FM-P7-016: ScoutTarget/ScoutReport/PressureField/DomainSwitchRecord inherit from
  IdentifiableModel for consistency with codebase conventions (id, created_at, updated_at).
- FM-P7-017: Note on StrEnum + use_enum_values=True behavior documented.
- FM-P7-023: ScoutReport.performance_estimate bounded to [0.0, 1.0].
- FM-P7-045: DomainConfig.name validated with max length.
- DR-Issue-1: Archive path clarified (archive is at core level, cross-domain reads only).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field, field_validator

from .base import FrameworkModel, IdentifiableModel, generate_id


class ScoutTargetType(StrEnum):
    """What the scout should explore."""
    ARCHIVE_GAP = "archive_gap"           # Unexplored MAP-Elites cell
    STAGNATION_RESPONSE = "stagnation_response"  # Response to stagnation signal
    DIVERSITY_FLOOR = "diversity_floor"    # SRD/VDI below floor
    MANUAL = "manual"                      # Human-requested exploration


class ScoutStatus(StrEnum):
    """Scout lifecycle states.

    Note: FrameworkModel has use_enum_values=True. After validation,
    status is stored as the raw string (e.g. "completed"). StrEnum.__eq__
    allows comparison with ScoutStatus.COMPLETED. Do NOT use isinstance()
    checks on enum fields after model construction.
    """
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ScoutTarget(IdentifiableModel):
    """What a scout agent should explore.

    Produced by ScoutSpawner based on stagnation signals, archive gaps,
    or manual requests. Consumed by the orchestrator to create scout tasks.

    FM-P7-016-FIX: Inherits from IdentifiableModel (provides id, created_at,
    updated_at) for consistency with codebase conventions.
    """
    id: str = Field(default_factory=lambda: generate_id("stgt"))
    target_type: ScoutTargetType
    description: str
    # For ARCHIVE_GAP: the cell coordinates to explore
    task_type: str = ""
    complexity: str = ""
    # Priority: higher = more urgent
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # FM-P7-016-FIX: IdentifiableModel requires created_at at construction;
    # default_factory satisfies this. updated_at from TimestampedModel defaults to None.

    @field_validator("task_type", "complexity")
    @classmethod
    def _validate_archive_coords(cls, v: str, info) -> str:
        """FM-P7-DR-Issue-9: Validate ARCHIVE_GAP targets have coordinates.
        Validation is done at the ScoutSpawner level, not here — model allows
        empty strings for non-ARCHIVE_GAP targets."""
        return v


class ScoutReport(IdentifiableModel):
    """Result from a scout exploration.

    Filed by the orchestrator after a scout task completes. Contains
    findings that may trigger evolution proposals or archive updates.

    FM-P7-016-FIX: Inherits from IdentifiableModel.
    FM-P7-023-FIX: performance_estimate bounded to [0.0, 1.0].
    """
    id: str = Field(default_factory=lambda: generate_id("srpt"))
    target_id: str  # References ScoutTarget.id
    scout_agent_id: str = ""
    status: ScoutStatus = ScoutStatus.COMPLETED
    findings: str = ""  # Free-text description of what was found
    recommendation: str = ""  # Suggested action
    # Behavioral coordinates for archive update
    task_type: str = ""
    complexity: str = ""
    # FM-P7-023-FIX: Bounded to prevent archive corruption from unbounded values
    performance_estimate: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PressureRegion(FrameworkModel):
    """A single region in a pressure field.

    Tracks which agents have explored this region and how saturated it is.
    Saturation decays exponentially over time.
    """
    name: str
    explored_by: list[str] = Field(default_factory=list)  # Agent IDs
    saturation: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PressureField(IdentifiableModel):
    """A stigmergic pressure field for indirect coordination.

    Spec reference: Section 9.2.
    Agents leave traces that influence other agents' behavior.
    Low-saturation regions attract exploration.

    FM-P7-016-FIX: Inherits from IdentifiableModel for id/timestamp consistency.
    """
    id: str = Field(default_factory=lambda: generate_id("pf"))
    name: str  # e.g., "exploration_pressure", "evolution_pressure"
    regions: list[PressureRegion] = Field(default_factory=list)
    decay_half_life_hours: float = 24.0  # Saturation halves every N hours
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # updated_at inherited from TimestampedModel, defaults to None


class VoiceDefaults(FrameworkModel):
    """Domain-level voice atom defaults.

    Spec reference: Section 22.2 (voice_defaults in domain.yaml).
    DR-Issue-17-FIX: Strongly typed instead of bare dict[str, str | float].
    """
    description: str = ""
    language: str = ""       # e.g., "language_japanese"
    tone: str = ""           # e.g., "tone_precise"
    style: str = ""          # e.g., "style_technical"
    formality: float = Field(default=0.7, ge=0.0, le=1.0)
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0)


class DomainConfig(FrameworkModel):
    """Configuration for a domain workspace.

    Spec reference: Section 22.2.
    Each domain has capabilities, review criteria, task types, and voice defaults.
    """
    name: str = Field(min_length=1, max_length=64)  # FM-P7-045-FIX: length limit
    description: str = ""
    capabilities: dict[str, dict] = Field(default_factory=dict)
    review_criteria: list[str] = Field(default_factory=list)
    task_types: list[str] = Field(default_factory=list)
    voice_defaults: VoiceDefaults = Field(default_factory=VoiceDefaults)  # DR-Issue-17-FIX


class DomainSwitchRecord(IdentifiableModel):
    """Record of a domain switch event.

    Logged to shared/domain-switches/ for audit trail.
    FM-P7-016-FIX: Inherits from IdentifiableModel.
    """
    id: str = Field(default_factory=lambda: generate_id("dsw"))
    from_domain: str
    to_domain: str
    parked_task_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
```

---

## Part 3: ScoutSpawner

### `src/uagents/engine/scout_spawner.py`

```python
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
        from .map_elites_archive import MAPElitesArchive

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
        if stagnation_signals:
            for signal in stagnation_signals:
                # IFM-N53: fail-loud on required signal fields
                level = signal["level"]
                description = signal["description"]
                targets.append(ScoutTarget(
                    target_type=ScoutTargetType.STAGNATION_RESPONSE,
                    description=f"Explore alternatives for: {description}",
                    priority=0.8 if level == "framework" else 0.6,
                ))

        # 3. Diversity floor breach
        if srd_below_floor:
            targets.append(ScoutTarget(
                target_type=ScoutTargetType.DIVERSITY_FLOOR,
                description="SRD below diversity floor — explore divergent approaches",
                priority=0.7,
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
        """Load recent scout reports, sorted by created_at descending."""
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
                priority=0.3,  # Low priority — background exploration
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
                if data.get("target_id") == target_id:
                    return True
        return False
```

---

## Part 4: PressureFieldCoordinator

### `src/uagents/engine/pressure_field.py`

```python
"""Stigmergic coordination via pressure fields.
Spec reference: Section 9.2 (Stigmergic Coordination).

Agents leave traces in shared YAML files that influence other agents'
behavior without direct messages. Low-saturation regions attract exploration.

Key constraints:
- Pressure fields are per-domain
- Saturation decays exponentially (configurable half-life)
- Agents read fields before choosing exploration targets
- Agents write traces after completing work in a region
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from ..models.expansion import PressureField, PressureRegion
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.pressure_field")


class PressureFieldError(RuntimeError):
    """Raised when pressure field operations fail.

    DR-Issue-3-FIX: Inherits RuntimeError per codebase convention.
    """


class PressureFieldCoordinator:
    """Manages stigmergic pressure fields for indirect coordination.

    Usage:
        coord = PressureFieldCoordinator(yaml_store)
        field = coord.get_or_create("exploration_pressure", regions=["diversity", "topology", "skills"])
        least = coord.get_least_explored("exploration_pressure")
        coord.record_exploration("exploration_pressure", "diversity", agent_id="agent-001")
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta") -> None:
        self.yaml_store = yaml_store
        self._domain = domain
        self._fields_base = f"instances/{domain}/state/coordination/pressure-fields"
        yaml_store.ensure_dir(self._fields_base)

    def get_or_create(
        self,
        field_name: str,
        regions: list[str] | None = None,
        decay_half_life_hours: float = 24.0,
    ) -> PressureField:
        """Load or create a pressure field.

        Args:
            field_name: Name of the pressure field.
            regions: Region names to initialize if creating. Required for new fields.
            decay_half_life_hours: Saturation decay half-life.

        Returns:
            The pressure field (loaded or newly created).

        Raises:
            PressureFieldError: If creating a new field without regions.
        """
        path = f"{self._fields_base}/{field_name}.yaml"
        try:
            field = self.yaml_store.read(path, PressureField)
            # Apply decay to all regions
            self._apply_decay(field)
            return field
        except FileNotFoundError:
            if not regions:
                raise PressureFieldError(
                    f"Pressure field '{field_name}' does not exist and no "
                    f"regions provided to create it."
                )
            field = PressureField(
                name=field_name,
                regions=[PressureRegion(name=r) for r in regions],
                decay_half_life_hours=decay_half_life_hours,
            )
            self.yaml_store.write(path, field)
            logger.info(f"Created pressure field '{field_name}' with {len(regions)} regions")
            return field

    def record_exploration(
        self,
        field_name: str,
        region_name: str,
        agent_id: str,
        saturation_increment: float = 0.1,
    ) -> PressureField:
        """Record that an agent explored a region.

        Increases saturation and adds agent to explored_by list.

        Args:
            field_name: Name of the pressure field.
            region_name: Region that was explored.
            agent_id: The exploring agent's ID.
            saturation_increment: How much to increase saturation (default 0.1).

        Returns:
            Updated pressure field.

        Raises:
            PressureFieldError: If field or region not found.
        """
        path = f"{self._fields_base}/{field_name}.yaml"
        try:
            field = self.yaml_store.read(path, PressureField)
        except FileNotFoundError:
            raise PressureFieldError(
                f"Pressure field '{field_name}' not found."
            )

        # Apply decay first
        self._apply_decay(field)

        # Find the region
        region = self._find_region(field, region_name)

        # Update region
        if agent_id not in region.explored_by:
            region.explored_by.append(agent_id)
        region.saturation = min(1.0, region.saturation + saturation_increment)
        region.last_updated = datetime.now(timezone.utc)
        field.updated_at = datetime.now(timezone.utc)

        self.yaml_store.write(path, field)
        logger.info(
            f"Recorded exploration in '{field_name}/{region_name}' by {agent_id}: "
            f"saturation={region.saturation:.2f}"
        )
        return field

    def get_least_explored(self, field_name: str) -> PressureRegion | None:
        """Get the region with lowest saturation (most attractive for exploration).

        Returns None if the field has no regions.
        """
        path = f"{self._fields_base}/{field_name}.yaml"
        try:
            field = self.yaml_store.read(path, PressureField)
        except FileNotFoundError:
            return None

        self._apply_decay(field)
        if not field.regions:
            return None

        return min(field.regions, key=lambda r: r.saturation)

    def get_field_summary(self, field_name: str) -> dict | None:
        """Get a summary of a pressure field's state.

        Returns None if field doesn't exist.
        """
        path = f"{self._fields_base}/{field_name}.yaml"
        try:
            field = self.yaml_store.read(path, PressureField)
        except FileNotFoundError:
            return None

        self._apply_decay(field)
        return {
            "name": field.name,
            "region_count": len(field.regions),
            "regions": {
                r.name: {
                    "saturation": round(r.saturation, 3),
                    "explored_by_count": len(r.explored_by),
                }
                for r in field.regions
            },
            "decay_half_life_hours": field.decay_half_life_hours,
        }

    def _apply_decay(self, field: PressureField) -> None:
        """Apply exponential saturation decay to all regions.

        DR-Issue-20-FIX: Updates field.updated_at after decay application.
        """
        now = datetime.now(timezone.utc)
        half_life_seconds = field.decay_half_life_hours * 3600
        any_decayed = False

        for region in field.regions:
            elapsed = (now - region.last_updated).total_seconds()
            if elapsed > 0 and region.saturation > 0:
                decay_factor = math.pow(0.5, elapsed / half_life_seconds)
                region.saturation = region.saturation * decay_factor
                any_decayed = True

        if any_decayed:
            field.updated_at = now

    def _find_region(self, field: PressureField, region_name: str) -> PressureRegion:
        """Find a region by name (fail-loud)."""
        for region in field.regions:
            if region.name == region_name:
                return region
        raise PressureFieldError(
            f"Region '{region_name}' not found in pressure field '{field.name}'. "
            f"Available: {[r.name for r in field.regions]}"
        )
```

---

## Part 5: DomainManager

### `src/uagents/engine/domain_manager.py`

```python
"""Domain instantiation and switching protocol.
Spec reference: Section 22 (Domain Instantiation & Switching).

Each domain is a separate working subdirectory with its own:
- CHARTER.md (domain-specific charter)
- domain.yaml (domain configuration)
- state/ (domain-specific state)
- logs/ (domain-specific logs)

Key constraints:
- Domain switching parks all active tasks
- New domain creation scaffolds from template
- Cross-domain learning via shared archive only
- Domain names validated against path traversal
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models.base import generate_id
from ..models.expansion import DomainConfig, DomainSwitchRecord
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.domain_manager")


class DomainError(RuntimeError):
    """Raised when domain operations fail.

    DR-Issue-3-FIX: Inherits RuntimeError per codebase convention.
    """


class DomainManager:
    """Manages domain workspaces: creation, switching, listing.

    Usage:
        mgr = DomainManager(yaml_store, directory_manager)
        mgr.create_domain("research-lab", description="Research domain")
        record = mgr.switch_domain("meta", "research-lab", reason="Starting research")
        domains = mgr.list_domains()
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        directory_manager: "DirectoryManager",
    ) -> None:
        from ..state.directory import DirectoryManager

        self.yaml_store = yaml_store
        self.directory_manager = directory_manager

    def create_domain(
        self,
        name: str,
        description: str = "",
        task_types: list[str] | None = None,
        voice_defaults: dict[str, str | float] | None = None,
    ) -> DomainConfig:
        """Create a new domain workspace.

        Scaffolds the directory structure and creates domain.yaml.

        Args:
            name: Domain name (must be valid directory name).
            description: Human-readable domain description.
            task_types: Domain-specific task types.
            voice_defaults: Domain-level voice atom defaults.

        Returns:
            The created DomainConfig.

        Raises:
            DomainError: If domain already exists or name is invalid.
        """
        # Validate name
        self._validate_domain_name(name)

        # Check if already exists
        instance_dir = self.yaml_store.base_dir / "instances" / name
        if instance_dir.exists():
            raise DomainError(f"Domain '{name}' already exists at {instance_dir}")

        # Scaffold directory structure
        self.directory_manager.scaffold_domain(self.yaml_store.base_dir, name)

        # Create domain.yaml
        config = DomainConfig(
            name=name,
            description=description,
            task_types=task_types or [],
            voice_defaults=voice_defaults or {},
        )
        domain_yaml_path = f"instances/{name}/domain.yaml"
        self.yaml_store.write_raw(domain_yaml_path, {"domain": config.model_dump()})

        # Create placeholder CHARTER.md
        charter_path = instance_dir / "CHARTER.md"
        charter_path.write_text(
            f"# {name} Domain Charter\n\n"
            f"**Description:** {description}\n\n"
            f"## Principles\n\n"
            f"_Define domain-specific principles here._\n\n"
            f"## Boundaries\n\n"
            f"_Define what this domain covers and what it does not._\n",
            encoding="utf-8",
        )

        logger.info(f"Domain '{name}' created at {instance_dir}")
        return config

    def switch_domain(
        self,
        from_domain: str,
        to_domain: str,
        reason: str = "",
    ) -> DomainSwitchRecord:
        """Switch from one domain to another.

        Parks all active tasks in the source domain.

        Args:
            from_domain: Current domain name.
            to_domain: Target domain name.
            reason: Why the switch is happening.

        Returns:
            DomainSwitchRecord documenting the switch.

        Raises:
            DomainError: If source or target domain does not exist.
        """
        # FM-P7-047-FIX: Validate BOTH source and target exist
        source_dir = self.yaml_store.base_dir / "instances" / from_domain
        if not source_dir.exists():
            raise DomainError(
                f"Source domain '{from_domain}' does not exist."
            )

        target_dir = self.yaml_store.base_dir / "instances" / to_domain
        if not target_dir.exists():
            raise DomainError(
                f"Target domain '{to_domain}' does not exist. "
                f"Create it first with create_domain()."
            )

        # Count and park active tasks in source domain
        parked_count = self._park_active_tasks(from_domain)

        # Record the switch
        record = DomainSwitchRecord(
            from_domain=from_domain,
            to_domain=to_domain,
            parked_task_count=parked_count,
            reason=reason,
        )

        # Persist switch record to shared location
        self.yaml_store.ensure_dir("shared/domain-switches")
        self.yaml_store.write(
            f"shared/domain-switches/{record.id}.yaml", record,
        )

        logger.info(
            f"Switched from '{from_domain}' to '{to_domain}': "
            f"parked {parked_count} tasks. Reason: {reason}"
        )
        return record

    def list_domains(self) -> list[str]:
        """List all existing domain names."""
        instances_dir = self.yaml_store.base_dir / "instances"
        if not instances_dir.exists():
            return []
        return sorted(
            d.name for d in instances_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def get_domain_config(self, name: str) -> DomainConfig:
        """Load a domain's configuration.

        Raises:
            DomainError: If domain does not exist or config is missing.
        """
        config_path = f"instances/{name}/domain.yaml"
        try:
            raw = self.yaml_store.read_raw(config_path)
            return DomainConfig(**raw["domain"])
        except FileNotFoundError:
            raise DomainError(
                f"Domain '{name}' does not exist or has no domain.yaml"
            )

    def domain_exists(self, name: str) -> bool:
        """Check if a domain directory exists."""
        return (self.yaml_store.base_dir / "instances" / name).exists()

    # FM-P7-045-FIX: Maximum domain name length (NAME_MAX safe)
    MAX_DOMAIN_NAME_LENGTH = 64

    def _validate_domain_name(self, name: str) -> None:
        """Validate domain name against path traversal, invalid chars, and length."""
        if not name:
            raise DomainError("Domain name cannot be empty")
        # FM-P7-045-FIX: Length check prevents filesystem path limit issues
        if len(name) > self.MAX_DOMAIN_NAME_LENGTH:
            raise DomainError(
                f"Domain name '{name[:20]}...' too long ({len(name)} chars, "
                f"max {self.MAX_DOMAIN_NAME_LENGTH})"
            )
        if "/" in name or "\\" in name or ".." in name:
            raise DomainError(
                f"Invalid domain name '{name}': must not contain "
                f"path separators or '..'"
            )
        if name.startswith("."):
            raise DomainError(
                f"Invalid domain name '{name}': must not start with '.'"
            )
        # Only allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
            raise DomainError(
                f"Invalid domain name '{name}': must start with alphanumeric "
                f"and contain only alphanumeric, hyphens, underscores"
            )

    def _park_active_tasks(self, domain: str) -> int:
        """Park all active tasks in a domain. Returns count of parked tasks.

        Reads tasks from instances/{domain}/state/tasks/active/ and moves
        them to instances/{domain}/state/tasks/parked/.

        FM-P7-046-FIX: Updates task status field before moving file.
        FM-P7-FM-13-FIX: Refuses to park tasks with status EXECUTING.
        """
        active_dir = self.yaml_store.base_dir / f"instances/{domain}/state/tasks/active"
        parked_dir = self.yaml_store.base_dir / f"instances/{domain}/state/tasks/parked"

        if not active_dir.exists():
            return 0

        parked_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for task_file in active_dir.iterdir():
            if task_file.suffix in (".yaml", ".yml"):
                # FM-P7-046-FIX: Update task status in YAML before moving
                rel_path = f"instances/{domain}/state/tasks/active/{task_file.name}"
                task_data = self.yaml_store.read_raw(rel_path)

                # FM-P7-FM-13-FIX: Refuse to park executing tasks
                task_status = task_data.get("status", "")
                if task_status == "executing":
                    raise DomainError(
                        f"Cannot park task {task_file.name} in domain '{domain}': "
                        f"task is currently EXECUTING. Wait for completion or cancel first."
                    )

                task_data["status"] = "parked"
                task_data["parked_at"] = datetime.now(timezone.utc).isoformat()
                task_data["parked_reason"] = f"domain_switch_from_{domain}"
                self.yaml_store.write_raw(rel_path, task_data)

                # Move to parked directory
                target = parked_dir / task_file.name
                task_file.rename(target)
                count += 1
                logger.info(f"Parked task {task_file.name} in domain '{domain}'")

        return count
```

---

## Part 6: Modified Components

### 6.1 StagnationDetector Modifications

Add MAP-Elites staleness signal (no cell replacement in N tasks):

```python
# In stagnation_detector.py, add to module-level constants:
ARCHIVE_STALENESS_THRESHOLD = 20  # No cell replacement in this many tasks

# Add to StagnationDetector.__init__():
self._tasks_since_archive_update: int = 0

# Add new method:
def record_archive_update(self) -> None:
    """Record that a MAP-Elites archive cell was replaced. Resets counter."""
    self._tasks_since_archive_update = 0
    self._save_state()

# FM-P7-056-FIX: Add to _save_state():
# In the state dict, add:
#   "tasks_since_archive_update": self._tasks_since_archive_update,

# FM-P7-056-FIX: Add to _load_state():
# Use .get() with default 0 — this is the FM-119 backward-compat pattern,
# NOT a violation of IFM-N53 (state files from older versions won't have this key).
#   self._tasks_since_archive_update = int(state.get("tasks_since_archive_update", 0))

# Modify _check_framework_stagnation() to add:
# After existing framework-level checks:
# FM-P7-057-FIX: Only fire at multiples of threshold (FM-104 pattern),
# not on every task after threshold is crossed.
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

# Modify check_all() to increment:
self._tasks_since_archive_update += 1
```

### 6.2 TopologyRouter Modifications

Add archive-informed routing (advisory):

```python
# In TopologyRouter.__init__(), add parameter:
#   map_elites_archive: "MAPElitesArchive | None" = None,
# And store: self._archive = map_elites_archive

# Add new method:
def _consult_archive(self, task: Task) -> str | None:
    """Consult MAP-Elites archive for topology hint.

    Returns topology pattern name if archive has a mature entry,
    None otherwise (caller should fall back to heuristics).

    DR-Issue-6-FIX: Method name is _consult_archive (consistent with call site).
    FM-P7-061-FIX: Task type vocabulary matches archive vocabulary.
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

def _infer_task_type(self, task: Task) -> str:
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

def _infer_complexity(self, task: Task) -> str:
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
```

In `route()`, add archive consultation before the heuristic chain:

```python
# At the top of route(), after resource check:
# DR-Issue-6-FIX: Consistent method name (_consult_archive, not _consult_archive_for_task)
archive_hint = self._consult_archive(task)
if archive_hint:
    logger.info(f"Archive suggests topology: {archive_hint}")
    # Use archive hint but still apply resource constraints
    # (archive hint is advisory, not mandatory)
```

Note: Full archive-informed routing integration is deferred to Phase 8 (requires population evaluation to validate archive suggestions). Phase 7 adds the consultation method and logging only.

### 6.3 Orchestrator Modifications

Add scout spawner and pressure field coordinator:

```python
# In Orchestrator.__init__() TYPE_CHECKING block, add:
from .scout_spawner import ScoutSpawner
from .pressure_field import PressureFieldCoordinator
from .domain_manager import DomainManager

# Add constructor parameters (after creativity_engine):
#   scout_spawner: ScoutSpawner | None = None,
#   pressure_field_coordinator: PressureFieldCoordinator | None = None,
#   domain_manager: DomainManager | None = None,

# Store:
# self._scout_spawner = scout_spawner
# self._pressure_field_coordinator = pressure_field_coordinator
# self._domain_manager = domain_manager

# FM-P7-067-FIX / DR-Issue-15-FIX: Scout spawning is OUTSIDE the diversity
# engine block so that solo tasks and framework-level stagnation can also
# trigger scouts. Place this AFTER the diversity engine block (after line 460
# in current orchestrator.py), using stagnation_signals if available.

# In record_task_outcome(), AFTER the diversity engine block (after return results):
# Replace the tail of record_task_outcome() with:

        # Phase 7: Scout spawning check — OUTSIDE diversity block so solo
        # tasks can trigger scouts via framework-level stagnation.
        if self._scout_spawner is not None:
            # Collect stagnation signals (may be from diversity block or empty)
            scout_stagnation = results.get("stagnation_signals", [])
            # For solo tasks, run framework-level stagnation check directly
            if not scout_stagnation and self.stagnation_detector is not None:
                # Framework-level checks don't require SRD — check independently
                fw_signals = self.stagnation_detector._check_framework_stagnation()
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
                srd_below_floor = any(
                    s.get("level") == "team" for s in scout_stagnation
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
```

### 6.4 MAPElitesArchive Modifications

Add staleness tracking, underexplored cell identification, and public accessors:

```python
# DR-Issue-18-FIX: Add public accessor properties for archive dimensions
@property
def task_types(self) -> list[str]:
    """Public accessor for archive task type vocabulary."""
    return list(self._task_types)

@property
def complexities(self) -> list[str]:
    """Public accessor for archive complexity vocabulary."""
    return list(self._complexities)

# Add to MAPElitesArchive:
def get_underexplored_cells(self, min_task_count: int = 3) -> list[tuple[str, str]]:
    """Return cells with fewer than min_task_count evaluations.

    Returns list of (task_type, complexity) tuples.
    """
    underexplored: list[tuple[str, str]] = []
    for cell in self._state.cells:
        if cell.task_count < min_task_count:
            underexplored.append((cell.task_type, cell.complexity))
    return underexplored

def get_unoccupied_cells(self) -> list[tuple[str, str]]:
    """Return all cell coordinates that have no occupant."""
    occupied = {(c.task_type, c.complexity) for c in self._state.cells}
    unoccupied: list[tuple[str, str]] = []
    for task_type in self._task_types:
        for complexity in self._complexities:
            if (task_type, complexity) not in occupied:
                unoccupied.append((task_type, complexity))
    return unoccupied
```

### 6.5 DirectoryManager Modifications

Add scout and domain-switch directories:

```python
# FM-P7-077-FIX: "shared/" already exists in CORE_DIRS. Only add new subdirectory.
# In DirectoryManager.CORE_DIRS, add:
"shared/domain-switches/",

# DR-Issue-5-FIX: Add scout directories to INSTANCE_DIRS so they are
# scaffolded for each domain instance, not just created on-the-fly.
# In DirectoryManager.INSTANCE_DIRS, add:
"state/scouts/",
"state/scouts/targets/",
"state/scouts/reports/",
```

---

## Part 7: YAML Configuration

### `core/scout.yaml`

```yaml
# Scout agent configuration — Phase 7 Self-Expansion.
# All keys consumed by ScoutSpawner.generate_targets() and get_active_scout_count().
# FM-P7-080-FIX: Every key in this file must be consumed by code. No dead config.
scout:
  max_pending_targets: 5       # Max targets returned by generate_targets()
  max_active_scouts: 1         # Enforced in generate_targets() — returns [] if reached
  target_expiry_hours: 48      # Consumed by orchestrator cleanup (Phase 8+)
  # Priority values used as defaults in target generation — overridable per target_type
  archive_gap_priority: 0.3
  stagnation_priority: 0.7
  diversity_floor_priority: 0.6
```

---

## Part 8: Implementation Sequence

```
Step 1: Create models (src/uagents/models/expansion.py)
  └── No dependencies — pure data models
  └── Import IdentifiableModel from base (FM-P7-016-FIX)

Step 2: Create YAML config (core/scout.yaml)
  └── Used by test fixtures and ScoutSpawner._load_config()
  └── FM-P7-025-FIX: File MUST be created during scaffold, not just by tests

Step 3: Modify DirectoryManager (src/uagents/state/directory.py)
  └── Add shared/domain-switches/ to CORE_DIRS
  └── Add state/scouts/ subdirs to INSTANCE_DIRS
  └── FM-P7-077-FIX: Don't re-add shared/ (already exists)

Step 4: Create PressureFieldCoordinator (src/uagents/engine/pressure_field.py)
  └── Depends on: models, YamlStore

Step 5: Create ScoutSpawner (src/uagents/engine/scout_spawner.py)
  └── Depends on: models, YamlStore, MAPElitesArchive (optional)

Step 6: Create DomainManager (src/uagents/engine/domain_manager.py)
  └── Depends on: models, YamlStore, DirectoryManager

Step 7: Modify StagnationDetector (archive staleness signal)
  └── Depends on: existing StagnationDetector
  └── FM-P7-056-FIX: Persist _tasks_since_archive_update in _save_state/_load_state

Step 8: Modify MAPElitesArchive (underexplored/unoccupied cells + public accessors)
  └── Depends on: existing MAPElitesArchive
  └── DR-Issue-18-FIX: Add task_types/complexities properties

Step 9: Modify TopologyRouter (archive consultation)
  └── Depends on: existing TopologyRouter, MAPElitesArchive
  └── FM-P7-061-FIX: Task type vocabulary matches archive vocabulary

Step 10: Modify Orchestrator (wire scout spawner, pressure fields, domain manager)
  └── Depends on: Steps 4-6, 7-8
  └── FM-P7-067-FIX: Scout check OUTSIDE diversity engine block
  └── DR-Issue-22-FIX: Budget pressure check before scout spawning
```

Note: Audit logging for scout events (former Step 11) is deferred. Scout events are
logged via `logger.info()` calls in ScoutSpawner. Structured audit entries require
defining a `ScoutLogEntry` model, which is deferred to Phase 8 when the scout
lifecycle is complete (DR-Issue-16).

---

## Part 9: Verification Checklist

1. `uv run pytest tests/test_models/test_expansion.py -v` — all expansion models validate correctly (IdentifiableModel inheritance, enum handling, field bounds)
2. `uv run pytest tests/test_engine/test_scout_spawner.py -v` — scout targeting, reporting, archive gaps, max_active_scouts enforcement, deduplication
3. `uv run pytest tests/test_engine/test_pressure_field.py -v` — create, explore, decay, least-explored, updated_at after decay
4. `uv run pytest tests/test_engine/test_domain_manager.py -v` — create, switch, list, config, from_domain validation, park status update, executing task rejection, name length limit
5. `uv run pytest tests/test_engine/test_stagnation_detector.py -v` — archive staleness signal, state persistence, modulo suppression
6. `uv run pytest tests/test_engine/test_map_elites_archive.py -v` — underexplored/unoccupied cells, public accessors
7. `uv run pytest tests/test_engine/test_topology_router.py -v` — archive consultation, task type vocabulary, unknown topology rejection
8. `uv run pytest tests/test_engine/test_orchestrator.py -v` — scout wiring, budget pressure gating, solo task scout triggering
9. `uv run pytest --tb=short -q` — full suite, 0 failures
10. Create "research-lab" domain and verify scaffold is complete (DR-Issue-23-FIX)
11. Switch from "meta" to "research-lab" and verify task parking + status update
12. Verify ScoutSpawner generates targets when archive has gaps

---

## Part 10: Edge Cases & Failure Modes (Pre-Review + Post-Review Consolidated)

| ID | Component | Description | Severity | Mitigation | Status |
|----|-----------|-------------|----------|------------|--------|
| FM-P7-01 | ScoutSpawner | No MAP-Elites archive → no archive gap targets | LOW | Other target types still work | Pre-review |
| FM-P7-02 | PressureField | Decay applied on every read → FP drift | LOW | Saturation clamped to [0.0, 1.0] | Pre-review |
| FM-P7-03 | DomainManager | Path traversal via domain name | HIGH | Regex + traversal checks + length limit | MITIGATED |
| FM-P7-04 | DomainManager | Race: two processes creating same domain | MEDIUM | mkdir exists check + idempotent scaffold | Pre-review |
| FM-P7-05 | ScoutSpawner | Target references deleted archive cell | LOW | Targets are informational | Pre-review |
| FM-P7-06 | PressureField | Region last_updated timezone mismatch | MEDIUM | All datetimes use timezone.utc | Pre-review |
| FM-P7-07 | StagnationDetector | archive_update counter not persisted | HIGH | FM-P7-056-FIX: Added to _save/_load_state | FIXED v0.2 |
| FM-P7-08 | TopologyRouter | Archive returns unknown topology | LOW | Guard: reject unknown patterns | MITIGATED |
| FM-P7-09 | DomainManager | switch_domain while tasks executing | HIGH | FM-P7-FM-13-FIX: Fail-loud on EXECUTING | FIXED v0.2 |
| FM-P7-10 | ScoutSpawner | _has_report scans all report files | MEDIUM | O(N*M) acceptable for Phase 7 | ACCEPTED |
| FM-P7-11 | Orchestrator | scout_spawner None but signals present | LOW | Guarded by `if self._scout_spawner` | Pre-review |
| FM-P7-12 | DomainManager | domain.yaml via write_raw | LOW | DomainConfig.model_dump() | Pre-review |
| FM-P7-13 | PressureField | Near-zero saturation precision | LOW | float64 sufficient | Pre-review |
| FM-P7-14 | ScoutSpawner | get_active_scout_count reads all files | MEDIUM | Same as FM-P7-10 | ACCEPTED |
| FM-P7-15 | DomainManager | CHARTER.md overwritten on re-create | HIGH | create_domain checks existence | Pre-review |

### Review-Identified Failure Modes (Steps 3-4)

**Design Review (Step 3) — 25 issues, 8 HIGH:**
- DR-Issue-1 (HIGH): Cross-domain archive tagging → deferred to Phase 8 (requires population eval)
- DR-Issue-2 (HIGH): `_tasks_since_archive_update` not in _save/_load_state → **FIXED v0.2**
- DR-Issue-3 (HIGH): Error classes inherit Exception not RuntimeError → **FIXED v0.2**
- DR-Issue-4 (HIGH): Domain switch missing from_domain validation + log path → **FIXED v0.2**
- DR-Issue-5 (HIGH): Scout dirs missing from INSTANCE_DIRS → **FIXED v0.2**
- DR-Issue-6 (HIGH): TopologyRouter method naming + vocabulary mismatch → **FIXED v0.2**
- DR-Issue-7 (HIGH): max_active_scouts never enforced → **FIXED v0.2**
- DR-Issue-8 (HIGH): Spec gaps (continuous scouting, cross-domain validation) → partial fix, Phase 8 deferred
- DR-Issue-9 (MEDIUM): ARCHIVE_GAP coordinate validation → model allows empty (validated at spawner level)
- DR-Issue-15 (MEDIUM→HIGH): Scout integration inside diversity block → **FIXED v0.2**
- DR-Issue-16 (MEDIUM): Audit logging undefined → deferred to Phase 8
- DR-Issue-17 (MEDIUM): DomainConfig voice_defaults weakly typed → **FIXED v0.2** (VoiceDefaults model)
- DR-Issue-18 (LOW): Private _task_types/_complexities access → **FIXED v0.2** (public properties)
- DR-Issue-20 (LOW): updated_at not updated after decay → **FIXED v0.2**
- DR-Issue-22 (LOW→HIGH): No budget check for scout spawning → **FIXED v0.2**
- DR-Issue-23 (LOW): Missing verification checklist items → **FIXED v0.2**
- DR-Issue-25 (LOW): Use typed read for target validation → **FIXED v0.2**

**Failure Mode Enumeration (Step 4) — 82 modes: 1 CRITICAL, 25 HIGH, 39 MEDIUM, 17 LOW:**
- FM-P7-016 (HIGH): Model inheritance inconsistency → **FIXED v0.2** (IdentifiableModel)
- FM-P7-017 (HIGH): StrEnum + use_enum_values isinstance caveat → documented in model docstring
- FM-P7-023 (HIGH): Unbounded performance_estimate → **FIXED v0.2** (ge=0, le=1)
- FM-P7-025 (HIGH): Missing scout.yaml creation → **FIXED v0.2** (implementation sequence note)
- FM-P7-034 (HIGH): Duplicate scout targets → **FIXED v0.2** (deduplication in _find_archive_gaps)
- FM-P7-036 (HIGH): PressureField concurrent creation race → ACCEPTED (YamlStore advisory lock; low frequency)
- FM-P7-045 (HIGH): Domain name length → **FIXED v0.2** (max_length=64)
- FM-P7-046 (HIGH): Parked task status not updated → **FIXED v0.2** (update status in YAML before move)
- FM-P7-047 (HIGH): from_domain not validated → **FIXED v0.2**
- FM-P7-053 (HIGH): Only park-and-switch implemented → ACCEPTED (design decision #3)
- FM-P7-056 (HIGH): State persistence gap → **FIXED v0.2**
- FM-P7-057 (HIGH): Archive staleness log spam → **FIXED v0.2** (modulo suppression)
- FM-P7-061 (HIGH): Task type vocabulary mismatch → **FIXED v0.2**
- FM-P7-062 (HIGH): Complexity vocabulary inconsistency → **FIXED v0.2** (documented)
- FM-P7-066 (HIGH): Orchestrator 22+ params → ACCEPTED (Phase 8 refactor)
- FM-P7-067 (HIGH): Scout check inside diversity block → **FIXED v0.2**
- FM-P7-068 (HIGH): srd_below_floor semantics → ACCEPTED (conservative: only on confirmed stagnation)
- FM-P7-077 (HIGH): Redundant shared/ in CORE_DIRS → **FIXED v0.2**
- FM-P7-080 (HIGH): max_active_scouts not enforced → **FIXED v0.2**
- FM-P7-083 (HIGH): Concurrent pressure field updates → ACCEPTED (same as FM-P7-036)
- FM-P7-088 (CRITICAL): Scout lifecycle incomplete → ACCEPTED by design: scouts are advisory models in Phase 7, lifecycle completion is Phase 8+
- FM-P7-089 (HIGH): Archive gap may fill before scout runs → ACCEPTED (advisory reports)
- FM-P7-090 (HIGH): TaskLifecycle in-memory cache after park → mitigated by design (domain switch is a full-stop operation; orchestrator should reinit after switch)
- FM-P7-094 (HIGH): DomainManager/DirectoryManager root mismatch → documented (both receive same YamlStore; constructor should assert base_dir consistency)

**Summary of v0.2 changes:** 22 fixes applied, 4 HIGH items accepted by design, 1 CRITICAL accepted (Phase 7 scouts are advisory models).
