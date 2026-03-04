"""Creativity engine data models — Phase 6.
Spec reference: Section 11 (Creativity Engine), Section 4.6 (Voice System)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, generate_id


class CreativePhase(IntEnum):
    """Phases of the Separate-Then-Together protocol."""
    DIVERGE = 1
    CROSS_POLLINATE = 2
    SYNTHESIZE = 3
    EVALUATE = 4


class CreativeActivationTrigger(FrameworkModel):
    """Why the creativity engine was activated."""
    trigger_type: Literal[
        "stagnation_detected",
        "task_tagged_novel",
        "conventional_approach_failed",
        "human_requested",
        "evolution_needs_novel_solution",
    ]
    detail: str
    task_id: str
    stagnation_signals: list[dict] = Field(default_factory=list)


class CreativeAgentAssignment(FrameworkModel):
    """A single agent's creative role assignment."""
    agent_slot: int  # 0-indexed position in the creative session
    persona_atom: str  # e.g., "persona_analogist"
    tone_atom: str  # e.g., "tone_assertive"
    style_atom: str | None = None
    temperature_offset: float = Field(default=0.0, ge=-0.3, le=0.3)  # FM-P6-45-FIX


class DivergentIdea(FrameworkModel):
    """A single idea produced during the diverge phase."""
    id: str = Field(default_factory=lambda: generate_id("idea"))
    agent_slot: int
    content: str
    category: str = ""  # Assigned during evaluation (for flexibility metric)
    originality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class CrossPollinationResult(FrameworkModel):
    """Result of one agent reviewing another's idea (blind)."""
    reviewer_slot: int
    original_idea_id: str
    combined_output: str  # "yes, and..." combination
    build_on_elements: list[str] = Field(default_factory=list)


class SynthesisResult(FrameworkModel):
    """Orchestrator's synthesis of best ideas."""
    selected_idea_ids: list[str]
    synthesis_text: str
    diversity_preserved: bool  # Did synthesis preserve minority ideas?
    minority_ideas: list[str] = Field(default_factory=list)  # IDs of preserved minority ideas


class GuilfordScores(FrameworkModel):
    """Creativity metrics based on Guilford dimensions."""
    fluency: int = Field(ge=0)  # Number of distinct ideas
    flexibility: int = Field(ge=0)  # Number of distinct categories/approaches
    originality: float = Field(ge=0.0, le=1.0)  # Mean semantic distance from common solutions
    elaboration: float = Field(ge=0.0, le=1.0)  # Detail and development of ideas


class CreativeEvaluation(FrameworkModel):
    """Evaluation of a creative session's output."""
    id: str = Field(default_factory=lambda: generate_id("ceval"))
    created_at: datetime
    guilford: GuilfordScores
    novelty: float = Field(ge=0.0, le=1.0)  # Genuinely new?
    quality: float = Field(ge=0.0, le=1.0)  # Solves the problem?
    diversity: float = Field(ge=0.0, le=1.0)  # Differs from other solutions?
    feasibility: float = Field(ge=0.0, le=1.0)  # Can be implemented?
    vdi_score: float = Field(ge=0.0, le=1.0)  # Voice diversity during session


class CreativeSession(FrameworkModel):
    """Tracks a complete creative problem-solving session."""
    id: str = Field(default_factory=lambda: generate_id("csess"))
    created_at: datetime
    task_id: str
    trigger: CreativeActivationTrigger
    agent_count: int = Field(ge=3, le=5)
    assignments: list[CreativeAgentAssignment] = Field(default_factory=list)
    current_phase: CreativePhase = CreativePhase.DIVERGE

    # Phase outputs (populated as session progresses)
    divergent_ideas: list[DivergentIdea] = Field(default_factory=list)
    cross_pollinations: list[CrossPollinationResult] = Field(default_factory=list)
    synthesis: SynthesisResult | None = None
    evaluation: CreativeEvaluation | None = None

    # Anti-stagnation tracking
    persona_history_hash: str = ""  # SHA-256 of sorted persona+tone combo, for rotation check
