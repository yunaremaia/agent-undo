# Python API reference

`agent-undo` exposes a small Python API for applications that want to record
agent operations without invoking the CLI. The public classes live in
`agent_undo.journal` and `agent_undo.rollback`.

## `agent_undo.journal.Journal`

`Journal(db_path: str | pathlib.Path)` opens or creates a SQLite journal at
`db_path`. Parent directories are created automatically, and the schema is
created on first use.

### `record`

```python
record(
    session_id: str,
    op_type: str,
    *,
    command: str | None = None,
    path: str | None = None,
    content_before: str | None = None,
    content_after: str | None = None,
    exit_code: int | None = None,
    metadata: dict[str, Any] | None = None,
    parent_id: int | None = None,
    timestamp: float | None = None,
) -> int
```

Records one operation and returns its SQLite row id. `op_type` is an
application-defined label; built-in integrations use values such as
`file-write`, `shell`, `git`, `api`, and `checkpoint`. The optional metadata
dictionary is serialized as JSON. SQLite errors propagate so callers can
decide whether to retry or fail the surrounding operation.

### Checkpoints and queries

- `checkpoint(session_id: str, label: str, op_id: int | None = None) -> int`
  creates a checkpoint operation when `op_id` is omitted and returns its id.
- `get_session_ops(session_id: str, op_type: str | None = None) -> list[dict]`
  returns operations ordered by timestamp, optionally filtered by type.
- `get_timeline(session_id: str) -> list[dict]` returns operations with any
  checkpoint label joined onto each row.
- `find_checkpoint(session_id: str, label: str) -> int | None` returns the
  newest matching operation id, or `None` when the label is unknown.
- `get_ops_since(session_id: str, since_op_id: int) -> list[dict]` returns
  operations after the supplied id; an unknown id returns an empty list.
- `get_statistics() -> dict` returns `total_operations`, `total_sessions`,
  and a `by_type` count mapping.

Use `transaction()` as a context manager for custom SQLite work. It commits
on success and rolls back when the managed block raises.

## `agent_undo.rollback.RollbackGenerator`

`RollbackGenerator(journal: Journal)` binds a generator to a journal.

### `generate`

```python
generate(
    session_id: str,
    target_op_id: int | None = None,
    checkpoint_label: str | None = None,
) -> str
```

Returns a Bash script that undoes operations after `target_op_id`, or after
the operation named by `checkpoint_label`. A missing checkpoint or target
raises `ValueError`. When there is nothing to undo, it returns a comment-only
script. Shell and remote git operations may be left as manual-review comments.

### `preview_rollback`

```python
preview_rollback(
    journal: Journal,
    session_id: str,
    target_op_id: int | None = None,
    checkpoint_label: str | None = None,
) -> str
```

Returns a human-readable preview without writing or executing a script. It
has the same target requirements and raises `ValueError` for an unknown
checkpoint or when no target is supplied.

## Hook helpers

`agent_undo.hooks` contains integration helpers for agent hooks:

- `get_session_file() -> pathlib.Path` and `get_session_id() -> str` locate
  the current `.agent-undo/session` file.
- `run_pre_tool_hook(tool_name: str, tool_input: str) -> None` records the
  operation before a tool runs, including file content when available.
- `run_post_tool_hook(tool_name: str, tool_output: str, exit_code: int) -> None`
  records the tool result and output length.
- `shell_wrapper(agent_cmd: list[str], db_path: pathlib.Path | None = None) -> int`
  runs a subprocess with start/end checkpoints and returns its exit code. A
  missing executable returns `127`; Ctrl-C returns `130`.

These helpers use `AGENT_UNDO_DB` when set, otherwise they write to
`.agent-undo/journal.db` below the current working directory.
