"""Skill extraction from successful task trajectories.
Spec reference: Section 12.1 (Skill Extraction).

Identifies completed tasks with high review scores and extracts the
reasoning pattern into a transferable capability atom. Uses ModelExecuteFn
for LLM-assisted abstraction from real trajectories.

Key constraints:
- Extract from REAL trajectories only -- never generate from scratch
- Minimum review confidence threshold (configurable, default 0.7)
- Minimum trajectory length (configurable, default 200 chars)
- Token budget for extraction call (configurable, default 3000)
- Deduplication against existing library skills
- Cooldown between extractions of same task_type

Literature basis:
- SkillsBench (arXiv:2602.12670): "NEVER generate skills from scratch"
- EvolveR: Offline distillation from trajectories works
- AutoRefine: Dual-form extraction (procedural + declarative) works
- CASCADE (arXiv:2512.23880): Experience-grounded extraction
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.audit import DecisionLogEntry, LogStream
from ..models.base import generate_id
from ..models.environment import ModelExecuteFn
from ..models.skill import (
    ExtractionCandidate,
    SkillSource,
)
from ..models.task import Task, TaskReview
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_extractor")

# Extraction prompt template.
# This prompt asks the LLM to abstract a reasoning pattern from a concrete
# task trajectory. It does NOT ask the LLM to generate a skill from scratch.
# FM-S01: The trajectory is included verbatim to ground the extraction.
EXTRACTION_PROMPT = """You are extracting a reusable reasoning pattern from a successful task execution.

## Task that was completed successfully
Title: {task_title}
Type: {task_type}
Description: {task_description}

## Key reasoning steps from the execution trajectory
{trajectory_snippet}

## Your job
Abstract the reasoning pattern used in this task into a REUSABLE capability instruction.

Rules:
1. Focus on the TRANSFERABLE pattern, not task-specific details
2. The instruction should be 2-5 sentences, focused and actionable
3. It should help an agent perform similar tasks better
4. Do NOT include task-specific names, IDs, or data
5. Do NOT generate generic advice -- extract the SPECIFIC pattern that made this task succeed

