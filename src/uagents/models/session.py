"""Session lock model.
Spec reference: Section 3.3 (Bootstrap boot sequence, step 3)."""
from __future__ import annotations

from datetime import datetime

from .base import FrameworkModel


class SessionLock(FrameworkModel):
    """Contents of .claude-framework.lock file."""

    pid: int
    started: datetime
    session_id: str
    claude_version: str
    active_domain: str
