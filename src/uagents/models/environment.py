"""Environment awareness models.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking).

Phase 0: ModelFingerprint, CanaryResult, DriftDetection.
Phase 2.5: CanarySuiteResult, VersionInfo, PerformanceTrack,
           SkillPerformance, ToolPerformance, RevalidationResult,
           BenchmarkSuiteResult, TraceEntry, ModelExecuteFn.
"""
from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import Field

from .base import FrameworkModel, TimestampedModel


# SF-1: Typed protocol for model execution function (replaces bare `callable`)
class ModelExecuteFn(Protocol):
    """Protocol for model execution functions used by CanaryRunner and
    RevalidationEngine.

    Signature: (prompt: str, max_tokens: int) -> tuple[str, int]
    Returns: (output_text, tokens_used)
    """

    def __call__(self, prompt: str, max_tokens: int) -> tuple[str, int]: ...


# ── Existing Phase 0 models ──
# Migration note (MF-3): Phase 2.5 adds Field(ge=0.0, le=1.0) validators
# to CanaryResult.score and Field(ge=0) to CanaryResult.tokens_used and
# CanaryResult.latency_ms. Existing stored CanaryResult YAML files must
# contain valid values (non-negative, score in [0,1]) or they will fail
# Pydantic validation on load. Phase 0 data should already conform since
# scores are always 0.0-1.0 and counts are non-negative.

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

    def per_dimension_delta(self, other: ModelFingerprint) -> dict[str, float]:
        """Per-dimension signed delta (self - other). Positive = improvement."""
        return {
            "reasoning": self.reasoning_score - other.reasoning_score,
            "instruction": self.instruction_score - other.instruction_score,
            "code": self.code_score - other.code_score,
            "creative": self.creative_score - other.creative_score,
            "tool": self.tool_score - other.tool_score,
        }

    def score_vector(self) -> list[float]:
        """Return the 5 capability scores as a list."""
        return [
            self.reasoning_score,
            self.instruction_score,
            self.code_score,
            self.creative_score,
            self.tool_score,
        ]


class CanaryResult(FrameworkModel):
    """Result of a single canary micro-benchmark."""

    task_name: str
    expected: str
    actual: str
    score: float = Field(ge=0.0, le=1.0)
    tokens_used: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


class DriftDetection(FrameworkModel):
    """Result of drift analysis comparing current vs baseline fingerprints."""

    current: ModelFingerprint
    baseline: ModelFingerprint
    distance: float
    threshold: float = 0.15
    drift_detected: bool
    affected_dimensions: list[str]


# ── Phase 2.5 new models ──

class CanarySuiteResult(TimestampedModel):
    """Complete result of running the 5-task canary suite."""

    results: list[CanaryResult]
    fingerprint: ModelFingerprint
    total_tokens: int = Field(ge=0)
    total_latency_ms: int = Field(ge=0)
    all_passed: bool

    @property
    def task_scores(self) -> dict[str, float]:
        """Map of task_name -> score for quick lookup."""
        return {r.task_name: r.score for r in self.results}


class VersionInfo(FrameworkModel):
    """Tracked version information for environment change detection."""

    claude_code_version: str
    python_version: str
    os_info: str
    timestamp: datetime

    def differs_from(self, other: VersionInfo) -> list[str]:
        """Return list of fields that differ between two VersionInfo instances."""
        changes: list[str] = []
        if self.claude_code_version != other.claude_code_version:
            changes.append("claude_code_version")
        if self.python_version != other.python_version:
            changes.append("python_version")
        if self.os_info != other.os_info:
            changes.append("os_info")
        return changes


