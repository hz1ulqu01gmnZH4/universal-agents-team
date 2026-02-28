"""Protection ring models.
Spec reference: Section 20 (Self-Leaning-Down & Capability Protection)."""
from __future__ import annotations

from enum import IntEnum, StrEnum

from .base import FrameworkModel


class ProtectionRing(IntEnum):
    """OS-inspired protection rings. Same hierarchy as evolution tiers."""

    RING_0_IMMUTABLE = 0   # Constitution, self-monitor, pruner — NEVER modified
    RING_1_PROTECTED = 1   # Memory, context engine, evolution — human approval
    RING_2_VALIDATED = 2   # Curated skills, proven tools — quorum approval
    RING_3_EXPENDABLE = 3  # New skills, experimental — auto-approved


class RingClassification(FrameworkModel):
    path: str  # File or capability path
    ring: ProtectionRing
    reason: str


class RingTransition(FrameworkModel):
    item: str
    from_ring: ProtectionRing
    to_ring: ProtectionRing
    reason: str
    evidence: str
    approved_by: str


class ContextPressureLevel(StrEnum):
    """Context window utilization levels (Section 20.5)."""

    HEALTHY = "healthy"    # < 60%
    PRESSURE = "pressure"  # 60-80% → trigger compression
    CRITICAL = "critical"  # 80-95% → aggressive compression
    OVERFLOW = "overflow"  # > 95% → emergency
