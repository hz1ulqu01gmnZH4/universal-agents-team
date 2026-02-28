#!/usr/bin/env bash
# tools/session-check.sh — Session lock management
set -euo pipefail
exec uv run python -m uagents.cli.session_check "$@"
