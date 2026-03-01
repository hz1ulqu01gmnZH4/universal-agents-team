"""Ring-ordered prompt assembly engine.
Spec reference: Section 21 (Context Engineering Pipeline),
Section 4.6 (Voice System), Section 20.5 (Compression Cascade).

Phase 1.5: Budget injection (FM-21) and cache-aware prefix (FM-20).
"""
from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.base import FrameworkModel
from ..models.capability import CapabilityAtom
from ..models.constitution import Constitution
from ..models.context import (
    CompressionStage,
    ContextBudgetAllocation,
    ContextSnapshot,
)
from ..models.domain import DomainConfig, VoiceDefaults
from ..models.protection import ContextPressureLevel
from ..models.resource import TokenBudget
from ..models.role import RoleComposition
from ..models.task import Task
from ..models.voice import VoiceAtom, VoiceProfile
from ..state.yaml_store import YamlStore

if TYPE_CHECKING:
    from .cache_manager import CacheManager


class PromptRing(IntEnum):
    """Injection order matches protection ring hierarchy."""

    RING_0 = 0  # Constitution, safety, self-monitor — NEVER compressed
    RING_1 = 1  # Infrastructure, coordination, resource awareness
    RING_2 = 2  # Role composition: behavioral + voice + capability fragments
    RING_3 = 3  # Skills, task context, tools, working memory


class PromptSection(FrameworkModel):
    """A discrete section of the composed prompt."""

    ring: PromptRing
    name: str
    content: str
    token_estimate: int
    compressible: bool  # Ring 0 sections = False, all others = True
    priority: float     # 0.0 = drop first, 1.0 = drop last (within ring)
    is_cached: bool = False  # Phase 1.5: marks section as part of cached prefix


class ComposedPrompt(FrameworkModel):
    """The fully assembled agent prompt with metadata."""

    sections: list[PromptSection]
    total_tokens: int
    compression_stage: CompressionStage
    voice_profile: VoiceProfile
    tools_loaded: list[str]
    dropped_sections: list[str]  # Names of sections removed by compression


# Token estimation: 3.5 chars/token for English (cold start seed)
# Calibrated against /usage output after 10+ samples (rolling average)
CHARS_PER_TOKEN_DEFAULT = 3.5


def estimate_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN_DEFAULT) -> int:
    """Estimate token count from text length.
    Primary method: parse /usage output (see ResourceTracker).
    Fallback: character-ratio estimation."""
    return max(1, int(len(text) / chars_per_token))


