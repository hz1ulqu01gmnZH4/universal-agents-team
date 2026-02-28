"""Git operations for evolution tracking and rollback.
Spec reference: Section 9 (Dual-Copy Evolution), Section 20.1 (immutability)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class GitOpsError(Exception):
    """Raised when a git operation fails."""


class GitOps:
    """Git operations for evolution tracking and rollback.

    Design invariants:
    - Never rebase or force-push (E5: preserve audit trail)
    - All evolution branches are merge-only
    - Structured commit messages for machine parsing
    - SHA-256 hash verification for constitution guard
    """

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir.resolve()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repo directory."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise GitOpsError(
                f"git {' '.join(args)} failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def commit_evolution(
        self,
        evo_id: str,
        tier: int,
        rationale: str,
        approved_by: str,
        files: list[str],
    ) -> str:
        """Structured evolution commit. Returns SHA.

        Commit message format:
            [evo] {evo_id} tier={tier}

            Rationale: {rationale}
            Approved-by: {approved_by}
            Files: {comma-separated files}
        """
        for f in files:
            self._run("add", f)
        msg = (
            f"[evo] {evo_id} tier={tier}\n\n"
            f"Rationale: {rationale}\n"
            f"Approved-by: {approved_by}\n"
            f"Files: {', '.join(files)}"
        )
        self._run("commit", "-m", msg)
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def create_rollback_point(self) -> str:
        """Tag current HEAD as a rollback target. Returns SHA."""
        result = self._run("rev-parse", "HEAD")
        sha = result.stdout.strip()
        return sha

    def rollback_to(self, commit_sha: str) -> None:
        """Create a revert commit to undo changes back to the given SHA.
        Never uses git reset --hard (E5: preserve history)."""
        self._run("revert", "--no-commit", f"{commit_sha}..HEAD")
        self._run("commit", "-m", f"[rollback] Revert to {commit_sha[:8]}")

    def compute_file_hash(self, path: str) -> str:
        """Compute SHA-256 of a file's content."""
        full_path = self.repo_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"Cannot hash missing file: {full_path}")
        content = full_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def verify_file_hash(self, path: str, expected_hash: str) -> bool:
        """Verify file content hash (SHA-256)."""
        actual = self.compute_file_hash(path)
        return actual == expected_hash

    def get_diff(self, from_sha: str, to_sha: str) -> str:
        """Get unified diff between two commits."""
        result = self._run("diff", from_sha, to_sha)
        return result.stdout

    def create_evolution_branch(self, evo_id: str) -> str:
        """Create a branch for evolution evaluation."""
        branch_name = f"evo/{evo_id}"
        self._run("checkout", "-b", branch_name)
        return branch_name

    def merge_evolution_branch(self, branch_name: str) -> str:
        """Merge evolution branch back to main. Returns merge commit SHA."""
        self._run("checkout", "main")
        self._run("merge", "--no-ff", branch_name,
                  "-m", f"[evo-merge] {branch_name}")
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def delete_evolution_branch(self, branch_name: str) -> None:
        """Delete a rejected evolution branch."""
        self._run("branch", "-d", branch_name)
