"""Bootstrap the Universal Agents Framework directory structure.
Spec reference: Part 8, Step 4-6, Step 10."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml


CONSTITUTION_TEXT = """\
# Constitution — Universal Agents Framework

## Preamble

This constitution defines the immutable axioms governing the Universal Agents Framework.
No agent, evolution process, or automated system may modify this document.
Changes require explicit human action with full audit trail.

## Axioms

### A1: Human Halt
The human operator can halt all framework operations at any time, with immediate effect.
No agent may delay, buffer, or ignore a halt command.
**Enforcement:** Every agent checks for halt signal before each action.

### A2: Human Veto
The human operator can veto any decision, including approved evolution proposals.
Vetoed actions are immediately reversed if already applied.
**Enforcement:** All non-trivial decisions include a veto window.

### A3: Constitutional Immutability
The framework must not modify its own constitution through any automated process.
This document (CONSTITUTION.md) is Ring 0 immutable.
**Enforcement:** ConstitutionGuard verifies SHA-256 hash at boot and before every evolution.

### A4: Complete Auditability
Every action, decision, and state change must be logged and traceable.
Logs are append-only and never deleted during normal operation.
**Enforcement:** AuditLogger dispatches to 8 JSONL streams.

### A5: Reversible Evolution
All evolution (framework changes) must be reversible via git rollback.
No destructive evolution is permitted. Every change preserves rollback capability.
**Enforcement:** Git-based evolution with merge-only branches.

### A6: Budget Hard Limits
Task token budgets are hard limits, not soft guidelines.
Exceeding a budget triggers immediate task parking, not silent continuation.
**Enforcement:** ResourceTracker enforces budget pressure levels.

### A7: Mandatory Review
Every task must pass through the REVIEWING state before completion.
No task may transition directly from EXECUTING to COMPLETE.
**Enforcement:** TaskLifecycle validates VALID_TRANSITIONS state machine.

