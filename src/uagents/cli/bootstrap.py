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

    # Step 5.5: Create engine configuration files
    _create_engine_configs(root)

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


def _create_engine_configs(root: Path) -> None:
    """Create engine configuration files from design-doc defaults.

    Each file is only created if it doesn't already exist (D2 invariant).
    Config schemas match the IFM-N53 fail-loud access patterns in each engine.
    """
    core_dir = root / "core"
    core_dir.mkdir(parents=True, exist_ok=True)

    configs: dict[str, dict] = {
        "resource-awareness.yaml": _resource_awareness_config(),
        "environment-awareness.yaml": _environment_awareness_config(),
        "canary-expectations.yaml": _canary_expectations_config(),
        "skill-system.yaml": _skill_system_config(),
        "context-pressure.yaml": _context_pressure_config(),
        "tool-taxonomy.yaml": _tool_taxonomy_config(),
        "evolution.yaml": _evolution_config(),
        "self-governance.yaml": _self_governance_config(),
        "creativity.yaml": _creativity_config(),
        "scout.yaml": _scout_config(),
    }

    for filename, config_data in configs.items():
        path = core_dir / filename
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
            print(f"  Created: core/{filename}")


def _resource_awareness_config() -> dict:
    return {
        "resource_awareness": {
            "claude_max_plan": "max5",
            "cost_caps": {"daily": 50.0, "weekly": 200.0},
            "rate_limits": {
                "rpm_estimate": 60,
                "itpm_estimate": 80000,
                "otpm_estimate": 16000,
            },
            "cold_seeds": {
                "simple_fix": 3000,
                "feature_small": 8000,
                "feature_medium": 15000,
                "research": 20000,
                "review": 2000,
            },
            "rolling_average_threshold": 10,
            "safety_margin_novel": 1.5,
            "budget_reserve_pct": 0.20,
        }
    }


def _environment_awareness_config() -> dict:
    return {
        "environment_awareness": {
            "canary_suite": {
                "max_total_tokens": 5000,
                "max_runtime_seconds": 120,
                "per_task_token_cap": 1200,
                "pass_score": 0.7,
                "skip_if_recent_hours": 5,
            },
            "drift_detection": {
                "threshold": 0.15,
                "history_size": 10,
                "baseline_window": 5,
                "per_dimension_alert": 0.10,
                "periodic_check_interval": 50,
            },
            "revalidation": {
                "budget_cap_pct": 0.10,
                "min_budget_tokens": 2000,
                "improved_threshold": 0.05,
                "degraded_minor_threshold": 0.05,
                "degraded_major_threshold": 0.15,
                "broken_threshold": 0.30,
            },
            "performance_monitoring": {
                "skill_window_size": 20,
                "skill_alert_drop_pp": 10,
                "tool_alert_drop_pp": 15,
                "tool_quarantine_threshold": 0.5,
                "trace_retention_tasks": 100,
            },
            "self_benchmarking": {
                "full_suite_interval": 100,
                "quick_suite_interval": 20,
                "quick_suite_tasks": 3,
            },
            "version_tracking": {
                "check_on_session_start": True,
                "version_command": "claude --version",
                "version_timeout_seconds": 5,
            },
        }
    }


