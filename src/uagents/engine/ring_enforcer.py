"""Ring integrity enforcement engine.
Spec reference: Section 20.2 (Hierarchical Protection Rings).

Runtime verification of the Ring 0-3 hierarchy. Hash verification
for Ring 0 content. Validates ring transitions. Prevents Ring 0/1
pruning, disabling, or compression.

Key constraints:
- Ring 0 hash verified at boot and after every evolution cycle
- Ring 0/1 content cannot be pruned, disabled, or compressed
- Ring transition requests validated against hierarchy rules
- Violation of Ring 0 triggers HALT + recovery runbook
- All enforcement events logged in audit trail

Literature basis:
- Xu & Yan (arXiv:2602.12430): Skill Trust Framework
- AI-45 Degree Law: Balanced capability-safety growth
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models.audit import EnvironmentLogEntry  # IFM-N55: ring events -> ENVIRONMENT stream
from ..models.base import generate_id
from ..models.protection import ProtectionRing, RingClassification, RingTransition
from ..models.reconfiguration import RingEnforcementEvent
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.ring_enforcer")


class RingViolationError(RuntimeError):
    """Raised when a Ring 0 integrity violation is detected.

    This is a CRITICAL error that requires immediate HALT.
    The framework must stop all operations and alert human.
    """


class RingEnforcer:
    """Runtime ring integrity verification and enforcement.

    Design invariants:
    - Ring 0 files are hash-verified at boot and after evolution
    - Ring 0/1 content is NEVER pruned, disabled, or compressed
    - Ring transitions validated: only valid promotion/demotion paths
    - Violations logged as RingEnforcementEvent to audit trail
    - Ring 0 violation -> RingViolationError (HALT)
    - Hash registry stored in state for persistence across sessions
    - Recovery runbook referenced but not executed (human must act)

    Usage:
        enforcer = RingEnforcer(yaml_store, constitution_path, audit_logger)
        enforcer.verify_ring_0_integrity()  # At boot
        enforcer.authorize_transition(transition)  # Before ring change
        enforcer.verify_no_ring_0_modification(modified_files)  # After evolution
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        constitution_path: Path,
        domain: str = "meta",
        audit_logger: object | None = None,
    ):
        self.yaml_store = yaml_store
        # IFM-N61: Resolve all paths to absolute to prevent CWD-change breakage
        self._constitution_path = Path(constitution_path).resolve()
        self._domain = domain
        self._audit_logger = audit_logger

        # State paths
        self._state_dir = f"instances/{domain}/state/ring-enforcement"
        self._hash_registry_path = f"{self._state_dir}/hash-registry.yaml"
        yaml_store.ensure_dir(self._state_dir)

        # Ring 0 protected files (absolute paths — IFM-N61)
        self._ring_0_files: list[str] = [
            str(self._constitution_path),
            # SF-3: canary-expectations.yaml is Ring 0 (additional files
            # can be added via config in future phases)
        ]
        # SF-3: Add canary expectations if path is resolvable
        canary_path = Path(f"instances/{domain}/state/canaries/canary-expectations.yaml").resolve()
        if canary_path.exists():
            self._ring_0_files.append(str(canary_path))

        # Load or initialize hash registry
        self._hash_registry: dict[str, str] = self._load_hash_registry()

    def verify_ring_0_integrity(self) -> bool:
        """Verify Ring 0 file hashes against stored registry.

        Called at boot and after every evolution cycle.
        On first run, computes and stores baseline hashes.
        On subsequent runs, compares against stored hashes.

        Returns:
            True if all hashes match (or first run).

        Raises:
            RingViolationError: If any Ring 0 file hash does not match.
        """
        current_hashes: dict[str, str] = {}
        for file_path in self._ring_0_files:
            file_hash = self._compute_file_hash(file_path)
            if file_hash is None:
                # File missing — critical violation
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail=f"Ring 0 file missing: {file_path}",
                    severity="critical",
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file missing: {file_path}. "
                    f"HALT all operations. Recovery runbook: "
                    f"Restore from last known-good git commit."
                )
            current_hashes[file_path] = file_hash

        if not self._hash_registry:
            # First run — store baseline
            self._hash_registry = current_hashes
            self._persist_hash_registry()
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_0_IMMUTABLE,
                target="all_ring_0_files",
                detail=f"Baseline hashes computed for {len(current_hashes)} files",
                severity="info",
            )
            logger.info(
                f"Ring 0 baseline hashes established for "
                f"{len(current_hashes)} files"
            )
            return True

        # Compare against stored hashes
        for file_path, current_hash in current_hashes.items():
            stored_hash = self._hash_registry.get(file_path)
            if stored_hash is None:
                # New Ring 0 file — add to registry
                self._hash_registry[file_path] = current_hash
                self._persist_hash_registry()
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail="New Ring 0 file added to registry",
                    severity="info",
                )
                continue

            if current_hash != stored_hash:
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail=(
                        f"Hash mismatch: expected {stored_hash[:16]}..., "
                        f"got {current_hash[:16]}..."
                    ),
                    severity="critical",
                    recovery_action=(
                        "HALT + restore from git: "
                        f"git checkout $(git log --oneline -- {file_path} | "
                        f"head -1 | cut -d' ' -f1) -- {file_path}"
                    ),
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file modified: {file_path}. "
                    f"Expected hash: {stored_hash[:16]}..., "
                    f"actual: {current_hash[:16]}... "
                    f"HALT all operations immediately. "
                    f"Recovery: restore from last known-good git commit."
                )

        self._log_enforcement_event(
            event_type="hash_check",
            ring=ProtectionRing.RING_0_IMMUTABLE,
            target="all_ring_0_files",
            detail=f"All {len(current_hashes)} Ring 0 files verified OK",
            severity="info",
        )
        logger.info("Ring 0 integrity verified: all hashes match")
        return True

    def update_ring_0_hashes(self) -> None:
        """Update Ring 0 hashes after a human-authorized modification.

        Called ONLY after explicit human approval of a Ring 0 change.
        This is the ONLY way to update Ring 0 hashes — no programmatic
        modification path exists.
        """
        new_hashes: dict[str, str] = {}
        for file_path in self._ring_0_files:
            file_hash = self._compute_file_hash(file_path)
            if file_hash is None:
                raise FileNotFoundError(
                    f"Cannot update hash for missing Ring 0 file: {file_path}"
                )
            new_hashes[file_path] = file_hash

        self._hash_registry = new_hashes
        self._persist_hash_registry()

        self._log_enforcement_event(
            event_type="hash_check",
            ring=ProtectionRing.RING_0_IMMUTABLE,
            target="all_ring_0_files",
            detail=(
                f"Ring 0 hashes updated (human-authorized) for "
                f"{len(new_hashes)} files"
            ),
            severity="info",
        )
        logger.info(
            f"Ring 0 hashes updated after human authorization: "
            f"{len(new_hashes)} files"
        )

    def authorize_transition(
        self,
        transition: RingTransition,
    ) -> tuple[bool, str]:
        """Validate a ring transition request.

        Rules:
        - Ring 3 -> Ring 2: auto-approved if evidence provided
        - Ring 2 -> Ring 1: human approval required
        - Ring 1 -> Ring 2: human approval required (very rare)
        - Ring 2 -> Ring 3: auto-approved (demotion)
        - ANY -> Ring 0: NEVER (Ring 0 is immutable)
        - Ring 0 -> ANY: NEVER (Ring 0 is immutable)
        - Ring 1 -> Ring 0: NEVER
        - Ring 0 -> Ring 1: NEVER

        Args:
            transition: The proposed ring transition.

        Returns:
            (authorized, reason) tuple.
        """
        from_ring = transition.from_ring
        to_ring = transition.to_ring
        # Handle int values from use_enum_values=True
        if isinstance(from_ring, int):
            from_int = from_ring
        else:
            from_int = int(from_ring)
        if isinstance(to_ring, int):
            to_int = to_ring
        else:
            to_int = int(to_ring)

        # Ring 0 is immutable — no transitions in or out
        if from_int == ProtectionRing.RING_0_IMMUTABLE or to_int == ProtectionRing.RING_0_IMMUTABLE:
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_0_IMMUTABLE,
                target=transition.item,
                detail=(
                    f"Ring transition denied: Ring {from_int} -> Ring {to_int}. "
                    f"Ring 0 is immutable."
                ),
                severity="warning",
            )
            return False, "Ring 0 is immutable: no transitions in or out"

        # Ring 3 -> Ring 2: auto-approved with evidence
        if from_int == ProtectionRing.RING_3_EXPENDABLE and to_int == ProtectionRing.RING_2_VALIDATED:
            if not transition.evidence:
                self._log_enforcement_event(
                    event_type="access_denied",
                    ring=ProtectionRing.RING_3_EXPENDABLE,
                    target=transition.item,
                    detail="Promotion Ring 3->2 denied: no evidence provided",
                    severity="warning",
                )
                return False, "Promotion requires evidence (>= +5pp improvement)"
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_2_VALIDATED,
                target=transition.item,
                detail=f"Ring 3->2 promotion authorized: {transition.reason}",
                severity="info",
            )
            return True, "Ring 3->2 promotion authorized"

        # Ring 2 -> Ring 3: auto-approved (demotion)
        if from_int == ProtectionRing.RING_2_VALIDATED and to_int == ProtectionRing.RING_3_EXPENDABLE:
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_3_EXPENDABLE,
                target=transition.item,
                detail=f"Ring 2->3 demotion authorized: {transition.reason}",
                severity="info",
            )
            return True, "Ring 2->3 demotion authorized"

        # Ring 2 -> Ring 1: requires human approval
        if from_int == ProtectionRing.RING_2_VALIDATED and to_int == ProtectionRing.RING_1_PROTECTED:
            if transition.approved_by == "human":
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_1_PROTECTED,
                    target=transition.item,
                    detail=f"Ring 2->1 promotion authorized (human): {transition.reason}",
                    severity="info",
                )
                return True, "Ring 2->1 promotion authorized (human approval)"
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_1_PROTECTED,
                target=transition.item,
                detail="Ring 2->1 promotion denied: requires human approval",
                severity="warning",
            )
            return False, "Ring 2->1 promotion requires human approval"

        # Ring 1 -> Ring 2: requires human approval (rare)
        if from_int == ProtectionRing.RING_1_PROTECTED and to_int == ProtectionRing.RING_2_VALIDATED:
            if transition.approved_by == "human":
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_2_VALIDATED,
                    target=transition.item,
                    detail=f"Ring 1->2 demotion authorized (human): {transition.reason}",
                    severity="info",
                )
                return True, "Ring 1->2 demotion authorized (human approval)"
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_2_VALIDATED,
                target=transition.item,
                detail="Ring 1->2 demotion denied: requires human approval",
                severity="warning",
            )
            return False, "Ring 1->2 demotion requires human approval"

        # All other transitions: not defined
        self._log_enforcement_event(
            event_type="access_denied",
            ring=ProtectionRing(min(from_int, 3)),
            target=transition.item,
            detail=f"Undefined transition: Ring {from_int} -> Ring {to_int}",
            severity="warning",
        )
        return False, f"Undefined ring transition: Ring {from_int} -> Ring {to_int}"

    def can_prune(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be pruned.

        Ring 0 and Ring 1 content can NEVER be pruned.

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be pruned.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            return False
        return True

    def can_compress(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be compressed.

        Ring 0 content can NEVER be compressed.
        Ring 1 content can only be parameter-compressed (not removed).

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be fully compressed.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int == ProtectionRing.RING_0_IMMUTABLE:
            return False
        return True

    def can_disable(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be disabled.

        Ring 0 and Ring 1 can NEVER be disabled.
        Ring 2 can be temporarily disabled (auto-re-enable after session).

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be disabled.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            return False
        return True

    def verify_no_ring_0_modification(
        self,
        modified_files: list[str],
    ) -> bool:
        """Check that no Ring 0 files were modified.

        Called after evolution cycles to ensure Ring 0 integrity.

        Args:
            modified_files: List of file paths that were modified.

        Returns:
            True if no Ring 0 files were modified.

        Raises:
            RingViolationError: If a Ring 0 file was modified.
        """
        # IFM-N88-FIX: Resolve all paths to absolute before comparison
        ring_0_set = {str(Path(f).resolve()) for f in self._ring_0_files}
        for modified in modified_files:
            resolved_modified = str(Path(modified).resolve())
            if resolved_modified in ring_0_set:
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=modified,
                    detail=f"Ring 0 file modified by evolution: {modified}",
                    severity="critical",
                    recovery_action="Revert modification and re-verify hashes",
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file '{modified}' was modified by "
                    f"evolution cycle. This is NEVER allowed. "
                    f"HALT and revert."
                )
        return True

    # -- Internal Methods --

    def _compute_file_hash(self, file_path: str) -> str | None:
        """Compute SHA-256 hash of a file.

        Returns None if file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _load_hash_registry(self) -> dict[str, str]:
        """Load hash registry from YAML."""
        try:
            data = self.yaml_store.read_raw(self._hash_registry_path)
            return dict(data.get("hashes", {}))
        except FileNotFoundError:
            return {}

    def _persist_hash_registry(self) -> None:
        """Persist hash registry to YAML."""
        self.yaml_store.write_raw(
            self._hash_registry_path,
            {"hashes": self._hash_registry},
        )

    def _log_enforcement_event(
        self,
        event_type: str,
        ring: ProtectionRing,
        target: str,
        detail: str,
        severity: str,
        recovery_action: str = "",
    ) -> None:
        """Log a ring enforcement event."""
        now = datetime.now(timezone.utc)
        event = RingEnforcementEvent(
            id=generate_id("ring"),
            created_at=now,
            event_type=event_type,
            ring=ring,
            target=target,
            detail=detail,
            severity=severity,
            recovery_action=recovery_action,
        )

        # Persist to state
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = event.id.split("-")[-1]
        path = f"{self._state_dir}/{timestamp_str}_{unique_suffix}.yaml"
        self.yaml_store.write(path, event)

        # IFM-N55: Ring events go to ENVIRONMENT stream (not EVOLUTION)
        if self._audit_logger is not None:
            try:
                entry = EnvironmentLogEntry(
                    id=generate_id("env"),
                    timestamp=now,
                    event_type=f"ring_enforcement:{event_type}",
                    detail={
                        "ring": int(ring),
                        "target": target,
                        "description": detail,
                        "severity": severity,
                        "recovery_action": recovery_action,
                    },
                )
                self._audit_logger.log_environment(entry)
            except Exception as e:
                # IFM-N98-FIX: Escalate to error for critical severity events
                if severity == "critical":
                    logger.error(f"Failed to log CRITICAL ring enforcement to audit: {e}")
                else:
                    logger.warning(f"Failed to log ring enforcement to audit: {e}")
