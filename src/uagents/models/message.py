"""Inter-agent message models.
Spec reference: Section 9 (Coordination Layer)."""
from __future__ import annotations

from enum import StrEnum

from .base import TimestampedModel


class MessageType(StrEnum):
    """Types of inter-agent messages (Section 9)."""

    TASK_ASSIGNMENT = "task_assignment"  # Orchestrator -> Worker
    STATUS_UPDATE = "status_update"  # Worker -> Orchestrator
    REVIEW_REQUEST = "review_request"  # Worker -> Reviewer
    REVIEW_RESULT = "review_result"  # Reviewer -> Orchestrator
    ESCALATION = "escalation"  # Any -> Orchestrator
    SUBTASK_RESULT = "subtask_result"  # Worker -> Orchestrator
    PARK_REQUEST = "park_request"  # Any -> Orchestrator
    COORDINATION_ACK = "coordination_ack"  # Any -> Any


class AgentMessage(TimestampedModel):
    """A message between agents, logged for audit."""

    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: str
    task_id: str | None = None
    requires_ack: bool = False
    ack_received: bool = False