### A8: Graceful Degradation on Resource Exhaustion
Resource exhaustion triggers graceful degradation (park tasks, reduce agents),
never silent failure or data corruption.
**Enforcement:** BudgetPressureLevel cascade (GREEN → YELLOW → ORANGE → RED).
"""

FRAMEWORK_YAML = {
    "framework": {
        "name": "universal-agents",
        "version": "0.1.0",
        "phase": "0",
        "active_domain": "meta",
        "max_concurrent_agents": 5,
        "topology_patterns": ["solo", "hierarchical_team"],
    }
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the Universal Agents Framework"
    )
    parser.add_argument(
        "--domain", default="meta",
        help="Domain name (default: meta)"
    )
    parser.add_argument(
        "--root", default=".",
        help="Framework root directory (default: current dir)"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    domain = args.domain

    print(f"Bootstrapping Universal Agents Framework at: {root}")
    print(f"Domain: {domain}")

    # Step 1: Scaffold directory structure
    from ..state.directory import DirectoryManager
    dm = DirectoryManager()
    created = dm.scaffold(root, domain)
    for item in created:
        print(f"  Created: {item}")

    # Step 2: Create CONSTITUTION.md
    constitution_path = root / "CONSTITUTION.md"
    if not constitution_path.exists():
        constitution_path.write_text(CONSTITUTION_TEXT, encoding="utf-8")
        print("  Created: CONSTITUTION.md")
    else:
        print("  Exists:  CONSTITUTION.md (not overwritten)")

    # Step 3: Compute and store constitution hash
    content = constitution_path.read_text(encoding="utf-8")
    constitution_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    hash_path = root / "core" / "constitution-hash.txt"
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path.write_text(constitution_hash, encoding="utf-8")
    print(f"  Constitution hash: {constitution_hash[:16]}...")

    # Step 4: Create framework.yaml
    framework_yaml_path = root / "framework.yaml"
    if not framework_yaml_path.exists():
        fw_config = dict(FRAMEWORK_YAML)
        fw_config["framework"]["active_domain"] = domain
        with open(framework_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(fw_config, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
        print("  Created: framework.yaml")
    else:
        print("  Exists:  framework.yaml (not overwritten)")

    # Step 5: Create sample role files (only if they don't exist)
    _create_sample_roles(root)

    # Step 6: Generate CLAUDE.md
    from ..state.yaml_store import YamlStore
    from ..claude_md.generator import ClaudeMdGenerator
    yaml_store = YamlStore(root)
    generator = ClaudeMdGenerator(yaml_store, root)
    claude_md_content = generator.generate(domain)
    claude_md_path = root / "CLAUDE.md"
    claude_md_path.write_text(claude_md_content, encoding="utf-8")
    print("  Generated: CLAUDE.md")

    print("\nBootstrap complete.")


def _create_sample_roles(root: Path) -> None:
    """Create sample capabilities.yaml, voice.yaml, and role compositions."""
    roles_dir = root / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)

    # capabilities.yaml
    cap_path = roles_dir / "capabilities.yaml"
    if not cap_path.exists():
        capabilities = {
            "code_generation": {
                "name": "code_generation",
                "description": "Write, modify, and debug code",
                "instruction_fragment": (
                    "You are skilled at writing clean, tested code. "
                    "Always include error handling."
                ),
                "model_preference": "sonnet",
            },
            "strategic_thinking": {
                "name": "strategic_thinking",
                "description": "High-level planning and task decomposition",
                "instruction_fragment": (
                    "Think strategically. Break complex tasks into manageable "
                    "subtasks. Consider dependencies and risks."
                ),
                "model_preference": "opus",
                "authority": True,
            },
            "quality_review": {
                "name": "quality_review",
                "description": "Thorough code and design review",
                "instruction_fragment": (
                    "Review thoroughly. Check for correctness, security, "
                    "performance, and adherence to requirements. "
                    "Provide specific, actionable feedback."
                ),
                "model_preference": "opus",
            },
            "research_analysis": {
                "name": "research_analysis",
                "description": "Deep research and knowledge synthesis",
                "instruction_fragment": (
                    "Research thoroughly. Synthesize information from multiple "
                    "sources. Identify gaps and connections."
                ),
                "model_preference": "opus",
            },
            "exploration": {
                "name": "exploration",
                "description": "Explore problem spaces and find novel approaches",
                "instruction_fragment": (
                    "Explore broadly. Look for non-obvious solutions and "
                    "unexpected connections. Question assumptions."
                ),
                "model_preference": "sonnet",
            },
        }
        with open(cap_path, "w", encoding="utf-8") as f:
            yaml.dump(capabilities, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
        print("  Created: roles/capabilities.yaml")

    # voice.yaml
    voice_path = roles_dir / "voice.yaml"
    if not voice_path.exists():
        voice_atoms = {
            "language_japanese": {
                "name": "language_japanese",
                "category": "language",
                "description": "Japanese language output",
                "instruction_fragment": "Respond in Japanese (\u65e5\u672c\u8a9e\u3067\u56de\u7b54\u3057\u3066\u304f\u3060\u3055\u3044)\u3002",
                "token_cost": "minimal",
            },
            "language_english": {
                "name": "language_english",
                "category": "language",
                "description": "English language output",
                "instruction_fragment": "Respond in English.",
                "token_cost": "minimal",
            },
            "tone_cautious": {
                "name": "tone_cautious",
                "category": "tone",
                "description": "Careful, measured responses",
                "instruction_fragment": (
                    "Be cautious and measured. Flag uncertainties explicitly. "
                    "Prefer safety over speed."
                ),
                "token_cost": "low",
            },
            "tone_assertive": {
                "name": "tone_assertive",
                "category": "tone",
                "description": "Confident, direct responses",
                "instruction_fragment": (
                    "Be direct and confident. State conclusions clearly. "
                    "Don't hedge unnecessarily."
                ),
                "token_cost": "low",
            },
            "style_technical": {
                "name": "style_technical",
                "category": "style",
                "description": "Technical, precise communication",
                "instruction_fragment": (
                    "Use precise technical language. Include specifics: "
                    "versions, file paths, function names."
                ),
                "token_cost": "low",
            },
            "style_concise": {
                "name": "style_concise",
                "category": "style",
                "description": "Brief, efficient communication",
                "instruction_fragment": (
                    "Be concise. Omit unnecessary explanation. "
                    "Prefer bullet points over paragraphs."
                ),
                "token_cost": "minimal",
                "output_token_impact": "reduces",
            },
        }
        with open(voice_path, "w", encoding="utf-8") as f:
            yaml.dump(voice_atoms, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
        print("  Created: roles/voice.yaml")

    # Role compositions
    compositions_dir = roles_dir / "compositions"
    compositions_dir.mkdir(parents=True, exist_ok=True)

    compositions = {
        "orchestrator": {
            "name": "orchestrator",
            "description": "Strategic coordination and task decomposition",
            "capabilities": ["strategic_thinking"],
            "model": "opus",
            "thinking": {"value": True},
            "behavioral_descriptors": {
                "reasoning_style": "strategic",
                "risk_tolerance": "low",
                "exploration_vs_exploitation": 0.3,
            },
            "voice": {
                "language": "language_japanese",
                "tone": "tone_cautious",
                "style": "style_technical",
                "formality": 0.8,
                "verbosity": 0.4,
            },
            "authority_level": 2,
            "forbidden": [
                "Never execute code directly \u2014 delegate to implementer",
                "Never skip review phase",
            ],
        },
        "implementer": {
            "name": "implementer",
            "description": "Efficient task execution and code generation",
            "capabilities": ["code_generation"],
            "model": "sonnet",
            "thinking": {"value": True},
            "behavioral_descriptors": {
                "reasoning_style": "analytical",
                "risk_tolerance": "moderate",
                "exploration_vs_exploitation": 0.7,
            },
            "voice": {
                "language": "language_japanese",
                "tone": "tone_assertive",
                "style": "style_technical",
                "formality": 0.6,
                "verbosity": 0.5,
            },
            "authority_level": 0,
            "forbidden": [
                "Never modify CONSTITUTION.md",
                "Never approve evolution proposals",
            ],
        },
        "reviewer": {
            "name": "reviewer",
            "description": "Thorough quality verification",
            "capabilities": ["quality_review"],
            "model": "opus",
            "thinking": {"value": "extended"},
            "behavioral_descriptors": {
                "reasoning_style": "analytical",
                "risk_tolerance": "very_low",
                "exploration_vs_exploitation": 0.2,
            },
            "voice": {
                "language": "language_japanese",
                "tone": "tone_cautious",
                "style": "style_technical",
                "formality": 0.8,
                "verbosity": 0.6,
            },
            "authority_level": 1,
            "review_mandate": {
                "required_checks": [
                    "correctness",
                    "security",
                    "performance",
                    "adherence_to_requirements",
                ],
            },
            "forbidden": [
                "Never approve your own work",
            ],
        },
        "researcher": {
            "name": "researcher",
            "description": "Deep research and analysis",
            "capabilities": ["research_analysis"],
            "model": "opus",
            "thinking": {"value": "extended"},
            "behavioral_descriptors": {
                "reasoning_style": "divergent",
                "risk_tolerance": "moderate",
                "exploration_vs_exploitation": 0.5,
            },
            "voice": {
                "language": "language_japanese",
                "tone": "tone_cautious",
                "style": "style_technical",
                "formality": 0.7,
                "verbosity": 0.7,
            },
            "authority_level": 0,
            "forbidden": [
                "Never modify CONSTITUTION.md",
            ],
        },
        "scout": {
            "name": "scout",
            "description": "Exploration and anomaly detection",
            "capabilities": ["exploration"],
            "model": "sonnet",
            "thinking": {"value": True},
            "behavioral_descriptors": {
                "reasoning_style": "lateral",
                "risk_tolerance": "high",
                "exploration_vs_exploitation": 0.9,
            },
            "voice": {
                "language": "language_japanese",
                "tone": "tone_assertive",
                "style": "style_concise",
                "formality": 0.4,
                "verbosity": 0.3,
            },
            "authority_level": 0,
            "scout_config": {
                "max_depth": 3,
                "breadth_first": True,
            },
            "forbidden": [
                "Never modify CONSTITUTION.md",
            ],
        },
    }

    for name, composition in compositions.items():
        comp_path = compositions_dir / f"{name}.yaml"
        if not comp_path.exists():
            with open(comp_path, "w", encoding="utf-8") as f:
                yaml.dump(composition, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
            print(f"  Created: roles/compositions/{name}.yaml")


if __name__ == "__main__":
    main()
