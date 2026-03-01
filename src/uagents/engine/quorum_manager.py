"""Quorum manager for Tier 2 evolution approval.
Spec reference: Section 7.3 (Quorum Sensing).

Implements sealed-ballot quorum voting with anti-gaming rules:
- Minimum 3 voters from different role compositions
- Scout agent always participates
- Sealed votes (not visible until all submitted)
- Role maturity requirement (>= min_tasks_for_voter tasks)
- Max 1 voter per role lineage
- Roles from same evolution proposal can't both vote

Key constraints:
- Voters CANNOT see others' votes before submitting (sealed)
- Proposal author CANNOT vote on own proposal
- QuorumSession persisted to YAML for crash recovery
- Votes persisted individually for audit trail
- Timeout enforcement for vote collection

Literature basis:
- Anthropic 2024: 78% alignment faking — independent voting critical
- COCOA (EMNLP 2025): co-evolving constitutions with safeguards
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..models.base import generate_id
from ..models.evolution import (
    EvolutionProposal,
    QuorumResult,
    QuorumVote,
)
from ..models.governance import (
    QuorumEligibility,
    QuorumSession,
    QuorumSessionStatus,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.quorum_manager")


class QuorumError(RuntimeError):
    """Raised when quorum process fails non-recoverably."""


class InsufficientVotersError(QuorumError):
    """Raised when not enough eligible voters are available."""


class QuorumManager:
    """Manages sealed-ballot quorum voting for Tier 2 evolution.

    Design invariants:
    - Votes are sealed: individual votes not revealed until all collected
    - Voters must be from different role compositions
    - Scout always votes (anti-homogenization)
    - Role maturity enforced (>= min_tasks_for_voter)
    - Max 1 voter per role lineage
    - Roles from same evolution can't both vote
    - Proposal author excluded from voting
    - Sessions persisted for crash recovery

    Usage:
        mgr = QuorumManager(yaml_store, domain)
        session = mgr.create_session(proposal, eligible_roles)
        mgr.submit_vote(session.id, vote)
        result = mgr.tally(session.id)
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._audit_logger = audit_logger

        config_raw = yaml_store.read_raw("core/self-governance.yaml")
        q = config_raw["self_governance"]["quorum"]

        self._min_voters = int(q["minimum_voters"])
        self._threshold = float(q["threshold"])
        self._min_tasks_for_voter = int(q["min_tasks_for_voter"])
        self._max_per_lineage = int(q["max_voters_per_lineage"])
        self._scout_required = bool(q["scout_required"])
        self._vote_timeout_min = int(q["vote_timeout_minutes"])

        self._sessions_dir = "state/governance/quorum_sessions"
        self._votes_dir = "state/governance/quorum_votes"

    def create_session(
        self,
        proposal: EvolutionProposal,
        role_registry: list[dict],
        proposer_role: str = "",
    ) -> QuorumSession:
        """Create a new quorum voting session for a Tier 2 proposal.

        Args:
            proposal: The Tier 2 evolution proposal.
            role_registry: List of role dicts with keys:
                name, task_count, lineage_id, created_by_evolution, is_scout.
            proposer_role: Role name of the proposer (excluded from voting).

        Returns:
            QuorumSession with eligible voters populated.

        Raises:
            InsufficientVotersError: If fewer than minimum_voters are eligible.
        """
        now = datetime.now(timezone.utc)
        session_id = generate_id("quorum")

        eligible = self._compute_eligibility(
            role_registry, proposer_role, proposal.id
        )

        eligible_count = sum(1 for e in eligible if e.eligible)
        if eligible_count < self._min_voters:
            raise InsufficientVotersError(
                f"Only {eligible_count} eligible voters found, "
                f"minimum {self._min_voters} required. "
                f"Ineligible reasons: "
                f"{[e.rejection_reason for e in eligible if not e.eligible]}"
            )

        scout_eligible = [e for e in eligible if e.is_scout and e.eligible]
        if self._scout_required and not scout_eligible:
            raise InsufficientVotersError(
                "No eligible scout role found. Scout participation is required "
                "for quorum voting (anti-homogenization check)."
            )

        session = QuorumSession(
            id=session_id,
            created_at=now,
            proposal_id=proposal.id,
            required_voters=self._min_voters,
            threshold=self._threshold,
            eligible_voters=eligible,
            status=QuorumSessionStatus.COLLECTING,
        )

        self.yaml_store.write(
            f"{self._sessions_dir}/{session_id}.yaml", session
        )

        # S-03-FIX: Governance audit logging
        if self._audit_logger is not None:
            self._audit_logger.log_governance(
                event_type="quorum_session",
                proposal_id=proposal.id,
                quorum_session_id=session_id,
                detail=f"Created: {eligible_count} eligible voters",
            )

        logger.info(
            f"Quorum session {session_id} created for proposal {proposal.id}: "
            f"{eligible_count} eligible voters"
        )
        return session

    def submit_vote(
        self,
        session_id: str,
        voter_id: str,
        voter_role: str,
        vote: str,
        rationale: str,
    ) -> QuorumVote:
        """Submit a sealed vote to a quorum session.

        Args:
            session_id: The quorum session ID.
            voter_id: The agent ID submitting the vote.
            voter_role: The role composition name of the voter.
            vote: "approve" or "reject".
            rationale: Explanation for the vote.

        Returns:
            The created QuorumVote.

        Raises:
            QuorumError: If session not found, voter ineligible, or duplicate vote.
        """
        if vote not in ("approve", "reject"):
            raise QuorumError(
                f"Invalid vote '{vote}'. Must be 'approve' or 'reject'."
            )

        session = self._load_session(session_id)

        if session.status != QuorumSessionStatus.COLLECTING:
            raise QuorumError(
                f"Session {session_id} is in status '{session.status}', "
                f"not 'collecting'. Cannot accept new votes."
            )

        eligible_entry = None
        for e in session.eligible_voters:
            if e.role_name == voter_role:
                eligible_entry = e
                break

        if eligible_entry is None:
            raise QuorumError(
                f"Role '{voter_role}' is not in the eligible voter list "
                f"for session {session_id}."
            )
        if not eligible_entry.eligible:
            raise QuorumError(
                f"Role '{voter_role}' is not eligible to vote: "
                f"{eligible_entry.rejection_reason}"
            )

        for existing_vote_id in session.sealed_votes:
            existing_vote = self._load_vote(existing_vote_id, session_id)
            if existing_vote.voter_role == voter_role:
                raise QuorumError(
                    f"Role '{voter_role}' has already submitted a vote "
                    f"in session {session_id}."
                )

        now = datetime.now(timezone.utc)
        qv = QuorumVote(
            voter_id=voter_id,
            voter_role=voter_role,
            vote=vote,
            rationale=rationale,
            timestamp=now,
        )

        vote_id = generate_id("vote")
        vote_dir = f"{self._votes_dir}/{session_id}"
        vote_path = f"{vote_dir}/{vote_id}.yaml"
        self.yaml_store.write(vote_path, qv)

        session.sealed_votes.append(vote_id)
        if eligible_entry.is_scout:
            session.scout_voted = True

        self.yaml_store.write(
            f"{self._sessions_dir}/{session_id}.yaml", session
        )

        logger.info(
            f"Vote {vote_id} submitted by {voter_role} in session {session_id}"
        )
        return qv

    def tally(self, session_id: str) -> QuorumResult:
        """Tally votes and determine quorum outcome.

        Args:
            session_id: The quorum session to tally.

        Returns:
            QuorumResult with votes, threshold, and approved flag.

        Raises:
            QuorumError: If session not found, insufficient votes, or
                         scout didn't vote (when required).
        """
        session = self._load_session(session_id)

        if session.status not in (
            QuorumSessionStatus.COLLECTING,
            QuorumSessionStatus.TALLIED,
        ):
            raise QuorumError(
                f"Session {session_id} is in status '{session.status}', "
                f"cannot tally."
            )

        if len(session.sealed_votes) < session.required_voters:
            raise QuorumError(
                f"Insufficient votes in session {session_id}: "
                f"{len(session.sealed_votes)} collected, "
                f"{session.required_voters} required."
            )

        if self._scout_required and not session.scout_voted:
            raise QuorumError(
                f"Scout has not voted in session {session_id}. "
                f"Scout participation is required for quorum validity."
            )

        votes: list[QuorumVote] = []
        approve_count = 0
        reject_count = 0
        for vote_id in session.sealed_votes:
            qv = self._load_vote(vote_id, session_id)
            votes.append(qv)
            if qv.vote == "approve":
                approve_count += 1
            else:
                reject_count += 1

        total = approve_count + reject_count
        approval_ratio = approve_count / total if total > 0 else 0.0
        approved = approval_ratio >= session.threshold

        now = datetime.now(timezone.utc)
        session.tally_approve = approve_count
        session.tally_reject = reject_count
        session.status = (
            QuorumSessionStatus.APPROVED
            if approved
            else QuorumSessionStatus.REJECTED
        )
        session.completed_at = now
        self.yaml_store.write(
            f"{self._sessions_dir}/{session_id}.yaml", session
        )

        result = QuorumResult(
            votes=votes,
            threshold=session.threshold,
            approved=approved,
        )

        # S-03-FIX: Governance audit logging
        if self._audit_logger is not None:
            self._audit_logger.log_governance(
                event_type="quorum_session",
                proposal_id=session.proposal_id,
                quorum_session_id=session_id,
                detail=f"Tallied: {'APPROVED' if approved else 'REJECTED'} "
                       f"({approve_count}/{total})",
            )

        logger.info(
            f"Quorum session {session_id} tallied: "
            f"{approve_count}/{total} approve "
            f"({'APPROVED' if approved else 'REJECTED'}, "
            f"threshold {session.threshold:.0%})"
        )
        return result

    def get_session(self, session_id: str) -> QuorumSession:
        """Load a quorum session by ID."""
        return self._load_session(session_id)

    def check_timeout(self, session_id: str) -> bool:
        """Check if a quorum session has timed out.

        Returns True if the session timed out and was updated.
        """
        session = self._load_session(session_id)
        if session.status != QuorumSessionStatus.COLLECTING:
            return False

        now = datetime.now(timezone.utc)
        deadline = session.created_at + timedelta(
            minutes=self._vote_timeout_min
        )

        if now >= deadline:
            session.status = QuorumSessionStatus.TIMED_OUT
            session.completed_at = now
            self.yaml_store.write(
                f"{self._sessions_dir}/{session_id}.yaml", session
            )
            logger.warning(
                f"Quorum session {session_id} timed out after "
                f"{self._vote_timeout_min} minutes "
                f"({len(session.sealed_votes)}/{session.required_voters} votes)"
            )
            return True
        return False

    # -- Private helpers --

    def _compute_eligibility(
        self,
        role_registry: list[dict],
        proposer_role: str,
        proposal_id: str,
    ) -> list[QuorumEligibility]:
        """Compute voter eligibility for each role.

        Anti-gaming rules applied:
        1. Proposer excluded
        2. Role must have >= min_tasks_for_voter completed tasks
        3. Max 1 voter per role lineage
        4. Roles from same evolution can't both vote
        """
        eligibility: list[QuorumEligibility] = []
        seen_lineages: set[str] = set()
        seen_evolutions: set[str] = set()

        sorted_registry = sorted(
            role_registry, key=lambda r: str(r["name"])
        )

        for role_info in sorted_registry:
            name = str(role_info["name"])
            task_count = int(role_info.get("task_count", 0))
            lineage_id = str(role_info.get("lineage_id", ""))
            created_by_evo = str(role_info.get("created_by_evolution", ""))
            is_scout = bool(role_info.get("is_scout", False))

            effective_lineage = lineage_id if lineage_id else name

            entry = QuorumEligibility(
                role_name=name,
                task_count=task_count,
                lineage_id=effective_lineage,
                created_by_evolution=created_by_evo,
                is_scout=is_scout,
            )

            if name == proposer_role:
                entry.eligible = False
                entry.rejection_reason = (
                    "Proposer cannot vote on own proposal"
                )
                eligibility.append(entry)
                continue

            if not is_scout and task_count < self._min_tasks_for_voter:
                entry.eligible = False
                entry.rejection_reason = (
                    f"Role has {task_count} tasks, "
                    f"minimum {self._min_tasks_for_voter} required"
                )
                eligibility.append(entry)
                continue

            if effective_lineage in seen_lineages:
                entry.eligible = False
                entry.rejection_reason = (
                    f"Another role with lineage '{effective_lineage}' "
                    f"already eligible"
                )
                eligibility.append(entry)
                continue

            if created_by_evo and created_by_evo in seen_evolutions:
                entry.eligible = False
                entry.rejection_reason = (
                    f"Another role from evolution '{created_by_evo}' "
                    f"already eligible"
                )
                eligibility.append(entry)
                continue

            entry.eligible = True
            seen_lineages.add(effective_lineage)
            if created_by_evo:
                seen_evolutions.add(created_by_evo)
            eligibility.append(entry)

        return eligibility

    def _load_session(self, session_id: str) -> QuorumSession:
        """Load a quorum session from disk. Raises QuorumError if not found."""
        path = f"{self._sessions_dir}/{session_id}.yaml"
        try:
            return self.yaml_store.read(path, QuorumSession)
        except FileNotFoundError:
            raise QuorumError(f"Quorum session '{session_id}' not found")

    def _load_vote(self, vote_id: str, session_id: str) -> QuorumVote:
        """Load a quorum vote from disk.

        session_id is REQUIRED — votes are always stored under
        their session directory.
        """
        path = f"{self._votes_dir}/{session_id}/{vote_id}.yaml"
        try:
            return self.yaml_store.read(path, QuorumVote)
        except FileNotFoundError:
            raise QuorumError(
                f"Vote '{vote_id}' not found in session '{session_id}'"
            )
