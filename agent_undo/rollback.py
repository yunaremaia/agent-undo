"""Rollback script generator for agent-undo."""

from __future__ import annotations

import json
import shlex

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

    def _undo_op(self, op: dict) -> list[str]:
        """Generate undo commands for a single operation."""
        op_type = op["op_type"]
        detail = op.get("command") or op.get("path") or op.get("checkpoint_label", "")
        if op_type == "file-write" and op.get("path") is not None:
            detail = json.dumps(op["path"])
        lines = [f"# [{op_type}] {detail}"]

        if op_type == "file-write" and op.get("content_before") is not None:
            path = shlex.quote(op["path"])
            before = op["content_before"]
            delimiter_base = f"AGENT_UNDO_EOF_{op.get('id', 'op')}"
            delimiter = delimiter_base
            suffix = 1
            content_lines = set(before.splitlines())
            while delimiter in content_lines:
                delimiter = f"{delimiter_base}_{suffix}"
                suffix += 1

            lines.append(f"if [ -f {path} ]; then")
            lines.append(f"  cat > {path} << '{delimiter}'")
            lines.append(before)
            lines.append(delimiter)
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
