#!/usr/bin/env bash
# tools/bootstrap.sh — Bootstrap the Universal Agents Framework
set -euo pipefail
exec uv run python -m uagents.cli.bootstrap "$@"
