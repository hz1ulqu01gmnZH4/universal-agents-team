"""Voice system models.
Spec reference: Section 4.6 (Voice System)."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import FrameworkModel


class VoiceAtomCategory(StrEnum):
    """Categories of voice atoms — prefix determines category."""

    LANGUAGE = "language"
    TONE = "tone"
    STYLE = "style"
    PERSONA = "persona"


class TokenCost(StrEnum):
    """Token cost classification for voice atoms."""

    MINIMAL = "minimal"  # ~5 tokens
    LOW = "low"          # ~10-15 tokens
    MODERATE = "moderate" # ~20-30 tokens


class VoiceAtom(FrameworkModel):
    """A single voice configuration fragment.
    Names use category prefixes: language_*, tone_*, style_*, persona_*."""

    name: str  # e.g., "language_japanese", "tone_assertive"
    category: VoiceAtomCategory
    description: str
    instruction_fragment: str
    token_cost: TokenCost = TokenCost.LOW
    creativity_mode: bool = False  # True for persona atoms that unlock creative behaviors
    tone_default: str | None = None  # For persona atoms: override tone
    output_token_impact: Literal["reduces", "increases", "neutral"] = "neutral"


class VoiceProfile(FrameworkModel):
    """A complete voice configuration for a role.
    Resolution cascade: role > domain_defaults > framework_defaults."""

    language: str  # Required — references a language_* atom
    tone: str | None = None  # References a tone_* atom
    style: str | None = None  # References a style_* atom
    persona: str | None = None  # References a persona_* atom (max 1)
    formality: float = Field(0.5, ge=0.0, le=1.0)
    verbosity: float = Field(0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_atom_prefixes(self) -> Self:
        """Ensure atom references use correct category prefixes."""
        if not self.language.startswith("language_"):
            raise ValueError(f"Language atom must start with 'language_': {self.language}")
        if self.tone and not self.tone.startswith("tone_"):
            raise ValueError(f"Tone atom must start with 'tone_': {self.tone}")
        if self.style and not self.style.startswith("style_"):
            raise ValueError(f"Style atom must start with 'style_': {self.style}")
        if self.persona and not self.persona.startswith("persona_"):
            raise ValueError(f"Persona atom must start with 'persona_': {self.persona}")
        return self


class VoiceSafetyConfig(FrameworkModel):
    """Validation rules for voice atom content safety.
    Spec reference: Section 4.6.3."""

    forbidden_patterns: list[str]  # Regex patterns that instruction_fragments must NOT match
    max_token_budget_pct: float = 0.02  # Voice must be < 2% of system_instructions
