"""Prompt caching strategy for rate-limit arbitrage.
Spec reference: Section 18.3 (Caching Strategy).

Key insight: Cached tokens don't count toward ITPM.
By caching the shared prefix (constitution + config), we get 2-5x effective ITPM.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from ..models.base import FrameworkModel
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.cache_manager")


class CacheStats(FrameworkModel):
    """Cache hit/miss tracking."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0  # Tokens that didn't count toward ITPM

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests


class CacheManager:
    """Manages prompt caching for rate-limit arbitrage.

    Strategy (Section 18.3):
    1. Shared system prompt prefix across all agents
       - Constitution (Ring 0): ~500 tokens, NEVER changes within session
       - Framework config (Ring 1): ~300 tokens, changes on evolution only
       - Resource awareness (Ring 1): ~100 tokens, changes per window
    2. Role-specific fragments appended AFTER shared prefix
    3. Task context appended last (most variable)

    Cache hierarchy (most -> least stable):
    - Level 1: Constitution + axioms (~500 tokens) -- session-stable
    - Level 2: Role composition (~200 tokens) -- task-stable
    - Level 3: Resource awareness (~100 tokens) -- window-stable
    - Level 4: Task context -- changes per request (not cached)

    Design invariants:
    - Shared prefix must exceed 1024 tokens for Anthropic cache
    - Prefix must be IDENTICAL across agents for cache hits
    - Constitution hash checked on every cache refresh
    """

    # Minimum tokens for effective caching (Anthropic requirement)
    MIN_CACHE_BLOCK = 1024

    def __init__(self, yaml_store: YamlStore | None = None, domain: str = "meta"):
        self._prefix_cache: str | None = None
        self._prefix_hash: str | None = None
        self._prefix_tokens: int = 0
        self._yaml_store = yaml_store
        self._stats_path = f"instances/{domain}/state/resources/cache-stats.yaml"
        self.stats = self._load_stats()

    def get_shared_prefix(self, constitution_text: str, framework_config: str) -> str:
        """Get the cached shared prefix, rebuilding if changed.

        Returns the system prompt prefix that should be identical
        across all agents to maximize cache hits.
        """
        # Compute hash of inputs
        content = constitution_text + framework_config
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        if self._prefix_hash == content_hash and self._prefix_cache is not None:
            self.stats.cache_hits += 1
            self.stats.total_requests += 1
            self._persist_stats()
            return self._prefix_cache

        # Cache miss -- rebuild prefix
        self._prefix_cache = self._build_prefix(constitution_text, framework_config)
        self._prefix_hash = content_hash
        # FM-35 FIX: Use same CHARS_PER_TOKEN as PromptComposer (3.5, not 4)
        self._prefix_tokens = int(len(self._prefix_cache) / 3.5)
        self.stats.cache_misses += 1
        self.stats.total_requests += 1
        self._persist_stats()

        if self._prefix_tokens < self.MIN_CACHE_BLOCK:
            logger.warning(
                f"Shared prefix is only ~{self._prefix_tokens} tokens, "
                f"below {self.MIN_CACHE_BLOCK} minimum for cache hits. "
                f"Consider adding more shared content."
            )

        return self._prefix_cache

    def estimate_cache_savings(self, total_input_tokens: int) -> int:
        """Estimate tokens saved from caching on a request.

        If the prefix is cached, those tokens don't count toward ITPM.

        FM-36 NOTE: This method is ESTIMATION ONLY -- it does NOT update stats.
        Call `record_cache_savings()` after the request to update stats once.
        """
        if self._prefix_tokens > 0:
            return min(self._prefix_tokens, total_input_tokens)
        return 0

    def record_cache_savings(self, saved_tokens: int) -> None:
        """Record actual cache savings after a request completes.

        FM-36 FIX: Separated from estimate_cache_savings() to prevent
        double-counting when estimate is called multiple times per request.
        """
        self.stats.tokens_saved += saved_tokens
        self._persist_stats()

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
            except Exception:
                # FM-119: Catches FileNotFoundError (first run), ValueError,
                # ValidationError (schema mismatch), yaml.ScannerError (corrupt YAML)
                pass  # Start fresh
        return CacheStats()

    def _build_prefix(self, constitution_text: str, framework_config: str) -> str:
        """Build the shared prefix from constitution + config.

        Order matters for cache hits -- must be identical across all agents.
        """
        return (
            "# CONSTITUTION (Ring 0 — immutable)\n"
            f"{constitution_text}\n\n"
            "# FRAMEWORK CONFIGURATION\n"
            f"{framework_config}\n"
        )
