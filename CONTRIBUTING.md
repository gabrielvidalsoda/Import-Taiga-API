# Contributing to Import Taiga API

Thanks for taking the time to contribute! This is a small, single-maintainer
utility, so the process is intentionally lightweight.

## Before you start

- For small fixes (typos, docs, small bugs), feel free to open a pull request
  directly.
- For anything larger (new commands, changes to the config file format,
  behavior changes), please open an issue first to discuss the approach —
  it avoids wasted work if the direction needs to change.

## Reporting bugs

Open an [issue](../../issues/new/choose) with:

- What you ran (command + flags) and what you expected to happen.
- What actually happened (full error output, if any).
- Your Python version and OS.
- A minimal `config.json`/report snippet that reproduces the issue, with any
  real project data (client names, real tags, real slugs) removed or
  anonymized. **Never** paste your `.env` contents or Taiga password/token.

## Suggesting features

Open a [feature request issue](../../issues/new/choose) describing the
problem you're trying to solve, not just the solution — it makes it easier to
evaluate whether it fits the project's scope (a generic Taiga import tool
driven by an external config, not project-specific logic hardcoded into the
scripts).

## Development setup

```bash
git clone https://github.com/gabrielvidalsoda/Import-Taiga-API.git
cd Import-Taiga-API
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in with a test Taiga project
cp config.example.json config.json
```

`.env` and `config.json` are gitignored on purpose — use a personal/test
Taiga project while developing, never a production one, and never commit
either file.

## Code style

- Plain Python 3.9+, standard library + `requests`. No new dependencies
  without a good reason.
- Keep the code and all user-facing strings (CLI output, error messages,
  docstrings) in **English** — this keeps the tool usable and reviewable by
  contributors who don't read Portuguese. Documentation is bilingual (see
  [README.md](README.md) / [README.pt-BR.md](README.pt-BR.md)), the code
  itself is not.
- Match the existing style (small functions, `argparse` subcommands, dry-run
  by default for anything that writes to Taiga).

## Testing your change

There's no test suite yet. Before opening a PR, at minimum:

1. Run `extract` against a sample report and check the generated JSON looks
   right.
2. Run `apply` **without** `--apply` (dry-run) and check the printed payloads.
3. If you touched `apply`/`retag`, test against a real (test) Taiga project
   with `--only <id>` before running it unrestricted.

## Pull requests

- Keep PRs focused on one change.
- Update `README.md` **and** `README.pt-BR.md` if you change behavior,
  flags, or the config format (English first is fine if you can't translate —
  a maintainer can help with the Portuguese side).
- Add an entry to [CHANGELOG.md](CHANGELOG.md) under `Unreleased`.

## Response times

This is maintained in spare time, so please allow a few days for a first
response on issues and PRs. If you haven't heard back after a week, a polite
ping on the issue/PR is completely fine.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you're expected to uphold it.

## Contact

Questions that don't fit an issue? See the [Contact section in the
README](README.md#contact).
