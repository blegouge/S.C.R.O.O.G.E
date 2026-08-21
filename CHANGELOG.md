# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-09

### Added
- Configurable savings coefficients (`git_cache_savings_coefficient` and `guardrail_savings_coefficient`) for A/B calibration.
- Dynamic environment variable resolution for model-aware token count estimation.
- Local HTTP server security: strict validation of the `Host` header to block DNS rebinding.
- Single-use session tokens randomly generated on startup to authenticate `/api/*` requests.
- Platform-specific virtual environment lockfiles (`requirements-desktop-*.lock`) for reproducible deployments.
- Enforced minimum test coverage gate at 80% with coverage tracking.
- Added project governance documentation: `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.

### Changed
- Shifted all hardcoded home directory and user paths to generic templates (`{{HUB}}` and `{{HOME}}`).
- Removed `Access-Control-Allow-Origin: *` headers from `/api/*` endpoints.
- Plafonded transcript reading to 500k characters to prevent high memory usage.
- Enabled strict mypy checking (`check_untyped_defs = true`) globally and resolved type issues.

## [1.0.0] - 2026-07-07

### Added
- First public release of the S.C.R.O.O.G.E agent telemetry stack.

## v1.4.3 (2026-08-21)

### Refactor

- **config**: remove company-specific MySQL secret references

## v1.4.2 (2026-08-21)

### Refactor

- **native**: remove macOS app build pipeline and related references

## v1.4.1 (2026-08-21)

### Fix

- **docs**: drop trailing period from S.C.R.O.O.G.E clone path

## v1.4.0 (2026-08-20)

### Feat

- **providers**: reorder AI agent priorities to make Claude Code default and Cursor last

## v1.3.0 (2026-08-17)

### Feat

- **telemetry**: add OTEL-shaped span context for agent traces

### Fix

- **diff-only**: make apply hooks operational and idempotent

## v1.2.0 (2026-07-30)

### Feat

- **dashboard**: add agent status inspector & component deployer, cleanup analysis dir & boost coverage to 87%
- **ci**: add automated versioning and release pipeline with commitizen
- **install**: add uv/uvx installation support and enhance environment setup
- **agent-optim**: implement P2 agent stack optimizations
- **telemetry**: improve token measurement reliability & integrate Claude tokenizer
- **ab-test**: implement A/B testing framework and dashboard calibration interface
- implement model-aware token counting propagation and provider-aware cache reads
- **refactor**: modularize monolith dashboard.js into ES Modules
- **quality**: implement Wave 1 quality, testing, and governance improvements
- **telemetry**: make savings coefficients configurable and add env fallback for model encoding
- **telemetry**: implement cache-aware token billing, server security, and portability (P1)
- **telemetry**: implement accurate token measurement and align quality tools (P0)
- setup comprehensive CI pipeline with linting, security, and tests
- **claude-code**: add support for Claude Code hooks and telemetry
- rename telemetry proxy application to S.C.R.O.O.G.E
- implement architectural evolutions 1 to 5
- add full-page error when no providers configured
- externalize AI provider config to YAML
- add interactive installer & environment configuration for multi-agent deployment - Implement install_stack.py to automate deployment of rules, skills, hooks, and binaries across multiple agent directories (~/.cursor, ~/.gemini/antigravity, ~/.claude, ~/.hermes, ~/.gemini). - Add dynamic text rewriting to replace agent/IDE references (e.g. Cursor, Antigravity, Claude Code, Hermes, Gemini CLI) based on the target hub path. - Introduce .env and .env.example configurations to manage server ports, codebase roots, and agent home folders, replacing hardcoded directories. - Dynamically load environmental parameters in telemetry_paths.py, telemetry_common.py, and serve_dashboard.py. - Include all version-controlled reference hub components (bin, rules, skills, hooks, and logic) under hub_files/. - Track repository-level MDC rules inside .cursor/rules/.
- add Claude Code support to dashboard

### Fix

- **ci**: fix single-dash flag in cz version command
- **diff-only**: add structured message parsing, stop hook and robust error handling
- **diff-only**: soft-allow full write on existing paths by default
- **telemetry**: separate configured home env checks and update source detection unit tests
- **telemetry**: separate configured home env checks and update source detection unit tests
- **telemetry**: pin agent attribution and dedupe SQLite sync
- **tests**: isolate os.environ in test_get_home_dir_resolution for CI environments
- **ci**: replace commitizen action with direct cz check in PR pipeline
- **ci**: update commitizen-action version reference to master
- **dashboard**: resolve element ID mappings, module imports, and vendor asset packaging
- **agent-optim**: unblock targeted diff-only edits
- add root src directory to PYTHONPATH in test_optimization_stack for CI subprocess environment
- expert critique remediation (sys.path shadowing, git mocking, secure token, mypy config, ci documentation, versioning)
- update frontend linter paths and bandit scan targets for CI
- support spaces in French colons and synthetic afterAgentResponse on stop
- fix provider auto-detection and sys.path resolution
- **native**: allow parent directory resolution for static assets path validation when frozen
- **native**: include split dashboard modules in PyInstaller datas list
- **ci**: fix prettier format check for dashboard.js
- **ci**: fix ruff format check and resolve pip-audit vulnerabilities
- force TASK_BRIEF_ENFORCE=deny in test_invalid_brief_denied to make it environment-independent
- resolve ruff lint and format issues in python files and hooks
- resolve hardcoded .cursor path in tests and inject PYTHONPATH for subprocess hooks
- fetch full history for security job to support gitleaks scan
- add contents and pull-requests read permissions for gitleaks action
- align pre-commit prettier version and configure endOfLine auto
- change mypy run command to read pyproject.toml settings
- make copy_tree_idempotent robust and remove local path symlink

### Refactor

- modularize compression hook, installer, and dashboard JS code
- reorganize repository structure to domain-driven layout
- standardisation PEP 621, mutualisation des hooks et correction des tests unitaires
- introduce provider abstraction for multi-IDE support
- remove hardcoded user path dependencies and make paths dynamic
