"""Assigns creative voice profiles to agents in creative sessions.
Spec reference: Section 11.1 (persona_assignment), Section 4.6 (Voice Atoms).

Key constraints:
- No two agents may share the same persona atom
- Each agent gets a unique tone atom
- Never repeat the same persona+tone combo as the previous session
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from ..models.creativity import CreativeAgentAssignment
from ..models.voice import TokenCost, VoiceAtom, VoiceAtomCategory
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.persona_assigner")


class PersonaAssignmentError(Exception):
    """Raised when persona assignment fails."""


class PersonaAssigner:
    """Assigns diverse creative voice profiles to agents.

    Loads voice atoms from roles/voice.yaml, filters by creativity_mode,
    and produces unique assignments per session with rotation enforcement.
    """

    def __init__(self, yaml_store: YamlStore) -> None:
        self.yaml_store = yaml_store
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load creativity engine config (fail-loud)."""
        raw = self.yaml_store.read_raw("core/creativity.yaml")
        return raw["creativity_engine"]

    def assign(
        self,
        agent_count: int,
        previous_session_hash: str = "",
    ) -> list[CreativeAgentAssignment]:
        """Assign unique persona + tone combinations to N agents.

        Args:
            agent_count: Number of agents (3-5).
            previous_session_hash: Hash of previous session's assignments
                for rotation enforcement.

        Returns:
            List of CreativeAgentAssignment, one per agent slot.

        Raises:
            PersonaAssignmentError: If not enough creative personas or tones.
        """
        atoms = self._load_voice_atoms()

        # use_enum_values=True: .category is already a str, not an enum
        creative_personas = [
            a for a in atoms.values()
            if a.creativity_mode and a.category == "persona"
        ]
        tone_atoms = [
            a for a in atoms.values()
            if a.category == "tone"
        ]

        if len(creative_personas) < agent_count:
            raise PersonaAssignmentError(
                f"Need {agent_count} creative personas but only "
                f"{len(creative_personas)} available (creativity_mode=true). "
                f"Available: {[p.name for p in creative_personas]}"
            )
        if len(tone_atoms) < agent_count:
            raise PersonaAssignmentError(
                f"Need {agent_count} unique tone atoms but only "
                f"{len(tone_atoms)} available. "
                f"Available: {[t.name for t in tone_atoms]}"
            )

        # IFM-N53: fail-loud — no .get() defaults for required config values
        temp_offsets = self._config["persona_assignment"]["temperature_offsets"]

        # Build assignments with unique persona + tone per agent
        assignments = self._build_assignments(
            agent_count, creative_personas, tone_atoms,
            temp_offsets, previous_session_hash,
        )
        return assignments

    def _build_assignments(
        self,
        agent_count: int,
        personas: list[VoiceAtom],
        tones: list[VoiceAtom],
        temp_offsets: list[float],
        previous_hash: str,
    ) -> list[CreativeAgentAssignment]:
        """Build assignments, enforcing rotation constraint.

        FM-P6-01: If first candidate combo matches previous_hash,
        rotate by shifting persona order by 1.
        """
        # Sort for determinism
        personas = sorted(personas, key=lambda a: a.name)
        tones = sorted(tones, key=lambda a: a.name)

        # Initial assignment: persona[i] + tone[i]
        assignments: list[CreativeAgentAssignment] = []
        for i in range(agent_count):
            assignments.append(CreativeAgentAssignment(
                agent_slot=i,
                persona_atom=personas[i].name,
                tone_atom=tones[i].name,
                temperature_offset=temp_offsets[i] if i < len(temp_offsets) else 0.0,
            ))

        # Check rotation constraint
        combo_hash = self._compute_combo_hash(assignments)
        if combo_hash == previous_hash and previous_hash != "":
            # Rotate: shift personas by 1 position
            logger.info("Rotating persona assignments to avoid repetition")
            for i, a in enumerate(assignments):
                shifted_idx = (i + 1) % len(personas)
                a.persona_atom = personas[shifted_idx].name
            combo_hash = self._compute_combo_hash(assignments)

        return assignments

    def _load_voice_atoms(self) -> dict[str, VoiceAtom]:
        """Load all voice atoms from roles/voice.yaml."""
        raw = self.yaml_store.read_raw("roles/voice.yaml")
        atoms_raw = raw["voice_atoms"]
        atoms: dict[str, VoiceAtom] = {}
        for name, data in atoms_raw.items():
            data = dict(data)  # FM-P6-29-FIX: copy before mutation
            data["name"] = name
            # strict=True on FrameworkModel requires actual enum instances, not
            # raw strings — VoiceAtomCategory and TokenCost constructors are needed
            for cat in ("language", "tone", "style", "persona"):
                if name.startswith(f"{cat}_"):
                    data["category"] = VoiceAtomCategory(cat)
                    break
            else:
                raise PersonaAssignmentError(
                    f"Voice atom '{name}' does not match any known "
                    f"category prefix (language_, tone_, style_, persona_)"
                )
            # Coerce token_cost to enum if it's a string (strict mode)
            if "token_cost" in data and isinstance(data["token_cost"], str):
                data["token_cost"] = TokenCost(data["token_cost"])
            atoms[name] = VoiceAtom(**data)
        return atoms

    @staticmethod
    def _compute_combo_hash(assignments: list[CreativeAgentAssignment]) -> str:
        """Compute deterministic hash of persona+tone combos for rotation tracking."""
        combos = sorted(f"{a.persona_atom}:{a.tone_atom}" for a in assignments)
        return hashlib.sha256("|".join(combos).encode()).hexdigest()[:16]
