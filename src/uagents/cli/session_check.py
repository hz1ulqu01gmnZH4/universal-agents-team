"""Session lock management CLI.
Spec reference: Part 3.4 (LockManager)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..state.lock_manager import LockManager, SessionAlreadyActiveError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Session lock management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # acquire
    acquire_parser = subparsers.add_parser("acquire", help="Acquire session lock")
    acquire_parser.add_argument("--domain", default="meta", help="Domain name")
    acquire_parser.add_argument("--root", default=".", help="Framework root")

    # release
    release_parser = subparsers.add_parser("release", help="Release session lock")
    release_parser.add_argument("--root", default=".", help="Framework root")

    # status
    status_parser = subparsers.add_parser("status", help="Check lock status")
    status_parser.add_argument("--root", default=".", help="Framework root")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    lock_mgr = LockManager(root)

    if args.command == "acquire":
        try:
            lock = lock_mgr.acquire(args.domain)
            print(f"Session lock acquired:")
            print(f"  Session ID: {lock.session_id}")
            print(f"  PID:        {lock.pid}")
            print(f"  Started:    {lock.started}")
            print(f"  Domain:     {lock.active_domain}")
        except SessionAlreadyActiveError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "release":
        lock_mgr.release()
        print("Session lock released.")

    elif args.command == "status":
        lock = lock_mgr.check()
        if lock is None:
            print("No active session.")
        else:
            print(f"Active session:")
            print(f"  Session ID: {lock.session_id}")
            print(f"  PID:        {lock.pid}")
            print(f"  Started:    {lock.started}")
            print(f"  Domain:     {lock.active_domain}")


if __name__ == "__main__":
    main()
