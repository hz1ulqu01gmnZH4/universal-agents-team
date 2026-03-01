"""Dual-copy fork pipeline for evolution evaluation.
Spec reference: Section 8.2 (The Dual-Copy Pattern).

Manages the fork → modify → evaluate → promote/rollback pipeline.
Forks are isolated copies of configuration files stored in
state/evolution/candidates/{evo-id}/. Changes are NEVER applied
in-place until promotion.

Key constraints:
- Fork only Tier 2-3 eligible files (no CONSTITUTION.md, no logs)
- Changes must be expressible as file diffs
- Promotion uses YamlStore atomic writes (tmp + os.replace) — NOT shutil.copy2
- Rollback discards fork and reverts via GitOps
- Fork directory cleaned up after resolution (promote or rollback)
- "old" value verification: diff application checks current values before overwriting

Literature basis:
- Darwin Godel Machine: population of forks evaluated in parallel
- STOP (Microsoft): self-taught optimizer with copy mechanism
- AlphaEvolve: island model with migration between copies
"""
from __future__ import annotations

import fnmatch
import logging
import os
import shutil
from pathlib import Path

import yaml

from ..models.evolution import DualCopyCandidate, EvolutionProposal
from ..models.base import generate_id
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.dual_copy_manager")


class ForkError(RuntimeError):
    """Raised when fork creation or manipulation fails."""


class PromotionError(RuntimeError):
    """Raised when promotion of a fork fails.

    This is a critical error — the active config may be inconsistent.
    GitOps rollback should be triggered immediately.
    """