def _canary_expectations_config() -> dict:
    return {
        "canary_expectations": {
            "reasoning": {
                "prompt": (
                    "Solve this logic puzzle step by step:\n"
                    "There are 3 boxes. Box A contains only apples. Box B contains only bananas.\n"
                    "Box C contains a mix of apples and bananas. All labels are WRONG.\n"
                    "You pick one fruit from Box C and it is an apple.\n"
                    "What does each box actually contain?"
                ),
                "expected_answer": "Box C has apples, Box A has bananas, Box B has the mix",
                "scoring": {
                    "method": "keyword_match",
                    "required_keywords": ["C", "apples", "A", "bananas", "B", "mix"],
                    "min_keywords": 5,
                },
            },
            "instruction_following": {
                "prompt": (
                    "Follow these instructions exactly:\n"
                    '1. Start your response with the word "RESPONSE"\n'
                    "2. List exactly 3 colors, one per line, numbered 1-3\n"
                    "3. Each color must be a single word\n"
                    '4. End your response with the word "DONE"\n'
                    "5. Do not include any other text"
                ),
                "expected_answer": "RESPONSE\\n1. <color>\\n2. <color>\\n3. <color>\\nDONE",
                "scoring": {
                    "method": "constraint_check",
                    "constraints": [
                        {"name": "starts_with_response", "checker": "starts_with", "arg": "RESPONSE"},
                        {"name": "ends_with_done", "checker": "ends_with", "arg": "DONE"},
                        {"name": "has_three_numbered", "checker": "regex_count_eq",
                         "arg": {"pattern": "^\\d+\\.", "count": 3}},
                        {"name": "no_extra_text", "checker": "line_count_le", "arg": 6},
                    ],
                },
            },
            "code_generation": {
                "prompt": (
                    "Write a Python function called `fibonacci` that takes an integer n\n"
                    "and returns the nth Fibonacci number (0-indexed, so fibonacci(0)=0,\n"
                    "fibonacci(1)=1, fibonacci(6)=8). Use iteration, not recursion.\n"
                    "Return ONLY the function, no explanation."
                ),
                "expected_answer": "def fibonacci(n):",
                "scoring": {
                    "method": "code_validation",
                    "test_cases": [
                        {"input": 0, "expected": 0},
                        {"input": 1, "expected": 1},
                        {"input": 6, "expected": 8},
                    ],
                },
            },
        }
    }


def _skill_system_config() -> dict:
    return {
        "skill_system": {
            "extraction": {
                "min_review_confidence": 0.7,
                "min_trajectory_length": 200,
                "max_trajectory_snippet": 2000,
                "extraction_token_budget": 3000,
                "qualifying_verdicts": ["pass", "pass_with_notes"],
                "extraction_cooldown_tasks": 5,
            },
            "validation": {
                "total_token_budget": 15000,
                "stage_budgets": {
                    "syntax": 0,
                    "execution": 6000,
                    "comparison": 6000,
                    "review": 3000,
                },
                "min_test_tasks": 2,
                "min_improvement_pp": 5,
                "comparison_runs": 2,
                "review_approvers": ["human", "authority_agent"],
            },
            "library": {
                "capacity": {"per_domain": 50, "per_level": 20},
                "skills_dir": "state/skills",
                "candidates_dir": "state/skills/candidates",
                "maintenance_dir": "state/skills/maintenance-history",
            },
            "maintenance": {
                "period_tasks": 20,
                "prune_success_rate": 0.5,
                "prune_unused_tasks": 30,
                "merge_similarity_threshold": 0.85,
                "max_maintenance_history": 100,
                "scoring_weights": {
                    "usage_frequency": 0.4,
                    "success_rate": 0.4,
                    "freshness": 0.2,
                },
            },
            "ring_transitions": {
                "ring_3_to_2": {
                    "min_improvement_pp": 5,
                    "min_usage_count": 5,
                    "min_success_rate": 0.7,
                    "require_full_validation": True,
                },
                "ring_2_to_3": {
                    "on_revalidation_failure": True,
                    "on_success_rate_below": 0.5,
                },
                "ring_0_immutable": True,
                "ring_1_human_only": True,
            },
            "security": {
                "injection_position": "after_constitution",
                "ring_3_sandboxed": True,
                "max_instruction_length": 1500,
                "forbidden_patterns": [
                    "ignore previous instructions",
                    "ignore all instructions",
                    "disregard",
                    "override constitution",
                    "bypass safety",
                    "system prompt",
                ],
            },
        }
    }


