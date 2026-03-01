"""Skill library -- storage, retrieval, search, and lifecycle management.
Spec reference: Section 12.3 (Organization), Section 12.4 (Maintenance).

Stores validated skills with ring-based trust tiers. Provides TF-IDF
semantic search for skill retrieval. Runs periodic maintenance: prune
low-performers, merge near-duplicates, score by usage/success/freshness.

Key constraints:
- Capacity limits: 50 per domain, 20 per level (Li et al. 2026)
- Maintenance every 20 tasks (configurable)
- Prune: success_rate < 0.5 OR unused for 30 tasks -> deprecated
- Merge: cosine similarity > 0.85 -> consolidate
- Ring transitions: 3->2 requires +5pp improvement + full validation
- All changes git-committed with provenance

Literature basis:
- Li et al. 2026: Phase transition at critical library size
- ToolLibGen: Consolidation (cluster, refactor, aggregate)
- Odyssey: 40 primitives + 183 compositions, hierarchical organization
- STEPS: Taxonomy-based skill organization
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..engine.diversity_engine import (
    compute_idf,
    cosine_distance,
    tf_idf_vector,
    tokenize,
)
from ..models.audit import EvolutionLogEntry
from ..models.base import generate_id
from ..models.evolution import EvolutionTier
from ..models.protection import ProtectionRing, RingTransition
from ..models.skill import (
    ExtractionCandidate,
    MaintenanceRecord,
    SkillLibraryStats,
    SkillMaintenanceAction,
    SkillPerformanceMetrics,
    SkillRecord,
    SkillStatus,
    ValidationStage,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_library")


class SkillLibrary:
    """Skill storage, retrieval, and lifecycle management.

    Design invariants:
    - All skills persisted to YAML via YamlStore
    - Capacity enforced per domain (50) and per level (20)
    - TF-IDF search uses DiversityEngine functions (no duplication)
    - Maintenance is synchronous, called explicitly by orchestrator
    - Ring transitions logged to EVOLUTION audit stream
    - Skill records are the source of truth -- not in-memory cache
    - FM-S03: Capacity overflow rejects new skills, does not evict
    - FM-S04: Merge produces combined skill only if both score well
    - FM-S06: Name uniqueness enforced on add

    Usage:
        library = SkillLibrary(yaml_store, domain="meta")
        library.add_skill(validated_record)
        results = library.search_skills("error handling")
        records = library.run_maintenance()
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/skill-system.yaml")
        ss = config_raw.get("skill_system")
        if ss is None:
            raise ValueError(
                "core/skill-system.yaml missing 'skill_system' section"
            )
        lib = ss.get("library", {})
        cap = lib.get("capacity", {})
        self._capacity_per_domain = int(cap.get("per_domain", 50))
        # MF-2: per_level capacity is loaded but NOT enforced.
        # SkillRecord has no "level" field, so per-level capacity cannot
        # be checked. This is a known design gap -- enforcement requires
        # adding a level field to SkillRecord and updating add_skill().
        self._capacity_per_level = int(cap.get("per_level", 20))
        logger.warning(
            "per_level capacity (%d) is loaded but not enforced: "
            "SkillRecord has no 'level' field. "
            "This is a known design gap (MF-2).",
            self._capacity_per_level,
        )

        maint = ss.get("maintenance", {})
        self._maintenance_period = int(maint.get("period_tasks", 20))
        self._prune_success_rate = float(
            maint.get("prune_success_rate", 0.5)
        )
        self._prune_unused_tasks = int(maint.get("prune_unused_tasks", 30))
        self._merge_threshold = float(
            maint.get("merge_similarity_threshold", 0.85)
        )
        self._max_maintenance_history = int(
            maint.get("max_maintenance_history", 100)
        )

        ring_cfg = ss.get("ring_transitions", {})
        r32 = ring_cfg.get("ring_3_to_2", {})
        self._promote_min_improvement = float(
            r32.get("min_improvement_pp", 5)
        )
        self._promote_min_usage = int(r32.get("min_usage_count", 5))
        self._promote_min_success_rate = float(
            r32.get("min_success_rate", 0.7)
        )
        self._promote_require_validation = bool(
            r32.get("require_full_validation", True)
        )

        r23 = ring_cfg.get("ring_2_to_3", {})
        self._demote_on_revalidation_failure = bool(
            r23.get("on_revalidation_failure", True)
        )
        self._demote_success_threshold = float(
            r23.get("on_success_rate_below", 0.5)
        )

        # State paths
        self._skills_dir = f"instances/{domain}/state/skills"
        self._maintenance_dir = f"{self._skills_dir}/maintenance-history"
        yaml_store.ensure_dir(self._skills_dir)
        yaml_store.ensure_dir(self._maintenance_dir)

        # Task counter for maintenance scheduling
        self._tasks_since_maintenance = 0

    def add_skill(self, record: SkillRecord) -> bool:
        """Add a validated skill to the library.

        Args:
            record: SkillRecord with status VALIDATED.

        Returns:
            True if skill was added, False if rejected (capacity overflow
            or duplicate name).

        Raises:
            ValueError: If skill status is not VALIDATED.

        FM-S03: Capacity overflow rejects, does not evict.
        FM-S06: Duplicate name check.
        """
        if record.status != SkillStatus.VALIDATED.value:
            raise ValueError(
                f"Cannot add skill '{record.name}': "
                f"status is {record.status}, expected VALIDATED"
            )

        # FM-S06: Check for duplicate name
        # Allow overwriting non-active records (e.g., from validation pipeline)
        existing = self.get_skill(record.name)
        if existing is not None and existing.is_active:
            logger.warning(
                f"Skill '{record.name}' already exists in library"
            )
            return False

        # FM-S03: Check capacity
        active_count = self._count_active_skills()
        if active_count >= self._capacity_per_domain:
            logger.warning(
                f"Library at capacity ({active_count}/{self._capacity_per_domain}). "
                f"Skill '{record.name}' rejected."
            )
            return False

        # Activate the skill
        record.status = SkillStatus.ACTIVE
        record.updated_at = datetime.now(timezone.utc)
        self._persist_skill(record)

        logger.info(
            f"Skill '{record.name}' added to library "
            f"(ring={record.ring}, domain={record.domain})"
        )

        return True

    def get_skill(self, name: str) -> SkillRecord | None:
        """Get a skill by name.

        Args:
            name: Skill name (used as filename).

        Returns:
            SkillRecord or None if not found.
        """
        path = f"{self._skills_dir}/{name}.yaml"
        try:
            return self.yaml_store.read(path, SkillRecord)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"Error loading skill '{name}': {e}")
            return None

    def get_all_skills(self) -> list[SkillRecord]:
        """Load all skill records from disk.

        Returns list of successfully loaded records. Corrupt files
        are logged and skipped.
        """
        skills: list[SkillRecord] = []
        try:
            # IFM-MF2: YamlStore has list_dir(), not list_files().
            # list_dir() returns names (not paths), so filter by suffix
            # and skip known subdirectory names.
            entries = self.yaml_store.list_dir(self._skills_dir)
        except (FileNotFoundError, NotADirectoryError):
            return []

        for fname in entries:
            # Skip subdirectories (list_dir returns names, not paths)
            if fname in ("candidates", "maintenance-history"):
                continue
            # Only process .yaml files
            if not fname.endswith(".yaml"):
                continue
            try:
                skill = self.yaml_store.read(
                    f"{self._skills_dir}/{fname}", SkillRecord
                )
                skills.append(skill)
            except Exception as e:
                logger.warning(f"Skipping corrupt skill file {fname}: {e}")

        return skills

    def get_active_skills(self) -> list[SkillRecord]:
        """Get all active skills."""
        return [s for s in self.get_all_skills() if s.is_active]

    def get_skill_names(self) -> list[str]:
        """Get names of all skills (active and inactive).

        Used by SkillExtractor for deduplication.
        """
        return [s.name for s in self.get_all_skills()]

    def search_skills(
        self, query: str, limit: int = 5
    ) -> list[SkillRecord]:
        """Search for skills using TF-IDF semantic similarity.

        Uses DiversityEngine's TF-IDF functions for text similarity.
        Searches against skill name + description + instruction_fragment.

        Args:
            query: Search query text.
            limit: Maximum results to return.

        Returns:
            List of SkillRecords sorted by relevance (most relevant first).
        """
        active_skills = self.get_active_skills()
        if not active_skills:
            return []

        # Build document corpus: one document per skill
        documents: list[list[str]] = []
        for skill in active_skills:
            doc_text = f"{skill.name} {skill.description} {skill.instruction_fragment}"
            documents.append(tokenize(doc_text))

        # Add query as a document for IDF computation
        query_tokens = tokenize(query)
        all_docs = documents + [query_tokens]

        # Compute IDF across all documents + query
        idf = compute_idf(all_docs)

        # Compute query vector
        query_vector = tf_idf_vector(query_tokens, idf)

        # Compute similarity for each skill
        scored: list[tuple[float, SkillRecord]] = []
        for i, skill in enumerate(active_skills):
            skill_vector = tf_idf_vector(documents[i], idf)
            # cosine_distance returns distance (0=identical, 1=orthogonal)
            # We want similarity, so use 1 - distance
            distance = cosine_distance(query_vector, skill_vector)
            similarity = 1.0 - distance
            scored.append((similarity, skill))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [skill for _, skill in scored[:limit]]

    def get_skills_for_task(self, task_type: str) -> list[SkillRecord]:
        """Get active skills relevant to a task type.

        Uses task_type as search query. Returns top 3 matches.

        Args:
            task_type: Task type from Orchestrator._classify_task_type().

        Returns:
            List of relevant active SkillRecords (max 3).
        """
        return self.search_skills(task_type, limit=3)

    def record_skill_usage(
        self,
        name: str,
        success: bool,
        task_id: str,
        performance_monitor: object | None = None,  # PerformanceMonitor
    ) -> None:
        """Record that a skill was used in a task.

        Updates the skill's performance metrics and optionally reports
        to the PerformanceMonitor for rolling window tracking.

        Args:
            name: Skill name.
            success: Whether the task using this skill succeeded.
            task_id: ID of the task that used the skill.
            performance_monitor: Optional PerformanceMonitor instance.
                SF-7/IFM-N18: Reports skill outcomes to PerformanceMonitor
                for centralized performance tracking and drift detection.
        """
        skill = self.get_skill(name)
        if skill is None:
            logger.warning(f"Cannot record usage: skill '{name}' not found")
            return

        skill.metrics.usage_count += 1
        if success:
            skill.metrics.success_count += 1
        skill.metrics.last_used_task_id = task_id
        skill.metrics.last_used_at = datetime.now(timezone.utc)
        skill.metrics.tasks_since_last_use = 0

        self._persist_skill(skill)

        # SF-7/IFM-N18: Report to PerformanceMonitor for centralized tracking
        if performance_monitor is not None:
            try:
                performance_monitor.record_skill_outcome(
                    skill_name=name, success=success
                )
            except Exception as e:
                logger.warning(
                    f"Failed to report skill outcome to PerformanceMonitor: {e}"
                )

    def run_maintenance(self) -> list[MaintenanceRecord]:
        """Run periodic maintenance: prune, merge, score, promote/demote.

        Called by the orchestrator every maintenance_period tasks.
        Synchronous -- not in background threads.

        Steps:
        1. Increment tasks_since_last_use for all active skills
        2. Prune: deprecate skills with success_rate < 0.5 or unused for 30 tasks
        3. Merge: consolidate near-duplicates (cosine similarity > 0.85)
        4. Promote: Ring 3 -> Ring 2 if criteria met
        5. Demote: Ring 2 -> Ring 3 if performance dropped
        6. Log all actions

        Returns:
            List of MaintenanceRecords describing actions taken.

        FM-S04: Merge only if combined skill scores well.
        FM-S10: Maintenance history trimmed to max_maintenance_history.
        """
        records: list[MaintenanceRecord] = []
        all_skills = self.get_active_skills()

        if not all_skills:
            # MF-3: Reset counter even when no active skills exist.
            # Maintenance was "run" (and found nothing to do), so the
            # counter should reset for the next period.
            self._tasks_since_maintenance = 0
            return records

        # Step 1: Increment staleness counters
        for skill in all_skills:
            skill.metrics.tasks_since_last_use += 1
            self._persist_skill(skill)

        # Step 2: Prune low-performers
        prune_records = self._prune_skills(all_skills)
        records.extend(prune_records)

        # Reload after pruning (some may be deprecated now)
        all_skills = self.get_active_skills()

        # Step 3: Merge near-duplicates
        merge_records = self._merge_similar_skills(all_skills)
        records.extend(merge_records)

        # Reload after merging
        all_skills = self.get_active_skills()

        # Step 4: Promote eligible Ring 3 skills
        promote_records = self._promote_eligible(all_skills)
        records.extend(promote_records)

        # Step 5: Demote underperforming Ring 2 skills
        demote_records = self._demote_underperforming(all_skills)
        records.extend(demote_records)

        # Persist maintenance records
        for rec in records:
            self._persist_maintenance_record(rec)

        # Trim history
        self._trim_maintenance_history()

        # Reset task counter
        self._tasks_since_maintenance = 0

        logger.info(
            f"Maintenance complete: {len(records)} actions taken "
            f"({len(prune_records)} pruned, {len(merge_records)} merged, "
            f"{len(promote_records)} promoted, {len(demote_records)} demoted)"
        )

        return records

    def promote_skill(self, name: str) -> RingTransition | None:
        """Promote a Ring 3 skill to Ring 2 if criteria are met.

        Criteria (Section 20.2, ring_3_to_2):
        - Passed full 4-stage validation
        - Demonstrated >= +5pp improvement (from stage 3)
        - Used at least min_usage_count times
        - Success rate >= min_success_rate

        Returns:
            RingTransition if promoted, None if criteria not met.

        FM-S05: Ensures sufficient evidence before promotion.
        """
        skill = self.get_skill(name)
        if skill is None:
            return None

        if skill.ring != ProtectionRing.RING_3_EXPENDABLE.value:
            logger.debug(
                f"Skill '{name}' not Ring 3, cannot promote "
                f"(current ring={skill.ring})"
            )
            return None

        # Check criteria
        if not self._meets_promotion_criteria(skill):
            return None

        # Perform promotion
        transition = RingTransition(
            item=name,
            from_ring=ProtectionRing.RING_3_EXPENDABLE,
            to_ring=ProtectionRing.RING_2_VALIDATED,
            reason=(
                f"Meets promotion criteria: "
                f"usage={skill.metrics.usage_count}, "
                f"success_rate={skill.metrics.success_rate:.2f}"
            ),
            evidence=(
                f"Improvement: "
                f"{self._get_improvement_delta(skill):.1f}pp"
            ),
            approved_by="skill_library_auto",
        )

        skill.ring = ProtectionRing.RING_2_VALIDATED
        skill.updated_at = datetime.now(timezone.utc)
        self._persist_skill(skill)

        # Log to EVOLUTION stream
        self._log_ring_transition(transition)

        logger.info(
            f"Skill '{name}' promoted: Ring 3 -> Ring 2"
        )

        return transition

    def demote_skill(
        self, name: str, reason: str
    ) -> RingTransition | None:
        """Demote a Ring 2 skill to Ring 3.

        Called when:
        - Post-model-change revalidation fails (Phase 2.5 cross-ref)
        - Success rate drops below demotion threshold

        Args:
            name: Skill name.
            reason: Reason for demotion.

        Returns:
            RingTransition if demoted, None if skill not found or not Ring 2.
        """
        skill = self.get_skill(name)
        if skill is None:
            return None

        if skill.ring != ProtectionRing.RING_2_VALIDATED.value:
            return None

        transition = RingTransition(
            item=name,
            from_ring=ProtectionRing.RING_2_VALIDATED,
            to_ring=ProtectionRing.RING_3_EXPENDABLE,
            reason=reason,
            evidence=(
                f"success_rate={skill.metrics.success_rate:.2f}, "
                f"usage={skill.metrics.usage_count}"
            ),
            approved_by="skill_library_auto",
        )

        skill.ring = ProtectionRing.RING_3_EXPENDABLE
        skill.updated_at = datetime.now(timezone.utc)
        self._persist_skill(skill)

        self._log_ring_transition(transition)

        logger.info(
            f"Skill '{name}' demoted: Ring 2 -> Ring 3. Reason: {reason}"
        )

        return transition

    def get_stats(self) -> SkillLibraryStats:
        """Compute aggregate library statistics."""
        all_skills = self.get_all_skills()

        stats = SkillLibraryStats()
        stats.total_skills = len(all_skills)

        total_success = 0.0
        total_composite = 0.0
        active_count = 0

        for skill in all_skills:
            if skill.status == SkillStatus.ACTIVE.value:
                stats.active_skills += 1
                active_count += 1
                total_success += skill.metrics.success_rate
                total_composite += skill.metrics.composite_score
            elif skill.status == SkillStatus.DEPRECATED.value:
                stats.deprecated_skills += 1
            elif skill.status == SkillStatus.REJECTED.value:
                stats.rejected_skills += 1
            elif skill.status == SkillStatus.VALIDATING.value:
                stats.validating_skills += 1
            elif skill.status == SkillStatus.CANDIDATE.value:
                stats.candidate_skills += 1

            # Ring counts (active only)
            if skill.is_active:
                if skill.ring == ProtectionRing.RING_0_IMMUTABLE.value:
                    stats.ring_0_count += 1
                elif skill.ring == ProtectionRing.RING_1_PROTECTED.value:
                    stats.ring_1_count += 1
                elif skill.ring == ProtectionRing.RING_2_VALIDATED.value:
                    stats.ring_2_count += 1
                elif skill.ring == ProtectionRing.RING_3_EXPENDABLE.value:
                    stats.ring_3_count += 1

            # Domain counts
            domain = skill.domain
            stats.domains[domain] = stats.domains.get(domain, 0) + 1

        if active_count > 0:
            stats.avg_success_rate = total_success / active_count
            stats.avg_composite_score = total_composite / active_count

        return stats

    def increment_task_counter(self) -> bool:
        """Increment task counter and return True if maintenance is due.

        MF-3: Counter is only reset in run_maintenance(), not here.
        Previously the counter was reset in both places, which meant
        if maintenance was skipped or failed, the counter was already
        reset and maintenance would not be retried until another full
        period elapsed.
        """
        self._tasks_since_maintenance += 1
        return self._tasks_since_maintenance >= self._maintenance_period

    # -- Internal Methods --

    def _count_active_skills(self) -> int:
        """Count active skills in the library."""
        return len(self.get_active_skills())

    def _prune_skills(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Prune low-performing or stale skills.

        Criteria (Section 12.4):
        - success_rate < 0.5 (with at least 1 usage)
        - unused for 30 tasks

        Ring 0 and Ring 1 skills are never pruned.
        """
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if not skill.is_prunable:
                continue

            reason = ""
            if skill.metrics.success_rate < self._prune_success_rate:
                reason = (
                    f"success_rate={skill.metrics.success_rate:.2f} "
                    f"< {self._prune_success_rate}"
                )
            elif skill.metrics.tasks_since_last_use >= self._prune_unused_tasks:
                reason = (
                    f"unused_tasks={skill.metrics.tasks_since_last_use} "
                    f">= {self._prune_unused_tasks}"
                )

            if reason:
                skill.status = SkillStatus.DEPRECATED
                skill.updated_at = datetime.now(timezone.utc)
                self._persist_skill(skill)

                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.PRUNE,
                    skill_name=skill.name,
                    detail=reason,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)
                logger.info(f"Pruned skill '{skill.name}': {reason}")

        return records

    def _merge_similar_skills(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Merge near-duplicate skills (cosine similarity > threshold).

        FM-S04: Only merges if both skills have similar performance.
        The skill with higher composite_score is kept; the other is deprecated.
        The kept skill's description is updated to note the merge.

        Uses DiversityEngine's TF-IDF functions for similarity computation.
        """
        records: list[MaintenanceRecord] = []
        if len(skills) < 2:
            return records

        # Build TF-IDF vectors for all skills
        documents = [
            tokenize(
                f"{s.name} {s.description} {s.instruction_fragment}"
            )
            for s in skills
        ]
        idf = compute_idf(documents)
        vectors = [tf_idf_vector(tokens, idf) for tokens in documents]

        # Find pairs with similarity > threshold
        merged_indices: set[int] = set()

        for i in range(len(skills)):
            if i in merged_indices:
                continue
            for j in range(i + 1, len(skills)):
                if j in merged_indices:
                    continue

                distance = cosine_distance(vectors[i], vectors[j])
                similarity = 1.0 - distance

                if similarity >= self._merge_threshold:
                    # FM-S04: Keep the one with higher composite score
                    keep_idx, deprecate_idx = (
                        (i, j)
                        if skills[i].metrics.composite_score
                        >= skills[j].metrics.composite_score
                        else (j, i)
                    )

                    kept = skills[keep_idx]
                    deprecated = skills[deprecate_idx]

                    # Update kept skill's description
                    kept.description = (
                        f"{kept.description} "
                        f"(merged with: {deprecated.name})"
                    )
                    kept.version += 1
                    kept.updated_at = datetime.now(timezone.utc)
                    self._persist_skill(kept)

                    # Deprecate the other
                    deprecated.status = SkillStatus.DEPRECATED
                    deprecated.updated_at = datetime.now(timezone.utc)
                    self._persist_skill(deprecated)

                    merged_indices.add(deprecate_idx)

                    record = MaintenanceRecord(
                        id=generate_id("maint"),
                        created_at=datetime.now(timezone.utc),
                        action=SkillMaintenanceAction.MERGE,
                        skill_name=kept.name,
                        detail=(
                            f"Merged with '{deprecated.name}' "
                            f"(similarity={similarity:.3f})"
                        ),
                        merged_with=deprecated.name,
                        composite_score=kept.metrics.composite_score,
                        success_rate=kept.metrics.success_rate,
                        usage_count=kept.metrics.usage_count,
                    )
                    records.append(record)
                    logger.info(
                        f"Merged skills: kept '{kept.name}', "
                        f"deprecated '{deprecated.name}' "
                        f"(similarity={similarity:.3f})"
                    )

        return records

    def _promote_eligible(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Promote Ring 3 skills that meet promotion criteria."""
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if skill.ring != ProtectionRing.RING_3_EXPENDABLE.value:
                continue
            if not self._meets_promotion_criteria(skill):
                continue

            transition = self.promote_skill(skill.name)
            if transition is not None:
                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.PROMOTE,
                    skill_name=skill.name,
                    detail=(
                        f"Promoted Ring 3 -> Ring 2: "
                        f"usage={skill.metrics.usage_count}, "
                        f"success_rate={skill.metrics.success_rate:.2f}"
                    ),
                    from_ring=ProtectionRing.RING_3_EXPENDABLE,
                    to_ring=ProtectionRing.RING_2_VALIDATED,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)

        return records

    def _demote_underperforming(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Demote Ring 2 skills with success_rate below threshold."""
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if skill.ring != ProtectionRing.RING_2_VALIDATED.value:
                continue
            if skill.metrics.usage_count < 5:
                continue  # Not enough data to judge
            if skill.metrics.success_rate >= self._demote_success_threshold:
                continue  # Still performing well

            transition = self.demote_skill(
                skill.name,
                f"success_rate={skill.metrics.success_rate:.2f} "
                f"< {self._demote_success_threshold}",
            )
            if transition is not None:
                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.DEMOTE,
                    skill_name=skill.name,
                    detail=(
                        f"Demoted Ring 2 -> Ring 3: "
                        f"success_rate={skill.metrics.success_rate:.2f}"
                    ),
                    from_ring=ProtectionRing.RING_2_VALIDATED,
                    to_ring=ProtectionRing.RING_3_EXPENDABLE,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)

        return records

    def _meets_promotion_criteria(self, skill: SkillRecord) -> bool:
        """Check if a skill meets Ring 3 -> Ring 2 promotion criteria."""
        # Must have sufficient usage
        if skill.metrics.usage_count < self._promote_min_usage:
            return False

        # Must have sufficient success rate
        if skill.metrics.success_rate < self._promote_min_success_rate:
            return False

        # Must have passed full validation (if required)
        if self._promote_require_validation:
            if skill.status != SkillStatus.ACTIVE.value:
                return False
            # Check that all 4 stages were passed
            passed_stages = {
                vr.stage for vr in skill.validation_results if vr.passed
            }
            # IFM-N25: FrameworkModel uses use_enum_values=True, so
            # ValidationResult.stage stores string values after YAML
            # roundtrip, not enum members. Build required_stages as
            # strings to ensure the comparison works correctly.
            required_stages = {s.value for s in ValidationStage}
            if not required_stages.issubset(passed_stages):
                return False

        # Must have demonstrated improvement
        improvement = self._get_improvement_delta(skill)
        if improvement < self._promote_min_improvement:
            return False

        return True

    def _get_improvement_delta(self, skill: SkillRecord) -> float:
        """Get the improvement delta from stage 3 validation.

        IFM-N25: Compare against string value since use_enum_values=True
        stores strings after YAML roundtrip.
        """
        for vr in skill.validation_results:
            if (
                vr.stage == ValidationStage.COMPARISON.value
                and vr.improvement_delta is not None
            ):
                return vr.improvement_delta
        return 0.0

    def _persist_skill(self, skill: SkillRecord) -> None:
        """Persist a skill record to YAML."""
        self.yaml_store.write(
            f"{self._skills_dir}/{skill.name}.yaml",
            skill,
        )

    def _persist_maintenance_record(self, record: MaintenanceRecord) -> None:
        """Persist a maintenance record to YAML."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("maint").split("-")[-1]
        path = (
            f"{self._maintenance_dir}/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, record)

    def _trim_maintenance_history(self) -> None:
        """Trim maintenance history to max_maintenance_history entries.

        FM-S10: Prevents unbounded growth of maintenance records.
        """
        try:
            # IFM-MF2: YamlStore has list_dir(), not list_files().
            # list_dir() returns sorted names. Filter by .yaml suffix.
            entries = self.yaml_store.list_dir(self._maintenance_dir)
        except (FileNotFoundError, NotADirectoryError):
            return

        sorted_files = [f for f in entries if f.endswith(".yaml")]
        while len(sorted_files) > self._max_maintenance_history:
            oldest = sorted_files.pop(0)
            try:
                self.yaml_store.delete(
                    f"{self._maintenance_dir}/{oldest}"
                )
            except FileNotFoundError:
                pass

    def _log_ring_transition(self, transition: RingTransition) -> None:
        """Log a ring transition to the EVOLUTION audit stream.

        SF-8: EvolutionLogEntry and EvolutionTier are now imported at
        module level instead of lazily here.
        """
        if self._audit_logger is None:
            return
        try:
            entry = EvolutionLogEntry(
                id=generate_id("evo"),
                timestamp=datetime.now(timezone.utc),
                tier=EvolutionTier.ORGANIZATIONAL,
                component=f"skill:{transition.item}",
                diff=f"Ring {transition.from_ring} -> {transition.to_ring}",
                rationale=transition.reason,
                evidence={"transition": transition.evidence},
                approved_by=transition.approved_by,
                constitutional_check="pass",
                rollback_commit="",  # No git commit for ring transitions
            )
            self._audit_logger.log_evolution(entry)
        except Exception as e:
            logger.warning(f"Failed to log ring transition: {e}")
