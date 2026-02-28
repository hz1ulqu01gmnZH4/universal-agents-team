# Skill: orchestrate

## When to Invoke
When a new task arrives and needs decomposition, or when coordinating multi-agent execution.

## Protocol

1. Read the task from `instances/{domain}/state/tasks/active/{task-id}.yaml`
2. Analyze task complexity:
   - Simple/low-risk: solo topology (single agent executes)
   - Complex/multi-step: hierarchical_team topology (orchestrator + workers)
3. Based on topology selection:
   a. **Solo**: Execute the task directly as the current agent
   b. **Team**: Spawn agents via `tools/spawn-agent.sh --role {role} --task-id {id}`
      - Determine required roles (researcher, implementer, reviewer, scout)
      - Spawn in dependency order (research before implementation)
      - Maximum 5 concurrent agents (framework.yaml constraint)
4. Monitor progress via `tools/audit-tree.sh --since now --stream tasks`
5. On completion: transition to REVIEWING via `tools/task-manager.sh transition --task-id {id} --status reviewing`

## Topology Selection Criteria

| Criterion | Solo | Hierarchical Team |
|-----------|------|-------------------|
| Estimated tokens | < 10K | > 10K |
| Subtask count | 1 | 2+ |
| Requires research | No | Yes |
| Risk level | Low | Medium/High |

## Constraints
- Never skip REVIEWING (Axiom A7)
- Never exceed max_concurrent_agents (currently 5)
- Log every spawn decision to decisions stream
- Every action must be logged (Axiom A4)
- Human can halt at any time (Axiom A1)
