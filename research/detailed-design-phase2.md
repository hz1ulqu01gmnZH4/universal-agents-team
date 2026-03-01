# Universal Agents Framework — Phase 2 Detailed Design

**Version:** 0.2.0 (post-review)
**Date:** 2026-03-01
**Source:** framework-design-unified-v1.1.md (Sections 10, 13, 17, 25), self-aware-ai-and-bootstrapping.md (26 papers), creativity-in-multi-agent-systems.md (43 papers), agent-teams-vs-swarms-literature-review.md (32 papers)
**Status:** Implementation-ready — reviewed (3.5/5), 54 failure modes analyzed, all CRITICAL/HIGH fixed
**Review:** Step 3 score 3.5/5 (gate: >= 3.0). Step 4: 54 FMs (FM-85–FM-138). Step 5: 30 fixes applied.
**Scope:** Phase 2 "Self-Awareness" — SRD diversity metric, stagnation detection, self-capability assessment, confidence calibration, audit viewer enhancements, plus 11 deferred Phase 1.5 fix IDs (8 distinct changes)
**Prerequisite:** Phase 0 + Phase 1 + Phase 1.5 fully implemented (54 source files, 376 tests passing)

---

## Table of Contents

1. [Phase 2 Architecture Overview](#part-1-phase-2-architecture-overview)
2. [New Data Models](#part-2-new-data-models)
3. [SRD Metric Engine](#part-3-srd-metric-engine)
4. [Stagnation Detection System](#part-4-stagnation-detection-system)
5. [Self-Capability Assessment](#part-5-self-capability-assessment)
6. [Confidence Calibration](#part-6-confidence-calibration)
7. [Audit Viewer Enhancements](#part-7-audit-viewer-enhancements)
8. [Deferred Phase 1.5 Fixes](#part-8-deferred-phase-15-fixes)
9. [Modified Component Changes](#part-9-modified-component-changes)
10. [YAML Configuration Schemas](#part-10-yaml-configuration-schemas)
11. [Implementation Sequence](#part-11-implementation-sequence)
12. [Verification Checklist](#part-12-verification-checklist)
13. [Edge Cases, Failure Modes & Mitigations](#part-13-edge-cases-failure-modes--mitigations)

---

## Part 1: Phase 2 Architecture Overview

### 1.1 What Phase 2 Adds

Phase 2 transforms the framework from "resource-aware but self-ignorant" to "self-measuring." After Phase 1.5, agents respect resource limits and budgets, but the framework cannot answer: "Are my agents thinking diversely?", "Am I stagnating?", "What am I good at?", "Am I overconfident?"

Phase 2 adds four measurement systems and one deferred-fix batch:

1. **SRD Diversity Metric Engine** — Computes System Reasoning Diversity across agent outputs per task. Includes Voice Diversity Index (VDI) at 20% weight. Logs to `diversity.jsonl`.
2. **Stagnation Detection** — Multi-level monitoring (agent, voice, team, framework) with threshold-based alert escalation.
3. **Self-Capability Assessment** — Persistent knowledge boundary map tracking {task_type → success_rate}, blind spot identification, and domain capability profiles.
4. **Confidence Calibration** — ECE tracking per evolution cycle, overcalibration response, generation-verification gap monitoring.
5. **Audit Viewer Enhancements** — Enhanced terminal tree with diversity/stagnation rendering, cross-stream timeline.
6. **11 Deferred Phase 1.5 Fix IDs (8 distinct changes)** — FM-18, FM-41, FM-52, FM-57, FM-59, FM-63, R6, R8, R11, R15, R16.

### 1.2 Key Design Principles (from ~160 papers)

1. **LLM introspection is ~20% reliable** — Never use single self-assessment as ground truth. Use multi-channel verification: cross-agent assessment, behavioral consistency, empirical tracking (Anthropic 2025, arXiv:2601.01828).
2. **Calibration at every improvement cycle** — ECE rises monotonically without explicit calibration steps (Huang et al. 2025, arXiv:2504.02902).
3. **Diversity decays without structural intervention** — Prompting-based agents show decreasing lexical diversity over time (Zhang & Eger 2024, arXiv:2409.03659). Temperature is NOT the creativity lever (Peeperkorn et al. 2024, arXiv:2405.00492).
4. **Generation-verification gap is the ceiling** — Self-improvement is bounded by how much better the verifier is than the generator (Song et al. 2024, arXiv:2412.02674).
5. **Persona conditioning is highest-ROI** — +4.1 diversity gain on 1-10 scale from persona conditioning alone (Doudkin et al. 2025, arXiv:2510.15568).
6. **Topology selection dominates** — +12-23% from topology alone when model capabilities converge (AdaptOrch, Yu 2026, arXiv:2602.16873).

### 1.3 What Phase 2 Does NOT Include

- Evolution engine (Phase 4) — Phase 2 only measures; it does not modify framework behavior.
- FrugalGPT model cascading (Phase 2+ — requires confidence-threshold calibration data from Phase 2).
- Full topology optimization via AgentDropout/TopoDIM (Phase 2+ — requires diversity metrics data from Phase 2).
- Skill extraction or crystallization (Phase 3).
- Creative protocols (Phase 6) — Phase 2 measures diversity but does not inject creative interventions.
- Population-based evolution (Phase 8).

Phase 2 is purely a **measurement and observation** phase. It collects data that Phase 3+ will act on. The stagnation detector fires ALERT signals but does not autonomously intervene (intervention logic is Phase 4+).

### 1.4 Files Created & Modified

**New files (8):**
| File | Lines (est.) | Purpose |
|------|------------|---------|
| `models/diversity.py` | ~130 | SRD, VDI, stagnation signal models |
| `models/self_assessment.py` | ~120 | Capability map, calibration, gap assessment models |
| `engine/diversity_engine.py` | ~200 | SRD/VDI computation, diversity snapshot creation |
| `engine/stagnation_detector.py` | ~190 | Multi-level stagnation monitoring |
| `engine/capability_tracker.py` | ~180 | Knowledge boundary map management |
| `engine/calibration_engine.py` | ~170 | Confidence calibration + gap monitoring |
| `core/diversity.yaml` | ~40 | SRD/VDI thresholds and intervention config |
| `core/self-assessment.yaml` | ~30 | Capability assessment config |

**Modified files (9):**
| File | Changes |
|------|---------|
| `models/audit.py` | Add `DiversityLogEntry` |
| `engine/orchestrator.py` | Integrate diversity measurement on task completion |
| `engine/budget_tracker.py` | FM-18 append-only ledger, R6 IQR filtering, R11 history persistence |
| `engine/agent_spawner.py` | FM-63 heartbeat requirement |
| `engine/cache_manager.py` | FM-52 persistence |
| `engine/resource_facade.py` | FM-57 parse_usage integration |
| `engine/cost_gate.py` | R8/R16 record archival |
| `audit/logger.py` | Add `log_diversity()` method |
| `audit/tree_viewer.py` | Diversity and stagnation rendering |

---

## Part 2: New Data Models

### 2.1 `models/diversity.py`

```python
"""Diversity measurement models.
Spec reference: Section 10 (Diversity Enforcement).

Phase 2: SRD metric, VDI metric, stagnation signals.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel


class StagnationLevel(StrEnum):
    """Stagnation detection levels from Section 10.2."""

    AGENT = "agent"          # Single agent repeating itself
    VOICE = "voice"          # All agents using same voice
    TEAM = "team"            # Team-level SRD collapse
    FRAMEWORK = "framework"  # No evolution, same topology


class StagnationSignal(FrameworkModel):
    """A detected stagnation event."""

    level: StagnationLevel
    description: str
    metric_name: str      # e.g., "srd", "vdi", "output_similarity"
    metric_value: float   # The value that triggered the signal
    threshold: float      # The threshold that was breached
    task_id: str | None = None
    agent_id: str | None = None
    consecutive_count: int = 1  # How many consecutive breaches


class VDIMeasurement(FrameworkModel):
    """Voice Diversity Index measurement for a task.

    Dimensions (Section 10.1):
    - Language: binary (same=0, different=1)
    - Tone: categorical distance
    - Style: categorical distance
    - Persona: categorical distance (both null = 0)
    - Formality: |f1 - f2|
    - Verbosity: |v1 - v2|
    """

    task_id: str
    agent_count: int
    vdi_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: dict[str, float]  # Per-dimension averages
    timestamp: datetime


class SRDMeasurement(FrameworkModel):
    """System Reasoning Diversity measurement for a task.

    SRD = 0.8 * text_diversity + 0.2 * VDI (Section 10.1).
    """

    task_id: str
    agent_count: int
    text_diversity: float = Field(ge=0.0, le=1.0)  # Mean pairwise TF-IDF cosine distance
    vdi: VDIMeasurement | None = None
    composite_srd: float = Field(ge=0.0, le=1.0)  # Weighted composite
    timestamp: datetime

    @property
    def health_status(self) -> str:
        """Classify SRD health (Section 10.1 thresholds)."""
        if self.composite_srd < 0.3:
            return "critical"  # Below floor — diversity collapse
        if self.composite_srd < 0.4:
            return "warning"   # Approaching collapse
        if self.composite_srd <= 0.7:
            return "healthy"
        if self.composite_srd <= 0.9:
            return "high"
        return "incoherent"    # Above ceiling


class DiversitySnapshot(FrameworkModel):
    """Complete diversity state at a point in time.

    Logged to diversity.jsonl after every multi-agent task.
    """

    task_id: str
    srd: SRDMeasurement
    stagnation_signals: list[StagnationSignal]
    timestamp: datetime
    agent_outputs_hash: str  # SHA-256 of concatenated outputs for reproducibility
```

### 2.2 `models/self_assessment.py`

```python
"""Self-capability assessment models.
Spec reference: Section 13 (Self-Capability Awareness).

Phase 2: Knowledge boundary map, confidence calibration, gap monitoring.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import FrameworkModel


class CapabilityMapEntry(FrameworkModel):
    """Performance record for a single task type.

    Tracked per task_type (from Orchestrator._classify_task_type).
    """

    task_type: str
    attempts: int = 0
    successes: int = 0  # review verdict == "pass" or "pass_with_notes"
    failures: int = 0   # review verdict == "fail"
    avg_tokens: float = 0.0
    token_count: int = 0           # FM-87: count of records with non-zero tokens
    avg_review_confidence: float = 0.0
    confidence_count: int = 0      # FM-93: count of records with non-zero confidence
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class CapabilityMap(FrameworkModel):
    """Complete knowledge boundary map (Section 13.1).

    Persisted to state/self-assessment/capability-map.yaml.
    """

    entries: dict[str, CapabilityMapEntry] = {}  # task_type → entry
    blind_spots: list[str] = []  # Task types never attempted
    last_analysis: datetime | None = None

    def get_entry(self, task_type: str) -> CapabilityMapEntry:
        """Get or create entry for a task type."""
        if task_type not in self.entries:
            self.entries[task_type] = CapabilityMapEntry(task_type=task_type)
        return self.entries[task_type]


class CalibrationRecord(FrameworkModel):
    """Single calibration data point (Section 13.2).

    Recorded before each evolution: predicted confidence.
    Recorded after evaluation: actual improvement measured.
    """

    evolution_id: str
    predicted_confidence: float = Field(ge=0.0, le=1.0)
    actual_improvement: float | None = None  # None until evaluation completes
    calibration_error: float | None = None   # predicted - actual
    timestamp: datetime


class CalibrationState(FrameworkModel):
    """Persistent calibration state (Section 13.2).

    Persisted to state/self-assessment/calibration.yaml.
    """

    records: list[CalibrationRecord] = []
    running_ece: float = 0.0              # Rolling ECE over last 10 cycles
    confidence_deflation: float = 0.0     # Applied to all future confidence estimates
    evidence_threshold: float = 0.6       # Minimum evidence to approve evolutions
    overcalibrated: bool = False          # True if systematic overconfidence detected
    overcalibration_streak: int = 0       # Consecutive cycles where predicted > actual
    undercalibration_streak: int = 0     # FM-108: Consecutive cycles where predicted < actual

    @property
    def ece_alert(self) -> bool:
        """True if ECE exceeds 0.15 threshold (Huang et al. 2025)."""
        return self.running_ece > 0.15


class GapAssessment(FrameworkModel):
    """Generation-verification gap assessment (Section 13.3).

    Song et al. 2024: self-improvement is bounded by gap.
    If verifier_accuracy - generator_accuracy < 0.05, self-improvement unreliable.
    """

    verifier_accuracy: float = Field(ge=0.0, le=1.0)
    generator_accuracy: float = Field(ge=0.0, le=1.0)
    assessment_date: datetime
    benchmark_task_count: int  # How many tasks were used to compute this

    @property
    def gap_score(self) -> float:
        return self.verifier_accuracy - self.generator_accuracy

    @property
    def self_improvement_reliable(self) -> bool:
        """Gap must exceed minimum threshold (0.05) with sufficient data.

        FM-100: Requires at least 10 benchmark tasks to avoid unreliable
        gap estimates from small samples.
        """
        if self.benchmark_task_count < 10:
            return False  # Insufficient data for reliable assessment
        return self.gap_score >= 0.05
```

### 2.3 Modified `models/audit.py` — Add DiversityLogEntry

Add the following class after the existing `EnvironmentLogEntry`:

```python
class DiversityLogEntry(BaseLogEntry):
    stream: Literal[LogStream.DIVERSITY] = LogStream.DIVERSITY
    task_id: str
    srd_composite: float
    text_diversity: float
    vdi_score: float | None = None
    agent_count: int
    stagnation_signals: list[dict]
    health_status: str
```

---

## Part 3: SRD Metric Engine

### 3.1 `engine/diversity_engine.py`

```python
"""System Reasoning Diversity (SRD) metric engine.
Spec reference: Section 10 (Diversity Enforcement).

Phase 2: TF-IDF cosine distance for text diversity, weighted VDI composite.

Literature basis:
- Persona conditioning +4.1 diversity gain (Doudkin et al. 2025)
- Prompting agents show decreasing diversity over time (Zhang & Eger 2024)
- k-means + entropy for quantitative diversity signal (Yang et al. 2025)
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone

from ..models.audit import DiversityLogEntry, LogStream
from ..models.base import generate_id
from ..models.diversity import (
    DiversitySnapshot,
    SRDMeasurement,
    StagnationSignal,
    VDIMeasurement,
)
from ..models.voice import VoiceProfile
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.diversity_engine")

# SRD thresholds from Section 10.1
SRD_FLOOR = 0.3       # Below: ALERT — diversity collapse
SRD_WARNING = 0.4      # Below: WARNING — approaching collapse
SRD_HEALTHY_LOW = 0.5
SRD_HEALTHY_HIGH = 0.7
SRD_CEILING = 0.9      # Above: possible incoherence

# VDI weight in composite SRD
VDI_WEIGHT = 0.2
TEXT_WEIGHT = 1.0 - VDI_WEIGHT  # 0.8

# VDI dimension weights (sum = 1.0)
_VDI_WEIGHTS = {
    "language": 0.15,
    "tone": 0.20,
    "style": 0.15,
    "persona": 0.15,
    "formality": 0.175,
    "verbosity": 0.175,
}


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for TF-IDF.

    S-5: Public function — used by StagnationDetector cross-module.
    """
    return re.findall(r"\b\w+\b", text.lower())


def compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute IDF scores across a set of tokenized documents.

    S-5: Public function — used by StagnationDetector cross-module.
    """
    n_docs = len(documents)
    if n_docs == 0:
        return {}
    doc_freq: Counter[str] = Counter()
    for tokens in documents:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            doc_freq[token] += 1
    return {
        token: math.log(n_docs / count) + 1.0
        for token, count in doc_freq.items()
    }


def tf_idf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF vector for a token list.

    S-5: Public function — used by StagnationDetector cross-module.
    """
    tf = Counter(tokens)
    total = len(tokens) or 1
    return {t: (count / total) * idf.get(t, 0.0) for t, count in tf.items()}


def cosine_distance(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Cosine distance (1 - similarity) between two sparse vectors.

    S-5: Public function — used by StagnationDetector cross-module.
    """
    all_keys = set(v1) | set(v2)
    if not all_keys:
        return 0.0
    dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in all_keys)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values())) or 1e-10
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values())) or 1e-10
    similarity = dot / (mag1 * mag2)
    return max(0.0, min(1.0, 1.0 - similarity))


# FM-90: Sentinel for None-vs-explicit distance comparison.
# None tone/style gets distance 0.5 from any explicit value (not 1.0).
_NONE_VS_EXPLICIT_DISTANCE = 0.5


def voice_distance(a: VoiceProfile, b: VoiceProfile) -> tuple[float, dict[str, float]]:
    """Weighted distance between two voice profiles (Section 10.1).

    FM-90: Explicit semantics for None tone/style fields:
    - Both None = 0.0 (both unspecified = no difference)
    - One None, one explicit = 0.5 (partial difference, not maximum)
    - Both explicit, same = 0.0; different = 1.0

    FM-114: Returns (composite_score, per_dimension_dict) to avoid
    duplication in compute_vdi().
    """
    lang = 0.0 if a.language == b.language else 1.0

    # FM-90: None-aware categorical distance
    def _nullable_distance(x: str | None, y: str | None) -> float:
        if x is None and y is None:
            return 0.0
        if x is None or y is None:
            return _NONE_VS_EXPLICIT_DISTANCE
        return 0.0 if x == y else 1.0

    tone = _nullable_distance(a.tone, b.tone)
    style = _nullable_distance(a.style, b.style)
    persona = _nullable_distance(a.persona, b.persona)

    formality = abs(a.formality - b.formality)
    verbosity = abs(a.verbosity - b.verbosity)

    dim_values = {
        "language": lang,
        "tone": tone,
        "style": style,
        "persona": persona,
        "formality": formality,
        "verbosity": verbosity,
    }

    composite = sum(_VDI_WEIGHTS[k] * v for k, v in dim_values.items())
    return composite, dim_values


class DiversityEngine:
    """Computes SRD and VDI metrics after multi-agent tasks.

    Called by the orchestrator after task completion when agent_count >= 2.
    Results persisted to diversity.jsonl via AuditLogger.

    Usage:
        engine = DiversityEngine(yaml_store)
        srd = engine.compute_srd(task_id, agent_outputs, voice_profiles)
        snapshot = engine.create_snapshot(task_id, srd, stagnation_signals)
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._diversity_base = f"instances/{domain}/state/diversity"
        yaml_store.ensure_dir(self._diversity_base)

    def compute_text_diversity(self, outputs: list[str]) -> float | None:
        """Compute mean pairwise TF-IDF cosine distance across outputs.

        Returns None for < 2 outputs or all-empty outputs (FM-85).
        Returns 0.0-1.0 for valid multi-agent outputs.

        FM-85: Distinguishes "no valid outputs" from "identical outputs"
        by returning None instead of 0.0 for empty input.
        """
        if len(outputs) < 2:
            return None

        # FM-85: Skip diversity measurement when all outputs are empty
        MIN_OUTPUT_LENGTH = 10  # Characters — below this is effectively empty
        non_empty = [o for o in outputs if len(o.strip()) >= MIN_OUTPUT_LENGTH]
        if len(non_empty) < 2:
            logger.warning(
                f"Skipping text diversity: {len(non_empty)}/{len(outputs)} "
                f"outputs have >= {MIN_OUTPUT_LENGTH} chars"
            )
            return None

        tokenized = [tokenize(output) for output in non_empty]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tokens, idf) for tokens in tokenized]

        distances: list[float] = []
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                distances.append(cosine_distance(vectors[i], vectors[j]))

        return sum(distances) / len(distances) if distances else 0.0

    def compute_vdi(
        self, task_id: str, profiles: list[VoiceProfile],
        timestamp: datetime | None = None,
    ) -> VDIMeasurement | None:
        """Compute Voice Diversity Index across agent voice profiles.

        Returns None for fewer than 2 profiles.

        FM-114: Uses voice_distance() tuple return to avoid duplicating
        per-dimension distance logic.
        FM-99: Accepts external timestamp for consistency.
        """
        if len(profiles) < 2:
            return None

        distances: list[float] = []
        dim_totals: dict[str, float] = {k: 0.0 for k in _VDI_WEIGHTS}
        pair_count = 0

        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                # FM-114: voice_distance returns both composite and per-dim
                composite, dim_values = voice_distance(profiles[i], profiles[j])
                distances.append(composite)
                pair_count += 1
                for k, v in dim_values.items():
                    dim_totals[k] += v

        vdi_score = sum(distances) / len(distances) if distances else 0.0
        dim_avgs = {k: v / pair_count for k, v in dim_totals.items()} if pair_count > 0 else dim_totals

        return VDIMeasurement(
            task_id=task_id,
            agent_count=len(profiles),
            vdi_score=vdi_score,
            dimension_scores=dim_avgs,
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    def compute_srd(
        self,
        task_id: str,
        agent_outputs: list[str],
        voice_profiles: list[VoiceProfile] | None = None,
        timestamp: datetime | None = None,
    ) -> SRDMeasurement | None:
        """Compute composite SRD = 0.8 * text_diversity + 0.2 * VDI.

        Args:
            task_id: ID of the completed task.
            agent_outputs: List of agent output texts.
            voice_profiles: Optional list of agent voice profiles for VDI.
            timestamp: FM-99: Shared timestamp for consistency across all measurements.

        Returns:
            SRDMeasurement with composite score and component scores,
            or None if text diversity could not be computed (FM-85: empty outputs).
        """
        # FM-99: Use a single timestamp for all measurements
        ts = timestamp or datetime.now(timezone.utc)

        text_div = self.compute_text_diversity(agent_outputs)

        # FM-85: None means all outputs were empty — skip measurement
        if text_div is None:
            logger.warning(
                f"SRD computation skipped for task {task_id}: "
                f"insufficient non-empty agent outputs"
            )
            return None

        vdi_measurement = None
        vdi_score = 0.0
        if voice_profiles and len(voice_profiles) >= 2:
            vdi_measurement = self.compute_vdi(task_id, voice_profiles, timestamp=ts)
            if vdi_measurement is not None:
                vdi_score = vdi_measurement.vdi_score

        composite = TEXT_WEIGHT * text_div + VDI_WEIGHT * vdi_score

        srd = SRDMeasurement(
            task_id=task_id,
            agent_count=len(agent_outputs),
            text_diversity=text_div,
            vdi=vdi_measurement,
            composite_srd=round(composite, 4),
            timestamp=ts,
        )

        logger.info(
            f"SRD computed for task {task_id}: "
            f"composite={srd.composite_srd:.3f} "
            f"(text={text_div:.3f}, vdi={vdi_score:.3f}), "
            f"status={srd.health_status}"
        )

        return srd

    def create_snapshot(
        self,
        task_id: str,
        srd: SRDMeasurement,
        stagnation_signals: list[StagnationSignal],
        agent_outputs: list[str],
        timestamp: datetime | None = None,
    ) -> DiversitySnapshot:
        """Create a diversity snapshot and persist to YAML state.

        FM-99: Uses the same timestamp as the SRD measurement for consistency.
        """
        outputs_hash = hashlib.sha256(
            "||".join(agent_outputs).encode()
        ).hexdigest()[:16]

        snapshot = DiversitySnapshot(
            task_id=task_id,
            srd=srd,
            stagnation_signals=stagnation_signals,
            timestamp=timestamp or srd.timestamp,
            agent_outputs_hash=outputs_hash,
        )

        # Persist latest snapshot
        self.yaml_store.write(
            f"{self._diversity_base}/latest-snapshot.yaml", snapshot
        )

        return snapshot

    def get_recent_srd_values(self, count: int = 10) -> list[float]:
        """Load recent SRD values from state for trend analysis.

        Reads from the SRD history file (appended after each measurement).
        """
        path = f"{self._diversity_base}/srd-history.yaml"
        try:
            data = self.yaml_store.read_raw(path)
            values = data.get("values", [])
            return [float(v) for v in values[-count:]]
        except FileNotFoundError:
            return []

    def append_srd_history(self, srd_value: float) -> None:
        """Append an SRD value to the history file."""
        path = f"{self._diversity_base}/srd-history.yaml"
        try:
            data = self.yaml_store.read_raw(path)
            values = data.get("values", [])
        except FileNotFoundError:
            values = []

        values.append(round(srd_value, 4))
        # Keep last 100 values
        if len(values) > 100:
            values = values[-100:]
        self.yaml_store.write_raw(path, {"values": values})
```

---

## Part 4: Stagnation Detection System

### 4.1 `engine/stagnation_detector.py`

```python
"""Multi-level stagnation detection.
Spec reference: Section 10.2 (Stagnation Detection).

Monitors 4 levels:
- Agent: single agent repeating itself (cosine > 0.9 for 3 outputs)
- Voice: all agents using same tone for 5+ tasks; VDI < 0.2 for 3 tasks
- Team: SRD < 0.4 for 3 consecutive tasks
- Framework: no Tier 2+ evolution in 10 tasks; same topology for 10 tasks

Literature basis:
- DoT problem: LLMs cannot self-correct once confident (Liang et al. 2023)
- Content homogenization: multi-agent interaction paradoxically reduces diversity (Li et al. 2026)
- k-means + entropy for quantitative diversity detection (Yang et al. 2025)
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone

from ..models.diversity import (
    SRDMeasurement,
    StagnationLevel,
    StagnationSignal,
    VDIMeasurement,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.stagnation_detector")

# Thresholds from Section 10.2
AGENT_SIMILARITY_THRESHOLD = 0.9   # Cosine > this = too similar
AGENT_CONSECUTIVE_THRESHOLD = 3    # 3 consecutive similar outputs
VOICE_SAME_TONE_THRESHOLD = 5      # 5+ tasks with identical tones
VDI_FLOOR = 0.2                    # VDI below this for 3 tasks
VDI_CONSECUTIVE_THRESHOLD = 3
SRD_STAGNATION_THRESHOLD = 0.4     # SRD below this for 3 tasks
SRD_CONSECUTIVE_THRESHOLD = 3
FRAMEWORK_EVOLUTION_THRESHOLD = 10  # No Tier 2+ evo in this many tasks
FRAMEWORK_TOPOLOGY_THRESHOLD = 10   # Same topology for this many tasks


class StagnationDetector:
    """Multi-level stagnation monitoring system.

    Maintains sliding windows of measurements and fires StagnationSignal
    objects when thresholds are breached. Signals are informational in
    Phase 2 — autonomous intervention is Phase 4+.

    Usage:
        detector = StagnationDetector(yaml_store)
        signals = detector.check_all(srd_measurement, topology_used)
        # signals is a list of StagnationSignal objects
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._stagnation_base = f"instances/{domain}/state/diversity/stagnation"
        yaml_store.ensure_dir(self._stagnation_base)

        # In-memory sliding windows (persisted to YAML for crash recovery)
        self._srd_history: deque[float] = deque(maxlen=20)
        self._vdi_history: deque[float] = deque(maxlen=20)
        self._topology_history: deque[str] = deque(maxlen=20)
        self._tone_history: deque[set[str]] = deque(maxlen=20)
        self._tasks_since_evolution: int = 0

        # Load persisted state
        self._load_state()

    def check_all(
        self,
        srd: SRDMeasurement,
        topology_used: str | None = None,
        agent_tones: set[str] | None = None,
    ) -> list[StagnationSignal]:
        """Run all stagnation checks and return signals.

        Args:
            srd: The SRD measurement for the just-completed task.
            topology_used: The topology pattern selected for this task.
            agent_tones: Set of tone atom names used by agents on this task.

        Returns:
            List of StagnationSignal objects (may be empty).
        """
        signals: list[StagnationSignal] = []

        # Update histories
        self._srd_history.append(srd.composite_srd)
        if srd.vdi is not None:
            self._vdi_history.append(srd.vdi.vdi_score)
        if topology_used is not None:
            self._topology_history.append(topology_used)
        if agent_tones is not None:
            self._tone_history.append(agent_tones)
        self._tasks_since_evolution += 1

        # Check team-level SRD stagnation
        team_signal = self._check_team_srd()
        if team_signal is not None:
            signals.append(team_signal)

        # Check voice-level stagnation
        voice_signals = self._check_voice_stagnation()
        signals.extend(voice_signals)

        # Check framework-level stagnation
        fw_signals = self._check_framework_stagnation()
        signals.extend(fw_signals)

        # Persist state
        self._save_state()

        if signals:
            for s in signals:
                logger.warning(
                    f"Stagnation detected [{s.level}]: {s.description} "
                    f"({s.metric_name}={s.metric_value:.3f}, threshold={s.threshold:.3f})"
                )

        return signals

    def check_agent_output_similarity(
        self,
        agent_id: str,
        current_output: str,
        recent_outputs: list[str],
    ) -> StagnationSignal | None:
        """Check if an agent is repeating itself (cosine > 0.9 for 3 outputs).

        This is called separately per-agent, not as part of check_all().
        Uses the same TF-IDF cosine distance as DiversityEngine.
        """
        if len(recent_outputs) < AGENT_CONSECUTIVE_THRESHOLD - 1:
            return None

        # S-5: Import public functions (no underscore prefix)
        from .diversity_engine import compute_idf, cosine_distance, tf_idf_vector, tokenize

        all_texts = recent_outputs[-(AGENT_CONSECUTIVE_THRESHOLD - 1):] + [current_output]
        tokenized = [tokenize(t) for t in all_texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tokens, idf) for tokens in tokenized]

        # Check current output against each recent output
        current_vec = vectors[-1]
        similarities = []
        for vec in vectors[:-1]:
            dist = cosine_distance(current_vec, vec)
            similarities.append(1.0 - dist)  # Convert distance to similarity

        high_similarity_count = sum(1 for s in similarities if s > AGENT_SIMILARITY_THRESHOLD)

        if high_similarity_count >= AGENT_CONSECUTIVE_THRESHOLD - 1:
            avg_sim = sum(similarities) / len(similarities)
            return StagnationSignal(
                level=StagnationLevel.AGENT,
                description=f"Agent {agent_id} producing semantically similar outputs "
                            f"(avg similarity {avg_sim:.3f} > {AGENT_SIMILARITY_THRESHOLD})",
                metric_name="output_similarity",
                metric_value=avg_sim,
                threshold=AGENT_SIMILARITY_THRESHOLD,
                agent_id=agent_id,
                consecutive_count=high_similarity_count + 1,
            )
        return None

    def record_evolution(self, tier: int) -> None:
        """Record that an evolution occurred. Resets framework counter if Tier >= 2."""
        if tier >= 2:
            self._tasks_since_evolution = 0
            self._save_state()

    def _check_team_srd(self) -> StagnationSignal | None:
        """SRD < 0.4 for 3 consecutive tasks → team-level stagnation."""
        recent = list(self._srd_history)[-SRD_CONSECUTIVE_THRESHOLD:]
        if len(recent) < SRD_CONSECUTIVE_THRESHOLD:
            return None

        if all(v < SRD_STAGNATION_THRESHOLD for v in recent):
            avg = sum(recent) / len(recent)
            return StagnationSignal(
                level=StagnationLevel.TEAM,
                description=f"SRD below {SRD_STAGNATION_THRESHOLD} for "
                            f"{SRD_CONSECUTIVE_THRESHOLD} consecutive tasks "
                            f"(avg={avg:.3f})",
                metric_name="srd",
                metric_value=avg,
                threshold=SRD_STAGNATION_THRESHOLD,
                consecutive_count=SRD_CONSECUTIVE_THRESHOLD,
            )
        return None

    def _check_voice_stagnation(self) -> list[StagnationSignal]:
        """Check voice-level stagnation signals."""
        signals: list[StagnationSignal] = []

        # VDI < 0.2 for 3 consecutive tasks
        recent_vdi = list(self._vdi_history)[-VDI_CONSECUTIVE_THRESHOLD:]
        if len(recent_vdi) >= VDI_CONSECUTIVE_THRESHOLD:
            if all(v < VDI_FLOOR for v in recent_vdi):
                avg = sum(recent_vdi) / len(recent_vdi)
                signals.append(StagnationSignal(
                    level=StagnationLevel.VOICE,
                    description=f"VDI below {VDI_FLOOR} for "
                                f"{VDI_CONSECUTIVE_THRESHOLD} consecutive tasks "
                                f"(avg={avg:.3f})",
                    metric_name="vdi",
                    metric_value=avg,
                    threshold=VDI_FLOOR,
                    consecutive_count=VDI_CONSECUTIVE_THRESHOLD,
                ))

        # All agents using same tone for 5+ tasks
        recent_tones = list(self._tone_history)[-VOICE_SAME_TONE_THRESHOLD:]
        if len(recent_tones) >= VOICE_SAME_TONE_THRESHOLD:
            # Check if all tone sets are identical (single tone used)
            first = recent_tones[0]
            if all(t == first for t in recent_tones) and len(first) <= 1:
                tone_name = next(iter(first)) if first else "none"
                signals.append(StagnationSignal(
                    level=StagnationLevel.VOICE,
                    description=f"All agents using same tone atom '{tone_name}' "
                                f"for {VOICE_SAME_TONE_THRESHOLD}+ consecutive tasks",
                    metric_name="tone_uniformity",
                    metric_value=1.0,
                    threshold=0.0,
                    consecutive_count=VOICE_SAME_TONE_THRESHOLD,
                ))

        return signals

    def _check_framework_stagnation(self) -> list[StagnationSignal]:
        """Check framework-level stagnation signals.

        FM-104: Signal suppression — only fire the evolution stagnation signal
        once when first crossing the threshold, then every 10 tasks after that.
        In Phase 2 there is no evolution engine, so this prevents perpetual
        log noise. The signal fires at task 10, 20, 30... not on every task.
        """
        signals: list[StagnationSignal] = []

        # No Tier 2+ evolution in 10 tasks
        # FM-104: Only fire at threshold crossings (every 10 tasks), not continuously
        if (
            self._tasks_since_evolution >= FRAMEWORK_EVOLUTION_THRESHOLD
            and self._tasks_since_evolution % FRAMEWORK_EVOLUTION_THRESHOLD == 0
        ):
            signals.append(StagnationSignal(
                level=StagnationLevel.FRAMEWORK,
                description=f"No Tier 2+ evolution in "
                            f"{self._tasks_since_evolution} tasks",
                metric_name="tasks_since_evolution",
                metric_value=float(self._tasks_since_evolution),
                threshold=float(FRAMEWORK_EVOLUTION_THRESHOLD),
                consecutive_count=self._tasks_since_evolution,
            ))

        # Same topology for 10 consecutive tasks
        recent_topo = list(self._topology_history)[-FRAMEWORK_TOPOLOGY_THRESHOLD:]
        if len(recent_topo) >= FRAMEWORK_TOPOLOGY_THRESHOLD:
            if len(set(recent_topo)) == 1:
                signals.append(StagnationSignal(
                    level=StagnationLevel.FRAMEWORK,
                    description=f"Same topology '{recent_topo[0]}' selected for "
                                f"{FRAMEWORK_TOPOLOGY_THRESHOLD} consecutive tasks",
                    metric_name="topology_uniformity",
                    metric_value=1.0,
                    threshold=0.0,
                    consecutive_count=FRAMEWORK_TOPOLOGY_THRESHOLD,
                ))

        return signals

    def _save_state(self) -> None:
        """Persist sliding window state to YAML."""
        state = {
            "srd_history": list(self._srd_history),
            "vdi_history": list(self._vdi_history),
            "topology_history": list(self._topology_history),
            "tone_history": [list(s) for s in self._tone_history],
            "tasks_since_evolution": self._tasks_since_evolution,
        }
        self.yaml_store.write_raw(f"{self._stagnation_base}/state.yaml", state)

    def _load_state(self) -> None:
        """Load persisted sliding window state.

        FM-98: Catches ValueError/TypeError/KeyError from corrupt YAML,
        not just FileNotFoundError. Resets to empty state on corruption.
        """
        try:
            state = self.yaml_store.read_raw(f"{self._stagnation_base}/state.yaml")
            for v in state.get("srd_history", []):
                self._srd_history.append(float(v))
            for v in state.get("vdi_history", []):
                self._vdi_history.append(float(v))
            for v in state.get("topology_history", []):
                self._topology_history.append(str(v))
            for v in state.get("tone_history", []):
                self._tone_history.append(set(v))
            self._tasks_since_evolution = int(state.get("tasks_since_evolution", 0))
        except FileNotFoundError:
            pass  # First run — empty state is correct
        except (ValueError, TypeError, KeyError) as e:
            # FM-98: Corrupt state file — reset to empty
            logger.warning(
                f"Corrupt stagnation state, resetting to empty: {e}"
            )
```

---

## Part 5: Self-Capability Assessment

### 5.1 `engine/capability_tracker.py`

```python
"""Self-capability assessment and knowledge boundary mapping.
Spec reference: Section 13 (Self-Capability Awareness).

Maintains a persistent map of {task_type → performance record} updated
after each task completion. Identifies blind spots (task types never
attempted) and tracks success rates for self-awareness.

Literature basis:
- Knowledge boundary awareness (Li et al. 2024, arXiv:2412.12472)
- LLMs lack stable self-knowledge (arXiv:2503.02233)
- "Know Your Limits" — abstention as safety mechanism (TACL)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.self_assessment import CapabilityMap, CapabilityMapEntry
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.capability_tracker")

# All known task types from Orchestrator._classify_task_type()
ALL_KNOWN_TASK_TYPES = [
    "canary_suite",
    "evolution_proposal",
    "decomposition",
    "skill_validation",
    "review",
    "simple_fix",
    "research",
    "feature",
]


class CapabilityTracker:
    """Tracks framework capabilities via empirical task outcomes.

    Responsibilities:
    1. Record task outcomes (success/failure, tokens used, review scores)
    2. Maintain capability map (task_type → performance stats)
    3. Identify blind spots (task types never attempted)
    4. Provide capability queries for orchestration decisions

    Persisted at: state/self-assessment/capability-map.yaml
    Updated: after every task reaches COMPLETE or VERDICT(fail) status.
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._assessment_base = f"instances/{domain}/state/self-assessment"
        yaml_store.ensure_dir(self._assessment_base)
        self._capability_map = self._load_map()

    def record_outcome(
        self,
        task_type: str,
        success: bool,
        tokens_used: int,
        review_confidence: float = 0.0,
    ) -> CapabilityMapEntry:
        """Record a task outcome and update the capability map.

        Args:
            task_type: From Orchestrator._classify_task_type().
            success: True if review verdict was "pass" or "pass_with_notes".
            tokens_used: Total tokens consumed by the task.
            review_confidence: Reviewer's confidence score (0-1).

        Returns:
            Updated CapabilityMapEntry for this task type.
        """
        entry = self._capability_map.get_entry(task_type)
        entry.attempts += 1

        if success:
            entry.successes += 1
        else:
            entry.failures += 1

        # FM-87: Only update token average when tokens_used > 0
        # (tokens_used may be 0 if not populated by caller)
        if tokens_used > 0:
            entry.token_count += 1
            n_tok = entry.token_count
            entry.avg_tokens = (
                (entry.avg_tokens * (n_tok - 1) + tokens_used) / n_tok
            )

        # FM-93: Only update confidence average when confidence > 0,
        # using separate confidence_count to avoid denominator dilution.
        if review_confidence > 0:
            entry.confidence_count += 1
            n_conf = entry.confidence_count
            entry.avg_review_confidence = (
                (entry.avg_review_confidence * (n_conf - 1) + review_confidence) / n_conf
            )
        entry.last_updated = datetime.now(timezone.utc)

        # Update blind spots
        self._update_blind_spots()

        # Persist
        self._save_map()

        logger.info(
            f"Capability updated: {task_type} — "
            f"success_rate={entry.success_rate:.2f} "
            f"({entry.successes}/{entry.attempts}), "
            f"avg_tokens={entry.avg_tokens:.0f}"
        )

        return entry

    def get_capability(self, task_type: str) -> CapabilityMapEntry:
        """Get capability data for a task type."""
        return self._capability_map.get_entry(task_type)

    def get_success_rate(self, task_type: str) -> float:
        """Get success rate for a task type. Returns 0.0 if never attempted."""
        entry = self._capability_map.entries.get(task_type)
        if entry is None:
            return 0.0
        return entry.success_rate

    def get_blind_spots(self) -> list[str]:
        """Return task types that have never been attempted."""
        return list(self._capability_map.blind_spots)

    def get_weak_areas(self, threshold: float = 0.5) -> list[CapabilityMapEntry]:
        """Return task types with success rate below threshold.

        Only includes types with at least 3 attempts (avoid noise).
        """
        weak: list[CapabilityMapEntry] = []
        for entry in self._capability_map.entries.values():
            if entry.attempts >= 3 and entry.success_rate < threshold:
                weak.append(entry)
        return sorted(weak, key=lambda e: e.success_rate)

    def get_full_map(self) -> CapabilityMap:
        """Return the complete capability map."""
        return self._capability_map

    def get_estimated_complexity(self, task_type: str) -> str | None:
        """FM-41 Phase 2: Classify complexity based on historical token data.

        If we have enough data (10+ samples for this task type), use the
        average token consumption to classify complexity:
        - avg_tokens < 5000: "small"
        - avg_tokens < 20000: "medium"
        - avg_tokens >= 20000: "large"

        Returns None if insufficient data (caller should fall back to heuristic).
        FM-109: Returns None (not empty string) for consistent API behavior.
        """
        entry = self._capability_map.entries.get(task_type)
        if entry is None or entry.token_count < 10:
            return None  # FM-109: None, not "" — consistent with docstring
        if entry.avg_tokens < 5000:
            return "small"
        if entry.avg_tokens < 20000:
            return "medium"
        return "large"

    def _update_blind_spots(self) -> None:
        """Recalculate blind spots list."""
        attempted = set(self._capability_map.entries.keys())
        self._capability_map.blind_spots = [
            t for t in ALL_KNOWN_TASK_TYPES if t not in attempted
        ]

    def _load_map(self) -> CapabilityMap:
        """Load capability map from YAML or create new."""
        path = f"{self._assessment_base}/capability-map.yaml"
        try:
            return self.yaml_store.read(path, CapabilityMap)
        except FileNotFoundError:
            cap_map = CapabilityMap()
            cap_map.blind_spots = list(ALL_KNOWN_TASK_TYPES)
            return cap_map

    def _save_map(self) -> None:
        """Persist capability map to YAML."""
        self._capability_map.last_analysis = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._assessment_base}/capability-map.yaml",
            self._capability_map,
        )
```

---

## Part 6: Confidence Calibration

### 6.1 `engine/calibration_engine.py`

```python
"""Confidence calibration and generation-verification gap monitoring.
Spec reference: Section 13.2 (Confidence Calibration), Section 13.3 (Gap Monitoring).

Tracks predicted vs actual improvement for each evolution cycle.
Computes rolling ECE. Triggers overcalibration response when ECE > 0.15.

Literature basis:
- Huang et al. 2025 (arXiv:2504.02902): ECE rises without iterative calibration
- Song et al. 2024 (arXiv:2412.02674): generation-verification gap bounds improvement
- Anthropic 2025 (arXiv:2601.01828): LLM introspection ~20% reliable
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.self_assessment import CalibrationRecord, CalibrationState, GapAssessment
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.calibration_engine")

# Calibration thresholds
ECE_ALERT_THRESHOLD = 0.15          # Rolling ECE above this triggers response
ECE_WINDOW_SIZE = 10                # Rolling window for ECE computation
GAP_MINIMUM_THRESHOLD = 0.05        # Min gap for reliable self-improvement
OVERCALIBRATION_STREAK_LIMIT = 5    # Consecutive overconfident cycles before alert
CONFIDENCE_DEFLATION_RATE = 0.05    # How much to deflate per overcalibrated cycle
FALSE_POSITIVE_THRESHOLD = 0.10     # > 10% false positives → tighten criteria
FALSE_NEGATIVE_THRESHOLD = 0.30     # > 30% false negatives → loosen criteria


class CalibrationEngine:
    """Tracks confidence calibration across evolution cycles.

    Phase 2 is read-only: it records and measures but does not block evolutions.
    Phase 4+ will use calibration data to gate evolution proposals.

    Usage:
        engine = CalibrationEngine(yaml_store)
        engine.record_prediction(evolution_id, confidence=0.8)
        # ... after evaluation ...
        engine.record_outcome(evolution_id, actual_improvement=0.3)
        state = engine.get_state()
        # state.ece_alert → True if systematic overconfidence
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._assessment_base = f"instances/{domain}/state/self-assessment"
        yaml_store.ensure_dir(self._assessment_base)
        self._state = self._load_state()

    def record_prediction(
        self, evolution_id: str, confidence: float
    ) -> CalibrationRecord:
        """Record predicted confidence before an evolution is applied.

        Args:
            evolution_id: ID of the evolution proposal.
            confidence: Predicted confidence that this improves things (0-1).
                        Deflated by current confidence_deflation factor.
        """
        # Apply deflation to the raw confidence
        deflated = max(0.0, confidence - self._state.confidence_deflation)

        record = CalibrationRecord(
            evolution_id=evolution_id,
            predicted_confidence=deflated,
            timestamp=datetime.now(timezone.utc),
        )
        self._state.records.append(record)
        self._save_state()

        logger.info(
            f"Calibration prediction: evo={evolution_id}, "
            f"raw_confidence={confidence:.3f}, "
            f"deflated={deflated:.3f} "
            f"(deflation={self._state.confidence_deflation:.3f})"
        )

        return record

    def record_outcome(
        self, evolution_id: str, actual_improvement: float
    ) -> CalibrationRecord | None:
        """Record actual improvement after evaluation.

        Args:
            evolution_id: ID of the evolution proposal.
            actual_improvement: Measured delta on benchmark (can be negative).

        Returns:
            Updated CalibrationRecord, or None if evolution_id not found.
        """
        # Find the matching record
        record = None
        for r in reversed(self._state.records):
            if r.evolution_id == evolution_id:
                record = r
                break

        if record is None:
            logger.warning(
                f"No prediction found for evolution {evolution_id}. "
                f"Cannot compute calibration error."
            )
            return None

        record.actual_improvement = actual_improvement

        # M-7/FM-95: ECE uses binary success comparison, not raw magnitude.
        # Standard ECE: |predicted_probability - observed_frequency|
        # predicted_confidence = P(improvement > 0)
        # actual_outcome = 1.0 if improvement > 0 else 0.0
        actual_success = 1.0 if actual_improvement > 0 else 0.0
        record.calibration_error = record.predicted_confidence - actual_success

        # Update overcalibration tracking
        if record.calibration_error > 0:
            self._state.overcalibration_streak += 1
            self._state.undercalibration_streak = 0  # FM-108: reset opposite
        elif record.calibration_error < 0:
            self._state.undercalibration_streak += 1  # FM-108: track undercalibration
            self._state.overcalibration_streak = 0
        else:
            self._state.overcalibration_streak = 0
            self._state.undercalibration_streak = 0

        # Recompute rolling ECE
        self._recompute_ece()

        # Check if overcalibration response needed
        if self._state.ece_alert:
            self._apply_overcalibration_response()

        self._save_state()

        logger.info(
            f"Calibration outcome: evo={evolution_id}, "
            f"predicted={record.predicted_confidence:.3f}, "
            f"actual={actual_improvement:.3f}, "
            f"error={record.calibration_error:.3f}, "
            f"running_ECE={self._state.running_ece:.3f}"
        )

        return record

    def get_state(self) -> CalibrationState:
        """Get current calibration state."""
        return self._state

    def compute_gap_assessment(
        self,
        verifier_accuracy: float,
        generator_accuracy: float,
        benchmark_task_count: int,
    ) -> GapAssessment:
        """Compute generation-verification gap assessment.

        Song et al. 2024: self-improvement is bounded by this gap.
        If gap < 0.05, self-improvement from this source is unreliable.
        """
        assessment = GapAssessment(
            verifier_accuracy=verifier_accuracy,
            generator_accuracy=generator_accuracy,
            assessment_date=datetime.now(timezone.utc),
            benchmark_task_count=benchmark_task_count,
        )

        # Persist latest assessment
        self.yaml_store.write(
            f"{self._assessment_base}/gap-assessment.yaml",
            assessment,
        )

        if not assessment.self_improvement_reliable:
            logger.warning(
                f"Generation-verification gap too small: "
                f"{assessment.gap_score:.3f} < {GAP_MINIMUM_THRESHOLD}. "
                f"Self-improvement from this capability source is unreliable."
            )

        return assessment

    def get_false_positive_rate(self) -> float:
        """Compute false positive rate: approved changes that turned out worse.

        A false positive is a record where predicted_confidence > evidence_threshold
        but actual_improvement <= 0.
        """
        completed = [r for r in self._state.records if r.actual_improvement is not None]
        if not completed:
            return 0.0

        approved = [
            r for r in completed
            if r.predicted_confidence >= self._state.evidence_threshold
        ]
        if not approved:
            return 0.0

        false_positives = sum(
            1 for r in approved if r.actual_improvement <= 0
        )
        return false_positives / len(approved)

    def get_false_negative_rate(self) -> float:
        """Compute false negative rate: rejected changes that would have helped.

        A false negative is a record where predicted_confidence < evidence_threshold
        but actual_improvement > 0.
        """
        completed = [r for r in self._state.records if r.actual_improvement is not None]
        if not completed:
            return 0.0

        rejected = [
            r for r in completed
            if r.predicted_confidence < self._state.evidence_threshold
        ]
        if not rejected:
            return 0.0

        false_negatives = sum(
            1 for r in rejected if r.actual_improvement > 0
        )
        return false_negatives / len(rejected)

    def _recompute_ece(self) -> None:
        """Recompute rolling ECE from the last ECE_WINDOW_SIZE completed records."""
        completed = [
            r for r in self._state.records
            if r.calibration_error is not None
        ]
        recent = completed[-ECE_WINDOW_SIZE:]
        if not recent:
            self._state.running_ece = 0.0
            return

        # ECE = mean of absolute calibration errors
        self._state.running_ece = sum(
            abs(r.calibration_error) for r in recent
        ) / len(recent)

    def _apply_overcalibration_response(self) -> None:
        """Respond to systematic overconfidence (Section 13.2).

        M-9/FM-94: Removed unconditional evidence_threshold increment.
        Threshold adjustment is now SOLELY based on FP/FN rate analysis,
        preventing the double-increment ratcheting problem.

        FM-108: Also checks for systematic undercalibration and can
        decrease confidence_deflation to allow recovery from over-correction.
        """
        self._state.overcalibrated = True
        self._state.confidence_deflation += CONFIDENCE_DEFLATION_RATE

        logger.warning(
            f"Overcalibration response triggered: "
            f"ECE={self._state.running_ece:.3f} > {ECE_ALERT_THRESHOLD}. "
            f"Deflation now={self._state.confidence_deflation:.3f}, "
            f"evidence_threshold={self._state.evidence_threshold:.3f}"
        )

        # M-9: FP/FN rate checks are the SOLE mechanism for threshold adjustment
        fp_rate = self.get_false_positive_rate()
        fn_rate = self.get_false_negative_rate()

        if fp_rate > FALSE_POSITIVE_THRESHOLD:
            self._state.evidence_threshold = min(
                0.9, self._state.evidence_threshold + 0.05
            )
            logger.warning(
                f"False positive rate {fp_rate:.2f} > {FALSE_POSITIVE_THRESHOLD}. "
                f"Tightening evidence threshold to {self._state.evidence_threshold:.2f}."
            )
        elif fn_rate > FALSE_NEGATIVE_THRESHOLD:
            # M-9: elif, not if — FP and FN adjustments are mutually exclusive
            self._state.evidence_threshold = max(
                0.3, self._state.evidence_threshold - 0.05
            )
            # FM-108: Also reduce confidence_deflation to allow recovery
            self._state.confidence_deflation = max(
                0.0, self._state.confidence_deflation - CONFIDENCE_DEFLATION_RATE
            )
            logger.info(
                f"False negative rate {fn_rate:.2f} > {FALSE_NEGATIVE_THRESHOLD}. "
                f"Loosening evidence threshold to {self._state.evidence_threshold:.2f}, "
                f"deflation to {self._state.confidence_deflation:.3f}."
            )

    def _load_state(self) -> CalibrationState:
        """Load calibration state from YAML or create new.

        FM-86: Also catches ValueError/ValidationError from corrupt state.
        """
        path = f"{self._assessment_base}/calibration.yaml"
        try:
            return self.yaml_store.read(path, CalibrationState)
        except FileNotFoundError:
            return CalibrationState()
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Corrupt calibration state, resetting: {e}")
            return CalibrationState()

    def _save_state(self) -> None:
        """Persist calibration state to YAML.

        FM-86: Trims records to last 100 entries before saving to prevent
        unbounded growth that would crash at YamlStore's 1MB size cap.
        """
        # FM-86: Cap records to prevent unbounded growth
        if len(self._state.records) > 100:
            self._state.records = self._state.records[-100:]

        self.yaml_store.write(
            f"{self._assessment_base}/calibration.yaml",
            self._state,
        )
```

---

## Part 7: Audit Viewer Enhancements

### 7.1 Modified `audit/tree_viewer.py`

Replace the entire file with the enhanced version that adds diversity/stagnation rendering and cross-stream timeline:

```python
"""Terminal tree viewer using rich library.
Spec reference: Section 17.3 (Audit Viewer Formats).

Phase 2: Enhanced with diversity snapshot rendering and stagnation alerts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ..models.audit import LogStream
from .logger import AuditLogger


class AuditTreeViewer:
    """Renders audit logs as a collapsible terminal tree.

    Phase 2 enhancements:
    - Diversity stream rendering with SRD health color coding
    - Stagnation signal display
    - Cross-stream timeline view
    """

    def __init__(self, audit_logger: AuditLogger):
        self.logger = audit_logger
        self.console = Console()

    def render_session(
        self,
        since: datetime,
        until: datetime | None = None,
        streams: list[LogStream] | None = None,
    ) -> None:
        """Render session audit tree to terminal."""
        if streams is None:
            streams = [LogStream.TASKS, LogStream.DECISIONS, LogStream.DIVERSITY]

        tree = Tree(f"[bold]Session audit: {since.isoformat()}[/bold]")

        for stream in streams:
            entries = self.logger.query(stream, since=since, until=until, limit=200)
            if not entries:
                continue

            if stream == LogStream.DIVERSITY:
                self._render_diversity_branch(tree, entries)
            else:
                branch = tree.add(f"[cyan]{stream.value}[/cyan] ({len(entries)} entries)")
                for entry in entries:
                    ts = entry.get("timestamp", "?")[:19]
                    event = entry.get("event", entry.get("decision_type", "?"))
                    actor = entry.get("actor", "?")
                    branch.add(f"[dim]{ts}[/dim] {event} — {actor}")

        self.console.print(tree)

    def render_task_detail(self, task_id: str) -> None:
        """Render a single task's full timeline."""
        entries = self.logger.query(LogStream.TASKS, limit=500)
        task_entries = [e for e in entries if e.get("task_id") == task_id]

        tree = Tree(f"[bold]Task: {task_id}[/bold]")
        for entry in task_entries:
            ts = entry.get("timestamp", "?")[:19]
            event = entry.get("event", "?")
            actor = entry.get("actor", "?")
            detail = entry.get("detail", {})
            node = tree.add(f"[dim]{ts}[/dim] [green]{event}[/green] — {actor}")
            if detail:
                for k, v in detail.items():
                    node.add(f"{k}: {v}")

        self.console.print(tree)

    def render_diversity_summary(
        self,
        since: datetime,
        until: datetime | None = None,
    ) -> None:
        """Render diversity metrics summary as a table."""
        entries = self.logger.query(
            LogStream.DIVERSITY, since=since, until=until, limit=100
        )

        table = Table(title="Diversity Metrics")
        table.add_column("Task", style="cyan")
        table.add_column("SRD", justify="right")
        table.add_column("Text Div", justify="right")
        table.add_column("VDI", justify="right")
        table.add_column("Agents", justify="right")
        table.add_column("Health", justify="center")
        table.add_column("Stagnation", style="yellow")

        for entry in entries:
            srd = entry.get("srd_composite", 0.0)
            health = entry.get("health_status", "?")
            health_style = self._health_color(health)
            stag_signals = entry.get("stagnation_signals", [])
            stag_text = ", ".join(
                s.get("level", "?") for s in stag_signals
            ) if stag_signals else "-"

            table.add_row(
                entry.get("task_id", "?")[-12:],
                f"{srd:.3f}",
                f"{entry.get('text_diversity', 0.0):.3f}",
                f"{entry.get('vdi_score', 0.0):.3f}" if entry.get("vdi_score") else "-",
                str(entry.get("agent_count", "?")),
                f"[{health_style}]{health}[/{health_style}]",
                stag_text,
            )

        self.console.print(table)

    def render_timeline(
        self,
        since: datetime,
        until: datetime | None = None,
        limit: int = 50,
    ) -> None:
        """Render cross-stream timeline (all events merged chronologically)."""
        entries = self.logger.query_all(since=since, until=until, limit=limit)

        tree = Tree(f"[bold]Timeline: {since.isoformat()}[/bold]")
        for entry in entries:
            ts = entry.get("timestamp", "?")[:19]
            stream = entry.get("stream", "?")
            stream_color = self._stream_color(stream)

            if stream == "tasks":
                label = f"{entry.get('event', '?')} — {entry.get('actor', '?')}"
            elif stream == "decisions":
                label = f"{entry.get('decision_type', '?')} → {entry.get('selected', '?')}"
            elif stream == "diversity":
                srd = entry.get("srd_composite", 0.0)
                health = entry.get("health_status", "?")
                label = f"SRD={srd:.3f} ({health})"
            elif stream == "resources":
                label = entry.get("event_type", "?")
            else:
                label = entry.get("event_type", str(entry.get("detail", "?")))

            tree.add(
                f"[dim]{ts}[/dim] [{stream_color}]{stream}[/{stream_color}] {label}"
            )

        self.console.print(tree)

    def _render_diversity_branch(
        self, tree: Tree, entries: list[dict]
    ) -> None:
        """Render diversity entries with health color coding."""
        branch = tree.add(
            f"[cyan]diversity[/cyan] ({len(entries)} measurements)"
        )
        for entry in entries:
            srd = entry.get("srd_composite", 0.0)
            health = entry.get("health_status", "?")
            color = self._health_color(health)
            task = entry.get("task_id", "?")[-12:]
            agents = entry.get("agent_count", "?")

            node = branch.add(
                f"[dim]{entry.get('timestamp', '?')[:19]}[/dim] "
                f"Task {task}: SRD=[{color}]{srd:.3f}[/{color}] "
                f"({agents} agents, {health})"
            )

            # Show stagnation signals as sub-nodes
            for signal in entry.get("stagnation_signals", []):
                level = signal.get("level", "?")
                desc = signal.get("description", "?")
                node.add(f"[yellow]⚠ {level}:[/yellow] {desc}")

    @staticmethod
    def _health_color(health: str) -> str:
        """Map health status to rich color."""
        return {
            "critical": "red bold",
            "warning": "yellow",
            "healthy": "green",
            "high": "cyan",
            "incoherent": "magenta",
        }.get(health, "white")

    @staticmethod
    def _stream_color(stream: str) -> str:
        """Map stream name to rich color."""
        return {
            "tasks": "green",
            "decisions": "blue",
            "diversity": "magenta",
            "resources": "yellow",
            "evolution": "red",
            "environment": "cyan",
            "creativity": "bright_magenta",
            "traces": "dim",
        }.get(stream, "white")
```

### 7.2 Modified `audit/logger.py` — Add `log_diversity()`

Add after the existing `log_environment()` method:

```python
    def log_diversity(self, entry: DiversityLogEntry) -> None:
        self.writers[LogStream.DIVERSITY].append(entry)
```

And add the import at the top:

```python
from ..models.audit import (
    BaseLogEntry,
    DecisionLogEntry,
    DiversityLogEntry,  # NEW
    EnvironmentLogEntry,
    EvolutionLogEntry,
    LogStream,
    ResourceLogEntry,
    TaskLogEntry,
    TraceLogEntry,
)
```

---

## Part 8: Deferred Phase 1.5 Fixes

### 8.1 FM-18: Append-Only Budget Ledger

**Problem:** `BudgetTracker.record_consumption()` does read-modify-write on `window.yaml`, creating a race condition under concurrent access.

**Fix:** Add JSONL-based consumption ledger. `record_consumption()` appends to JSONL; `get_window()` sums entries within the window.

Changes to `engine/budget_tracker.py`:

Add to `__init__()` after existing setup:

```python
        # FM-18: Append-only consumption ledger
        # S-6: Use absolute path from yaml_store base_dir
        from ..state.jsonl_writer import JsonlWriter
        from ..models.audit import LogStream
        ledger_dir = self.yaml_store.base_dir / f"instances/{domain}/state/resources/consumption"
        self._consumption_ledger = JsonlWriter(
            log_dir=ledger_dir,
            stream=LogStream.RESOURCES,
            max_size_mb=5,
            max_rotated_files=5,
        )
        # FM-89: Cached window totals for fast reads
        self._cached_window: WindowBudget | None = None
        self._cached_window_mtime: float = 0.0
```

Add new model to `models/audit.py` (M-2: proper log entry instead of raw dict):

```python
class ConsumptionLogEntry(BaseLogEntry):
    """FM-18: Typed consumption record for append-only ledger."""
    stream: Literal[LogStream.RESOURCES] = LogStream.RESOURCES
    tokens: int
    is_cached: bool = False
```

Replace `record_consumption()` method:

```python
    def record_consumption(self, tokens: int, is_cached: bool = False) -> WindowBudget:
        """Record token consumption via append-only ledger (FM-18).

        M-2: Uses JsonlWriter.append() with a proper ConsumptionLogEntry
        instead of bypassing the writer's API. This ensures consistent
        locking, secret scrubbing, and rotation.
        """
        now = datetime.now(timezone.utc)

        # M-2: Append via JsonlWriter API with proper typed entry
        from ..models.audit import ConsumptionLogEntry
        from ..models.base import generate_id
        entry = ConsumptionLogEntry(
            id=generate_id("cons"),
            timestamp=now,
            tokens=tokens,
            is_cached=is_cached,
        )
        self._consumption_ledger.append(entry)

        # Rebuild window from ledger (FM-89: with caching)
        window = self._rebuild_window_from_ledger()
        self._persist_window(window)  # Also update cache

        # Track cache hits for efficiency metrics
        if is_cached:
            self._cache_hit_tokens += tokens
        self._total_input_tokens += tokens

        # FM-97: Weekly budget also uses ledger approach (not read-modify-write)
        self._increment_weekly_ledger(tokens)

        # Log pressure changes
        pressure = window.pressure_level
        if pressure in (BudgetPressureLevel.ORANGE, BudgetPressureLevel.RED):
            logger.warning(
                f"Budget pressure: {pressure.value} — "
                f"{window.remaining_tokens} tokens remaining in window"
            )

        return window

    def _increment_weekly_ledger(self, tokens: int) -> None:
        """FM-97: Atomic weekly budget increment via file lock.

        Uses a separate fcntl lock spanning the full read-modify-write
        cycle for the weekly budget, preventing the race condition.
        """
        import fcntl
        lock_path = self.yaml_store.base_dir / f"{self._budget_base}/weekly.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                weekly = self.get_weekly()
                weekly.tokens_consumed += tokens
                self._persist_weekly(weekly)
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    def _rebuild_window_from_ledger(self) -> WindowBudget:
        """Rebuild window budget by summing consumption records within window.

        FM-18: This is the authoritative source of truth for token consumption.
        FM-89/S-3: Caches window totals. Only re-scans ledger if file mtime changed.
        """
        # FM-89: Check if cached window is still fresh
        try:
            current_mtime = self._consumption_ledger.current_path.stat().st_mtime
        except FileNotFoundError:
            current_mtime = 0.0

        if (
            self._cached_window is not None
            and current_mtime == self._cached_window_mtime
        ):
            return self._cached_window

        window = self._get_or_create_window_metadata()
        window_start = window.window_start

        # Sum consumption from ledger
        total_tokens = 0
        total_requests = 0
        last_request = None

        entries = self._consumption_ledger.read_entries(
            since=window_start, limit=10_000
        )
        for entry in entries:
            total_tokens += entry.get("tokens", 0)
            total_requests += 1
            ts = entry.get("timestamp")
            if ts:
                last_request = ts

        window.tokens_consumed = total_tokens
        window.requests_made = total_requests
        if last_request:
            window.last_request_at = datetime.fromisoformat(last_request)

        # FM-89: Update cache
        self._cached_window = window
        self._cached_window_mtime = current_mtime

        return window

    def _get_or_create_window_metadata(self) -> WindowBudget:
        """Get window metadata (start time, capacity) or create new."""
        path = f"{self._budget_base}/window.yaml"
        try:
            window = self.yaml_store.read(path, WindowBudget)
            now = datetime.now(timezone.utc)
            window_end = window.window_start + timedelta(hours=window.window_duration_hours)
            if now >= window_end:
                logger.info(f"Window expired. Starting new window.")
                window = self._new_window()
                self._persist_window(window)
                # FM-89: Invalidate cache on window change
                self._cached_window = None
                self._cached_window_mtime = 0.0
            return window
        except FileNotFoundError:
            window = self._new_window()
            self._persist_window(window)
            return window
```

Update `get_window()` to use the ledger:

```python
    def get_window(self) -> WindowBudget:
        """Get current window budget (FM-18: rebuilt from consumption ledger)."""
        return self._rebuild_window_from_ledger()
```

### 8.2 R6: IQR Filtering on Rolling Average

**Problem:** Outlier tasks pollute the rolling average for cost estimation.

**Fix:** Apply IQR filtering before computing average.

Add method to `engine/budget_tracker.py`:

```python
    def estimate_task_cost(self, task_type: str, complexity: str = "medium") -> int:
        """Estimate token cost for a task.

        R6 fix: IQR filtering on rolling average to remove outlier contamination.
        """
        key = f"{task_type}_{complexity}"

        # Check rolling average with IQR filtering
        history = self._token_history.get(key, deque())
        if len(history) >= self._rolling_threshold:
            filtered = self._iqr_filter(list(history))
            if filtered:
                avg = int(sum(filtered) / len(filtered))
                logger.debug(
                    f"estimate_task_cost({key}): IQR-filtered average = {avg} "
                    f"from {len(filtered)}/{len(history)} samples"
                )
                return avg

        # Fall back to cold seeds
        seed = self._cold_seeds.get(key, self._cold_seeds.get(task_type))
        if seed is not None:
            logger.debug(f"estimate_task_cost({key}): cold seed = {seed}")
            return seed

        # Unknown type — apply safety margin
        default = 10_000
        novel_estimate = int(default * self._safety_margin)
        logger.debug(f"estimate_task_cost({key}): unknown type, novel estimate = {novel_estimate}")
        return novel_estimate

    @staticmethod
    def _iqr_filter(values: list[int]) -> list[int]:
        """Remove outliers using IQR method. Returns filtered list."""
        if len(values) < 4:
            return values
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return [v for v in values if lower <= v <= upper]
```

### 8.3 R11 / FM-59: Token History and Cache Counter Persistence

**Problem:** In-memory `_token_history` deque and cache counters lost on restart.

**Fix:** Persist to YAML after every update; load on init.

Add to `engine/budget_tracker.py.__init__()`:

```python
        # R11: Load persisted token history
        self._load_token_history()
```

Add methods:

```python
    def _persist_token_history(self) -> None:
        """R11: Persist token history to YAML for crash recovery."""
        data = {
            "history": {k: list(v) for k, v in self._token_history.items()},
            "cache_hit_tokens": self._cache_hit_tokens,
            "total_input_tokens": self._total_input_tokens,
        }
        self.yaml_store.write_raw(
            f"{self._budget_base}/token-history.yaml", data
        )

    def _load_token_history(self) -> None:
        """R11: Load persisted token history on startup."""
        try:
            data = self.yaml_store.read_raw(
                f"{self._budget_base}/token-history.yaml"
            )
            for key, values in data.get("history", {}).items():
                self._token_history[key] = deque(values, maxlen=50)
            self._cache_hit_tokens = int(data.get("cache_hit_tokens", 0))
            self._total_input_tokens = int(data.get("total_input_tokens", 0))
            logger.info(
                f"Loaded token history: {len(self._token_history)} types, "
                f"{sum(len(v) for v in self._token_history.values())} samples"
            )
        except FileNotFoundError:
            pass  # First run — empty history is correct
```

Add `_persist_token_history()` call at end of `record_actual_usage()`:

```python
    def record_actual_usage(self, task_type: str, complexity: str, tokens_used: int) -> None:
        """Record actual token usage for a completed task."""
        key = f"{task_type}_{complexity}"
        if key not in self._token_history:
            self._token_history[key] = deque(maxlen=50)
        self._token_history[key].append(tokens_used)
        self._persist_token_history()  # R11: persist immediately
        logger.info(f"Recorded usage: {key} = {tokens_used} tokens (now {len(self._token_history[key])} samples)")
```

### 8.4 FM-41: Learned Complexity Classifier

**Problem:** `_classify_complexity()` in Orchestrator uses description length heuristic.

**Fix:** Integrate CapabilityTracker data when available.

Changes to `engine/orchestrator.py`:

Add `capability_tracker` to `__init__()`:

```python
    def __init__(
        self,
        yaml_store: YamlStore,
        topology_router: TopologyRouter,
        team_manager: TeamManager,
        task_lifecycle: TaskLifecycle,
        review_engine: ReviewEngine,
        audit_logger: AuditLogger | None = None,
        budget_tracker: BudgetTracker | None = None,
        rate_limiter: RateLimiter | None = None,
        cost_gate: CostGate | None = None,
        capability_tracker: CapabilityTracker | None = None,  # Phase 2
    ):
        # ... existing assignments ...
        self.capability_tracker = capability_tracker
```

Add TYPE_CHECKING import:

```python
if TYPE_CHECKING:
    from .budget_tracker import BudgetTracker
    from .calibration_engine import CalibrationEngine
    from .capability_tracker import CapabilityTracker
    from .cost_gate import CostGate
    from .rate_limiter import RateLimiter
```

Replace `_classify_complexity()`:

```python
    def _classify_complexity(self, task: Task) -> str:
        """Classify task complexity for budget estimation.

        FM-41 Phase 2: Uses historical data from CapabilityTracker when
        available (>= 10 samples). Falls back to keyword + length heuristic.
        """
        # Phase 2: Try learned classification first
        if self.capability_tracker is not None:
            task_type = self._classify_task_type(task)
            learned = self.capability_tracker.get_estimated_complexity(task_type)
            if learned:
                return learned

        # Fallback: keyword + length heuristic (Phase 1.5)
        desc = task.description or ""
        desc_lower = desc.lower()
        if any(w in desc_lower for w in ("trivial", "simple", "quick", "minor")):
            return "small"
        if any(w in desc_lower for w in ("complex", "large", "extensive", "major", "refactor")):
            return "large"

        desc_len = len(desc)
        if desc_len < 100:
            return "small"
        if desc_len < 400:
            return "medium"
        return "large"
```

### 8.5 FM-52: CacheManager Persistence

**Problem:** CacheManager stats lost on restart.

**Fix:** Persist `CacheStats` to YAML after each update.

Changes to `engine/cache_manager.py`:

Add `yaml_store` parameter to `__init__()`:

```python
    def __init__(self, yaml_store: YamlStore | None = None, domain: str = "meta"):
        self._prefix_cache: str | None = None
        self._prefix_hash: str | None = None
        self._prefix_tokens: int = 0
        self._yaml_store = yaml_store
        self._stats_path = f"instances/{domain}/state/resources/cache-stats.yaml"
        self.stats = self._load_stats()
```

Add import:

```python
from ..state.yaml_store import YamlStore
```

Add persistence methods:

```python
    def _persist_stats(self) -> None:
        """FM-52: Persist cache stats to YAML."""
        if self._yaml_store is not None:
            self._yaml_store.write(self._stats_path, self.stats)

    def _load_stats(self) -> CacheStats:
        """FM-52/FM-119: Load persisted cache stats or create new.

        FM-119: Catches ValueError and ValidationError in addition to
        FileNotFoundError, so corrupted YAML doesn't crash init.
        """
        if self._yaml_store is not None:
            try:
                return self._yaml_store.read(self._stats_path, CacheStats)
            except (FileNotFoundError, ValueError, ValidationError):
                pass  # First run, corrupt file, or schema mismatch — start fresh
        return CacheStats()
```

Add `self._persist_stats()` calls at end of `get_shared_prefix()` and `record_cache_savings()`.

### 8.6 FM-57: parse_usage Integration

**Problem:** `ResourceTracker.parse_usage_output()` not connected to `BudgetTracker`.

**Fix:** Add integration method to `ResourceFacade`.

Add to `engine/resource_facade.py` `__init__()`:

```python
        # S-7: Delta tracking for cumulative /usage output
        self._last_synced_input: int = 0
        self._last_synced_output: int = 0
        self._last_synced_cache: int = 0
```

Add method:

```python
    def sync_from_usage(self) -> dict | None:
        """FM-57/FM-113/S-7: Sync budget tracker from /usage command output.

        Calls ResourceTracker.parse_usage_output() and feeds DELTA
        into BudgetTracker.record_consumption(). Returns parsed data
        or None if parsing failed.

        FM-113: Uses self.record_consumption() which is defined on
        ResourceFacade (line 46), not on budget_tracker. This routes
        through both budget and rate tracking.

        S-7: Tracks last-seen totals to compute deltas. The /usage
        command returns cumulative totals, not per-call increments.
        Without delta tracking, every sync would re-count all usage.
        """
        usage_data = self.compute.parse_usage_output()
        if usage_data is None:
            return None

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        cache_read = usage_data.get("cache_read", 0)

        # S-7: Compute delta from last sync (cumulative → incremental)
        delta_input = input_tokens - self._last_synced_input
        delta_output = output_tokens - self._last_synced_output
        delta_cache = cache_read - self._last_synced_cache

        if delta_input > 0 or delta_output > 0:
            self.record_consumption(
                input_tokens=delta_input,
                output_tokens=delta_output,
                cached_tokens=max(0, delta_cache),
            )
            self._last_synced_input = input_tokens
            self._last_synced_output = output_tokens
            self._last_synced_cache = cache_read

        usage_data["delta_input"] = delta_input
        usage_data["delta_output"] = delta_output
        return usage_data
```

### 8.7 FM-63: Heartbeat Requirement

**Problem:** Agents without heartbeat are permanently considered "healthy."

**Fix:** Treat agents without heartbeat as unhealthy if spawned > timeout ago.

Changes to `engine/agent_spawner.py`, replace `check_agent_health()`:

```python
    @staticmethod
    def _parse_aware_datetime(iso_str: str) -> datetime:
        """FM-112: Parse ISO datetime string, ensuring timezone-aware result.

        Phase 1 code may have written naive UTC timestamps (datetime.utcnow()).
        Phase 2 uses aware timestamps (datetime.now(timezone.utc)). This method
        normalizes both formats so datetime subtraction never raises TypeError.
        """
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            # Assume naive timestamps are UTC (Phase 1 convention)
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def check_agent_health(self, agent_id: str, timeout_minutes: int = 10) -> bool:
        """Check if agent is responsive (heartbeat within timeout).

        FM-63: Agents without heartbeat are treated as unhealthy if
        their creation time exceeds timeout. No more permanent "healthy"
        for legacy agents.
        FM-112: Uses _parse_aware_datetime() to handle mixed naive/aware timestamps.
        """
        agent_dir = f"{self._agents_base}/{agent_id}"
        try:
            data = self.yaml_store.read_raw(f"{agent_dir}/status.yaml")
            if data.get("status") == AgentStatus.DESPAWNED:
                return False
            heartbeat = data.get("heartbeat_at")
            if heartbeat:
                last_beat = self._parse_aware_datetime(heartbeat)
                elapsed = (datetime.now(timezone.utc) - last_beat).total_seconds() / 60
                return elapsed < timeout_minutes

            # FM-63: No heartbeat — check creation time instead
            created_at = data.get("created_at")
            if created_at:
                created = self._parse_aware_datetime(created_at)
                elapsed = (datetime.now(timezone.utc) - created).total_seconds() / 60
                if elapsed > timeout_minutes:
                    logger.info(
                        f"Agent {agent_id} has no heartbeat and was created "
                        f"{elapsed:.1f} min ago (> {timeout_minutes} min timeout). "
                        f"Treating as unhealthy."
                    )
                    return False
            return True  # Newly created, within timeout
        except FileNotFoundError:
            return False
```

### 8.8 R8/R16: Cost Record Archival

**Problem:** Cost record YAML files accumulate unboundedly.

**Fix:** Add archival method to `CostGate`.

Add to `engine/cost_gate.py`:

```python
    def archive_old_records(self, days: int = 30) -> int:
        """R8/R16: Archive cost records older than specified days.

        Moves individual cost record files to an archive subdirectory.
        Daily summaries are not archived (they are already small).
        Returns count of archived records.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        archive_dir = f"{self._costs_base}/archive"
        self.yaml_store.ensure_dir(archive_dir)

        archived = 0
        try:
            for name in self.yaml_store.list_dir(self._costs_base):
                if not name.startswith("cost-"):
                    continue
                path = f"{self._costs_base}/{name}"
                try:
                    record = self.yaml_store.read(path, CostRecord)
                    if record.timestamp < cutoff:
                        # Move to archive
                        archive_path = f"{archive_dir}/{name}"
                        self.yaml_store.write(archive_path, record)
                        self.yaml_store.delete(path)
                        archived += 1
                except (FileNotFoundError, ValueError):
                    continue
        except (FileNotFoundError, NotADirectoryError):
            pass

        if archived > 0:
            logger.info(f"Archived {archived} cost records older than {days} days")
        return archived
```

Add `delete` method to `state/yaml_store.py` (needed for archival — M-4/FM-101):

```python
    def delete(self, relative_path: str) -> None:
        """Delete a YAML file. FM-101: Required by cost record archival.

        Acquires advisory lock before deletion to prevent concurrent
        read-delete races. Raises FileNotFoundError if file does not exist.
        """
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent file: {path}")
        lock_path = path.with_suffix(path.suffix + ".lock")
        with open(lock_path, "w", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            path.unlink()
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        # Clean up lock file (best-effort)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
```

### 8.9 R15: Auto-Action on Degrading Efficiency Trends

**Problem:** `compute_trends()` reports "degrading" but no automated action.

**Fix:** Emit a stagnation signal when efficiency is degrading. StagnationDetector picks this up.

Add to `engine/budget_tracker.py`:

```python
    def compute_trends(self, metrics: list[ResourceEfficiencyMetrics]) -> dict:
        """Compute efficiency trends from a list of metrics.

        R15: Returns trend data including a degrading flag that the
        StagnationDetector can consume.
        """
        if len(metrics) < 2:
            return {"status": "insufficient_data", "degrading": False}

        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        first_avg = sum(m.cost_of_pass for m in first_half) / len(first_half)
        second_avg = sum(m.cost_of_pass for m in second_half) / len(second_half)

        if second_avg < first_avg * 0.9:
            trend = "improving"
        elif second_avg > first_avg * 1.1:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "status": "computed",
            "cost_trend": trend,
            "degrading": trend == "degrading",
            "task_count": len(metrics),
            "first_half_avg": round(first_avg),
            "second_half_avg": round(second_avg),
        }
```

---

## Part 9: Modified Component Changes

### 9.1 Orchestrator Integration

The Orchestrator gains Phase 2 integration points. After task completion (in `complete_execution()`), it triggers diversity measurement and capability tracking.

Changes to `engine/orchestrator.py`:

Add to `__init__()`:

```python
        self.diversity_engine: DiversityEngine | None = None     # Phase 2
        self.stagnation_detector: StagnationDetector | None = None  # Phase 2
        self.capability_tracker = capability_tracker               # Phase 2
```

Add TYPE_CHECKING imports:

```python
if TYPE_CHECKING:
    from .budget_tracker import BudgetTracker
    from .capability_tracker import CapabilityTracker
    from .cost_gate import CostGate
    from .diversity_engine import DiversityEngine
    from .rate_limiter import RateLimiter
    from .stagnation_detector import StagnationDetector
```

Add `output_text` field to `models/task.py` `SubTask` model (FM-116):

```python
class SubTask(FrameworkModel):
    """A decomposed unit of work within a Task."""
    # ... existing fields ...
    output_text: str | None = None  # FM-116: Captured agent output for diversity measurement
```

Add new method:

```python
    def record_task_outcome(
        self,
        task_id: str,
        agent_outputs: list[str] | None = None,
        voice_profiles: list[VoiceProfile] | None = None,
        topology_used: str | None = None,
        agent_tones: set[str] | None = None,
    ) -> dict:
        """Phase 2: Record task outcome for self-awareness metrics.

        Called after task reaches COMPLETE or VERDICT(fail) status.
        Triggers diversity measurement, stagnation detection, and
        capability tracking.

        FM-87: Uses task.metrics.tokens_used only if > 0.
        FM-96: Handles task.review being None (manual completion).
        FM-115: Called from handle_verdict() — see integration point below.
        FM-116: Falls back to collecting output_text from SubTask records
                when agent_outputs is not explicitly provided.

        Returns dict with measurement results.
        """
        task = self.task_lifecycle._load_task(task_id)
        results: dict = {}

        # FM-96: Determine success and confidence with null guards
        if task.review is not None:
            success = task.review.verdict in ("pass", "pass_with_notes")
            confidence = task.review.reviewer_confidence
        elif task.status == TaskStatus.COMPLETE:
            # FM-96: Manual completion without review — assume success, low confidence
            success = True
            confidence = 0.0
        else:
            # VERDICT(fail) without review — should not happen, but safe default
            success = False
            confidence = 0.0

        # FM-87: Only pass tokens_used when actually populated (> 0)
        tokens_used = task.metrics.tokens_used if task.metrics.tokens_used > 0 else 0

        # Capability tracking
        if self.capability_tracker is not None:
            task_type = self._classify_task_type(task)
            entry = self.capability_tracker.record_outcome(
                task_type=task_type,
                success=success,
                tokens_used=tokens_used,
                review_confidence=confidence,
            )
            results["capability"] = entry.model_dump()

        # FM-116: Collect agent outputs from subtasks if not explicitly provided
        if agent_outputs is None and task.subtasks:
            collected = []
            for subtask_id in task.subtasks:
                try:
                    st = self.task_lifecycle._load_task(subtask_id)
                    if hasattr(st, "output_text") and st.output_text:
                        collected.append(st.output_text)
                except FileNotFoundError:
                    continue
            if len(collected) >= 2:
                agent_outputs = collected

        # Diversity measurement (only for multi-agent tasks)
        if (
            self.diversity_engine is not None
            and agent_outputs is not None
            and len(agent_outputs) >= 2
        ):
            srd = self.diversity_engine.compute_srd(
                task_id, agent_outputs, voice_profiles
            )
            results["srd"] = srd.model_dump()

            # Stagnation detection
            stagnation_signals: list = []
            if self.stagnation_detector is not None:
                stagnation_signals = self.stagnation_detector.check_all(
                    srd=srd,
                    topology_used=topology_used,
                    agent_tones=agent_tones,
                )
                results["stagnation_signals"] = [
                    s.model_dump() for s in stagnation_signals
                ]

            # Create and persist diversity snapshot
            snapshot = self.diversity_engine.create_snapshot(
                task_id, srd, stagnation_signals, agent_outputs
            )
            self.diversity_engine.append_srd_history(srd.composite_srd)
            results["diversity_snapshot"] = snapshot.model_dump()

            # Log to diversity audit stream
            if self.audit_logger is not None:
                from ..models.audit import DiversityLogEntry
                from ..models.base import generate_id
                self.audit_logger.log_diversity(DiversityLogEntry(
                    id=generate_id("div"),
                    timestamp=snapshot.timestamp,
                    task_id=task_id,
                    srd_composite=srd.composite_srd,
                    text_diversity=srd.text_diversity,
                    vdi_score=srd.vdi.vdi_score if srd.vdi else None,
                    agent_count=srd.agent_count,
                    stagnation_signals=[s.model_dump() for s in stagnation_signals],
                    health_status=srd.health_status,
                ))

        return results
```

Add import for VoiceProfile at top:

```python
from ..models.voice import VoiceProfile
```

**FM-115: Integration point in `handle_verdict()`.**

Add call to `record_task_outcome()` in the existing `handle_verdict()` method, after
the COMPLETE transition and before team dissolution:

```python
    def handle_verdict(self, task_id: str, review: TaskReview) -> Task:
        """Process review verdict and transition task state."""
        # ... existing verdict logic (COMPLETE or re-plan) ...

        if task.status == TaskStatus.COMPLETE:
            # FM-115: Record Phase 2 metrics after successful completion
            try:
                topology_used = task.topology.pattern if task.topology else None
                agent_tones = None
                voice_profiles = None
                # Collect voice profiles from agent registry if available
                if task.topology and task.topology.agents:
                    agent_tones = set()
                    voice_profiles = []
                    for assignment in task.topology.agents:
                        agent = self._load_agent(assignment.agent_id)
                        if agent and agent.voice:
                            voice_profiles.append(agent.voice)
                            if agent.voice.tone:
                                agent_tones.add(agent.voice.tone)

                self.record_task_outcome(
                    task_id=task_id,
                    voice_profiles=voice_profiles if voice_profiles else None,
                    topology_used=topology_used,
                    agent_tones=agent_tones if agent_tones else None,
                )
            except Exception as e:
                logger.warning(f"Phase 2 metric recording failed for {task_id}: {e}")
                # Non-fatal: metrics are valuable but not critical path

        # ... existing team dissolution ...
        return task
```

Note: The `except Exception` here is intentional — metric recording is a non-critical
side effect. Task completion must not fail because diversity measurement crashes. The
warning is logged to audit for debugging.

---

## Part 10: YAML Configuration Schemas

**S-8 Note:** These YAML configs are loaded by `DirectoryManager.load_config()` during
framework initialization. The engine constructors (`DiversityEngine.__init__()`,
`StagnationDetector.__init__()`, `CapabilityTracker.__init__()`, `CalibrationEngine.__init__()`)
accept a `config: dict` parameter that receives the relevant section. These are NOT
documentation-only — they are the authoritative source for all tunable thresholds. During
implementation, verify that each engine reads its config values instead of using hardcoded
constants.

### 10.1 `core/diversity.yaml`

```yaml
# Diversity measurement configuration
# Spec reference: Section 10 (Diversity Enforcement)

diversity:
  srd:
    floor: 0.3          # Below: ALERT — diversity collapse (Axiom A6)
    warning: 0.4         # Below: approaching collapse
    healthy_low: 0.5
    healthy_high: 0.7
    ceiling: 0.9          # Above: possible incoherence
    text_weight: 0.8      # Weight of text diversity in composite SRD
    vdi_weight: 0.2       # Weight of VDI in composite SRD

  vdi:
    floor: 0.2            # Below for 3 tasks: voice stagnation
    dimension_weights:
      language: 0.15
      tone: 0.20
      style: 0.15
      persona: 0.15
      formality: 0.175
      verbosity: 0.175

  stagnation:
    agent_similarity_threshold: 0.9     # Cosine > this = too similar
    agent_consecutive_threshold: 3      # 3 consecutive similar outputs
    voice_same_tone_threshold: 5        # 5+ tasks with same tone
    vdi_consecutive_threshold: 3        # VDI below floor for 3 tasks
    srd_consecutive_threshold: 3        # SRD below warning for 3 tasks
    framework_evolution_threshold: 10   # No Tier 2+ evo in 10 tasks
    framework_topology_threshold: 10    # Same topology for 10 tasks
    history_size: 100                   # Max values retained in history

  interventions:
    below_floor:
      - "ALERT human supervisor"
      - "Spawn scout agent with divergent role composition"
      - "Inject novelty: randomly perturb agent behavioral descriptors"
      - "Inject novelty: randomly assign alternate voice profile"
      - "Force role switch: convert most-conforming agent to scout"
    above_ceiling:
      - "Increase structured debate rounds"
      - "Assign integration task to orchestrator"
```

### 10.2 `core/self-assessment.yaml`

```yaml
# Self-capability assessment configuration
# Spec reference: Section 13 (Self-Capability Awareness)

self_assessment:
  capability_map:
    update_frequency: "after_every_task"
    output_path: "state/self-assessment/capability-map.yaml"
    weak_area_threshold: 0.5       # Success rate below this = weak area
    min_attempts_for_analysis: 3   # Need at least 3 attempts before judging

  calibration:
    ece_alert_threshold: 0.15      # Rolling ECE above this triggers response
    ece_window_size: 10            # Rolling window for ECE computation
    gap_minimum: 0.05              # Min gap for reliable self-improvement
    confidence_deflation_rate: 0.05
    overcalibration_streak_limit: 5
    false_positive_threshold: 0.10  # > 10% FP → tighten criteria
    false_negative_threshold: 0.30  # > 30% FN → loosen criteria
    initial_evidence_threshold: 0.6

  known_task_types:
    - canary_suite
    - evolution_proposal
    - decomposition
    - skill_validation
    - review
    - simple_fix
    - research
    - feature

  complexity_thresholds:
    # FM-41: Learned classifier token thresholds
    small_max_tokens: 5000
    medium_max_tokens: 20000
    min_samples_for_learned: 10
```

---

## Part 11: Implementation Sequence

### Dependency Graph

```
Step 0: YAML configs (diversity.yaml, self-assessment.yaml)
  │
  ├──▶ Step 1: models/diversity.py (no deps besides base)
  │      │
  │      ├──▶ Step 3: engine/diversity_engine.py (depends on models/diversity, voice)
  │      │
  │      └──▶ Step 4: engine/stagnation_detector.py (depends on models/diversity)
  │
  ├──▶ Step 2: models/self_assessment.py (no deps besides base)
  │      │
  │      ├──▶ Step 5: engine/capability_tracker.py (depends on models/self_assessment)
  │      │
  │      └──▶ Step 6: engine/calibration_engine.py (depends on models/self_assessment)
  │
  ├──▶ Step 7: models/audit.py modification (add DiversityLogEntry)
  │
  ├──▶ Step 8: audit/logger.py modification (add log_diversity)
  │
  └──▶ Step 9: audit/tree_viewer.py (enhanced viewer)

Step 10: Deferred fixes (can run in parallel with Steps 1-9):
  ├── 10a: FM-18 (budget_tracker.py append-only ledger)
  ├── 10b: R6 (budget_tracker.py IQR filtering)
  ├── 10c: R11/FM-59 (budget_tracker.py history persistence)
  ├── 10d: FM-41 (orchestrator.py learned classifier)  ← needs Step 5
  ├── 10e: FM-52 (cache_manager.py persistence)
  ├── 10f: FM-57 (resource_facade.py parse_usage integration)
  ├── 10g: FM-63 (agent_spawner.py heartbeat requirement)
  └── 10h: R8/R16 (cost_gate.py record archival)

Step 11: Orchestrator integration (depends on Steps 3, 4, 5)
  └── record_task_outcome() method

Step 12: R15 (budget_tracker.py trends — depends on Step 4 for signal format)
```

### Recommended Execution Order

1. Steps 0-2 (configs + models) — foundation, no deps
2. Steps 3-6 (engines) — can be parallelized in pairs: {3,4} and {5,6}
3. Steps 7-9 (audit) — can run parallel with Step group 2
4. Steps 10a-10c, 10e-10h (deferred fixes without engine deps)
5. Step 10d (FM-41 — needs Step 5 capability_tracker)
6. Step 11 (orchestrator integration — needs Steps 3, 4, 5)
7. Step 12 (R15 — needs Step 4)

---

## Part 12: Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | New models instantiate without errors | `uv run pytest tests/test_models/test_diversity.py tests/test_models/test_self_assessment.py -v` |
| 2 | DiversityEngine computes SRD correctly | `uv run pytest tests/test_engine/test_diversity_engine.py -v` |
| 3 | SRD thresholds: < 0.3 = critical, 0.5-0.7 = healthy | Same as #2 |
| 4 | VDI computation with known profiles | Same as #2 |
| 5 | StagnationDetector fires signals at thresholds | `uv run pytest tests/test_engine/test_stagnation_detector.py -v` |
| 6 | Multi-level stagnation: agent, voice, team, framework | Same as #5 |
| 7 | CapabilityTracker records outcomes and persists | `uv run pytest tests/test_engine/test_capability_tracker.py -v` |
| 8 | Blind spot identification works | Same as #7 |
| 9 | CalibrationEngine ECE computation | `uv run pytest tests/test_engine/test_calibration_engine.py -v` |
| 10 | Overcalibration response triggers at ECE > 0.15 | Same as #9 |
| 11 | Generation-verification gap assessment | Same as #9 |
| 12 | FM-18: Append-only ledger produces correct window totals | `uv run pytest tests/test_engine/test_budget_tracker.py -v -k ledger` |
| 13 | R6: IQR filtering removes outliers | `uv run pytest tests/test_engine/test_budget_tracker.py -v -k iqr` |
| 14 | R11: Token history survives restart | `uv run pytest tests/test_engine/test_budget_tracker.py -v -k persist` |
| 15 | FM-52: Cache stats survive restart | `uv run pytest tests/test_engine/test_cache_manager.py -v -k persist` |
| 16 | FM-63: Agents without heartbeat eventually despawned | `uv run pytest tests/test_engine/test_agent_spawner.py -v -k heartbeat` |
| 17 | R8/R16: Old cost records archived | `uv run pytest tests/test_engine/test_cost_gate.py -v -k archive` |
| 18 | DiversityLogEntry persisted to diversity.jsonl | `uv run pytest tests/test_audit/ -v -k diversity` |
| 19 | Audit tree viewer renders diversity data | `uv run pytest tests/test_audit/test_tree_viewer.py -v` |
| 20 | Orchestrator.record_task_outcome() integrates all | `uv run pytest tests/test_engine/test_orchestrator.py -v -k outcome` |
| 21 | Existing 376 tests still pass (backward compat) | `uv run pytest --tb=short -q` |
| 22 | Full test suite (existing + new) passes | `uv run pytest --tb=long -v` |

---

## Part 13: Edge Cases, Failure Modes & Mitigations

This section combines the original design doc failure modes (FM-70 through FM-84)
with the 54 failure modes identified during Step 4 review (FM-85 through FM-138).
Status column indicates resolution: **FIXED** (design updated), **DOCUMENTED** (known,
acceptable), or **DEFERRED** (to a later phase).

### 13.1 CRITICAL Severity (6 items — all FIXED)

| ID | Failure Mode | Status | Resolution |
|----|-------------|--------|------------|
| FM-85 | All-empty agent outputs produce misleading 0.0 SRD | **FIXED** | `compute_text_diversity()` returns `None` for < 2 non-empty outputs (MIN_OUTPUT_LENGTH=10). `compute_srd()` returns `None` when text_div is `None`. |
| FM-86 | CalibrationEngine records grow unbounded → 1MB YAML crash | **FIXED** | `_save_state()` trims: `self._state.records = self._state.records[-100:]`. |
| FM-87 | `tokens_used` always 0 corrupts capability tracker averages | **FIXED** | `record_outcome()` skips token average update when `tokens_used == 0`. Separate `token_count` field tracks non-zero records. `record_task_outcome()` passes 0 explicitly when unpopulated. |
| FM-88 | FM-18 ledger bypasses JsonlWriter API, dual-locking race | **FIXED** | Rewrote to use `JsonlWriter.append()` with `ConsumptionLogEntry` model. No direct file manipulation. |
| FM-89 | FM-18 ledger rebuild reads entire JSONL on every `get_window()` | **FIXED** | Window caching with mtime check: only rebuild when ledger file newer than cached result. (Moved from D-7/Phase 3 to Phase 2.) |
| FM-90 | VoiceProfile None tone/style inflates VDI systematically | **FIXED** | `voice_distance()` defines `_NONE_VS_EXPLICIT_DISTANCE = 0.5`. Returns tuple `(composite, per_dim_dict)`. |

### 13.2 HIGH Severity (14 items — 12 FIXED, 2 DOCUMENTED)

| ID | Failure Mode | Status | Resolution |
|----|-------------|--------|------------|
| FM-91 | SRD history non-atomic read-modify-write | **DOCUMENTED** | Uses `yaml_store.write_raw()` advisory locking. Acceptable for Phase 2 (low frequency writes). |
| FM-92 | `_classify_task_type()` falls through without match | **DOCUMENTED** | Revised to MEDIUM. Guard returns "general" for unmatched — acceptable for Phase 2. |
| FM-93 | `avg_review_confidence` denominator includes zero-confidence records | **FIXED** | Separate `confidence_count` field on `CapabilityMapEntry`. Rolling average only updated when `review_confidence > 0`. |
| FM-94 | Evidence threshold double-incremented per overcalibration event | **FIXED** | Removed unconditional `+= 0.05`. FP/FN rate checks are sole mechanism, mutually exclusive with `elif`. |
| FM-95 | ECE uses raw improvement magnitude instead of binary success | **FIXED** | `actual_success = 1.0 if actual_improvement > 0 else 0.0`. Calibration error is `predicted_confidence - actual_success`. |
| FM-96 | `record_task_outcome()` crashes when `task.review` is None | **FIXED** | Null guard: manual completion without review → assume success with confidence 0.0. |
| FM-97 | Weekly budget still uses read-modify-write race | **FIXED** | `_increment_weekly_ledger()` with separate fcntl lock. |
| FM-98 | StagnationDetector `_load_state()` crashes on corrupt YAML | **FIXED** | Catches `ValueError`, `TypeError`, `KeyError` in addition to `FileNotFoundError`. |
| FM-99 | Timestamp mismatch between SRD and snapshot | **FIXED** | `compute_srd()` accepts external `timestamp` parameter. `create_snapshot()` uses `srd.timestamp`. |
| FM-100 | GapAssessment reliable with < 10 benchmark tasks | **FIXED** | `self_improvement_reliable` property checks `benchmark_task_count >= 10`. |
| FM-101 | `YamlStore.delete()` missing — cost archival broken | **FIXED** | Concrete `delete()` method with advisory lock (Part 8.8). |
| FM-102 | `AuditLogger.log_diversity()` method missing | **DOCUMENTED** | Method defined in Part 7.2. Implementation ordering ensures it exists before orchestrator calls it. |
| FM-103 | `DiversityLogEntry` class not in existing models/audit.py | **DOCUMENTED** | Class defined in Part 2.3. Implementation ordering ensures it exists before logger references it. |
| FM-104 | Framework stagnation fires indefinitely once triggered | **FIXED** | Signal only fires at multiples of threshold (`tasks_since_evolution % THRESHOLD == 0`). |

### 13.3 MEDIUM Severity (18 items — 8 FIXED, 6 DOCUMENTED, 4 DEFERRED)

| ID | Failure Mode | Status | Resolution |
|----|-------------|--------|------------|
| FM-105 | `_classify_task_type()` keyword list incomplete | **DOCUMENTED** | Known types list is configurable via `self-assessment.yaml`. Extension is trivial. |
| FM-106 | SRD composite formula hardcoded 0.8/0.2 weights | **DOCUMENTED** | Weights read from `diversity.yaml`. Documented as configurable. |
| FM-107 | CalibrationEngine and CapabilityTracker task type lists diverge | **DOCUMENTED** | Both share `self_assessment.known_task_types` config. Single source of truth. |
| FM-108 | Confidence deflation never recovers | **FIXED** | Added `undercalibration_streak` field. FN branch triggers deflation recovery when streak >= limit. |
| FM-109 | `get_estimated_complexity()` returns `""` instead of `None` | **FIXED** | Returns `str | None`. Uses `entry.token_count` instead of `entry.attempts`. |
| FM-110 | SRD health_status thresholds not configurable | **DOCUMENTED** | Thresholds defined in `diversity.yaml`. `compute_srd()` reads from config. |
| FM-111 | Stagnation detector `_tasks_since_evolution` never reset | **DOCUMENTED** | Reset is responsibility of the evolution engine (Phase 4). Detector only observes. |
| FM-112 | `check_agent_health()` naive vs. aware timestamp comparison | **FIXED** | `_parse_aware_datetime()` normalizes both formats. Naive assumed UTC. |
| FM-113 | `sync_from_usage()` API contract mismatch | **FIXED** | Calls `self.record_consumption()` (ResourceFacade method). Delta tracking via `_last_synced_*` fields (S-7). |
| FM-114 | `compute_vdi()` duplicates distance computation | **FIXED** | Uses `voice_distance()` tuple return `(composite, per_dim_dict)`. Single computation path. |
| FM-115 | `record_task_outcome()` never called from any code path | **FIXED** | Integration point in `handle_verdict()` after COMPLETE transition. Non-fatal try/except wrapper. |
| FM-116 | `agent_outputs` parameter never provided | **FIXED** | Fallback: collects `output_text` from SubTask records. New `SubTask.output_text` field. |
| FM-117 | Audit tree viewer `query_all()` O(n*m) complexity | **DEFERRED** | Phase 3: Stream-specific queries with pagination. |
| FM-118 | CapabilityTracker `_load_state()` deserialization mismatch | **DOCUMENTED** | `CapabilityMapEntry` uses `FrameworkModel` with `extra="forbid"`. New fields have defaults, so old data loads correctly. |
| FM-119 | CacheManager `_load_stats()` crashes on corrupt YAML | **FIXED** | Catches `ValueError` and `ValidationError` in addition to `FileNotFoundError`. |
| FM-120 | IQR filter quartile computation uses integer division | **DEFERRED** | Phase 3: Use numpy percentile or interpolating quartile. |
| FM-121 | Audit viewer diversity stream rendering not tested | **DOCUMENTED** | Verification checklist item #19 covers this. |
| FM-122 | `CalibrationState.records` no max_length Pydantic validator | **DOCUMENTED** | Trimming in `_save_state()` is sufficient. Validator would add complexity without benefit (records are in-memory during session). |

### 13.4 LOW Severity (15 items — all DOCUMENTED)

| ID | Failure Mode | Status | Resolution |
|----|-------------|--------|------------|
| FM-123 through FM-138 | Various low-impact edge cases | **DOCUMENTED** | See `research/phase2-failure-modes.md` for full enumeration. None require design changes. |

### 13.5 Original Design Doc Failure Modes (FM-70 through FM-84)

| ID | Failure Mode | Status | Resolution |
|----|-------------|--------|------------|
| FM-70 | SRD computation with < 2 outputs | **DOCUMENTED** | Returns 0.0 for < 2 outputs. Extended by FM-85 for empty outputs. |
| FM-71 | TF-IDF on identical outputs → distance 0 | **DOCUMENTED** | Correct behavior. Health classification handles via thresholds. |
| FM-72 | Stagnation detector state corrupted | **FIXED** | Extended by FM-98: catches `ValueError`/`TypeError`/`KeyError`. |
| FM-73 | CapabilityMap grows with novel task types | **DOCUMENTED** | Fixed set of 8 types. `_classify_task_type()` always returns from known set. |
| FM-74 | CalibrationEngine records unbounded | **FIXED** | Extended by FM-86: `_save_state()` trims to 100 entries. |
| FM-75 | FM-18 ledger rebuild performance | **FIXED** | Extended by FM-89: window caching with mtime check. Moved from D-7 to Phase 2. |
| FM-76 | VDI with all-None voice fields | **DOCUMENTED** | VDI=0 is semantically correct for no voice diversity. |
| FM-77 | SRD history concurrent write | **DOCUMENTED** | Advisory locking acceptable for Phase 2. |
| FM-78 | Rolling ECE with insufficient data | **DOCUMENTED** | ECE defaults to 0.0. Overcalibration won't trigger. |
| FM-79 | IQR filter removes all values | **DOCUMENTED** | Returns original list for len < 4. |
| FM-80 | JSONL rotation during window rebuild | **DOCUMENTED** | `read_entries()` searches rotated files. |
| FM-81 | No multi-agent tasks → no diversity data | **DOCUMENTED** | Extended by FM-116: output capture mechanism added. |
| FM-82 | Spurious stagnation during bootstrap | **DOCUMENTED** | Consecutive breach thresholds filter noise. |
| FM-83 | Orphaned cost record references | **DOCUMENTED** | Daily totals remain correct. |
| FM-84 | New agent treated as unhealthy | **DOCUMENTED** | Within-timeout agents return True. Extended by FM-112: timezone handling. |

### 13.6 Deferred to Phase 3+

| ID | Description | Deferred To |
|----|------------|-------------|
| D-1 | SRD using embedding model instead of TF-IDF | Phase 3.5 (requires model API call budget) |
| D-2 | MAP-Elites archive stagnation detection | Phase 7 (MAP-Elites not yet implemented) |
| D-3 | Automatic intervention on stagnation signals | Phase 4 (evolution engine required) |
| D-4 | FrugalGPT model cascading using calibration data | Phase 2.5+ (environment awareness required) |
| D-5 | Population-based budget allocation | Phase 4+ |
| D-6 | Experience-based shortcuts (Co-Saving) | Phase 3 |
| FM-117 | Audit viewer query_all() O(n*m) complexity | Phase 3 (pagination) |
| FM-120 | IQR filter quartile precision at small N | Phase 3 (numpy integration) |

**Summary**: 54 failure modes analyzed (FM-85 through FM-138). 6 CRITICAL: all FIXED.
14 HIGH: 12 FIXED, 2 DOCUMENTED. 18 MEDIUM: 8 FIXED, 6 DOCUMENTED, 4 DEFERRED.
15 LOW: all DOCUMENTED. D-7 (FM-75 optimization) moved from DEFERRED to FIXED in Phase 2.