def _context_pressure_config() -> dict:
    return {
        "context_pressure": {
            "thresholds": {
                "pressure": 0.60,
                "critical": 0.80,
                "overflow": 0.95,
            },
            "ring_0": {
                "reserved_tokens": 2000,
                "min_productive_tokens": 1000,
                "enforcement": "hard_fail",
            },
            "compression_cascade": {
                "stage_1_history": {
                    "trigger": 0.60,
                    "action": "Summarize oldest conversation turns, keep last 3 detailed",
                    "history_keep_recent": 3,
                },
                "stage_2_tool_reduction": {
                    "trigger": 0.70,
                    "action": "Reduce loaded tools to top-3 most relevant (Ring 0-1 exempt)",
                    "tool_reduction_target": 3,
                },
                "stage_3_task_pruning": {
                    "trigger": 0.80,
                    "action": "SWE-Pruner-style task-aware context pruning (23-54% reduction)",
                },
                "stage_4_system_compress": {
                    "trigger": 0.90,
                    "action": "Reduce system prompt to Ring 0 instructions only",
                },
                "stage_5_emergency": {
                    "trigger": 0.95,
                    "action": "Summarize all non-Ring-0 context. HARD_FAIL if still insufficient.",
                },
            },
            "placement": {
                "enabled": True,
                "rules": [
                    {"position": "beginning", "content": "System instructions, current task goal, safety constraints"},
                    {"position": "end", "content": "Latest results, next action, tool definitions"},
                    {"position": "middle", "content": "Historical context, reference material (least critical)"},
                ],
            },
            "budget_allocation": {
                "system_instructions_pct": 0.10,
                "active_tools_pct": 0.15,
                "current_task_pct": 0.40,
                "working_memory_pct": 0.25,
                "reserve_pct": 0.10,
            },
        }
    }


def _tool_taxonomy_config() -> dict:
    return {
        "tool_taxonomy": {
            "loading": {
                "max_tools_per_step": 5,
                "max_mcp_servers": 3,
                "mcp_idle_timeout_minutes": 10,
                "tool_token_budget_pct": 0.15,
                "avg_tokens_per_tool": 450,
                "high_token_threshold": 5000,
            },
            "categories": {
                "core": {
                    "description": "Always loaded — file ops, git, messaging",
                    "ring": 1,
                    "always_loaded": True,
                    "tools": [
                        {
                            "name": "constitution_check",
                            "description": "Verify constitution integrity",
                            "instruction_fragment": "Use constitution_check to verify Ring 0 compliance.",
                            "tags": ["constitution", "safety"],
                            "token_cost": 300,
                            "ring": 0,
                        },
                        {
                            "name": "file_read",
                            "description": "Read file contents",
                            "instruction_fragment": "Use file_read to read files.",
                            "tags": ["filesystem", "read"],
                            "token_cost": 200,
                        },
                        {
                            "name": "file_write",
                            "description": "Write file contents",
                            "instruction_fragment": "Use file_write to create or overwrite files.",
                            "tags": ["filesystem", "write"],
                            "token_cost": 200,
                        },
                        {
                            "name": "git_ops",
                            "description": "Git version control operations",
                            "instruction_fragment": "Use git_ops for commits, diffs, and branch management.",
                            "tags": ["git", "version_control"],
                            "token_cost": 300,
                        },
                        {
                            "name": "task_update",
                            "description": "Update task status",
                            "instruction_fragment": "Use task_update to change task status or add notes.",
                            "tags": ["task", "lifecycle"],
                            "token_cost": 250,
                        },
                    ],
                },
                "domain": {
                    "description": "Loaded when domain is active",
                    "ring": 2,
                    "always_loaded": False,
                    "tools": [],
                },
                "task": {
                    "description": "Loaded per-task based on task type",
                    "ring": 2,
                    "always_loaded": False,
                    "tools": [
                        {
                            "name": "code_search",
                            "description": "Search codebase for patterns",
                            "instruction_fragment": "Use code_search to find code patterns across the codebase.",
                            "tags": ["code", "search", "grep"],
                            "token_cost": 400,
                        },
                        {
                            "name": "test_runner",
                            "description": "Run test suites",
                            "instruction_fragment": "Use test_runner to execute tests and report results.",
                            "tags": ["testing", "pytest"],
                            "token_cost": 350,
                        },
                    ],
                },
                "specialist": {
                    "description": "Loaded per-step via semantic retrieval",
                    "ring": 3,
                    "always_loaded": False,
                    "tools": [],
                },
            },
            "mcp_servers": {
                "universal-memory": {
                    "ring": 1,
                    "auto_start": True,
                    "idle_exempt": True,
                },
            },
            "task_type_hints": {
                "simple_fix": ["code_search", "test_runner"],
                "feature_small": ["code_search", "test_runner", "file_read"],
                "feature_medium": ["code_search", "test_runner"],
                "research": ["memory_recall"],
                "review": ["code_search"],
            },
            "security": {
                "vulnerability_patterns": [
                    {"pattern": "ignore previous instructions", "severity": "critical"},
                    {"pattern": "disregard safety", "severity": "critical"},
                    {"pattern": "bypass constitution", "severity": "critical"},
                    {"pattern": "eval(", "severity": "high"},
                    {"pattern": "exec(", "severity": "high"},
                    {"pattern": "subprocess", "severity": "high"},
                    {"pattern": "__import__", "severity": "high"},
                ],
                "quarantine_on_critical": True,
                "quarantine_on_high": True,
            },
        }
    }


