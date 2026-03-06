# Universal Agents

Self-evolving multi-agent framework for Claude Code.

## What It Is

A Python toolbox that turns Claude Code into a self-improving multi-agent system. Claude Code **is** the runtime — this framework provides state management, task lifecycle, evolution engine, and CLI tools that Claude Code consumes via a generated `CLAUDE.md`.

## Quick Start

```sh
uv sync
uv run python -m uagents.cli.bootstrap --domain meta --root ./my-instance
```

This creates the full directory tree: constitution, roles, audit logs, task queues, evolution state.

## Usage

All commands run from the bootstrapped instance root:

```sh
# Session management
uv run python -m uagents.cli.session_check acquire
uv run python -m uagents.cli.session_check release

# Tasks
uv run python -m uagents.cli.task_manager create --title "..." --description "..."
uv run python -m uagents.cli.task_manager transition --task-id ID --status executing
uv run python -m uagents.cli.task_manager list
uv run python -m uagents.cli.task_manager park --task-id ID --reason "..."

# Agents
uv run python -m uagents.cli.spawn_agent --role implementer --task-id ID

# Audit
uv run python -m uagents.cli.audit_tree --since today

# Resources
uv run python -m uagents.cli.resource_monitor
```

## Architecture

```
CLAUDE.md (generated entry point — Claude Code reads this)
    ↓
CLI tools (uagents.cli.*) — Claude Code calls these
    ↓
Engine layer — orchestrator, evolution, governance, creativity
    ↓
State layer — YamlStore, GitOps, JSONL audit logs
```

**92 source files** across 8 implemented phases:

| Phase | What |
|-------|------|
| 0 | Core: models, state, audit, task lifecycle |
| 1 | Multi-agent: orchestrator, teams, review, messaging |
| 1.5 | Budget: token tracking, rate limits, cost gates |
| 2 | Self-awareness: diversity, stagnation, calibration |
| 2.5 | Environment: canary tests, model drift detection |
| 3 | Skills: extraction, validation, library |
| 3.5 | Self-leaning: context pressure, dynamic tools, ring protection |
| 4 | Evolution: dual-copy, MAP-Elites archive, constitution guard |
| 5 | Governance: quorum voting, risk scorecard, alignment |
| 6 | Creativity: debate topologies, Guilford metrics |
| 7 | Self-expansion: scouts, pressure fields, domain switching |
| 8 | Population: tournament selection, gap monitoring |

## Tests

```sh
uv run pytest          # 1491 tests
```

## Key Design Principles

- **Constitution**: 8 immutable axioms, SHA-256 verified at boot
- **Dual-copy evolution**: changes tested in forks, never in-place
- **Ring protection**: Ring 0 (constitution) can never be modified programmatically
- **Fail-loud**: no silent defaults, no fallback masking — errors propagate
- **Full audit**: 8 JSONL streams, append-only, every action traced
