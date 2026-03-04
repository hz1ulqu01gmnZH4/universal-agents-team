"""Domain instantiation and switching protocol.
Spec reference: Section 22 (Domain Instantiation & Switching).

Each domain is a separate working subdirectory with its own:
- CHARTER.md (domain-specific charter)
- domain.yaml (domain configuration)
- state/ (domain-specific state)
- logs/ (domain-specific logs)

Key constraints:
- Domain switching parks all active tasks
- New domain creation scaffolds from template
- Cross-domain learning via shared archive only
- Domain names validated against path traversal
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from ..models.expansion import DomainConfig, DomainSwitchRecord, VoiceDefaults
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.domain_manager")


class DomainError(RuntimeError):
    """Raised when domain operations fail.

    DR-Issue-3-FIX: Inherits RuntimeError per codebase convention.
    """


class DomainManager:
    """Manages domain workspaces: creation, switching, listing.

    Usage:
        mgr = DomainManager(yaml_store, directory_manager)
        mgr.create_domain("research-lab", description="Research domain")
        record = mgr.switch_domain("meta", "research-lab", reason="Starting research")
        domains = mgr.list_domains()
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        directory_manager: "DirectoryManager",
    ) -> None:
        from ..state.directory import DirectoryManager

        self.yaml_store = yaml_store
        self.directory_manager = directory_manager

    def create_domain(
        self,
        name: str,
        description: str = "",
        task_types: list[str] | None = None,
        voice_defaults: dict[str, str | float] | None = None,
    ) -> DomainConfig:
        """Create a new domain workspace.

        Scaffolds the directory structure and creates domain.yaml.

        Args:
            name: Domain name (must be valid directory name).
            description: Human-readable domain description.
            task_types: Domain-specific task types.
            voice_defaults: Domain-level voice atom defaults.

        Returns:
            The created DomainConfig.

        Raises:
            DomainError: If domain already exists or name is invalid.
        """
        # Validate name
        self._validate_domain_name(name)

        # Check if already exists
        instance_dir = self.yaml_store.base_dir / "instances" / name
        if instance_dir.exists():
            raise DomainError(f"Domain '{name}' already exists at {instance_dir}")

        # Scaffold directory structure
        self.directory_manager.scaffold_domain(self.yaml_store.base_dir, name)

        # Create domain.yaml
        vd = VoiceDefaults(**(voice_defaults or {})) if voice_defaults else VoiceDefaults()
        config = DomainConfig(
            name=name,
            description=description,
            task_types=task_types or [],
            voice_defaults=vd,
        )
        domain_yaml_path = f"instances/{name}/domain.yaml"
        self.yaml_store.write_raw(domain_yaml_path, {"domain": config.model_dump()})

        # Create placeholder CHARTER.md
        charter_path = instance_dir / "CHARTER.md"
        charter_path.write_text(
            f"# {name} Domain Charter\n\n"
            f"**Description:** {description}\n\n"
            f"## Principles\n\n"
            f"_Define domain-specific principles here._\n\n"
            f"## Boundaries\n\n"
            f"_Define what this domain covers and what it does not._\n",
            encoding="utf-8",
        )

        logger.info(f"Domain '{name}' created at {instance_dir}")
        return config

    def switch_domain(
        self,
        from_domain: str,
        to_domain: str,
        reason: str = "",
    ) -> DomainSwitchRecord:
        """Switch from one domain to another.

        Parks all active tasks in the source domain.

        Args:
            from_domain: Current domain name.
            to_domain: Target domain name.
            reason: Why the switch is happening.

        Returns:
            DomainSwitchRecord documenting the switch.

        Raises:
            DomainError: If source or target domain does not exist.
        """
        # Guard against self-switch
        if from_domain == to_domain:
            raise DomainError(f"Cannot switch domain '{from_domain}' to itself")

        # FM-P7-047-FIX: Validate BOTH source and target exist
        source_dir = self.yaml_store.base_dir / "instances" / from_domain
        if not source_dir.exists():
            raise DomainError(
                f"Source domain '{from_domain}' does not exist."
            )

        target_dir = self.yaml_store.base_dir / "instances" / to_domain
        if not target_dir.exists():
            raise DomainError(
                f"Target domain '{to_domain}' does not exist. "
                f"Create it first with create_domain()."
            )

        # Count and park active tasks in source domain
        parked_count = self._park_active_tasks(from_domain)

        # Record the switch
        record = DomainSwitchRecord(
            from_domain=from_domain,
            to_domain=to_domain,
            parked_task_count=parked_count,
            reason=reason,
        )

        # Persist switch record to shared location
        self.yaml_store.ensure_dir("shared/domain-switches")
        self.yaml_store.write(
            f"shared/domain-switches/{record.id}.yaml", record,
        )

        logger.info(
            f"Switched from '{from_domain}' to '{to_domain}': "
            f"parked {parked_count} tasks. Reason: {reason}"
        )
        return record

    def list_domains(self) -> list[str]:
        """List all existing domain names."""
        instances_dir = self.yaml_store.base_dir / "instances"
        if not instances_dir.exists():
            return []
        return sorted(
            d.name for d in instances_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def get_domain_config(self, name: str) -> DomainConfig:
        """Load a domain's configuration.

        Raises:
            DomainError: If domain does not exist or config is missing.
        """
        config_path = f"instances/{name}/domain.yaml"
        try:
            raw = self.yaml_store.read_raw(config_path)
            return DomainConfig(**raw["domain"])
        except FileNotFoundError:
            raise DomainError(
                f"Domain '{name}' does not exist or has no domain.yaml"
            )

    def domain_exists(self, name: str) -> bool:
        """Check if a domain directory exists."""
        return (self.yaml_store.base_dir / "instances" / name).exists()

    # FM-P7-045-FIX: Maximum domain name length (NAME_MAX safe)
    MAX_DOMAIN_NAME_LENGTH = 64

    def _validate_domain_name(self, name: str) -> None:
        """Validate domain name against path traversal, invalid chars, and length."""
        if not name:
            raise DomainError("Domain name cannot be empty")
        # FM-P7-045-FIX: Length check prevents filesystem path limit issues
        if len(name) > self.MAX_DOMAIN_NAME_LENGTH:
            raise DomainError(
                f"Domain name '{name[:20]}...' too long ({len(name)} chars, "
                f"max {self.MAX_DOMAIN_NAME_LENGTH})"
            )
        if "/" in name or "\\" in name or ".." in name:
            raise DomainError(
                f"Invalid domain name '{name}': must not contain "
                f"path separators or '..'"
            )
        if name.startswith("."):
            raise DomainError(
                f"Invalid domain name '{name}': must not start with '.'"
            )
        # Only allow alphanumeric, hyphens, underscores
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
            raise DomainError(
                f"Invalid domain name '{name}': must start with alphanumeric "
                f"and contain only alphanumeric, hyphens, underscores"
            )

    def _park_active_tasks(self, domain: str) -> int:
        """Park all active tasks in a domain. Returns count of parked tasks.

        Reads tasks from instances/{domain}/state/tasks/active/ and moves
        them to instances/{domain}/state/tasks/parked/.

        FM-P7-046-FIX: Updates task status field before moving file.
        FM-P7-IMP-002-FIX: Pre-flight scan rejects ALL tasks if ANY is EXECUTING.
        FM-P7-IMP-009-FIX: Snapshot file list before iterating (no iterdir mutation).
        """
        active_dir = self.yaml_store.base_dir / f"instances/{domain}/state/tasks/active"
        parked_dir = self.yaml_store.base_dir / f"instances/{domain}/state/tasks/parked"

        if not active_dir.exists():
            return 0

        # FM-P7-IMP-009-FIX: Snapshot into list to avoid iterdir-during-mutation
        task_files = [
            f for f in active_dir.iterdir()
            if f.suffix in (".yaml", ".yml")
        ]
        if not task_files:
            return 0

        # FM-P7-IMP-002-FIX: Pre-flight scan — reject if ANY task is EXECUTING.
        # This prevents partial parking where some tasks move but then we hit
        # an executing task and raise, leaving the domain in an inconsistent state.
        for task_file in task_files:
            rel_path = f"instances/{domain}/state/tasks/active/{task_file.name}"
            task_data = self.yaml_store.read_raw(rel_path)
            # IFM-N53: fail-loud — task files must have a status field
            if task_data["status"] == "executing":
                raise DomainError(
                    f"Cannot park tasks in domain '{domain}': "
                    f"task {task_file.name} is currently EXECUTING. "
                    f"Wait for completion or cancel first."
                )

        # All tasks safe to park — proceed with mutations
        parked_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for task_file in task_files:
            # FM-P7-046-FIX: Update task status in YAML before moving
            rel_path = f"instances/{domain}/state/tasks/active/{task_file.name}"
            task_data = self.yaml_store.read_raw(rel_path)

            task_data["status"] = "parked"
            task_data["parked_at"] = datetime.now(timezone.utc).isoformat()
            task_data["parked_reason"] = f"domain_switch_from_{domain}"
            self.yaml_store.write_raw(rel_path, task_data)

            # Move to parked directory
            target = parked_dir / task_file.name
            task_file.rename(target)
            count += 1
            logger.info(f"Parked task {task_file.name} in domain '{domain}'")

        return count