class SkillPerformance(FrameworkModel):
    """Rolling performance record for a single skill/task_type."""

    skill_name: str
    recent_outcomes: list[bool] = Field(default_factory=list)  # Last 20 outcomes
    total_attempts: int = 0
    total_successes: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    baseline_success_rate: float | None = None  # Set after first 20 attempts
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Current success rate from rolling window."""
        if not self.recent_outcomes:
            return 0.0
        return sum(1 for o in self.recent_outcomes if o) / len(self.recent_outcomes)

    @property
    def avg_tokens(self) -> float:
        """Average tokens per attempt."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_tokens / self.total_attempts

    @property
    def avg_latency_ms(self) -> float:
        """Average latency per attempt."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_latency_ms / self.total_attempts

    @property
    def success_rate_drop(self) -> float | None:
        """Drop in success rate vs baseline (positive = degradation).
        Returns None if no baseline established yet."""
        if self.baseline_success_rate is None:
            return None
        return self.baseline_success_rate - self.success_rate


class ToolPerformance(FrameworkModel):
    """Rolling performance record for a single tool."""

    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    total_tokens: int = 0
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def timeout_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.timeout_calls / self.total_calls

    @property
    def avg_token_cost(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_tokens / self.total_calls


class PerformanceTrack(TimestampedModel):
    """Complete performance tracking state. Persisted to YAML."""

    skills: dict[str, SkillPerformance] = Field(default_factory=dict)
    tools: dict[str, ToolPerformance] = Field(default_factory=dict)
    tasks_since_last_check: int = 0


class RevalidationTrigger(StrEnum):
    """What caused a revalidation."""

    MODEL_DRIFT = "model_drift"
    VERSION_CHANGE = "version_change"
    MCP_CHANGE = "mcp_change"
    PERFORMANCE_DROP = "performance_drop"
    MANUAL = "manual"


class AdaptationResponse(StrEnum):
    """Classification of how the environment changed."""

    IMPROVED = "improved"
    UNCHANGED = "unchanged"
    DEGRADED_MINOR = "degraded_minor"
    DEGRADED_MAJOR = "degraded_major"
    BROKEN = "broken"


class RevalidationResult(TimestampedModel):
    """Result of a triggered revalidation."""

    trigger: RevalidationTrigger
    trigger_detail: str
    scope: list[str]  # What was revalidated (skill names, tool names)
    tokens_used: int = Field(ge=0)
    budget_cap: int  # Max tokens allowed for this revalidation
    pre_fingerprint: ModelFingerprint | None = None
    post_fingerprint: ModelFingerprint | None = None
    adaptation: AdaptationResponse
    affected_skills: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)


class BenchmarkTask(FrameworkModel):
    """A single self-benchmarking meta-task."""

    name: str
    description: str
    expected_behavior: str
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    tokens_used: int = Field(ge=0, default=0)
    latency_ms: int = Field(ge=0, default=0)


class BenchmarkSuiteResult(TimestampedModel):
    """Result of self-benchmarking protocol."""

    tasks: list[BenchmarkTask]
    composite_score: float = Field(ge=0.0, le=1.0)
    suite_type: str  # "full" or "quick"
    total_tokens: int = Field(ge=0)

    @property
    def task_scores(self) -> dict[str, float]:
        return {t.name: t.score for t in self.tasks}


class TraceLevel(StrEnum):
    """Structured trace levels from AgentTrace (arXiv:2602.10133)."""

    OPERATIONAL = "operational"
    COGNITIVE = "cognitive"
    CONTEXTUAL = "contextual"


class TraceEntry(FrameworkModel):
    """A single structured trace entry."""

    level: TraceLevel
    task_id: str
    timestamp: datetime
    category: str  # e.g., "tool_call", "reasoning_step", "context_usage"
    detail: dict
    tokens_used: int = 0
    latency_ms: int = 0


# SF-2/IFM-22/IFM-23: Converted from plain classes to FrameworkModel
class PerformanceAlert(FrameworkModel):
    """A performance alert to be surfaced to the orchestrator."""

    alert_type: str  # "skill_degradation", "tool_degradation", "tool_quarantine"
    target_name: str
    message: str
    current_rate: float
    baseline_rate: float | None = None
    timestamp: datetime


class EnvironmentCheckResult(FrameworkModel):
    """Result of an environment check (session start or periodic)."""

    drift_detected: bool = False
    drift: DriftDetection | None = None
    version_changes: list[str] = Field(default_factory=list)
    version_info: VersionInfo | None = None
    fingerprint: ModelFingerprint | None = None
    revalidation_triggered: bool = False
    adaptation: AdaptationResponse | None = None
    alerts: list[PerformanceAlert] = Field(default_factory=list)
    canary_all_passed: bool = True
    skipped: bool = False
    skip_reason: str = ""
