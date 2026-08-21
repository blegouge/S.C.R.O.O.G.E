# Contributing to S.C.R.O.O.G.E

Thank you for your interest in contributing to S.C.R.O.O.G.E!

## Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:blegouge/S.C.R.O.O.G.E.git
   cd S.C.R.O.O.G.E
   ```

2. **Initialize python environment**:
   ```bash
   python3 -m venv .venv-desktop
   source .venv-desktop/bin/activate
   pip install --upgrade pip
   pip install -r requirements-desktop.txt -r requirements-dev.txt
   ```

3. **Install the hooks**:
   ```bash
   python3 install_stack.py
   ```

## Code Quality Standards

We enforce strict linting, formatting, and typing checks:

- **Linting & Formatting**: We use `ruff`.
  ```bash
  ruff check . --fix
  ruff format .
  ```
- **Type Checking**: We use `mypy`. Ensure that your code contains valid type hints.
  ```bash
  mypy
  ```

## Running Tests

All unit tests must pass, and the minimum test coverage is set at **85%**.

```bash
pytest
```

## Commit Conventions & Automated Releases

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for all commit messages.

### Message Format
- `feat: ...` : A new feature (triggers a MINOR version release)
- `fix: ...` : A bug fix (triggers a PATCH version release)
- `docs: ...` : Documentation changes only
- `style: ...` : Formatting, missing semi colons, etc.
- `refactor: ...` : A code change that neither fixes a bug nor adds a feature
- `test: ...` : Adding or updating tests
- `chore: ...` : Maintenance tasks, updating dependencies, etc.
- `FEAT!:` or `BREAKING CHANGE:` : Breaking change (triggers a MAJOR version release)

### Pre-commit Verification
Commits are validated automatically via `pre-commit` (`commitizen`).
You can use `cz commit` for an interactive commit prompt, or write conventional commit messages directly.

### CI/CD Releases
Upon merging to `main`, GitHub Actions automatically calculates the new version bump, updates `CHANGELOG.md`, `pyproject.toml`, and `package.json`, creates a git tag, and publishes a GitHub Release.
