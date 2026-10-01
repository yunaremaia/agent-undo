"""Rollback script generator and simulation for agent-undo."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .journal import Journal


class RollbackGenerator:
    """Generate undo.sh scripts from journaled operations."""

    def __init__(self, journal: Journal):
        self.journal = journal

    def generate(
        self,
        session_id: str,
        target_op_id: int | None = None,
        checkpoint_label: str | None = None,
    ) -> str:
        """Generate a bash script that undoes all operations since the target."""
        if checkpoint_label:
            op_id = self.journal.find_checkpoint(session_id, checkpoint_label)
            if op_id is None:
                raise ValueError(f"Checkpoint '{checkpoint_label}' not found")
            target_op_id = op_id

        if target_op_id is None:
            raise ValueError("Must provide target_op_id or checkpoint_label")

        ops = self.journal.get_ops_since(session_id, target_op_id)
        if not ops:
            return "# No operations to undo\n"

        lines = [
            "#!/bin/bash",
            "# agent-undo rollback script",
            f"# Session: {session_id}",
            f"# Rolling back {len(ops)} operations",
            "set -euo pipefail",
            "",
            "echo 'Applying agent-undo rollback...'",
            "",
        ]

        for op in ops:
            lines.extend(self._undo_op(op))

        lines.append("")
        lines.append("echo 'Rollback complete.'")
        return "\n".join(lines)

    def generate_plan(
        self,
        session_id: str,
        target_op_id: int | None = None,
        checkpoint_label: str | None = None,
    ) -> RollbackPlan:
        """Build a structured plan for rollback without generating a script."""
        if checkpoint_label:
            op_id = self.journal.find_checkpoint(session_id, checkpoint_label)
            if op_id is None:
                raise ValueError(f"Checkpoint '{checkpoint_label}' not found")
            target_op_id = op_id

        if target_op_id is None:
            raise ValueError("Must provide target_op_id or checkpoint_label")

        ops = self.journal.get_ops_since(session_id, target_op_id)
        return RollbackPlan(
            session_id=session_id,
            target_op_id=target_op_id,
            operations=[self._plan_op(op) for op in ops],
        )

    def _plan_op(self, op: dict) -> RollbackOperation:
        """Convert a journal operation dict into a RollbackOperation."""
        return RollbackOperation(
            op_type=op["op_type"],
            path=op.get("path"),
            command=op.get("command"),
            label=op.get("checkpoint_label", ""),
            content_before=op.get("content_before"),
        )

    def _undo_op(self, op: dict) -> list[str]:
        """Generate undo commands for a single operation."""
        op_type = op["op_type"]
        detail = op.get("command") or op.get("path") or op.get("checkpoint_label", "")
        lines = [f"# [{op_type}] {detail}"]

        if op_type == "file-write" and op.get("content_before") is not None:
            path = op["path"]
            lines.append(f"if [ -f '{path}' ]; then")
            # Escape content for heredoc-safe embedding
            before = op["content_before"].replace("'", "'\\''")
            lines.append(f"  cat > '{path}' << 'AGENT_UNDO_EOF'")
            lines.append(f"{(before)}")
            lines.append("AGENT_UNDO_EOF")
            lines.append("fi")

        elif op_type == "shell" and op.get("command"):
            # Shell commands can't be auto-undone, but we note them
            meta = json.loads(op["metadata"]) if op.get("metadata") else {}
            undo_cmd = meta.get("undo_command")
            if undo_cmd:
                lines.append(f"  {undo_cmd}")
            else:
                lines.append(f"# Manual review needed: {op['command']}")

        elif op_type == "git":
            cmd = op.get("command", "")
            if cmd.startswith("git commit"):
                lines.append(f"git reset --soft HEAD~1  # Undo: {cmd}")
            elif cmd.startswith("git push"):
                lines.append(f"# WARNING: Remote push cannot be auto-undone: {cmd}")
                lines.append("# Consider: git push --force-with-lease origin <previous-ref>")
            elif cmd.startswith("git branch -D"):
                lines.append(f"# Deleted branch cannot be recovered from journal alone: {cmd}")
            else:
                lines.append(f"# Manual review needed: {cmd}")

        elif op_type == "checkpoint":
            lines.append(f"# Checkpoint: {op.get('checkpoint_label', '(unnamed)')}")

        elif op_type == "api":
            lines.append(f"# API call: {op.get('metadata', 'no metadata')}")

        else:
            lines.append(f"# Unknown op type: {op_type}")

        lines.append("")
        return lines


def preview_rollback(
    journal: Journal,
    session_id: str,
    target_op_id: int | None = None,
    checkpoint_label: str | None = None,
) -> str:
    """Preview a rollback without generating a script."""
    if checkpoint_label:
        op_id = journal.find_checkpoint(session_id, checkpoint_label)
        if op_id is None:
            raise ValueError(f"Checkpoint '{checkpoint_label}' not found")
        target_op_id = op_id

    if target_op_id is None:
        raise ValueError("Must provide target_op_id or checkpoint_label")

    ops = journal.get_ops_since(session_id, target_op_id)
    lines = [f"Rollback preview — {len(ops)} operations would be undone:\n"]
    for op in ops:
        label = op.get("checkpoint_label") or ""
        lines.append(
            f"  [{op['op_type']}] {op.get('command') or op.get('path') or label or '(no details)'}"
        )
    return "\n".join(lines)


@dataclass
class RollbackOperation:
    """A single operation in a rollback plan."""

    op_type: str
    path: str | None = None
    command: str | None = None
    label: str = ""
    content_before: str | None = None
    content_after: str | None = None


@dataclass
class RollbackPlan:
    """Structured plan for rolling back operations."""

    session_id: str
    target_op_id: int
    operations: list[RollbackOperation]


def format_simulation(plan: RollbackPlan) -> str:
    """Format a RollbackPlan as a human-readable simulation."""
    lines = [
        "=== Rollback Simulation ===",
        f"Session: {plan.session_id}",
        f"Target checkpoint: operation #{plan.target_op_id}",
        f"Operations to undo: {len(plan.operations)}",
        "",
    ]

    # Categorize operations
    file_writes_restoring = [
        op for op in plan.operations if op.op_type == "file-write" and op.content_before is not None
    ]
    file_writes_unconditional = [
        op for op in plan.operations if op.op_type == "file-write" and op.content_before is None
    ]
    shell_ops = [op for op in plan.operations if op.op_type == "shell"]
    git_ops = [op for op in plan.operations if op.op_type == "git"]
    api_ops = [op for op in plan.operations if op.op_type == "api"]
    checkpoint_ops = [op for op in plan.operations if op.op_type == "checkpoint"]
    other_ops = [
        op
        for op in plan.operations
        if op.op_type not in ("file-write", "shell", "git", "api", "checkpoint")
    ]

    if file_writes_restoring:
        lines.append("Files that will be RESTORED (reverted to previous content):")
        for op in file_writes_restoring:
            lines.append(f"  [RESTORE] {op.path or '(unknown path)'}")
        lines.append("")

    if file_writes_unconditional:
        lines.append("File operations without stored content (may not be reversible):")
        for op in file_writes_unconditional:
            lines.append(f"  [FILE] {op.path or '(unknown path)'}")
        lines.append("")

    if shell_ops:
        lines.append(f"Shell commands that will be executed ({len(shell_ops)}):")
        for i, op in enumerate(shell_ops, 1):
            undo_cmd = _extract_undo_command(op)
            if undo_cmd:
                lines.append(f"  {i}. {undo_cmd}")
            else:
                lines.append(f"  {i}. # Manual review needed: {op.command}")
        lines.append("")

    if git_ops:
        lines.append(f"Git operations that will be handled ({len(git_ops)}):")
        for op in git_ops:
            undo_cmd = _git_undo_command(op)
            if undo_cmd:
                lines.append(f"  - {undo_cmd}")
            else:
                lines.append(f"  - # Manual review needed: {op.command}")
        lines.append("")

    if api_ops:
        lines.append(f"API calls recorded ({len(api_ops)}):")
        for op in api_ops:
            lines.append(f"  - API: {op.command or op.label or '(no metadata)'}")
        lines.append("")

    if other_ops:
        lines.append(f"Other operations ({len(other_ops)}):")
        for op in other_ops:
            detail = op.label or op.path or op.command or "(no details)"
            lines.append(f"  - [{op.op_type}] {detail}")
        lines.append("")

    if checkpoint_ops:
        lines.append("Checkpoints referenced:")
        for op in checkpoint_ops:
            lines.append(f"  - Checkpoint: {op.label or '(unnamed)'}")
        lines.append("")

    # Diff preview for files with content_before
    if file_writes_restoring:
        lines.append("=== Diff Preview ===")
        lines.append("")
        for op in file_writes_restoring:
            if op.path and op.content_before is not None:
                # For simulation, content_after is unknown — show original → current placeholder
                lines.append(f"--- {op.path} (original, to be restored)")
                lines.append(f"+++ {op.path} (current, will be overwritten)")
                lines.append("@@ -1,N +1,N @@")
                # Show a few lines of the original content as context
                orig_lines = op.content_before.splitlines()[:5]
                for line in orig_lines:
                    lines.append(f" {line}")
                if len(op.content_before.splitlines()) > 5:
                    lines.append(f" ... ({len(op.content_before.splitlines()) - 5} more lines)")
                lines.append("")

    # Summary stats
    files_affected = len([op for op in plan.operations if op.path])
    commands_count = len(shell_ops) + len([op for op in git_ops if _git_undo_command(op)])
    auto_undo_shell = len([op for op in shell_ops if _extract_undo_command(op)])
    lines.append("=== Summary ===")
    lines.append(f"Total operations: {len(plan.operations)}")
    lines.append(f"Files affected: {files_affected}")
    lines.append(f"Commands to execute: {commands_count}")
    lines.append(f"Manual review needed: {len(shell_ops) - auto_undo_shell}")
    lines.append("")
    lines.append(
        "NOTE: This is a simulation. No files, git repos, or the journal have been modified."
    )

    return "\n".join(lines)


def _extract_undo_command(op: RollbackOperation) -> str | None:
    """Extract the undo command from a shell operation's metadata."""
    if op.command:
        return f"# Would execute undo for: {op.command}"
    return None


def _git_undo_command(op: RollbackOperation) -> str | None:
    """Get the undo command for a git operation."""
    cmd = op.command or ""
    if cmd.startswith("git commit"):
        return "git reset --soft HEAD~1"
    if cmd.startswith("git push"):
        return "# WARNING: Remote push cannot be auto-undone"
    if cmd.startswith("git branch -D"):
        return "# Deleted branch cannot be recovered from journal alone"
    return None


def simulate_rollback(
    generator: RollbackGenerator,
    session_id: str,
    target_op_id: int | None = None,
    checkpoint_label: str | None = None,
) -> str:
    """Generate a human-readable simulation of the rollback (CLI entry point)."""
    plan = generator.generate_plan(session_id, target_op_id, checkpoint_label)
    return format_simulation(plan)
