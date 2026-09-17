# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/SECURITY.md`.
- Issue templates (bug report, feature request) and a pull request template.
- `README.pt-BR.md` as a Portuguese counterpart to `README.md`.
- Contact information for the maintainer in the README.
- A basic CI workflow that lints and syntax-checks the Python scripts.

### Changed

- Project language switched to English as the primary language for code,
  docstrings, and CLI output; documentation is now bilingual (English/pt-BR).
- `.env.example` now uses a generic placeholder slug and a correct
  Taiga Cloud `TAIGA_URL` example.

## [0.1.0] - 2026-09-16

### Added

- Initial release: `taiga_discover.py`, `taiga_import.py`
  (`extract`/`apply`/`retag`), `taiga_common.py`, and the config-driven report
  parsing described in `config.example.json`.
