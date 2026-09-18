# agent-undo

> Record and rollback AI agent operations — file writes, shell commands, git ops, API calls. Time-machine for AI agent actions.

AI agents are writing code, running commands, pushing to git, and calling APIs. When something goes wrong, you need to know *what happened* and *how to undo it*.

`agent-undo` records every operation your AI agent performs, builds a causality graph, and generates precise rollback scripts — so you can rewind to any point in the session, not just the last git commit.

## The Problem

Existing tools solve parts of this:
- **Git** tracks file state but not shell commands, API calls, or intent.
- **tmux/screen logs** capture output but not structured operations.
- **OS-level snapshots** (ZFS, btrfs, Time Machine) are coarse and agent-agnostic.
- **Agent harnesses** (Claude Code, Codex, Cursor) have no built-in audit trail.

`agent-undo` fills the gap: an agent-native operation journal with replayable rollback.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Agent Hook │────▶│  Journal DB  │────▶│  Rollback   │
│  (pre/post) │     │  (SQLite)    │     │  Generator  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
  File writes         Causality graph      Undo scripts
  Shell commands      Session timeline     Checkpoint restore
  Git operations      Evidence chain       Selective rollback
  API calls                               Diff preview
```

## Features

- **Pre/post hooks** for Claude Code, Codex, Cursor, and any agent that runs shell commands.
- **SQLite journal** with full operation history, file snapshots, and exit codes.
- **Causality tracking** — knows which file write caused which test failure.
- **Rollback generator** produces `undo.sh` scripts that restore files, reverse git ops, and clean up side effects.
- **Checkpoint markers** — tag any moment (`agent-undo checkpoint "before refactor"`) and restore exactly.
- **Session timeline** — see every operation in order, with timestamps and outcomes.
- **Evidence export** — generate audit reports (SARIF, JSON) for compliance or debugging.

## Quick Start

```bash
pip install agent-undo

# Start recording your agent session
agent-undo init

# Your agent runs... (all ops are journaled)

# See what happened
agent-undo timeline

# Generate a rollback script
agent-undo rollback --to checkpoint:before-refactor --output undo.sh

# Preview before applying
agent-undo preview --to checkpoint:before-refactor

# Apply the rollback
bash undo.sh
```

## Installation

```bash
pip install agent-undo
```

Or install from source:

```bash
git clone https://github.com/yunaremaia/agent-undo.git
cd agent-undo
pip install -e ".[dev]"
```

## Hooks

### Claude Code (`.claude/settings.json`)

```json
{
  "hooks": {
    "preToolUse": "agent-undo record --tool $TOOL_NAME --input $TOOL_INPUT",
    "postToolUse": "agent-undo record --tool $TOOL_NAME --output $TOOL_OUTPUT --exit $EXIT_CODE"
  }
}
```

### Shell-level (any agent)

```bash
# Wrap your agent invocation
agent-undo wrap -- claude-code "refactor the auth module"
```

### Manual recording

```bash
agent-undo log --type file-write --path src/auth.py --content "$(cat src/auth.py)"
agent-undo log --type shell --cmd "npm test" --exit 0
agent-undo log --type git --cmd "git commit -m 'refactor auth'"
agent-undo log --type api --endpoint https://api.github.com/repos/... --method POST --status 200
```

## Roadmap

- [x] Core journal + SQLite schema
- [ ] Claude Code hooks integration
- [ ] Codex/Cursor hooks
- [ ] Shell wrapper (strace-based)
- [ ] Git operation parser (detect commits, pushes, branches)
- [ ] API call interceptor (env-based HTTP proxy)
- [ ] Web UI for timeline visualization
- [ ] SARIF export
- [ ] Multi-agent session correlation
- [ ] Rollback dry-run and preview
- [ ] Checkpoint diff viewer
- [ ] Integration with agent-guard (permission-aware rollback)

## License

MIT

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

For security policies, supported versions, and vulnerability reporting procedures, please refer to [SECURITY.md](SECURITY.md).

## Credits

Built by [Yunare Maia](https://github.com/yunaremaia) — open-source developer from Mossoró-RN, Brazil.