class PromptComposer:
    """Assembles agent prompts from framework state.

    Composition pipeline:
    1. Build Ring 0: constitution axioms, safety constraints
    2. Build Ring 1: infrastructure instructions, coordination protocol
    3. Build Ring 2: role composition (capabilities + voice + behavioral)
    4. Build Ring 3: skills, task context, selected tools
    5. Apply context budget allocation (10/15/40/25/10%)
    6. Apply compression cascade if over budget
    7. Apply edge placement (critical info at beginning/end)
    8. Return assembled prompt with metadata
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        constitution_path: Path,
    ):
        self.yaml_store = yaml_store
        self.constitution_path = constitution_path

    def compose(
        self,
        role: RoleComposition,
        task: Task,
        domain: DomainConfig,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
        max_tokens: int = 200_000,
        allocation: ContextBudgetAllocation | None = None,
        budget_summary: dict | None = None,
        cache_manager: CacheManager | None = None,
    ) -> ComposedPrompt:
        """Full prompt composition pipeline.

        Phase 1.5 additions:
        - budget_summary: injected into Ring 1 via _build_ring_1_resource_awareness()
        - cache_manager: marks Ring 0/1 sections as cached for token accounting
        """
        if allocation is None:
            allocation = ContextBudgetAllocation()

        # 1. Build all ring sections
        sections: list[PromptSection] = []
        ring_0_sections = self._build_ring_0()
        sections.extend(ring_0_sections)
        ring_1_sections = self._build_ring_1(domain)
        # FM-21: Inject budget summary into Ring 1
        if budget_summary is not None:
            ring_1_sections.append(self._build_ring_1_resource_awareness(budget_summary))
        sections.extend(ring_1_sections)
        sections.extend(self._build_ring_2(role, capabilities, voice_atoms,
                                            domain.voice_defaults))
        sections.extend(self._build_ring_3(task))

        # FM-20: Cache-aware prefix marking
        if cache_manager is not None:
            ring_0_content = "\n".join(s.content for s in ring_0_sections)
            ring_1_content = "\n".join(s.content for s in ring_1_sections)
            cache_manager.get_shared_prefix(ring_0_content, ring_1_content)
            for section in sections:
                if section.ring in (PromptRing.RING_0, PromptRing.RING_1):
                    section.is_cached = True

        # 2. Calculate totals
        total = sum(s.token_estimate for s in sections)

        # 3. Determine compression stage
        utilization = total / max_tokens if max_tokens > 0 else 1.0
        stage = self._determine_compression_stage(utilization)

        # 4. Apply compression if needed
        dropped: list[str] = []
        if stage > CompressionStage.NONE:
            sections, dropped = self._apply_compression(sections, stage)

        # 5. Apply edge placement (lost-in-the-middle mitigation)
        sections = self._apply_edge_placement(sections)

        final_total = sum(s.token_estimate for s in sections)

        # Resolve voice profile: role.voice > domain defaults
        voice_profile = role.voice
        if voice_profile is None:
            voice_profile = VoiceProfile(
                language=domain.voice_defaults.language,
                tone=domain.voice_defaults.tone,
                style=domain.voice_defaults.style,
            )

        return ComposedPrompt(
            sections=sections,
            total_tokens=final_total,
            compression_stage=stage,
            voice_profile=voice_profile,
            tools_loaded=[],  # Populated by tool loader
            dropped_sections=dropped,
        )

    def _build_ring_0(self) -> list[PromptSection]:
        """Constitution axioms and safety constraints. NEVER compressed."""
        content = self.constitution_path.read_text(encoding="utf-8")
        return [
            PromptSection(
                ring=PromptRing.RING_0,
                name="constitution",
                content=f"## Constitutional Axioms (IMMUTABLE)\n\n{content}",
                token_estimate=estimate_tokens(content),
                compressible=False,
                priority=1.0,
            )
        ]

    def _build_ring_1(self, domain: DomainConfig) -> list[PromptSection]:
        """Infrastructure: coordination protocol, resource awareness."""
        charter_section = (
            f"## Domain: {domain.name}\n"
            f"Max concurrent agents: {domain.max_concurrent_agents}\n"
            f"Topology patterns: {', '.join(domain.topology_patterns)}\n"
        )
        return [
            PromptSection(
                ring=PromptRing.RING_1,
                name="domain_context",
                content=charter_section,
                token_estimate=estimate_tokens(charter_section),
                compressible=True,
                priority=0.8,
            )
        ]

    def _build_ring_1_resource_awareness(self, budget_summary: dict) -> PromptSection:
        """Inject resource awareness into Ring 1 (FM-21).

        BATS-style continuous budget visibility for executing agents.
        """
        content = (
            "## Resource Budget\n"
            f"Window: {budget_summary['window_remaining_tokens']:,} tokens remaining "
            f"({budget_summary['window_utilization_pct']}% used)\n"
            f"Pressure: {budget_summary['window_pressure']}\n"
            f"Weekly: {budget_summary['weekly_remaining_tokens']:,} tokens remaining "
            f"({budget_summary['weekly_utilization_pct']}% used)\n"
        )

        pressure = budget_summary["window_pressure"]
        if pressure == "yellow":
            content += "\nBUDGET GUIDANCE: Compress context, reduce tool calls, prefer cheaper operations.\n"
        elif pressure == "orange":
            content += "\nBUDGET WARNING: Critical-only tasks. Aggressive compression. Single-agent mode.\n"
        elif pressure == "red":
            content += "\nBUDGET EMERGENCY: Complete active task only. Park everything else. Alert human.\n"

        return PromptSection(
            ring=PromptRing.RING_1,
            name="resource_awareness",
            content=content,
            token_estimate=estimate_tokens(content),
            compressible=True,
            priority=0.9,
        )

    def _build_ring_2(
        self,
        role: RoleComposition,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
        domain_voice: VoiceDefaults | None,
    ) -> list[PromptSection]:
        """Role composition: capabilities + voice + behavioral descriptors."""
        sections: list[PromptSection] = []

        # Capability fragments
        cap_lines: list[str] = []
        for cap_name in role.capabilities:
            if cap_name not in capabilities:
                raise FileNotFoundError(
                    f"Capability atom '{cap_name}' not found. "
                    f"Available: {list(capabilities.keys())}"
                )
            atom = capabilities[cap_name]
            cap_lines.append(atom.instruction_fragment)

        cap_content = f"## Capabilities\n\n" + "\n".join(cap_lines)
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="capabilities",
            content=cap_content,
            token_estimate=estimate_tokens(cap_content),
            compressible=True,
            priority=0.7,
        ))

        # Voice block (with compression awareness)
        # Resolve voice: role.voice > domain defaults
        effective_voice = role.voice
        if effective_voice is None:
            effective_voice = VoiceProfile(
                language=domain_voice.language if domain_voice else "language_japanese",
                tone=domain_voice.tone if domain_voice else None,
                style=domain_voice.style if domain_voice else None,
            )
        voice_content = self._compose_voice_block(
            effective_voice, voice_atoms, CompressionStage.NONE
        )
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="voice",
            content=voice_content,
            token_estimate=estimate_tokens(voice_content),
            compressible=True,
            priority=0.5,  # Voice drops before capabilities
        ))

        # Behavioral descriptors
        bd = role.behavioral_descriptors
        bd_content = (
            f"## Behavioral Profile\n\n"
            f"Reasoning style: {bd.reasoning_style}\n"
            f"Risk tolerance: {bd.risk_tolerance}\n"
            f"Exploration vs exploitation: {bd.exploration_vs_exploitation:.1f}\n"
        )
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="behavioral",
            content=bd_content,
            token_estimate=estimate_tokens(bd_content),
            compressible=True,
            priority=0.6,
        ))

        # Forbidden actions
        if role.forbidden:
            forbidden_content = "## Forbidden\n\n" + "\n".join(
                f"- {f}" for f in role.forbidden
            )
            sections.append(PromptSection(
                ring=PromptRing.RING_2,
                name="forbidden",
                content=forbidden_content,
                token_estimate=estimate_tokens(forbidden_content),
                compressible=True,
                priority=0.9,  # Forbidden rules are high priority
            ))

        return sections

    def _build_ring_3(self, task: Task) -> list[PromptSection]:
        """Task context and working memory."""
        task_content = (
            f"## Current Task: {task.title}\n\n"
            f"Status: {task.status}\n"
            f"Priority: {task.priority}\n"
            f"Description: {task.description}\n"
        )
        if task.mandate.constraints:
            task_content += "\nConstraints:\n" + "\n".join(
                f"- {c}" for c in task.mandate.constraints
            )
        return [
            PromptSection(
                ring=PromptRing.RING_3,
                name="task_context",
                content=task_content,
                token_estimate=estimate_tokens(task_content),
                compressible=True,
                priority=0.8,
            )
        ]

    def _compose_voice_block(
        self,
        voice: VoiceProfile,
        atoms: dict[str, VoiceAtom],
        compression_stage: CompressionStage,
    ) -> str:
        """Build voice instruction text. Degrades under compression:

        Stage 0-2: full voice (language + tone + style + persona + scalars)
        Stage 3: persona summarized to 1 line, keep tone/style/language
        Stage 4: strip persona/style/tone, keep language only
        Stage 5: language only if non-default
        """
        parts: list[str] = ["## Voice\n"]

        # Language (always included unless stage 5 and default)
        if voice.language not in atoms:
            raise FileNotFoundError(
                f"Voice atom '{voice.language}' not found in voice.yaml. "
                f"Available: {list(atoms.keys())}"
            )

        if compression_stage >= CompressionStage.EMERGENCY:
            # Stage 5: language only if non-default
            if voice.language != "language_japanese":
                parts.append(atoms[voice.language].instruction_fragment)
            return "\n".join(parts) if len(parts) > 1 else ""

        # Language always included for stages 0-4
        parts.append(atoms[voice.language].instruction_fragment)

        if compression_stage >= CompressionStage.SYSTEM_COMPRESS:
            # Stage 4: language only
            return "\n".join(parts)

        # Tone
        if voice.tone and voice.tone in atoms:
            parts.append(atoms[voice.tone].instruction_fragment)

        # Style
        if voice.style and voice.style in atoms:
            parts.append(atoms[voice.style].instruction_fragment)

        if compression_stage >= CompressionStage.TASK_PRUNING:
            # Stage 3: persona summarized to 1 line
            if voice.persona and voice.persona in atoms:
                parts.append(f"Persona: {atoms[voice.persona].description}")
        else:
            # Stage 0-2: full persona
            if voice.persona and voice.persona in atoms:
                parts.append(atoms[voice.persona].instruction_fragment)

        # Scalars (stages 0-2 only)
        if compression_stage <= CompressionStage.TOOL_REDUCTION:
            parts.append(f"Formality: {voice.formality:.1f}/1.0")
            parts.append(f"Verbosity: {voice.verbosity:.1f}/1.0")

        return "\n".join(parts)

    @staticmethod
    def _determine_compression_stage(utilization: float) -> CompressionStage:
        """Map context utilization to compression stage."""
        if utilization < 0.60:
            return CompressionStage.NONE
        elif utilization < 0.70:
            return CompressionStage.HISTORY
        elif utilization < 0.80:
            return CompressionStage.TOOL_REDUCTION
        elif utilization < 0.90:
            return CompressionStage.TASK_PRUNING
        elif utilization < 0.95:
            return CompressionStage.SYSTEM_COMPRESS
        else:
            return CompressionStage.EMERGENCY

    @staticmethod
    def _apply_compression(
        sections: list[PromptSection],
        stage: CompressionStage,
    ) -> tuple[list[PromptSection], list[str]]:
        """Remove lowest-priority compressible sections until under budget.
        Returns (remaining_sections, dropped_section_names)."""
        dropped: list[str] = []
        # Sort compressible sections by priority ascending (drop lowest first)
        compressible = sorted(
            [s for s in sections if s.compressible],
            key=lambda s: s.priority,
        )
        incompressible = [s for s in sections if not s.compressible]

        # Drop sections based on stage severity
        drop_count = min(len(compressible), int(stage))
        for s in compressible[:drop_count]:
            dropped.append(s.name)

        remaining_compressible = compressible[drop_count:]
        result = incompressible + remaining_compressible
        # Re-sort by ring order
        result.sort(key=lambda s: (s.ring, -s.priority))
        return result, dropped

    @staticmethod
    def _apply_edge_placement(sections: list[PromptSection]) -> list[PromptSection]:
        """Critical info at beginning/end (lost-in-the-middle mitigation).
        Ring 0 always first. Highest-priority Ring 3 sections at the end."""
        ring_0 = [s for s in sections if s.ring == PromptRing.RING_0]
        middle = [s for s in sections if s.ring in (PromptRing.RING_1, PromptRing.RING_2)]
        ring_3 = [s for s in sections if s.ring == PromptRing.RING_3]

        # Sort middle by priority (lower priority → middle of prompt)
        middle.sort(key=lambda s: s.priority)

        return ring_0 + middle + ring_3

    def render(self, prompt: ComposedPrompt) -> str:
        """Render composed prompt to a single string."""
        return "\n\n".join(s.content for s in prompt.sections)
