"""Force-remove stale session lock.
Spec reference: Part 3.4 (LockManager.force_unlock)."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..state.lock_manager import LockManager


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Force-remove stale session lock"
    )
    parser.add_argument(
        "--root", default=".",
        help="Framework root directory (default: current dir)"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    lock_mgr = LockManager(root)

    # Check current state before force-unlocking
    lock = lock_mgr.check()
    if lock is not None:
        print(f"WARNING: Active session detected (PID {lock.pid}).")
        print("Force-unlocking may cause issues if the session is still running.")

    lock_mgr.force_unlock()
    print("Session lock removed.")


if __name__ == "__main__":
    main()
