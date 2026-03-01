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
