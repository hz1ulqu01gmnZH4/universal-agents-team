# Skill: resource

## When to Invoke
When checking resource availability, monitoring budgets, or managing resource constraints.

## Protocol

1. **Check compute resources**:
   - CPU utilization (threshold: 80%)
   - Memory utilization (threshold: 80%)
   - Disk utilization (threshold: 90%)
   - Active agent count vs max_concurrent_agents

2. **Token budget management**:
   - Each task has a token budget (hard limit, Axiom A6)
   - Budget pressure levels:
     | Level | Utilization | Action |
     |-------|------------|--------|
     | GREEN | < 50% | Normal operation |
     | YELLOW | 50-75% | Reduce verbosity, compress context |
     | ORANGE | 75-90% | Park non-essential subtasks |
     | RED | > 90% | Emergency: park task, alert human |

3. **Pre-spawn resource check**:
   - Before spawning any agent, verify 20% headroom on all metrics
   - If resources insufficient, raise ResourceConstrainedError

4. **Rate limit awareness**:
   - Monitor Claude API rate limits
   - Back off when approaching limits
   - Track per-minute and daily usage

5. **Cost monitoring**:
   - Track token costs per task
   - Estimate remaining budget
   - Alert at cost approval thresholds

## Constraints
- Budget limits are hard, not soft (Axiom A6)
- Resource exhaustion triggers graceful degradation (Axiom A8)
- All resource events must be logged (Axiom A4)
- Phase 0 limitation: token tracking not yet implemented