def _evolution_config() -> dict:
    return {
        "evolution": {
            "tiers": {
                "tier_3_auto_approve": True,
                "tier_2_requires_quorum": True,
                "tier_1_requires_human": True,
                "tier_0_immutable": True,
            },
            "lifecycle": {
                "max_proposals_per_cycle": 5,
                "max_concurrent_candidates": 1,
                "proposal_timeout_minutes": 30,
                "cooldown_between_evolutions": 3,
            },
            "evaluation": {
                "min_capability": 0.5,
                "min_consistency": 0.6,
                "min_robustness": 0.4,
                "min_predictability": 0.3,
                "min_safety": 0.9,
                "min_diversity": 0.4,
                "promote_threshold": 0.6,
                "hold_threshold": 0.5,
                "weights": {
                    "capability": 0.25,
                    "consistency": 0.20,
                    "robustness": 0.15,
                    "predictability": 0.10,
                    "safety": 0.20,
                    "diversity": 0.10,
                },
            },
            "dual_copy": {
                "fork_includes": [
                    "roles/compositions/*.yaml",
                    "core/topology.yaml",
                    "core/coordination.yaml",
                    "core/resource-awareness.yaml",
                ],
                "fork_excludes": [
                    "CONSTITUTION.md",
                    "core/constitution-hash.txt",
                    "logs/**",
                    "state/tasks/**",
                    "state/agents/**",
                ],
                "candidates_dir": "state/evolution/candidates",
            },
            "archive": {
                "task_types": ["research", "engineering", "creative", "meta"],
                "complexities": ["simple", "moderate", "complex", "extreme"],
                "novelty_bonus": 0.1,
                "min_tasks_for_cell": 3,
                "archive_path": "state/evolution/archive.yaml",
            },
            "objective_anchoring": {
                "check_every_n_cycles": 10,
                "min_alignment_score": 0.8,
                "alignment_check_agent": "",
            },
            "safety": {
                "max_file_modifications_per_proposal": 3,
                "max_diff_lines": 200,
                "forbidden_path_patterns": [
                    "CONSTITUTION.md",
                    "constitution-hash",
                    "core/evolution.yaml",
                    ".claude/",
                ],
                "allowed_extensions": [".yaml", ".yml", ".md"],
                "budget_change_cap_pct": 30,
            },
            "gap_monitoring": {
                "fp_tighten_threshold": 0.15,
                "fn_loosen_threshold": 0.15,
                "threshold_step": 0.05,
                "min_promote_threshold": 0.4,
                "max_promote_threshold": 0.9,
                "min_sample_size": 10,
            },
            "population": {
                "default_size": 3,
                "max_size": 5,
                "tournament_rounds": 1,
                "diversity_seed_from_archive": True,
            },
        }
    }


