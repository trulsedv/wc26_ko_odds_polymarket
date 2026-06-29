# Agent Instructions

- **Output style**: Only output crucial text. Be concise to save tokens.
- **Package manager**: Use `uv` for Python package management.
- **uv venv**: uv automatically uses the virtual environment; no need to run `source .venv/bin/activate`.
- **Python command**: Use `python` not `python3`.
- **Linting**: Run `uvx ruff check` before committing.
- **Type checking**: Run `uvx ty check` before committing.
- **ruff.toml**: Do not modify without explicit user permission.
- **noqa comments**: Do not add without explicit user permission.
- **Line breaks**: Avoid line breaks in code; keep statements on single lines where possible.