## Output format (respond with EXACTLY this structure, no other text)
NAME: <short_snake_case_name>
DESCRIPTION: <one sentence describing what this skill does>
INSTRUCTION: <2-5 sentence instruction fragment that can be injected into an agent prompt>
"""


class SkillExtractor:
    """Extracts reusable skills from successful task trajectories.

    Design invariants:
    - Only extracts from tasks with review verdict "pass" or "pass_with_notes"
    - Only extracts when reviewer_confidence >= threshold (default 0.7)
    - Uses real trajectory data -- never generates from scratch (SkillsBench)
    - Deduplicates against existing skills in the library
    - Respects extraction cooldown per task_type
    - Budget-capped LLM call for abstraction
    - Candidates stored temporarily for validation pipeline

    Usage:
        extractor = SkillExtractor(yaml_store, domain="meta")
        candidate = extractor.extract_from_task(task, execute_fn)
        if candidate is not None:
            # Send to SkillValidator
            validator.validate(candidate)

    FM-S01: Guards against low-quality trajectory extraction.
    FM-S06: Checks for duplicate skill names before extraction.
    FM-S07: Budget enforcement via token cap.
    FM-S08: Rejects instructions with forbidden patterns.
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,  # AuditLogger, optional
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
        ext = ss.get("extraction", {})
        self._min_review_confidence = float(
            ext.get("min_review_confidence", 0.7)
        )
        self._min_trajectory_length = int(
            ext.get("min_trajectory_length", 200)
        )
        self._max_trajectory_snippet = int(
            ext.get("max_trajectory_snippet", 2000)
        )
        self._extraction_token_budget = int(
            ext.get("extraction_token_budget", 3000)
        )
        self._qualifying_verdicts: list[str] = ext.get(
            "qualifying_verdicts", ["pass", "pass_with_notes"]
        )
        self._extraction_cooldown = int(
            ext.get("extraction_cooldown_tasks", 5)
        )

        # Security: forbidden patterns (FM-S08)
        sec = ss.get("security", {})
        self._max_instruction_length = int(
            sec.get("max_instruction_length", 1500)
        )
        self._forbidden_patterns: list[str] = sec.get(
            "forbidden_patterns", []
        )

        # State paths
        self._skills_base = f"instances/{domain}/state/skills"
        self._candidates_dir = f"{self._skills_base}/candidates"
        yaml_store.ensure_dir(self._skills_base)
        yaml_store.ensure_dir(self._candidates_dir)

        # Track recent extractions per task_type for cooldown
        # In-memory only -- rebuilt from disk is unnecessary (cooldown is short)
        self._recent_extractions: dict[str, int] = {}  # task_type -> tasks_ago

    def extract_from_task(
        self,
        task: Task,
        execute_fn: ModelExecuteFn,
        task_type: str,
        existing_skill_names: list[str] | None = None,
    ) -> ExtractionCandidate | None:
        """Extract a skill from a completed task trajectory.

        Args:
            task: Completed task with review verdict and trajectory.
            execute_fn: LLM execution function for abstraction.
            task_type: Task type classification from Orchestrator._classify_task_type().
                IFM-MF5: Passed in by the orchestrator to avoid divergent
                classification logic. Previously duplicated here.
            existing_skill_names: Names of skills already in library
                (for deduplication). If None, no dedup check.

        Returns:
            ExtractionCandidate if extraction succeeded, None if:
            - Task does not qualify (wrong verdict, low confidence)
            - Trajectory too short
            - Cooldown not elapsed for this task_type
            - LLM output unparseable
            - Duplicate skill name detected
            - Instruction contains forbidden patterns (FM-S08)

        FM-S01: Only extracts from high-confidence passing tasks.
        FM-S06: Checks for duplicate skill names.
        FM-S07: Respects extraction token budget.
        FM-S08: Rejects instructions with forbidden patterns.
        """
        # Guard: task must have a passing review
        if not self._qualifies_for_extraction(task):
            return None

        # Guard: cooldown check (task_type passed by orchestrator)
        if not self._cooldown_elapsed(task_type):
            logger.debug(
                f"Extraction skipped for task {task.id}: "
                f"cooldown not elapsed for task_type={task_type}"
            )
            return None

        # Build trajectory snippet from task timeline and artifacts
        trajectory = self._build_trajectory_snippet(task)
        if len(trajectory) < self._min_trajectory_length:
            logger.debug(
                f"Extraction skipped for task {task.id}: "
                f"trajectory too short ({len(trajectory)} < "
                f"{self._min_trajectory_length})"
            )
            return None

        # Build extraction prompt
        prompt = EXTRACTION_PROMPT.format(
            task_title=task.title,
            task_type=task_type,
            task_description=task.description[:500],
            trajectory_snippet=trajectory,
        )

        # Call LLM for abstraction (FM-S07: budget-capped)
        try:
            output, tokens_used = execute_fn(
                prompt, self._extraction_token_budget
            )
        except Exception as e:
            # SF-7: Log at ERROR level for unexpected LLM failures.
            # These are not expected conditions -- they indicate real
            # problems (API failures, timeouts, etc.) that need attention.
            logger.error(
                f"Extraction LLM call failed for task {task.id}: {e}"
            )
            return None

        # Parse LLM output
        parsed = self._parse_extraction_output(output)
        if parsed is None:
            logger.warning(
                f"Extraction output unparseable for task {task.id}: "
                f"output={output[:200]}..."
            )
            return None

        name, description, instruction = parsed

        # FM-S08: Check for forbidden patterns in instruction
        for pattern in self._forbidden_patterns:
            if pattern.lower() in instruction.lower():
                logger.warning(
                    f"Extraction rejected for task {task.id}: "
                    f"instruction contains forbidden pattern '{pattern}'"
                )
                self._log_decision(
                    task.id, name, "rejected_forbidden_pattern",
                    f"Instruction contains forbidden pattern: {pattern}"
                )
                return None

        # FM-S08: Enforce max instruction length
        if len(instruction) > self._max_instruction_length:
            logger.warning(
                f"Extraction rejected for task {task.id}: "
                f"instruction too long ({len(instruction)} > "
                f"{self._max_instruction_length})"
            )
            return None

        # FM-S06: Check for duplicate skill names
        if existing_skill_names and name in existing_skill_names:
            logger.info(
                f"Extraction skipped for task {task.id}: "
                f"skill name '{name}' already exists in library"
            )
            return None

        # Build candidate
        review = task.review
        assert review is not None  # Guaranteed by _qualifies_for_extraction

        source = SkillSource(
            task_id=task.id,
            task_title=task.title,
            task_type=task_type,
            review_verdict=review.verdict,
            reviewer_confidence=review.reviewer_confidence,
            trajectory_snippet=trajectory[:self._max_trajectory_snippet],
            extraction_timestamp=datetime.now(timezone.utc),
            extraction_tokens=tokens_used,
        )

        candidate = ExtractionCandidate(
            id=generate_id("cand"),
            created_at=datetime.now(timezone.utc),
            name=name,
            description=description,
            instruction_fragment=instruction,
            source=source,
            domain=self._domain,
        )

        # Persist candidate temporarily
        self.yaml_store.write(
            f"{self._candidates_dir}/{candidate.id}.yaml",
            candidate,
        )

        # Update cooldown tracker
        self._recent_extractions[task_type] = 0

        # Log decision
        self._log_decision(
            task.id, name, "extracted",
            f"Skill extracted from task {task.id} "
            f"(confidence={review.reviewer_confidence:.2f}, "
            f"tokens={tokens_used})"
        )

        logger.info(
            f"Skill extracted: name='{name}' from task {task.id} "
            f"(tokens={tokens_used})"
        )

        return candidate

    def increment_cooldowns(self) -> None:
        """Increment all cooldown counters by 1 task.

        Called by the orchestrator after each task completion.
        """
        for task_type in list(self._recent_extractions.keys()):
            self._recent_extractions[task_type] += 1
            # Clean up entries that have exceeded cooldown
            if self._recent_extractions[task_type] > self._extraction_cooldown:
                del self._recent_extractions[task_type]

    def _qualifies_for_extraction(self, task: Task) -> bool:
        """Check if a task qualifies for skill extraction.

        FM-S01: Strict qualification criteria prevent low-quality extraction.
        """
        # Must have a review
        if task.review is None:
            logger.debug(f"Task {task.id} skipped: no review")
            return False

        # Must have passing verdict
        if task.review.verdict not in self._qualifying_verdicts:
            logger.debug(
                f"Task {task.id} skipped: verdict={task.review.verdict}"
            )
            return False

        # Must have sufficient confidence
        if task.review.reviewer_confidence < self._min_review_confidence:
            logger.debug(
                f"Task {task.id} skipped: confidence="
                f"{task.review.reviewer_confidence:.2f} < "
                f"{self._min_review_confidence}"
            )
            return False

        return True

    def _cooldown_elapsed(self, task_type: str) -> bool:
        """Check if cooldown has elapsed for this task_type."""
        if task_type not in self._recent_extractions:
            return True
        return self._recent_extractions[task_type] >= self._extraction_cooldown

    def _build_trajectory_snippet(self, task: Task) -> str:
        """Build a trajectory snippet from task timeline and artifacts.

        Concatenates timeline entries and artifact summaries into a
        narrative of the task execution. Truncated to max_trajectory_snippet.
        """
        parts: list[str] = []

        # Timeline entries
        for entry in task.timeline:
            parts.append(
                f"[{entry.event}] {entry.actor}: {entry.detail}"
            )

        # Artifact summaries (keys and truncated values)
        for key, value in task.artifacts.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            parts.append(f"[artifact:{key}] {val_str}")

        trajectory = "\n".join(parts)
        return trajectory[:self._max_trajectory_snippet]

    def _parse_extraction_output(
        self, output: str
    ) -> tuple[str, str, str] | None:
        """Parse the LLM extraction output into (name, description, instruction).

        Expected format:
            NAME: <name>
            DESCRIPTION: <description>
            INSTRUCTION: <instruction>

        Returns None if parsing fails.
        """
        lines = output.strip().split("\n")
        name = None
        description = None
        instruction_parts: list[str] = []
        current_field: str | None = None

        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("NAME:"):
                name = stripped[5:].strip()
                current_field = "name"
            elif stripped.upper().startswith("DESCRIPTION:"):
                description = stripped[12:].strip()
                current_field = "description"
            elif stripped.upper().startswith("INSTRUCTION:"):
                instruction_parts.append(stripped[12:].strip())
                current_field = "instruction"
            elif current_field == "instruction" and stripped:
                # Multi-line instruction continuation
                instruction_parts.append(stripped)

        instruction = " ".join(instruction_parts).strip()

        # Validate all fields present and non-empty
        if not name or not description or not instruction:
            return None

        # Normalize name to snake_case
        name = name.lower().replace(" ", "_").replace("-", "_")
        # Remove non-alphanumeric characters (except underscore)
        name = "".join(c for c in name if c.isalnum() or c == "_")

        if not name:
            return None

        return name, description, instruction

    # IFM-MF5: _classify_task_type() REMOVED from SkillExtractor.
    # The orchestrator passes task_type as a parameter to extract_from_task()
    # to avoid maintaining a divergent copy of classification logic.

    def _log_decision(
        self, task_id: str, skill_name: str,
        decision: str, rationale: str
    ) -> None:
        """Log a skill extraction decision to the DECISIONS audit stream."""
        if self._audit_logger is None:
            return
        try:
            entry = DecisionLogEntry(
                id=generate_id("dec"),
                timestamp=datetime.now(timezone.utc),
                decision_type=f"skill_extraction_{decision}",
                actor="skill_extractor",
                options_considered=[
                    {"skill_name": skill_name, "task_id": task_id}
                ],
                selected=decision,
                rationale=rationale,
            )
            self._audit_logger.log_decision(entry)
        except Exception as e:
            logger.warning(f"Failed to log extraction decision: {e}")
