# Skill: audit

## When to Invoke
When viewing audit logs, rendering timeline trees, or investigating framework history.

## Protocol

1. **View session audit tree**:
   ```bash
   tools/audit-tree.sh --since today
   tools/audit-tree.sh --since 1h --stream tasks decisions
   ```

2. **View task detail**:
   ```bash
   tools/audit-tree.sh --task-id {task-id}
   ```

3. **Available log streams** (8 total):
   | Stream | Content |
   |--------|---------|
   | `tasks` | Task lifecycle events (create, transition, park, resume) |
   | `decisions` | Agent decisions (topology selection, spawn, verdict) |
   | `evolution` | Evolution proposals (Phase 1+, stub in Phase 0) |
   | `diversity` | Diversity metrics (Phase 1+, stub in Phase 0) |
   | `creativity` | Creative process logs (Phase 1+, stub in Phase 0) |
   | `resources` | Resource consumption events |
   | `environment` | Environment changes, model drift |
   | `traces` | Detailed execution traces |

4. **Log format**: All logs are JSONL (one JSON object per line), append-only.

5. **Log locations**: `instances/{domain}/logs/{stream}/{stream}.jsonl`

## Constraints
- Logs are append-only, never deleted during normal operation (Axiom A4)
- Every action must be traceable through the audit system
- Tree rendering uses the `rich` library for terminal output
