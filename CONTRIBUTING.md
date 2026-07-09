# Contributing to S.C.R.O.O.G.E.

Thank you for your interest in contributing to S.C.R.O.O.G.E.!

## Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:blegouge/S.C.R.O.O.G.E..git
   cd TelemetryToken
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

All unit tests must pass, and the minimum test coverage is set at **80%**.

```bash
pytest
```
