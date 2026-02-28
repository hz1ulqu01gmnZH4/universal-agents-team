#!/usr/bin/env bash
# tools/audit-tree.sh — Terminal audit log tree viewer
set -euo pipefail
exec uv run python -m uagents.cli.audit_tree "$@"
