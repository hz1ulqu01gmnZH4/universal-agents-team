"""Rehash constitution after legitimate human edits.
Spec reference: Axiom A3 (Constitutional Immutability)."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute constitution hash after legitimate edits"
    )
    parser.add_argument("--root", default=".", help="Framework root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    constitution_path = root / "CONSTITUTION.md"
    hash_path = root / "core" / "constitution-hash.txt"

    if not constitution_path.exists():
        print("Error: CONSTITUTION.md not found", file=__import__("sys").stderr)
        raise SystemExit(1)

    content = constitution_path.read_text(encoding="utf-8")
    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    old_hash = ""
    if hash_path.exists():
        old_hash = hash_path.read_text(encoding="utf-8").strip()

    hash_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path.write_text(new_hash, encoding="utf-8")

    if old_hash and old_hash != new_hash:
        print(f"Constitution hash updated:")
        print(f"  Old: {old_hash[:16]}...")
        print(f"  New: {new_hash[:16]}...")
    else:
        print(f"Constitution hash: {new_hash[:16]}...")


if __name__ == "__main__":
    main()
