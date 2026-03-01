"""Monetary cost approval gateway.
Spec reference: Section 18.5 (Cost-Aware Decision Making).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..models.base import generate_id
from ..models.resource import CostApproval, CostRecord, DailyCostSummary, SpendLevel
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.cost_gate")


class CostCapExceededError(RuntimeError):
    """Raised when daily/weekly cost cap would be exceeded."""


class ApprovalRequiredError(RuntimeError):
    """Raised when human approval is needed for a cost."""
    def __init__(self, approval: CostApproval):
        self.approval = approval
        super().__init__(
            f"Human approval required: {approval.purpose} "
            f"(${approval.amount:.2f}, level={SpendLevel(approval.spend_level).name})"
        )


class CostGate:
    """Enforces monetary cost approval tiers.

    Spend levels (Section 18.5):
    - FREE (0): File ops, git, Claude API — automatic
    - LOW (1): Web search, small API < $0.10 — auto with logging, daily cap
    - MEDIUM (2): Large API $0.10-$10 — async human approval (30min timeout)
    - HIGH (3): SaaS, > $10 — synchronous human approval required

    Design invariants:
    - Every cost-incurring action logged with amount, purpose, approval
    - Daily cap enforced regardless of spend level
    - Weekly cap enforced regardless of spend level
    - No action proceeds without explicit approval at correct level
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        daily_cap: float = 10.0,
        weekly_cap: float = 50.0,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self.daily_cap = daily_cap
        self.weekly_cap = weekly_cap
        self._costs_base = f"instances/{domain}/state/resources/costs"

    def request_approval(
        self,
        amount: float,
        purpose: str,
        task_id: str | None = None,
        agent_id: str | None = None,
    ) -> CostApproval:
        """Request approval for a cost-incurring action.

        Returns CostApproval with approved=True for auto-approved levels.
        Raises ApprovalRequiredError for levels needing human input.
        Raises CostCapExceededError if daily/weekly cap would be exceeded.
        """
        level = self._classify_spend(amount)

        # Check caps first (for non-FREE amounts)
        if level != SpendLevel.FREE:
            self._check_caps(amount)

        if level == SpendLevel.FREE:
            return CostApproval(spend_level=level, amount=amount, purpose=purpose, approved=True)

        if level == SpendLevel.LOW:
            approval = CostApproval(
                spend_level=level, amount=amount, purpose=purpose,
                approved=True, approved_by="auto_low"
            )
            self._record_cost(approval, task_id, agent_id)
            return approval

        if level == SpendLevel.MEDIUM:
            approval = CostApproval(
                spend_level=level, amount=amount, purpose=purpose, approved=False
            )
            self._record_cost(approval, task_id, agent_id)
            raise ApprovalRequiredError(approval)

        # HIGH
        approval = CostApproval(
            spend_level=level, amount=amount, purpose=purpose, approved=False
        )
        self._record_cost(approval, task_id, agent_id)
        raise ApprovalRequiredError(approval)

    def approve(self, record_id: str, approver: str) -> CostRecord:
        """Human approves a pending cost record.

        FM-43: After approving, update daily summary's total_spent.
        """
        record = self._load_record(record_id)
        record.approved = True
        record.approved_by = approver
        self._save_record(record)

        # FM-43: Update daily summary with the approved amount
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.get_daily_summary()
        daily.total_spent += record.amount
        daily.records.append(record.id)
        self.yaml_store.ensure_dir(f"{self._costs_base}/daily")
        self.yaml_store.write(f"{self._costs_base}/daily/{today}.yaml", daily)

        logger.info(f"Cost approved: {record.purpose} (${record.amount:.2f}) by {approver}")
        return record

    def reject(self, record_id: str, reason: str) -> CostRecord:
        """Human rejects a pending cost record."""
        record = self._load_record(record_id)
        record.approved = False
        record.approved_by = f"REJECTED: {reason}"
        self._save_record(record)
        logger.info(f"Cost rejected: {record.purpose} — {reason}")
        return record

    def get_daily_summary(self) -> DailyCostSummary:
        """Get today's cost summary."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = f"{self._costs_base}/daily/{today}.yaml"
        try:
            return self.yaml_store.read(path, DailyCostSummary)
        except FileNotFoundError:
            return DailyCostSummary(date=today, daily_cap=self.daily_cap)

    def _classify_spend(self, amount: float) -> SpendLevel:
        """Classify monetary amount into spend level."""
        if amount <= 0:
            return SpendLevel.FREE
        if amount < 0.10:
            return SpendLevel.LOW
        if amount < 10.0:
            return SpendLevel.MEDIUM
        return SpendLevel.HIGH

    def _check_caps(self, amount: float) -> None:
        """Check daily and weekly caps. Raises CostCapExceededError if exceeded."""
        daily = self.get_daily_summary()
        if daily.total_spent + amount > self.daily_cap:
            raise CostCapExceededError(
                f"Daily cap would be exceeded: ${daily.total_spent:.2f} + ${amount:.2f} "
                f"> ${self.daily_cap:.2f}"
            )

        # Weekly cap: aggregate last 7 daily summaries
        weekly_total = self._get_weekly_total()
        if weekly_total + amount > self.weekly_cap:
            raise CostCapExceededError(
                f"Weekly cap would be exceeded: ${weekly_total:.2f} + ${amount:.2f} "
                f"> ${self.weekly_cap:.2f}"
            )

    def _get_weekly_total(self) -> float:
        """Sum daily totals for the last 7 days."""
        total = 0.0
        today = datetime.now(timezone.utc).date()
        for i in range(7):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            path = f"{self._costs_base}/daily/{day}.yaml"
            try:
                summary = self.yaml_store.read(path, DailyCostSummary)
                total += summary.total_spent
            except FileNotFoundError:
                continue
        return total

    def _record_cost(self, approval: CostApproval, task_id: str | None, agent_id: str | None) -> CostRecord:
        """Create and persist a cost record."""
        record = CostRecord(
            id=generate_id("cost"),
            timestamp=datetime.now(timezone.utc),
            spend_level=SpendLevel(approval.spend_level),
            amount=approval.amount,
            purpose=approval.purpose,
            approved=approval.approved,
            approved_by=approval.approved_by,
            task_id=task_id,
            agent_id=agent_id,
        )
        self._save_record(record)

        # FM-42: Only add to daily records if approved.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.get_daily_summary()
        if approval.approved:
            daily.total_spent += approval.amount
            daily.records.append(record.id)
            self.yaml_store.ensure_dir(f"{self._costs_base}/daily")
            self.yaml_store.write(f"{self._costs_base}/daily/{today}.yaml", daily)

        return record

    def _save_record(self, record: CostRecord) -> None:
        self.yaml_store.ensure_dir(self._costs_base)
        self.yaml_store.ensure_dir(f"{self._costs_base}/daily")
        self.yaml_store.write(f"{self._costs_base}/{record.id}.yaml", record)

    def _load_record(self, record_id: str) -> CostRecord:
        return self.yaml_store.read(f"{self._costs_base}/{record_id}.yaml", CostRecord)

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
