"""Environment awareness models.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking)."""
from __future__ import annotations

import math

from pydantic import Field

from .base import FrameworkModel, TimestampedModel


class ModelFingerprint(TimestampedModel):
    """Compact representation of model capabilities at a point in time."""

    model_id: str
    reasoning_score: float = Field(ge=0.0, le=1.0)
    instruction_score: float = Field(ge=0.0, le=1.0)
    code_score: float = Field(ge=0.0, le=1.0)
    creative_score: float = Field(ge=0.0, le=1.0)
    tool_score: float = Field(ge=0.0, le=1.0)
    avg_latency_ms: int
    avg_output_tokens: int

    def distance_to(self, other: ModelFingerprint) -> float:
        """Euclidean distance between fingerprint vectors (5 dimensions)."""
        return math.sqrt(
            (self.reasoning_score - other.reasoning_score) ** 2
            + (self.instruction_score - other.instruction_score) ** 2
            + (self.code_score - other.code_score) ** 2
            + (self.creative_score - other.creative_score) ** 2
            + (self.tool_score - other.tool_score) ** 2
        )


class CanaryResult(FrameworkModel):
    """Result of a single canary micro-benchmark."""

    task_name: str
    expected: str
    actual: str
    score: float
    tokens_used: int
    latency_ms: int


class DriftDetection(FrameworkModel):
    """Result of drift analysis comparing current vs baseline fingerprints."""

    current: ModelFingerprint
    baseline: ModelFingerprint
    distance: float
    threshold: float = 0.15  # 15% deviation triggers investigation
    drift_detected: bool
    affected_dimensions: list[str]