def _self_governance_config() -> dict:
    return {
        "self_governance": {
            "quorum": {
                "minimum_voters": 3,
                "threshold": 0.67,
                "min_tasks_for_voter": 10,
                "max_voters_per_lineage": 1,
                "scout_required": True,
                "vote_timeout_minutes": 30,
                "sealed_votes": True,
            },
            "objective_anchoring": {
                "check_every_n_cycles": 10,
                "min_alignment_score": 0.8,
                "method": "evolution_success_rate",
                "recent_window": 10,
                "halt_on_failure": True,
            },
            "risk_scorecard": {
                "dimensions": {
                    "operational": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "evolutionary": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "diversity": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "knowledge": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "resource": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "governance": {
                        "weight": 2.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "alignment": {
                        "weight": 2.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "calibration": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "environment": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                    "complexity": {
                        "weight": 1.0,
                        "healthy_threshold": 0.3,
                        "warning_threshold": 0.5,
                        "critical_threshold": 0.7,
                    },
                },
                "aggregate_thresholds": {
                    "healthy": 0.3,
                    "warning": 0.5,
                    "critical": 0.7,
                },
            },
            "alignment_verification": {
                "check_every_n_tasks": 20,
                "check_after_tier2_evolution": True,
                "checks": {
                    "behavioral_consistency": {
                        "enabled": True,
                        "min_confidence": 0.7,
                    },
                    "capability_elicitation": {
                        "enabled": True,
                        "min_confidence": 0.6,
                    },
                    "cross_agent_monitoring": {
                        "enabled": True,
                        "min_confidence": 0.7,
                    },
                    "red_team": {
                        "enabled": False,
                        "min_confidence": 0.5,
                    },
                },
            },
            "human_decision_queue": {
                "storage_path": "state/governance/pending_human_decisions.yaml",
                "max_pending": 20,
            },
        }
    }


def _creativity_config() -> dict:
    return {
        "creativity_engine": {
            "creative_protocol": {
                "min_agents": 3,
                "max_agents": 5,
                "default_agents": 3,
                "phases": {
                    "diverge": {"description": "Persona-conditioned agents brainstorm independently"},
                    "cross_pollinate": {"description": "Agents share outputs via blind review"},
                    "synthesize": {"description": "Orchestrator integrates best ideas"},
                    "evaluate": {
                        "criteria": {
                            "novelty": "Genuinely new, not a reformulation?",
                            "quality": "Actually solves the problem?",
                            "diversity": "Differs from other solutions found?",
                            "feasibility": "Can it be implemented?",
                        }
                    },
                },
            },
            "persona_assignment": {
                "method": "Select from voice atoms with creativity_mode: true",
                "constraint": "No two agents may share a persona atom",
                "tone_variation": "Each creative agent gets a unique tone atom",
                "temperature_offsets": [0.0, 0.1, -0.1, 0.2, -0.2],
            },
            "anti_stagnation": {
                "persona_rotation": {"enabled": True},
                "entropy_injection": {"enabled": True, "entropy_threshold": 0.3},
                "adversarial_agent": {
                    "persona": "persona_inverter",
                    "tone": "tone_assertive",
                },
            },
            "activation": {
                "triggers": [
                    "stagnation_detected",
                    "task_tagged_novel",
                    "conventional_approach_failed",
                    "human_requested",
                    "evolution_needs_novel_solution",
                ],
                "topology": "debate",
                "srd_floor_trigger": 0.4,
                "consecutive_stagnation_threshold": 2,
            },
            "metrics": {
                "guilford_tracking": True,
                "originality_method": "cosine_distance_from_corpus",
                "flexibility_method": "category_count",
                "history_size": 50,
            },
        }
    }


def _scout_config() -> dict:
    return {
        "scout": {
            "max_pending_targets": 5,
            "max_active_scouts": 1,
            "target_expiry_hours": 48,
            "archive_gap_priority": 0.3,
            "stagnation_priority": 0.7,
            "diversity_floor_priority": 0.6,
        }
    }


if __name__ == "__main__":
    main()

