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
            # Apply decay to all regions — intentionally not persisted on read.
            # Decay is deterministic (idempotent), so re-applying from original
            # last_updated timestamps produces correct results every time.
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
