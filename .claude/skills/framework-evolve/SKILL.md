# Skill: evolve

## When to Invoke
When proposing or evaluating framework evolution changes.

**NOTE: This is a Phase 1 placeholder. Phase 0 does NOT support self-evolution.**
All framework changes in Phase 0 require explicit human action.

## Protocol (Phase 1+)

1. **Propose evolution**:
   - Create evolution proposal in `state/evolution/proposals/{evo-id}/proposal.yaml`
   - Proposal must specify: component, tier, description, expected impact
   - Constitutional check: verify proposal does not target Ring 0 (CONSTITUTION.md)

2. **Dual-copy evaluation**:
   - Create evolution branch: `evo/{evo-id}`
   - Apply proposed changes on branch
   - Run canary tasks on branch
   - Compare results with main branch

3. **Quorum voting** (Tier 2):
   - Multiple agents vote on the proposal
   - Sealed file-per-voter pattern
   - Quorum threshold must be met

4. **Decision**:
   - If approved and canary tasks pass: merge branch to main
   - If rejected or canary tasks fail: delete branch

5. **Rollback** (always available):
   - Evolution must be reversible via git (Axiom A5)
   - No destructive changes permitted

## Evolution Tiers
| Tier | Scope | Approval |
|------|-------|----------|
| 0 | Parameter tuning (thresholds, weights) | Auto (with canary check) |
| 1 | Prompt template changes | Single reviewer |
| 2 | Structural changes (new roles, topology) | Quorum vote |
| 3 | Architecture changes | Human approval required |

## Constraints
- Framework must not modify its own constitution (Axiom A3)
- All evolution must be reversible (Axiom A5)
- All evolution actions must be logged (Axiom A4)
- Phase 0: NO self-evolution. This skill is a placeholder for future phases.
