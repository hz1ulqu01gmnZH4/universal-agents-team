#!/usr/bin/env bash
# tools/constitution-check.sh — Verify CONSTITUTION.md integrity
set -euo pipefail
exec uv run python -c "
from pathlib import Path
from uagents.engine.constitution_guard import ConstitutionGuard
guard = ConstitutionGuard(Path('CONSTITUTION.md'), Path('core/constitution-hash.txt'))
guard.load_and_verify()
print('Constitution integrity: OK')
"
