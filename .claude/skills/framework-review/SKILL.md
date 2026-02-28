# Skill: review

## When to Invoke
When a task reaches REVIEWING status and requires quality verification (Axiom A7).

## Protocol

1. **Load review context**:
   - Read the task from `instances/{domain}/state/tasks/active/{task-id}.yaml`
   - Read all artifacts produced during EXECUTING phase
   - Load the review mandate from the reviewer role composition

2. **Structured review checklist**:
   - [ ] **Correctness**: Does the implementation match requirements?
   - [ ] **Security**: Are there any security concerns or vulnerabilities?
   - [ ] **Performance**: Are there performance issues or inefficiencies?
   - [ ] **Adherence to requirements**: Does it satisfy all stated constraints?
   - [ ] **Constitutional compliance**: Does it respect all 8 axioms?

3. **Findings format**:
   Each finding must include:
   - Severity: `critical` | `major` | `minor` | `note`
   - Category: One of the checklist items above
   - Description: What was found
   - Recommendation: How to fix it

4. **Verdict rules**:
   - `pass`: All checks pass, no critical/major findings
   - `pass_with_notes`: Minor findings only, acceptable for completion
   - `fail`: Any critical or major finding triggers re-planning
     - Task transitions back to PLANNING with feedback attached

5. **Record review**:
   ```bash
   uv run python -m uagents.cli.task_manager transition --task-id {id} --status verdict --detail "Review verdict: {verdict}"
   ```

## Constraints
- Never approve your own work (reviewer forbidden rule)
- Every review must be logged (Axiom A4)
- Reviews are mandatory, never optional (Axiom A7)
- Reviewer must use extended thinking for thorough analysis
