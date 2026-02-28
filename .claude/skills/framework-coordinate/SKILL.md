# Skill: coordinate

## When to Invoke
When multiple agents need to coordinate within a team topology, or when using stigmergic coordination.

## Protocol

### Team Coordination (Claude Code Teams)

1. **Create team**:
   ```
   TeamCreate(team_name="task-{id}", description="Team for {task title}")
   ```

2. **Spawn team members**:
   ```
   Task(name="{role}", team_name="task-{id}", prompt=<composed prompt>)
   ```

3. **Send messages**:
   ```
   SendMessage(type="message", recipient="{agent-name}", content="...")
   ```

4. **Monitor completion**: Check TaskUpdate messages from team members.

5. **Cleanup**: `TeamDelete` when all tasks complete.

### Stigmergic Coordination (Pressure Fields)

For swarm topologies, agents coordinate indirectly through shared YAML files:

1. **Read pressure field** before acting:
   ```yaml
   # instances/{domain}/state/coordination/pressure-fields/{task-id}.yaml
   pressure_field:
     task_id: "task-..."
     dimensions:
       research_coverage: 0.4
       implementation_progress: 0.1
       test_coverage: 0.0
       review_status: 0.0
   ```

2. **Act** on the dimension with lowest coverage.

3. **Update pressure field** after acting (single-writer convention).

### Quorum Voting

For decisions requiring consensus:
1. Each voter writes a sealed vote file in `state/evolution/proposals/{evo-id}/votes/`
2. No voter reads other votes before writing (sealed)
3. Proposer collects all votes and computes result

## Constraints
- Single-writer convention: each file has one owner
- All coordination must be logged (Axiom A4)
- Human can halt coordination at any time (Axiom A1)
