# toy-service

Context for the factory: .factory/context.md

## Commands
- `uv sync`
- `uv run ruff check . && uv run ruff format --check .`
- `uv run pytest`

## Rules
- Standard library only; no new dependencies without approval.
- Comments max 2 lines. Behaviour is documented in README.md.
- Add a failing test before fixing a bug.
