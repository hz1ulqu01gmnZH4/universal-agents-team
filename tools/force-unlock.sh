#!/usr/bin/env bash
# tools/force-unlock.sh — Force-remove stale session lock
set -euo pipefail
exec uv run python -m uagents.cli.force_unlock "$@"
