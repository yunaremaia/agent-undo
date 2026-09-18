# Contributing to agent-undo

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/yunaremaia/agent-undo.git
cd agent-undo
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Code Style

We use `ruff` for linting and formatting:

```bash
ruff check .
ruff format .
```

## Pull Request Process

1. Fork the repo and create a feature branch.
2. Add tests for any new functionality.
3. Ensure all tests pass (`pytest`).
4. Update the README if adding user-facing features.
5. Open a PR with a clear description of the change.

## Code of Conduct

Please note that `agent-undo` is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