class DualCopyManager:
    """Manages dual-copy fork pipeline for evolution evaluation.

    Design invariants:
    - Forks are created in candidates_dir/{evo-id}/
    - Source files copied according to fork_includes glob patterns
    - Fork excludes use fnmatch — no substring false positives (FM-P4-31)
    - Promotion uses YamlStore atomic writes — NOT shutil.copy2 (FM-P4-18)
    - Diff application verifies "old" values before overwriting (FM-P4-38)
    - Cleanup removes fork directory entirely
    - All operations are logged
    - instance_root derived from yaml_store.base_dir (DR-07)

    Usage:
        mgr = DualCopyManager(yaml_store, domain)
        candidate = mgr.create_fork(proposal)
        mgr.apply_diff(candidate, proposal)
        # ... evaluate candidate ...
        mgr.promote(candidate)  # or mgr.cleanup_fork(candidate)
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        # DR-07: Derive instance_root from yaml_store.base_dir
        self.instance_root = Path(yaml_store.base_dir).resolve()
        self.domain = domain

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        dc = config_raw["evolution"]["dual_copy"]

        # IFM-N53: Direct dict access
        self._fork_includes: list[str] = dc["fork_includes"]
        self._fork_excludes: list[str] = dc["fork_excludes"]
        self._candidates_dir = str(dc["candidates_dir"])

    def create_fork(self, proposal: EvolutionProposal) -> DualCopyCandidate:
        """Create an isolated fork for evaluating a proposal.

        Copies relevant source files into candidates_dir/{evo-id}/.
        Only files matching fork_includes glob patterns are copied.
        Files matching fork_excludes (via fnmatch) are skipped.

        FM-P4-44: Checks available disk space before creating fork.

        Args:
            proposal: The evolution proposal to fork for.

        Returns:
            DualCopyCandidate with fork path and source file list.

        Raises:
            ForkError: If fork directory creation or file copy fails,
                       or if insufficient disk space.
        """
        fork_dir = self.instance_root / self._candidates_dir / proposal.id
        if fork_dir.exists():
            raise ForkError(
                f"Fork directory already exists: {fork_dir}. "
                f"A previous fork for {proposal.id} was not cleaned up."
            )

        # FM-P4-44: Check disk space before fork creation
        disk_usage = shutil.disk_usage(str(self.instance_root))
        min_free_bytes = 50 * 1024 * 1024  # 50 MB
        if disk_usage.free < min_free_bytes:
            raise ForkError(
                f"Insufficient disk space for fork: "
                f"{disk_usage.free / (1024*1024):.1f} MB free, "
                f"minimum {min_free_bytes / (1024*1024):.0f} MB required"
            )

        fork_dir.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created fork directory: {fork_dir}")

        # Copy source files matching includes
        source_files: list[str] = []
        for pattern in self._fork_includes:
            matched = list(self.instance_root.glob(pattern))
            for src_file in matched:
                rel_path = str(src_file.relative_to(self.instance_root))
                # FM-P4-31: Use fnmatch for exclude checking
                if self._is_excluded(rel_path):
                    continue
                dest = fork_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                # FM-P4-24: Write fork files atomically (tmp + rename)
                self._atomic_copy(src_file, dest)
                source_files.append(rel_path)

        # Also copy the target file if not already included
        target_rel = proposal.component
        target_src = self.instance_root / target_rel
        if target_src.exists() and target_rel not in source_files:
            if not self._is_excluded(target_rel):
                dest = fork_dir / target_rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                self._atomic_copy(target_src, dest)
                source_files.append(target_rel)

        candidate = DualCopyCandidate(
            evo_id=proposal.id,
            fork_path=str(fork_dir.relative_to(self.instance_root)),
            source_files=source_files,
        )

        # Persist manifest via YamlStore (atomic write)
        self._persist_manifest(candidate, proposal.id)

        logger.info(
            f"Fork {proposal.id} created with {len(source_files)} source files"
        )
        return candidate

    def apply_diff(
        self, candidate: DualCopyCandidate, proposal: EvolutionProposal
    ) -> None:
        """Apply the proposal's diff to the forked copy.

        FM-P4-38: Each change verifies the "old" value matches the current
        value before overwriting.

        Args:
            candidate: The fork to modify.
            proposal: The proposal containing the diff.

        Raises:
            ForkError: If diff application fails, or old value mismatch detected.
        """
        fork_dir = self.instance_root / candidate.fork_path
        target_file = fork_dir / proposal.component

        if not target_file.exists():
            raise ForkError(
                f"Target file does not exist in fork: {target_file}. "
                f"Ensure the component '{proposal.component}' was included in fork."
            )

        try:
            current_content = yaml.safe_load(
                target_file.read_text(encoding="utf-8")
            )
            if current_content is None:
                raise ForkError(
                    f"Target file {target_file} in fork is empty. "
                    f"Fork copy may be corrupted."
                )

            # Parse diff as YAML change spec
            diff_spec = yaml.safe_load(proposal.diff)
            if diff_spec is None:
                raise ForkError("Diff is empty — nothing to apply")

            if "changes" not in diff_spec:
                raise ForkError(
                    f"Diff spec has no 'changes' key. "
                    f"Keys present: {list(diff_spec.keys())}"
                )
            changes = diff_spec["changes"]
            if not changes:
                raise ForkError("Diff 'changes' list is empty")

            for change in changes:
                key_path = change["key"]
                new_value = change["new"]

                # FM-P4-38: Verify "old" value before overwriting
                if "old" in change:
                    expected_old = change["old"]
                    actual_old = self._get_nested_value(current_content, key_path)
                    if actual_old != expected_old:
                        raise ForkError(
                            f"Old value mismatch at '{key_path}': "
                            f"expected {expected_old!r}, found {actual_old!r}. "
                            f"File may have been modified since proposal creation."
                        )

                self._set_nested_value(current_content, key_path, new_value)

            # Write back atomically (tmp + rename within fork dir)
            tmp_file = target_file.with_suffix(".tmp")
            tmp_file.write_text(
                yaml.dump(
                    current_content,
                    default_flow_style=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            tmp_file.replace(target_file)

            candidate.modified_files.append(proposal.component)
            logger.info(
                f"Applied {len(changes)} changes to {proposal.component} "
                f"in fork {candidate.evo_id}"
            )

        except ForkError:
            raise  # Re-raise our own errors without wrapping
        except (yaml.YAMLError, KeyError, TypeError) as e:
            raise ForkError(
                f"Failed to apply diff to {proposal.component}: {e}"
            ) from e

    def promote(self, candidate: DualCopyCandidate) -> None:
        """Promote a fork by copying modified files to active positions.

        FM-P4-18: Uses YamlStore's atomic write mechanism (tmp + os.replace)
        instead of shutil.copy2.

        Args:
            candidate: The evaluated and approved candidate.

        Raises:
            PromotionError: If any file copy fails.
        """
        fork_dir = self.instance_root / candidate.fork_path

        for rel_path in candidate.modified_files:
            src = fork_dir / rel_path
            dest = self.instance_root / rel_path

            if not src.exists():
                raise PromotionError(
                    f"Modified file missing from fork: {src}. "
                    f"Fork may be corrupted."
                )

            # FM-P4-18: Read the fork content and write via YamlStore
            # for atomic promotion. YamlStore.write_raw() uses tmp + os.replace.
            try:
                content = yaml.safe_load(src.read_text(encoding="utf-8"))
                self.yaml_store.write_raw(rel_path, content)
            except (OSError, yaml.YAMLError) as e:
                raise PromotionError(
                    f"Atomic promotion failed for {rel_path}: {e}"
                ) from e

            logger.info(f"Promoted {rel_path} from fork {candidate.evo_id}")

        candidate.promoted = True
        logger.info(
            f"Fork {candidate.evo_id} promoted: "
            f"{len(candidate.modified_files)} files updated"
        )

    def cleanup_fork(self, candidate: DualCopyCandidate) -> None:
        """Remove fork directory after resolution (promote or rollback).

        Safe to call multiple times — no-op if already cleaned up.

        Args:
            candidate: The resolved candidate to clean up.
        """
        fork_dir = self.instance_root / candidate.fork_path
        if fork_dir.exists():
            try:
                shutil.rmtree(str(fork_dir))
                logger.info(f"Cleaned up fork directory: {fork_dir}")
            except OSError as e:
                logger.error(
                    f"Failed to clean up fork directory {fork_dir}: {e}. "
                    f"Manual cleanup required."
                )

    def persist_manifest(self, candidate: DualCopyCandidate) -> None:
        """Public wrapper for _persist_manifest.

        Called by EvolutionEngine after apply_diff() to update manifest
        with modified_files list (FM-P4-42).
        """
        self._persist_manifest(candidate, candidate.evo_id)

    def _persist_manifest(
        self, candidate: DualCopyCandidate, proposal_id: str
    ) -> None:
        """Persist fork manifest via YamlStore (atomic write).

        FM-P4-42: Separate method for manifest persistence, used by both
        create_fork() and EvolutionEngine after apply_diff().
        """
        manifest_path = f"{self._candidates_dir}/{proposal_id}/manifest.yaml"
        self.yaml_store.write(manifest_path, candidate)

    def _is_excluded(self, rel_path: str) -> bool:
        """Check if a relative path matches any exclude pattern.

        FM-P4-31: Uses fnmatch for glob-style pattern matching instead of
        substring matching, which caused false positives.
        """
        for exclude in self._fork_excludes:
            # fnmatch supports *, ?, [seq] patterns
            if fnmatch.fnmatch(rel_path, exclude):
                return True
            # Also check if any path component matches (for patterns like "logs/**")
            # by checking if the exclude matches the path as a prefix
            if exclude.endswith("*"):
                prefix = exclude[:-1]  # Remove trailing *
                if rel_path.startswith(prefix):
                    return True
        return False

    @staticmethod
    def _atomic_copy(src: Path, dest: Path) -> None:
        """Copy a file atomically: write to tmp, then os.replace.

        FM-P4-24: Ensures fork files are never partially written.
        """
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        shutil.copy2(str(src), str(tmp))
        os.replace(str(tmp), str(dest))

    @staticmethod
    def _get_nested_value(data: dict, dotted_key: str):
        """Get a value from a nested dict using dotted key path.

        FM-P4-38: Used to verify "old" values before overwriting.
        Raises KeyError if any key in the path is missing.
        """
        keys = dotted_key.split(".")
        current = data
        for key in keys:
            current = current[key]  # KeyError if missing — fail-loud
        return current

    @staticmethod
    def _set_nested_value(data: dict, dotted_key: str, value) -> None:
        """Set a value in a nested dict using dotted key path.

        Raises KeyError if any intermediate key is missing.
        """
        keys = dotted_key.split(".")
        current = data
        for key in keys[:-1]:
            current = current[key]  # KeyError if missing — fail-loud
        current[keys[-1]] = value
