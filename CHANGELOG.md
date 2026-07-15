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
- First public release of the S.C.R.O.O.G.E. agent telemetry stack.
