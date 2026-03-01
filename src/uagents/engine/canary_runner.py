"""Fixed micro-benchmark runner for model fingerprinting.
Spec reference: Section 19.1 (Model Fingerprinting).

Executes 5 fixed canary tasks at session start to produce a ModelFingerprint.
Tasks are FIXED and never change — they are the ruler, not the subject.

Key constraints:
- Total budget: < 5000 tokens
- Total runtime: < 2 minutes
- Canary expectations loaded from core/canary-expectations.yaml
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import logging
import re
import time
from datetime import datetime, timezone

import yaml

from ..models.base import generate_id
from ..models.environment import (
    CanaryResult,
    CanarySuiteResult,
    ModelExecuteFn,
    ModelFingerprint,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.canary_runner")

# Scoring method constants
SCORE_KEYWORD_MATCH = "keyword_match"
SCORE_CONSTRAINT_CHECK = "constraint_check"
SCORE_CODE_VALIDATION = "code_validation"
SCORE_DIVERSITY = "diversity_score"
SCORE_EXACT_FIELDS = "exact_fields"

# Canary task names — fixed, never changed
CANARY_TASKS = [
    "reasoning",
    "instruction_following",
    "code_generation",
    "creative_divergence",
    "tool_use",
]

# Mapping from canary task name to fingerprint dimension
TASK_TO_DIMENSION = {
    "reasoning": "reasoning_score",
    "instruction_following": "instruction_score",
    "code_generation": "code_score",
    "creative_divergence": "creative_score",
    "tool_use": "tool_score",
}

# MF-1: Named constraint checkers replace eval().
# Each checker takes (output: str, arg: Any) -> bool.
CONSTRAINT_CHECKERS: dict[str, object] = {
    "starts_with": lambda output, arg: output.strip().startswith(arg),
    "ends_with": lambda output, arg: output.strip().endswith(arg),
    "regex_count_eq": lambda output, arg: (
        len(re.findall(arg["pattern"], output, re.MULTILINE)) == arg["count"]
    ),
    "line_count_le": lambda output, arg: len(output.strip().split("\n")) <= arg,
}


def _run_code_tests(code: str, test_cases: list[dict]) -> float:
    """Execute code and test cases in restricted namespace.

    Module-level function (not nested) so it can be pickled by
    ProcessPoolExecutor for subprocess execution.
    """
    namespace: dict = {"__builtins__": {"range": range, "int": int}}
    try:
        exec(code, namespace)  # noqa: S102 — sandboxed canary eval
    except Exception:
        return 0.0
    func = namespace.get("fibonacci")
    if func is None or not callable(func):
        return 0.0
    passed = 0
    for tc in test_cases:
        try:
            result = func(tc["input"])
            if result == tc["expected"]:
                passed += 1
        except Exception:
            pass
    return passed / len(test_cases)


class CanaryRunner:
    """Executes fixed micro-benchmark tasks and produces ModelFingerprints.

    Design invariants:
    - Canary tasks are FIXED — loaded from core/canary-expectations.yaml
    - Budget-capped: entire suite < 5000 tokens, < 2 minutes
    - Scoring is deterministic: no LLM-as-judge, only pattern matching
    - Results stored to state/environment/canary-results/
    - SF-10: Expectations file hash verified at startup
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        model_id: str = "unknown",  # SF-9: Accept model_id as parameter
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._model_id = model_id
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)
        self.yaml_store.ensure_dir(f"{self._state_base}/canary-results")

        # Load canary expectations (fail-loud if missing)
        raw = yaml_store.read_raw("core/canary-expectations.yaml")
        expectations = raw.get("canary_expectations")
        if expectations is None:
            raise ValueError(
                "core/canary-expectations.yaml missing 'canary_expectations' section"
            )
        self._expectations: dict = expectations

        # SF-10: Verify expectations hash to detect accidental modifications
        self._verify_expectations_hash(raw)

        # Load config (SF-5: config loading consolidated — see EnvironmentMonitor)
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        cs = ea.get("canary_suite", {})
        self._max_total_tokens = int(cs.get("max_total_tokens", 5000))
        self._max_runtime_seconds = int(cs.get("max_runtime_seconds", 120))
        self._per_task_token_cap = int(cs.get("per_task_token_cap", 1200))
        self._pass_score = float(cs.get("pass_score", 0.7))
        # SF-7/IFM-16: Use drift_detection.history_size for canary result trimming
        dd = ea.get("drift_detection", {})
        self._history_size = int(dd.get("history_size", 10))

    def _verify_expectations_hash(self, raw: dict) -> None:
        """SF-10: Verify SHA-256 of canary expectations against stored hash.

        On first run, stores the hash. On subsequent runs, compares and
        logs CRITICAL if the expectations have been modified.
        """
        canonical = yaml.dump(
            raw.get("canary_expectations", {}),
            default_flow_style=False,
            sort_keys=True,
        )
        current_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        hash_path = f"{self._state_base}/canary-expectations-hash.yaml"
        try:
            stored = self.yaml_store.read_raw(hash_path)
            stored_hash = stored.get("sha256", "")
            if stored_hash != current_hash:
                logger.critical(
                    "CANARY EXPECTATIONS MODIFIED! "
                    f"Stored hash: {stored_hash[:16]}..., "
                    f"Current hash: {current_hash[:16]}... "
                    "This invalidates all historical fingerprint comparisons. "
                    "If this change is intentional, delete "
                    f"{hash_path} and restart."
                )
                raise ValueError(
                    "Canary expectations hash mismatch — "
                    "historical fingerprint comparisons invalidated. "
                    "See log for details."
                )
        except FileNotFoundError:
            # First run — store hash
            self.yaml_store.write_raw(hash_path, {"sha256": current_hash})
            logger.info(
                f"Canary expectations hash stored: {current_hash[:16]}..."
            )

    def run_suite(self, execute_fn: ModelExecuteFn) -> CanarySuiteResult:
        """Execute all 5 canary tasks and return suite result.

        Args:
            execute_fn: Callable that takes (prompt: str, max_tokens: int)
                and returns (output: str, tokens_used: int).
                This is the model execution interface — injected to allow
                testing without actual model calls.

        Returns:
            CanarySuiteResult with all 5 results and computed fingerprint.

        Raises:
            RuntimeError: If suite exceeds budget or timeout.
        """
        results: list[CanaryResult] = []
        total_tokens = 0
        suite_start = time.monotonic()

        for task_name in CANARY_TASKS:
            # Check budget before each task
            if total_tokens >= self._max_total_tokens:
                logger.warning(
                    f"Canary suite budget exhausted at {total_tokens} tokens "
                    f"after {len(results)} tasks"
                )
                # Score remaining tasks as 0
                result = CanaryResult(
                    task_name=task_name,
                    expected=self._get_expected(task_name),
                    actual="[BUDGET_EXHAUSTED]",
                    score=0.0,
                    tokens_used=0,
                    latency_ms=0,
                )
                results.append(result)
                continue

            # Check timeout
            elapsed = time.monotonic() - suite_start
            if elapsed > self._max_runtime_seconds:
                logger.warning(
                    f"Canary suite timeout at {elapsed:.1f}s "
                    f"after {len(results)} tasks"
                )
                result = CanaryResult(
                    task_name=task_name,
                    expected=self._get_expected(task_name),
                    actual="[TIMEOUT]",
                    score=0.0,
                    tokens_used=0,
                    latency_ms=0,
                )
                results.append(result)
                continue

            # Execute canary task
            prompt = self._get_prompt(task_name)
            task_start = time.monotonic()
            try:
                output, tokens_used = execute_fn(prompt, self._per_task_token_cap)
            except Exception as e:
                logger.error(f"Canary task '{task_name}' execution failed: {e}")
                output = f"[ERROR: {e}]"
                tokens_used = 0
            task_elapsed_ms = int((time.monotonic() - task_start) * 1000)

            # Score the output
            score = self._score_task(task_name, output)
            total_tokens += tokens_used

            result = CanaryResult(
                task_name=task_name,
                expected=self._get_expected(task_name),
                actual=output[:500],  # Truncate for storage
                score=score,
                tokens_used=tokens_used,
                latency_ms=task_elapsed_ms,
            )
            results.append(result)

            logger.info(
                f"Canary '{task_name}': score={score:.2f}, "
                f"tokens={tokens_used}, latency={task_elapsed_ms}ms"
            )

        # Compute fingerprint from results
        fingerprint = self._compute_fingerprint(results)
        total_latency_ms = int((time.monotonic() - suite_start) * 1000)
        all_passed = all(r.score >= self._pass_score for r in results)

        now = datetime.now(timezone.utc)
        suite_result = CanarySuiteResult(
            created_at=now,
            results=results,
            fingerprint=fingerprint,
            total_tokens=total_tokens,
            total_latency_ms=total_latency_ms,
            all_passed=all_passed,
        )

        # Persist result
        self._store_result(suite_result)

        logger.info(
            f"Canary suite complete: all_passed={all_passed}, "
            f"total_tokens={total_tokens}, latency={total_latency_ms}ms"
        )

        return suite_result

    def _get_prompt(self, task_name: str) -> str:
        """Get the prompt for a canary task."""
        task = self._expectations.get(task_name)
        if task is None:
            raise ValueError(f"Unknown canary task: {task_name}")
        prompt = task.get("prompt")
        if prompt is None:
            raise ValueError(f"Canary task '{task_name}' missing 'prompt' field")
        return prompt.strip()

    def _get_expected(self, task_name: str) -> str:
        """Get the expected answer string for a canary task."""
        task = self._expectations.get(task_name)
        if task is None:
            return ""
        return task.get("expected_answer", "")

    def _score_task(self, task_name: str, output: str) -> float:
        """Score a canary task output against expectations.

        Scoring is deterministic — no LLM-as-judge. Uses pattern matching,
        keyword matching, constraint checking, or code validation.
        """
        task = self._expectations.get(task_name)
        if task is None:
            return 0.0
        scoring = task.get("scoring", {})
        method = scoring.get("method", "keyword_match")

        if method == SCORE_KEYWORD_MATCH:
            return self._score_keyword_match(output, scoring)
        elif method == SCORE_CONSTRAINT_CHECK:
            return self._score_constraint_check(output, scoring)
        elif method == SCORE_CODE_VALIDATION:
            return self._score_code_validation(output, scoring)
        elif method == SCORE_DIVERSITY:
            return self._score_diversity(output, scoring)
        elif method == SCORE_EXACT_FIELDS:
            return self._score_exact_fields(output, scoring)
        else:
            logger.warning(f"Unknown scoring method '{method}' for task '{task_name}'")
            return 0.0

    @staticmethod
    def _score_keyword_match(output: str, scoring: dict) -> float:
        """Score by counting required keywords present in output.

        Uses word-boundary matching to prevent partial matches
        (e.g., keyword "A" should not match inside "apples").
        """
        keywords = scoring.get("required_keywords", [])
        min_keywords = scoring.get("min_keywords", len(keywords))
        if not keywords:
            return 0.0
        matched = 0
        for kw in keywords:
            # Use word-boundary matching for single-char keywords,
            # substring matching for multi-char keywords
            if len(kw) <= 2:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, output, re.IGNORECASE):
                    matched += 1
            else:
                if kw.lower() in output.lower():
                    matched += 1
        if matched >= min_keywords:
            return 1.0
        return matched / len(keywords)

    @staticmethod
    def _score_constraint_check(output: str, scoring: dict) -> float:
        """Score by checking named constraints on output.

        MF-1: Uses CONSTRAINT_CHECKERS dict instead of eval().
        Each constraint specifies a `checker` name and `arg` value.
        IFM-18: Logs warning on individual constraint failures.
        """
        constraints = scoring.get("constraints", [])
        if not constraints:
            return 0.0
        passed = 0
        for constraint in constraints:
            checker_name = constraint.get("checker", "")
            arg = constraint.get("arg")
            name = constraint.get("name", checker_name)
            checker_fn = CONSTRAINT_CHECKERS.get(checker_name)
            if checker_fn is None:
                logger.warning(
                    f"Unknown constraint checker '{checker_name}' "
                    f"in constraint '{name}' — scoring 0"
                )
                continue
            try:
                result = checker_fn(output, arg)
                if result:
                    passed += 1
            except Exception as e:
                logger.warning(
                    f"Constraint checker '{name}' raised {type(e).__name__}: "
                    f"{e} — scoring 0 for this constraint"
                )
        return passed / len(constraints)

    @staticmethod
    def _score_code_validation(output: str, scoring: dict) -> float:
        """Score by extracting code and running test cases.

        MF-2: Uses concurrent.futures.ProcessPoolExecutor with 2-second
        timeout instead of bare exec(). Namespace restricted to builtins only.
        """
        test_cases = scoring.get("test_cases", [])
        if not test_cases:
            return 0.0

        # Extract the function from output
        # Look for def fibonacci(...): block
        code_match = re.search(
            r"(def\s+fibonacci\s*\([^)]*\)\s*:.*?)(?=\n\S|\Z)",
            output,
            re.DOTALL,
        )
        if not code_match:
            # Try extracting from code block
            block_match = re.search(r"```(?:python)?\s*\n(.*?)```", output, re.DOTALL)
            if block_match:
                code = block_match.group(1).strip()
            else:
                code = output.strip()
        else:
            code = code_match.group(1).strip()

        # MF-2: Run in subprocess with timeout to prevent infinite loops
        # and restrict namespace (no imports available).
        # Uses module-level _run_code_tests() function for picklability.
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_code_tests, code, test_cases)
                return future.result(timeout=2.0)
        except concurrent.futures.TimeoutError:
            logger.warning("Code validation timed out after 2 seconds")
            return 0.0
        except Exception as e:
            logger.warning(f"Code validation failed: {e}")
            return 0.0

    @staticmethod
    def _score_diversity(output: str, scoring: dict) -> float:
        """Score creative output by counting distinct items and uniqueness."""
        min_items = scoring.get("min_items", 5)

        # Extract numbered items
        items = re.findall(r"^\d+[.)]\s*(.+)$", output, re.MULTILINE)
        if len(items) < min_items:
            # Partial credit for having some items
            return len(items) / min_items * 0.5

        # Check uniqueness: simple word-set Jaccard distance
        scores: list[float] = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                words_i = set(items[i].lower().split())
                words_j = set(items[j].lower().split())
                if not words_i or not words_j:
                    continue
                intersection = len(words_i & words_j)
                union = len(words_i | words_j)
                jaccard_sim = intersection / union if union > 0 else 0.0
                distance = 1.0 - jaccard_sim
                scores.append(distance)

        if not scores:
            return 0.5  # Can't assess diversity with no pairs

        avg_distance = sum(scores) / len(scores)
        uniqueness_threshold = scoring.get("uniqueness_threshold", 0.3)

        if avg_distance >= uniqueness_threshold:
            return 1.0
        return avg_distance / uniqueness_threshold

    @staticmethod
    def _score_exact_fields(output: str, scoring: dict) -> float:
        """Score by extracting specific fields and comparing to expected values."""
        fields = scoring.get("fields", [])
        if not fields:
            return 0.0
        matched = 0
        for field in fields:
            pattern = field.get("pattern", "")
            expected = field.get("expected", "")
            match = re.search(pattern, output)
            if match and match.group(1).strip() == expected:
                matched += 1
        return matched / len(fields)

    def _compute_fingerprint(self, results: list[CanaryResult]) -> ModelFingerprint:
        """Build ModelFingerprint from canary results.

        SF-9: Uses self._model_id (injected via constructor) instead of
        hardcoded model ID.
        """
        scores: dict[str, float] = {}
        for r in results:
            dim = TASK_TO_DIMENSION.get(r.task_name)
            if dim:
                scores[dim] = r.score

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        token_counts = [r.tokens_used for r in results if r.tokens_used > 0]

        return ModelFingerprint(
            created_at=datetime.now(timezone.utc),
            model_id=self._model_id,
            reasoning_score=scores.get("reasoning_score", 0.0),
            instruction_score=scores.get("instruction_score", 0.0),
            code_score=scores.get("code_score", 0.0),
            creative_score=scores.get("creative_score", 0.0),
            tool_score=scores.get("tool_score", 0.0),
            avg_latency_ms=int(sum(latencies) / len(latencies)) if latencies else 0,
            avg_output_tokens=int(sum(token_counts) / len(token_counts)) if token_counts else 0,
        )

    def _store_result(self, suite_result: CanarySuiteResult) -> None:
        """Persist canary suite result to YAML.

        IFM-01: Appends generate_id() suffix to prevent timestamp collisions.
        SF-7/IFM-16: Trims old results to history_size.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("cr").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/canary-results/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, suite_result)
        self._trim_canary_results()

    def _trim_canary_results(self) -> None:
        """SF-7/IFM-16: Remove oldest canary results exceeding history_size."""
        results_dir = f"{self._state_base}/canary-results"
        try:
            files = self.yaml_store.list_dir(results_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > self._history_size:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{results_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)

    def get_latest_result(self) -> CanarySuiteResult | None:
        """Load the most recent canary suite result, or None if none exist."""
        results_dir = f"{self._state_base}/canary-results"
        try:
            files = self.yaml_store.list_dir(results_dir)
        except (NotADirectoryError, FileNotFoundError):
            return None
        yaml_files = [f for f in files if f.endswith(".yaml") and not f.endswith(".lock")]
        if not yaml_files:
            return None
        latest = sorted(yaml_files)[-1]
        return self.yaml_store.read(
            f"{results_dir}/{latest}", CanarySuiteResult
        )
