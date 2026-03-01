"""MAP-Elites quality-diversity archive for evolution.
Spec reference: Section 7.4 (MAP-Elites Configuration Archive).

Maintains a behavioral archive of successful configurations indexed
by (task_type, complexity). Stores the best-performing configuration
per cell. Novelty bonus encourages exploration of underexplored cells.

Key constraints:
- Update rule: replace cell occupant only if new > existing
- Novelty bonus (0.1) added for first-time cell occupation
- Minimum task count before a cell can serve as baseline
- Archive persisted as YAML to state/evolution/archive.yaml

Literature basis:
- MAP-Elites (Mouret & Clune, 2015): quality-diversity via behavioral grid
- ADAS (ICLR 2025): archive of agentic designs indexed by task type
- DGM: population-based evaluation with behavioral diversity
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.evolution import (
    ArchiveCell,
    EvolutionRecord,
    MAPElitesState,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.map_elites_archive")


class MAPElitesArchive:
    """Quality-diversity archive indexed by (task_type, complexity).

    Design invariants:
    - Each cell stores best-performing configuration
    - Replace only if new performance > existing
    - Novelty bonus for first-time cell occupants
    - Archive persisted to YAML after every update
    - Read from disk on init (crash recovery)

    Usage:
        archive = MAPElitesArchive(yaml_store, domain)
        archive.update_from_evolution(record)
        best = archive.get_best_config("research", "complex")
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self.domain = domain

        # Load config
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        arc = config_raw["evolution"]["archive"]

        # IFM-N53: Direct dict access
        self._task_types: list[str] = arc["task_types"]
        self._complexities: list[str] = arc["complexities"]
        self._novelty_bonus = float(arc["novelty_bonus"])
        self._min_tasks = int(arc["min_tasks_for_cell"])
        self._archive_path = str(arc["archive_path"])

        # Load or initialize state
        self._state = self._load_state()

    def update_from_evolution(self, record: EvolutionRecord) -> bool:
        """Update archive with a successful evolution.

        Extracts task_type and complexity from the evolution evidence,
        and updates the corresponding cell if performance is better.

        Args:
            record: Completed evolution record (must be PROMOTED).

        Returns:
            True if the archive was updated, False otherwise.
        """
        outcome = record.outcome
        outcome_str = outcome if isinstance(outcome, str) else str(outcome)
        if outcome_str != "promoted":
            return False

        # Extract behavioral coordinates from evidence
        evidence = record.proposal.evidence
        task_type = evidence.get("task_type")
        complexity_raw = evidence.get("complexity")

        # FM-P4-22/DR-14: Reject invalid coordinates — NO fallback to defaults.
        # Silent fallback masks bugs in the proposal pipeline. If coordinates
        # are missing or invalid, the proposer must fix the evidence dict.
        if task_type is None:
            logger.warning(
                f"Evolution {record.id} missing 'task_type' in evidence — "
                f"skipping archive update"
            )
            return False
        if task_type not in self._task_types:
            logger.warning(
                f"Evolution {record.id} has unknown task_type '{task_type}' — "
                f"valid types: {self._task_types}. Skipping archive update."
            )
            return False

        # DR-21: Map orchestrator's complexity vocabulary to archive vocabulary.
        # Orchestrator uses: "small", "medium", "large"
        # Archive uses: "simple", "moderate", "complex", "extreme"
        # This mapping bridges the vocabulary gap between subsystems.
        _complexity_map: dict[str, str] = {
            "small": "simple",
            "medium": "moderate",
            "large": "complex",
            # Direct archive vocabulary also accepted (identity mapping)
            "simple": "simple",
            "moderate": "moderate",
            "complex": "complex",
            "extreme": "extreme",
        }
        if complexity_raw is None:
            logger.warning(
                f"Evolution {record.id} missing 'complexity' in evidence — "
                f"skipping archive update"
            )
            return False
        complexity = _complexity_map.get(str(complexity_raw))
        if complexity is None:
            logger.warning(
                f"Evolution {record.id} has unmappable complexity "
                f"'{complexity_raw}' — valid values: "
                f"{list(_complexity_map.keys())}. Skipping archive update."
            )
            return False

        # Get evaluation score as performance.
        # PROMOTED records must have an evaluation — fail-loud if missing.
        if record.evaluation is None:
            raise ValueError(
                f"PROMOTED record {record.id} has no evaluation. "
                f"This indicates a bug in the evolution pipeline."
            )
        performance = record.evaluation.overall_score

        # Find or create cell
        cell = self._find_cell(task_type, complexity)
        now = datetime.now(timezone.utc)

        if cell is None:
            # New cell — novelty bonus applies
            effective_performance = performance + self._novelty_bonus
            new_cell = ArchiveCell(
                task_type=task_type,
                complexity=complexity,
                best_config=self._extract_config(record),
                performance=effective_performance,
                task_count=1,
                last_updated=now,
                evolution_id=record.id,
            )
            self._state.cells.append(new_cell)
            self._state.total_evaluations += 1
            self._state.total_replacements += 1
            self._save_state()
            logger.info(
                f"New archive cell ({task_type}, {complexity}) "
                f"with performance {effective_performance:.2f} (novelty bonus applied)"
            )
            return True

        # Existing cell — replace only if better
        self._state.total_evaluations += 1
        cell.task_count += 1

        if performance > cell.performance:
            old_perf = cell.performance
            cell.best_config = self._extract_config(record)
            cell.performance = performance
            cell.last_updated = now
            cell.evolution_id = record.id
            self._state.total_replacements += 1
            self._save_state()
            logger.info(
                f"Archive cell ({task_type}, {complexity}) updated: "
                f"{old_perf:.2f} → {performance:.2f}"
            )
            return True

        self._save_state()
        logger.info(
            f"Archive cell ({task_type}, {complexity}) not updated: "
            f"new {performance:.2f} <= existing {cell.performance:.2f}"
        )
        return False

    def get_best_config(
        self, task_type: str, complexity: str
    ) -> dict[str, str] | None:
        """Get the best configuration for a behavioral cell.

        Returns None if the cell doesn't exist or has insufficient tasks.
        """
        cell = self._find_cell(task_type, complexity)
        if cell is None:
            return None
        if cell.task_count < self._min_tasks:
            return None
        return cell.best_config

    def get_all_cells(self) -> list[ArchiveCell]:
        """Return all archive cells."""
        return list(self._state.cells)

    def get_coverage(self) -> float:
        """Return the fraction of cells that are occupied.

        Total possible cells = len(task_types) * len(complexities).
        """
        total_possible = len(self._task_types) * len(self._complexities)
        if total_possible == 0:
            return 0.0
        occupied = len(self._state.cells)
        return occupied / total_possible

    def get_stats(self) -> dict:
        """Return archive statistics."""
        return {
            "total_cells": len(self._state.cells),
            "total_possible": len(self._task_types) * len(self._complexities),
            "coverage": self.get_coverage(),
            "total_evaluations": self._state.total_evaluations,
            "total_replacements": self._state.total_replacements,
        }

    # ── Private helpers ──

    def _find_cell(
        self, task_type: str, complexity: str
    ) -> ArchiveCell | None:
        """Find a cell by its behavioral coordinates."""
        for cell in self._state.cells:
            if cell.task_type == task_type and cell.complexity == complexity:
                return cell
        return None

    def _extract_config(self, record: EvolutionRecord) -> dict[str, str]:
        """Extract configuration dict from an evolution record."""
        return {
            "component": record.proposal.component,
            "diff_summary": record.proposal.diff[:200],
            "rationale": record.proposal.rationale,
            "evolution_id": record.id,
        }

    def _load_state(self) -> MAPElitesState:
        """Load archive state from disk. Create empty if missing."""
        try:
            return self.yaml_store.read(self._archive_path, MAPElitesState)
        except FileNotFoundError:
            logger.info("No archive found — creating empty MAP-Elites state")
            return MAPElitesState()

    def _save_state(self) -> None:
        """Persist archive state to disk."""
        self.yaml_store.write(self._archive_path, self._state)
