#!/usr/bin/env bash
# tools/spawn-agent.sh — Compose prompt and output spawn descriptor
set -euo pipefail
exec uv run python -m uagents.cli.spawn_agent "$@"
