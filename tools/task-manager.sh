#!/usr/bin/env bash
# tools/task-manager.sh — Task lifecycle management
set -euo pipefail
exec uv run python -m uagents.cli.task_manager "$@"
