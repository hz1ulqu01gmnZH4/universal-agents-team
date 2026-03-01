"""Session lock management for single-instance enforcement.
Spec reference: Section 3.3 (bootstrap, step 3)."""
from __future__ import annotations

import atexit
import os
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..models.session import SessionLock

LOCK_FILENAME = ".claude-framework.lock"


class SessionAlreadyActiveError(RuntimeError):
    """Raised when attempting to acquire a lock held by a live process."""


class LockManager:
    """Manages .claude-framework.lock for single-session enforcement.

    Design invariants:
    - Atomic lock acquisition via open(path, 'x') (L4)
    - PID + start_time verification to detect PID reuse (L2)
    - atexit cleanup for normal exits (L5)
    - Signal handler for SIGTERM (X5)
    - Stale lock detection via os.kill(pid, 0) (L1)
    """

    def __init__(self, framework_root: Path):
        self.lock_path = framework_root / LOCK_FILENAME
        self._owns_lock = False

    @staticmethod
    def _get_process_start_time(pid: int) -> float | None:
        """Get process start time for PID reuse detection."""
        try:
            import psutil
            proc = psutil.Process(pid)
            return proc.create_time()
        except Exception:
            return None

    def acquire(self, domain: str = "meta") -> SessionLock:
        """Acquire lock. Raises SessionAlreadyActiveError if lock held
        by live process. Removes stale locks with warning."""
        if self.lock_path.exists():
            existing = self._read_lock()
            if existing and self._is_process_alive(existing.pid):
                # Additional PID reuse check via start_time
                current_start = self._get_process_start_time(existing.pid)
                if (existing.pid_start_time is not None
                        and current_start is not None
                        and abs(current_start - existing.pid_start_time) > 1.0):
                    # PID was reused — this is a stale lock
                    import sys
                    print(
                        f"WARNING: Removing stale lock (PID {existing.pid} was reused)",
                        file=sys.stderr,
                    )
                    self.lock_path.unlink()
                else:
                    raise SessionAlreadyActiveError(
                        f"Another framework session is active "
                        f"(PID {existing.pid}, started {existing.started}). "
                        f"Terminate it first or run 'tools/force-unlock.sh'."
                    )
            else:
                # Stale lock — warn and remove (L1)
                import sys
                pid_info = existing.pid if existing else "unknown"
                print(
                    f"WARNING: Removing stale lock (PID {pid_info} is dead)",
                    file=sys.stderr,
                )
                self.lock_path.unlink()

        lock = SessionLock(
            pid=os.getpid(),
            started=datetime.now(timezone.utc),
            session_id=f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            claude_version=self._get_claude_version(),
            active_domain=domain,
            pid_start_time=self._get_process_start_time(os.getpid()),
        )

        # Atomic create via exclusive open (L4)
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                data = lock.model_dump(mode="json")
                yaml.dump(data, f, default_flow_style=False)
        except FileExistsError:
            raise SessionAlreadyActiveError(
                "Lock file appeared during acquisition (race condition). "
                "Another session started simultaneously."
            )

        self._owns_lock = True

        # Register cleanup (L5)
        atexit.register(self.release)
        signal.signal(signal.SIGTERM, self._signal_handler)

        return lock

    def release(self) -> None:
        """Release lock on clean shutdown."""
        if self._owns_lock and self.lock_path.exists():
            self.lock_path.unlink(missing_ok=True)
            self._owns_lock = False

    def check(self) -> SessionLock | None:
        """Check if lock exists and holder is alive. Returns info or None."""
        if not self.lock_path.exists():
            return None
        lock = self._read_lock()
        if lock and self._is_process_alive(lock.pid):
            return lock
        return None  # Stale

    def force_unlock(self) -> None:
        """Force-remove lock (for stale lock recovery)."""
        if self.lock_path.exists():
            self.lock_path.unlink()

    def verify_ownership(self) -> bool:
        """Verify current process owns the lock."""
        if not self.lock_path.exists():
            return False
        lock = self._read_lock()
        return lock is not None and lock.pid == os.getpid()

    def _read_lock(self) -> SessionLock | None:
        """Read lock file, return None if corrupt."""
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                return None
            return SessionLock.model_validate(data, strict=False)
        except Exception:
            return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if process with PID is running (L1)."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _get_claude_version() -> str:
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle SIGTERM: release lock then exit (X5)."""
        self.release()
        raise SystemExit(128 + signum)
