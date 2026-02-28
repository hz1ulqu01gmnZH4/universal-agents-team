# Skill: spawn-agent

## When to Invoke
When the orchestrator needs to create a new agent for task execution.

## Protocol

1. **Pre-flight checks**:
   - Verify resource availability (CPU < 80%, memory < 80%, disk < 90%)
   - Check agent count against max_concurrent_agents limit
   - Verify role composition exists in `roles/compositions/{role}.yaml`

2. **Compose prompt**:
   ```bash
   uv run python -m uagents.cli.spawn_agent --role {role} --task-id {task-id} --domain {domain}
   ```
   This outputs a JSON spawn descriptor with the composed prompt.

3. **Spawn via Claude Code Task tool**:
   Use the spawn descriptor to invoke Claude Code's Task tool:
   ```
   Task(
     description="[role] for [task-id]",
     prompt=<composed prompt from step 2>,
     subagent_type="general-purpose",
     model=<from spawn descriptor>,
   )
   ```

4. **Post-spawn**: The agent registry is updated with the new agent entry.

## Model Mapping
- `opus` roles: orchestrator, researcher, reviewer (deep reasoning)
- `sonnet` roles: implementer, scout (efficient execution)

## Constraints
- Never spawn if resources are constrained (Axiom A8)
- Every spawn must be logged (Axiom A4)
- Budget must be checked before spawn (Axiom A6)
- All spawned agents inherit constitutional axioms in Ring 0 of their prompt
