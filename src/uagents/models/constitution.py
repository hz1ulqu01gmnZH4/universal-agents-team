"""Constitutional data models.
Spec reference: Section 2 (Constitutional Invariants)."""
from __future__ import annotations

from .base import FrameworkModel


class Axiom(FrameworkModel):
    """A single constitutional axiom (A1-A8)."""

    text: str
    enforcement: str


class Constitution(FrameworkModel):
    """Loaded representation of CONSTITUTION.md."""

    axioms: dict[str, Axiom]  # A1_human_halt, A2_human_veto, etc.
    hash: str  # SHA-256 of CONSTITUTION.md file content


class CharterPrinciple(FrameworkModel):
    """A domain charter principle."""

    id: str
    text: str


class Charter(FrameworkModel):
    """Domain-specific charter inheriting from constitution."""

    name: str
    motto: str
    principles: list[CharterPrinciple]
    quality_gates: list[str]
    forbidden: list[str]
    inherited_from: str  # Path to CONSTITUTION.md


class TaskMandate(FrameworkModel):
    """Per-task behavioral directives (overrides role defaults)."""

    motto: str | None = None
    constraints: list[str] = []
    relaxed_rules: list[str] = []
