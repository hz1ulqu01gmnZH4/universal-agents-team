"""Compose prompt and output spawn descriptor for an agent.
Spec reference: Part 6.1 (Agent Spawn), Part 4.6 (AgentSpawner)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from ..state.yaml_store import YamlStore


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compose agent prompt and output spawn descriptor"
    )
    parser.add_argument(
        "--role", required=True,
        help="Role name (e.g. orchestrator, implementer, reviewer, researcher, scout)"
    )
    parser.add_argument(
        "--task-id", required=True,
        help="Task ID to assign to the agent"
    )
    parser.add_argument(
        "--domain", default="meta",
        help="Domain name (default: meta)"
    )
    parser.add_argument(
        "--root", default=".",
        help="Framework root directory (default: current dir)"
    )
    parser.add_argument(
        "--context", default="",
        help="Additional context to include in the prompt"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    yaml_store = YamlStore(root)

    # Load role composition
    role_path = f"roles/compositions/{args.role}.yaml"
    if not yaml_store.exists(role_path):
        print(f"ERROR: Role composition not found: {role_path}", file=sys.stderr)
        sys.exit(1)
    role_data = yaml_store.read_raw(role_path)

    # Load capabilities
    capabilities = yaml_store.read_raw("roles/capabilities.yaml")

    # Load voice atoms
    voice_atoms = yaml_store.read_raw("roles/voice.yaml")

    # Load task
    task_data = None
    for subdir in ["active", "parked", "completed"]:
        task_path = f"instances/{args.domain}/state/tasks/{subdir}/{args.task_id}.yaml"
        if yaml_store.exists(task_path):
            task_data = yaml_store.read_raw(task_path)
            break

    if task_data is None:
        print(f"ERROR: Task not found: {args.task_id}", file=sys.stderr)
        sys.exit(1)

    # Build prompt sections
    prompt_parts: list[str] = []

    # Ring 0: Constitution reference
    constitution_path = root / "CONSTITUTION.md"
    if constitution_path.exists():
        prompt_parts.append(
            "## Constitutional Axioms (IMMUTABLE)\n\n"
            "- A1: Human can halt all operations at any time\n"
            "- A2: Human can veto any decision\n"
            "- A3: Framework must not modify its own constitution\n"
            "- A4: Every action must be logged and traceable\n"
            "- A5: Evolution must be reversible\n"
            "- A6: Task budgets are hard limits\n"
            "- A7: Every task must be reviewed before completion\n"
            "- A8: Resource exhaustion triggers graceful degradation\n"
        )

    # Ring 2: Role capabilities and voice
    cap_lines: list[str] = []
    for cap_name in role_data.get("capabilities", []):
        if cap_name in capabilities:
            cap_lines.append(capabilities[cap_name].get("instruction_fragment", ""))
    if cap_lines:
        prompt_parts.append("## Capabilities\n\n" + "\n".join(cap_lines))

    # Voice instructions
    voice_config = role_data.get("voice", {})
    voice_instructions: list[str] = []
    for key in ["language", "tone", "style"]:
        atom_name = voice_config.get(key)
        if atom_name and atom_name in voice_atoms:
            voice_instructions.append(
                voice_atoms[atom_name].get("instruction_fragment", "")
            )
    if voice_instructions:
        prompt_parts.append("## Voice\n\n" + "\n".join(voice_instructions))

    # Behavioral descriptors
    bd = role_data.get("behavioral_descriptors", {})
    if bd:
        prompt_parts.append(
            "## Behavioral Profile\n\n"
            f"Reasoning style: {bd.get('reasoning_style', 'analytical')}\n"
            f"Risk tolerance: {bd.get('risk_tolerance', 'moderate')}\n"
            f"Exploration vs exploitation: {bd.get('exploration_vs_exploitation', 0.5)}\n"
        )

    # Forbidden actions
    forbidden = role_data.get("forbidden", [])
    if forbidden:
        prompt_parts.append(
            "## Forbidden\n\n" + "\n".join(f"- {f}" for f in forbidden)
        )

    # Ring 3: Task context
    prompt_parts.append(
        f"## Current Task: {task_data.get('title', 'Unknown')}\n\n"
        f"Status: {task_data.get('status', 'unknown')}\n"
        f"Priority: {task_data.get('priority', 'medium')}\n"
        f"Description: {task_data.get('description', '')}\n"
    )

    if args.context:
        prompt_parts.append(f"## Additional Context\n\n{args.context}")

    composed_prompt = "\n\n".join(prompt_parts)

    # Determine model
    model = role_data.get("model", "sonnet")

    # Output spawn descriptor as JSON
    descriptor = {
        "role": args.role,
        "task_id": args.task_id,
        "model": model,
        "domain": args.domain,
        "prompt": composed_prompt,
        "subagent_type": "general-purpose",
    }

    print(json.dumps(descriptor, indent=2))


if __name__ == "__main__":
    main()
