"""Directory structure creation and validation.
Spec reference: Section 24 (Project Directory Tree)."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar


class DirectoryManager:
    """Creates and validates framework directory structure.

    Design invariants:
    - Idempotent: re-running is always safe (D1)
    - Never overwrites existing files (D2)
    - Clear error on permission denied (D3)
    - Matches Section 24 exactly
    """

    # Structure definition — directories end with /, files don't
    CORE_DIRS: ClassVar[list[str]] = [
        "core/",
        "core/canary-tasks/",
        "roles/",
        "roles/capabilities/",
        "roles/compositions/",
        "shared/",
        "shared/skills/",
        "shared/tools/",
        "shared/archive/",
        "shared/domain-switches/",
        "tools/",
        "tests/",
    ]

    INSTANCE_DIRS: ClassVar[list[str]] = [
        "state/",
        "state/tasks/",
        "state/tasks/active/",
        "state/tasks/parked/",
        "state/tasks/completed/",
        "state/agents/",
        "state/teams/",
        "state/evolution/",
        "state/evolution/proposals/",
        "state/evolution/candidates/",
        "state/evolution/archive/",
        # S-07-FIX: Missing evolution directories from Phase 4
        "state/evolution/records/",
        "state/evolution/evaluations/",
        # FM-P5-34-FIX: Role metadata directory
        "state/roles/",
        # Phase 5: Governance directories
        "state/governance/",
        "state/governance/quorum_sessions/",
        "state/governance/quorum_votes/",
        "state/governance/alignment_results/",
        "state/governance/alignment_reports/",
        "state/governance/risk_assessments/",
        "state/governance/pending_human_decisions/",
        # Phase 7: Scout directories
        "state/scouts/",
        "state/scouts/targets/",
        "state/scouts/reports/",
        # Phase 6: Creativity directories
        "state/creativity/",
        "state/creativity/sessions/",
        "state/creativity/evaluations/",
        "state/coordination/",
        "state/coordination/pressure-fields/",
        # Phase 8: Population evolution directories
        "state/evolution/populations/",
        "state/evolution/held/",
        "logs/",
        "logs/evolution/",
        "logs/tasks/",
        "logs/decisions/",
        "logs/diversity/",
        "logs/creativity/",
        "logs/resources/",
        "logs/environment/",
        "logs/traces/",
    ]

    CORE_FILES: ClassVar[dict[str, str]] = {
        "core/constitution-hash.txt": "",  # Populated during bootstrap
        "core/lifecycle.yaml": "",         # Task lifecycle definition
        "core/audit.yaml": "",             # Audit configuration
    }

    # Minimal role composition files for standard roles
    STANDARD_ROLES: ClassVar[dict[str, str]] = {
        "roles/compositions/orchestrator.yaml": (
            "name: orchestrator\n"
            "description: Strategic coordination and task decomposition\n"
            "capabilities: []\n"
            "model: opus\n"
            "thinking: extended\n"
        ),
        "roles/compositions/implementer.yaml": (
            "name: implementer\n"
            "description: Code implementation and execution\n"
            "capabilities: []\n"
            "model: sonnet\n"
            "thinking: normal\n"
        ),
        "roles/compositions/reviewer.yaml": (
            "name: reviewer\n"
            "description: Code review and quality assurance\n"
            "capabilities: []\n"
            "model: sonnet\n"
            "thinking: normal\n"
        ),
    }

    def scaffold(self, root: Path, domain: str = "meta") -> list[str]:
        """Create full directory structure. Returns list of created items."""
        created: list[str] = []

        # Top-level directories
        for d in self.CORE_DIRS:
            path = root / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(str(d))

        # Core placeholder files
        for filename, content in self.CORE_FILES.items():
            path = root / filename
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(filename)

        # Standard role compositions (never overwrite existing)
        for filename, content in self.STANDARD_ROLES.items():
            path = root / filename
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(filename)

        # Domain instance
        created.extend(self.scaffold_domain(root, domain))

        return created

    def scaffold_domain(self, root: Path, domain_name: str) -> list[str]:
        """Create a new domain instance directory."""
        # Validate domain_name to prevent path traversal
        if not domain_name or "/" in domain_name or "\\" in domain_name or ".." in domain_name:
            raise ValueError(
                f"Invalid domain name '{domain_name}': must not contain path separators or '..'"
            )
        created: list[str] = []
        instance_root = root / "instances" / domain_name

        for d in self.INSTANCE_DIRS:
            path = instance_root / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(f"instances/{domain_name}/{d}")

        # Create empty JSONL log files
        for stream in [
            "evolution", "tasks", "decisions", "diversity",
            "creativity", "resources", "environment", "traces",
        ]:
            log_file = instance_root / "logs" / stream / f"{stream}.jsonl"
            if not log_file.exists():
                log_file.touch()
                created.append(f"instances/{domain_name}/logs/{stream}/{stream}.jsonl")

        # Focus file
        focus_path = instance_root / "state" / "tasks" / "focus.yaml"
        if not focus_path.exists():
            focus_path.write_text("focus_task_id: null\n", encoding="utf-8")
            created.append(f"instances/{domain_name}/state/tasks/focus.yaml")

        return created

    def validate(self, root: Path) -> list[str]:
        """Check existing structure for missing items. Returns issues."""
        issues: list[str] = []
        for d in self.CORE_DIRS:
            if not (root / d).is_dir():
                issues.append(f"Missing directory: {d}")
        return issues
