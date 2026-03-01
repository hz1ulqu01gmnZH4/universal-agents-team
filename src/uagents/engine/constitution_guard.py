"""Constitutional integrity enforcement.
Spec reference: Section 2 (Constitutional Axioms), Section 20 (Protection Rings)."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ..models.constitution import Constitution
from ..models.evolution import EvolutionProposal
from ..state.git_ops import GitOps

logger = logging.getLogger("uagents.constitution_guard")


class ConstitutionIntegrityError(RuntimeError):
    """Raised when constitution hash verification fails."""


class ConstitutionGuard:
    """Enforces constitutional invariants.

    Design invariants:
    - Hash checked at boot and before every evolution (C1, C2)
    - Constitution file deletion → HARD_FAIL (C4)
    - Hash mismatch → HARD_FAIL with recovery instructions (C1)
    - Never auto-fixes hash mismatches
    """

    def __init__(self, constitution_path: Path, hash_path: Path):
        self.constitution_path = constitution_path
        self.hash_path = hash_path
        self._cached_hash: str | None = None

    def load_and_verify(self) -> str:
        """Load constitution, verify hash. Returns content.
        Raises ConstitutionIntegrityError on any failure."""
        # C4: file must exist
        if not self.constitution_path.exists():
            raise ConstitutionIntegrityError(
                f"CONSTITUTION.md not found at {self.constitution_path}. "
                f"HARD_FAIL: Restore from git or recreate. "
                f"ALL operations suspended until resolved."
            )

        content = self.constitution_path.read_text(encoding="utf-8")
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # First run (TOFU): store hash and log the trust-on-first-use event
        if not self.hash_path.exists():
            logger.warning(
                f"TOFU: No constitution hash found at {self.hash_path}. "
                f"Trusting first-seen hash: {actual_hash[:16]}... "
                f"This is expected on first boot only."
            )
            self.hash_path.write_text(actual_hash, encoding="utf-8")
            self._cached_hash = actual_hash
            return content

        # Subsequent runs: verify
        expected_hash = self.hash_path.read_text(encoding="utf-8").strip()
        if actual_hash != expected_hash:
            raise ConstitutionIntegrityError(
                f"Constitution hash mismatch!\n"
                f"  Expected: {expected_hash}\n"
                f"  Actual:   {actual_hash}\n"
                f"If you edited CONSTITUTION.md intentionally, run:\n"
                f"  tools/rehash-constitution.sh\n"
                f"Otherwise, restore from git:\n"
                f"  git checkout -- CONSTITUTION.md"
            )

        self._cached_hash = actual_hash
        return content

    def verify_hash(self) -> bool:
        """Quick hash check without full content loading."""
        try:
            self.load_and_verify()
            return True
        except ConstitutionIntegrityError:
            return False

    def check_proposal(self, proposal: EvolutionProposal) -> tuple[bool, str]:
        """Verify proposal does not target constitution-protected paths.
        Case-insensitive to prevent bypasses via casing tricks."""
        component_lower = proposal.component.lower()
        if "constitution.md" in component_lower:
            return False, "Evolution cannot modify CONSTITUTION.md (Ring 0 immutable)"
        if "constitution-hash" in component_lower or "constitution_hash" in component_lower:
            return False, "Evolution cannot modify constitution hash"
        return True, "Constitutional check passed"

    def rehash(self) -> str:
        """Recompute and store hash. Only called by explicit human action."""
        if not self.constitution_path.exists():
            raise ConstitutionIntegrityError("Cannot rehash: CONSTITUTION.md not found")
        content = self.constitution_path.read_text(encoding="utf-8")
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.hash_path.write_text(new_hash, encoding="utf-8")
        self._cached_hash = new_hash
        return new_hash
