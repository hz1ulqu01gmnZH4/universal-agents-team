# universal-agents-team

Self-evolving multi-agent framework for Claude Code.

## Tests

Tests are gitignored. They live on disk at `tests/` but are tracked in a separate private repo:
`~/universal-agents-team-tests` → [github.com/hz1ulqu01gmnZH4/universal-agents-team-tests](https://github.com/hz1ulqu01gmnZH4/universal-agents-team-tests)

```sh
uv run pytest --tb=short -q   # run from this directory
```

## Build

```sh
uv sync                        # install deps
uv run pytest                  # 1238 tests across Phases 0-5
```
