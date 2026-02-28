#!/usr/bin/env bash
set -euo pipefail
exec uv run python -m uagents.cli.resource_monitor "$@"
