"""CLAUDE.md generation from framework state.
Spec reference: Section 3.3 (bootstrap), Section 21.3 (prompt structure)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..state.yaml_store import YamlStore


class ClaudeMdGenerator:
    """Generates CLAUDE.md from framework state.

    CLAUDE.md is ~150-200 lines, ~2.5K tokens.
    Machine-generated section has a hard cap of 100 lines (P5).
    """

    MAX_DYNAMIC_LINES = 100

    def __init__(self, yaml_store: YamlStore, framework_root: Path):
        self.yaml_store = yaml_store
        self.root = framework_root

    def generate(self, domain: str = "meta") -> str:
        """Generate complete CLAUDE.md content."""
        # Load framework config
        config = self.yaml_store.read_raw("framework.yaml")
        fw = config.get("framework", config)

        # Compute constitution hash
        constitution_path = self.root / "CONSTITUTION.md"
        if constitution_path.exists():
            content = constitution_path.read_text(encoding="utf-8")
            constitution_hash = hashlib.sha256(content.encode()).hexdigest()
        else:
            constitution_hash = "NOT_FOUND"

        # Load active domain info
        phase = fw.get("phase", "0")

        # Build CLAUDE.md sections
        sections: list[str] = [
            self._build_header(phase, domain, constitution_hash),
            self._build_bootstrap_protocol(domain),
            self._build_axiom_reference(),
            self._build_task_lifecycle(),
            self._build_task_processing(),
            self._build_roles_table(),
            self._build_tool_reference(),
            self._build_key_directories(domain),
            self._build_limitations(),
        ]

        return "\n\n".join(sections)

    def update_active_context(self, domain: str = "meta") -> str:
        """Regenerate only the dynamic 'Current State' section.
        Appended to static CLAUDE.md. Capped at MAX_DYNAMIC_LINES."""
        tasks = []
        try:
            active_dir = f"instances/{domain}/state/tasks/active"
            for name in self.yaml_store.list_dir(active_dir):
                if name.endswith(".yaml"):
                    data = self.yaml_store.read_raw(f"{active_dir}/{name}")
                    tasks.append(data)
        except (FileNotFoundError, NotADirectoryError):
            pass

        lines = ["## Current State", ""]
        if tasks:
            for t in tasks[:10]:  # Cap at 10 tasks
                lines.append(f"- [{t.get('status', '?')}] {t.get('title', '?')}")
        else:
            lines.append("No active tasks. Ready for new work.")

        # Enforce cap
        if len(lines) > self.MAX_DYNAMIC_LINES:
            lines = lines[: self.MAX_DYNAMIC_LINES]
            lines.append("... (truncated)")

        return "\n".join(lines)

    # -- Section builders (static content) --

    @staticmethod
    def _build_header(phase: str, domain: str, hash_: str) -> str:
        return (
            f"# Universal Agents Framework — Bootstrap Instructions\n\n"
            f"**Phase:** {phase}\n"
            f"**Active Domain:** {domain}\n"
            f"**Constitution Hash:** {hash_}\n"
        )

    @staticmethod
    def _build_bootstrap_protocol(domain: str) -> str:
        return (
            "## Bootstrap Protocol\n\n"
            "When this session starts, execute IN ORDER:\n\n"
            "1. **Session Lock**: `tools/session-check.sh acquire`\n"
            "2. **Constitution Check**: `tools/constitution-check.sh`\n"
            f"3. **Load Context**: Read CONSTITUTION.md, "
            f"instances/{domain}/CHARTER.md, focus.yaml\n"
            "4. **Offer Options**: Resume parked tasks or accept new task\n"
        )

    @staticmethod
    def _build_axiom_reference() -> str:
        return (
            "## Constitutional Axioms\n\n"
            "- A1: Human can halt all operations at any time\n"
            "- A2: Human can veto any decision\n"
            "- A3: Framework must not modify its own constitution\n"
            "- A4: Every action must be logged and traceable\n"
            "- A5: Evolution must be reversible\n"
            "- A6: Task budgets are hard limits\n"
            "- A7: Every task must be reviewed before completion\n"
            "- A8: Resource exhaustion → graceful degradation\n"
        )

    @staticmethod
    def _build_task_lifecycle() -> str:
        return (
            "## Task Lifecycle\n\n"
            "INTAKE → ANALYSIS → PLANNING → EXECUTING → "
            "REVIEWING → VERDICT → COMPLETE → ARCHIVED\n\n"
            "Rules: A7 (review mandatory), A4 (all logged), "
            "A1 (human halt), A2 (human veto)\n"
        )

    @staticmethod
    def _build_task_processing() -> str:
        return (
            "## Processing Tasks\n\n"
            "1. INTAKE: `task_manager create`\n"
            "2. ANALYSIS: Select topology\n"
            "3. PLANNING: Decompose, assign roles\n"
            "4. EXECUTING: Spawn agents\n"
            "5. REVIEWING: Spawn reviewer\n"
            "6. VERDICT: Pass → complete, Fail → re-plan\n"
            "7. COMPLETE: Record metrics\n"
        )

    @staticmethod
    def _build_roles_table() -> str:
        return (
            "## Roles\n\n"
            "| Role | Model | Purpose |\n"
            "|------|-------|--------|\n"
            "| orchestrator | opus | Coordination |\n"
            "| researcher | opus | Analysis |\n"
            "| implementer | sonnet | Execution |\n"
            "| reviewer | opus | Verification |\n"
            "| scout | sonnet | Exploration |\n"
        )

    @staticmethod
    def _build_tool_reference() -> str:
        return (
            "## Tools\n\n"
            "All tools: `uv run python -m uagents.cli.<module> [args]`\n"
            "Shell wrappers in `tools/` directory.\n"
        )

    @staticmethod
    def _build_key_directories(domain: str) -> str:
        return (
            "## Key Directories\n\n"
            f"- `instances/{domain}/state/tasks/` — Task YAML files\n"
            f"- `instances/{domain}/state/agents/` — Agent registry\n"
            f"- `instances/{domain}/logs/` — 8-stream audit logs\n"
            "- `roles/` — Capabilities, voice atoms, compositions\n"
        )

    @staticmethod
    def _build_limitations() -> str:
        return (
            "## Phase 0 Limitations\n\n"
            "- No self-evolution\n"
            "- No diversity enforcement\n"
            "- No resource tracking\n"
            "- No environment awareness\n"
            "- Topology: solo, hierarchical_team only\n"
            "- Max 5 concurrent agents\n"
        )
