# Import Taiga API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

🇬🇧 English | 🇧🇷 [Português](README.pt-BR.md)

A Python tool that extracts items (bugs/defects) from a QA report written in
`.md` and creates them — or fixes their tags after they've been created — as
**Issues** in [Taiga](https://www.taiga.io/) via its REST API, without going
through manual creation in the UI.

It isn't tied to any specific project: how the report is parsed (how to
recognize each item, how to extract severity, how to map report sections to
Taiga tags) lives in a separate configuration file — see
[`config.example.json`](config.example.json).

## Why

Creating dozens of issues by hand, one at a time, pasting fields into the
Taiga UI, is slow and error-prone (wrong severity, forgotten tag, blank
field). This project automates that from a QA report already written in
Markdown, keeping a **dry-run by default** (nothing is created without an
explicit `--apply`) and a **local log** that prevents duplicate issues on
re-runs.

## Requirements

- Python 3.9+
- A Taiga account with a username/password (a "normal" login; SSO/GitHub/
  GitLab logins have no password and don't work with this authentication flow)

```bash
pip install -r requirements.txt
```

## Setup

### 1. Credentials (`.env`)

Copy `.env.example` to `.env` and fill it in:

```
TAIGA_URL=https://api.taiga.io
TAIGA_WEB_URL=https://tree.taiga.io
TAIGA_PROJECT_SLUG=my-project-slug
TAIGA_USER=
TAIGA_PASSWORD=
```

- `TAIGA_URL` — the **API** host. On Taiga Cloud this is `https://api.taiga.io`
  (don't confuse it with the web UI domain). On a self-hosted instance it's
  usually the same host as the UI, e.g. `https://taiga.mycompany.com`.
- `TAIGA_WEB_URL` — the **web UI** host, used only to build clickable links in
  the import log. If omitted, it falls back to `TAIGA_URL` (correct for most
  self-hosted instances). On Taiga Cloud it's `https://tree.taiga.io`
  (different from the API host).
- `TAIGA_PROJECT_SLUG` — the project slug, visible in the project's URL on
  Taiga (`.../project/<slug>`).
- `.env` is never committed (it's in `.gitignore`); the password is only used
  at runtime to obtain a token via `POST /api/v1/auth` — it isn't persisted to
  disk.

### 2. Extraction config (`config.json`)

Copy `config.example.json` to `config.json` and adapt it to your report.
Fields:

| Field | Description |
|---|---|
| `source_label` | Name of the source report, used only for reference in each created issue's description. |
| `bug_heading_pattern` | Regex with 2 capture groups: `(id)` and `(title)` of each item's heading in the `.md`. E.g.: `^####\s+(BUG-\d{8}-\d{2})\s+—\s+(.*)$`. |
| `severity_pattern` | Regex with 1 capture group: the severity digit inside the item's text (this line is removed from the final description). |
| `base_tags` | List of tags applied to **every** item (e.g. the name of the module/product being tested). |
| `default_tag` | Tag used when no `heading_tag_rules` rule matches. |
| `transversal_tag` | Extra tag applied to items marked `"transversal": true` (e.g. bugs that affect the whole system rather than a specific screen). |
| `heading_tag_rules` | Ordered list of `{pattern, tag, transversal}`. While walking the `.md` line by line, the first rule whose `pattern` matches a heading line (`##`, `###`, ...) becomes the active mapping for every item found afterwards, until the next rule matches. A rule with no `tag` **resets** the mapping (useful for sections that have no tag of their own). More specific rules should come before more generic ones in the list. |
| `fallback_tag_by_keyword` | List of `{keyword, tag}`, used only when `heading_tag_rules` didn't assign a tag to the item — it looks for `keyword` in the item's body and uses the matching `tag`. |

`config.json` is also not committed — the section mapping usually reflects the
internal structure/naming of one specific project.

## Usage

### 1. Discovery (read-only)

Confirms the credentials work and lists the issue type, severity and status
IDs configured in your Taiga project:

```bash
python taiga_discover.py
```

### 2. Extract the report to JSON

```bash
python taiga_import.py extract --report path/to/report.md --config config.json --out taiga-import.json
```

Review the generated `taiga-import.json` before the next step — it's your
chance to check each item's subject/description/severity/tags before any
write call to the API.

### 3. Create the issues in Taiga

Runs in **dry-run** by default (prints the payloads, creates nothing):

```bash
python taiga_import.py apply --input taiga-import.json
```

Test with a single item before creating them all:

```bash
python taiga_import.py apply --input taiga-import.json --apply --only BUG-20260915-01
```

Create the rest (re-runs automatically skip anything already in the log):

```bash
python taiga_import.py apply --input taiga-import.json --apply
```

To keep a permanent record of a real run (not just the scratch working
files), pass `--out`/`--log` paths under `reports/` — see
[`reports/README.md`](reports/README.md) for the naming convention. Unlike
the default `taiga-import.json`/`import-log.csv`, files under `reports/` are
committed to the repository as import history.

Useful flags: `--issue-type` (default `Bug`), `--sev1`/`--sev2`/`--sev3` (Taiga
severity names for your report's 1/2/3 scale — default `Minor`/`Normal`/
`Critical`, Taiga's own defaults), `--log` (tracking file, default
`import-log.csv`).

### 4. Fix tags on issues already created

If you change the rules in `config.json` after issues have already been
created, `retag` reapplies the tags from the extracted JSON to each issue
already recorded in the log (uses optimistic concurrency — fetches the
issue's current `version` before writing):

```bash
python taiga_import.py retag --input taiga-import.json          # dry-run
python taiga_import.py retag --input taiga-import.json --apply  # applies it
```

### 5. Assign issues to a project member

Given an import-log CSV (from a past `apply --apply` run), assigns each
issue in it to a project member. Members are matched by full name, since
the Taiga API does not expose other members' emails:

```bash
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe"            # dry-run
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe" --apply     # applies it
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe" --apply --only BUG-20260915-01
```

## Files

| File | Tracked? | Description |
|---|---|---|
| `taiga_common.py` | yes | HTTP client (auth, GET/POST/PATCH) and `.env` loader. |
| `taiga_discover.py` | yes | Lists issue types/severities/statuses for the configured project. |
| `taiga_import.py` | yes | `extract` / `apply` / `retag`. |
| `taiga_assign.py` | yes | Assigns issues from an import-log CSV to a project member, by name. |
| `config.example.json` | yes | Generic extraction config template. |
| `.env.example` | yes | Credentials template. |
| `config.json` | no | Your real config, specific to your report/project. |
| `.env` | no | Your real credentials. |
| `taiga-import.json`, `import-log.csv` (repo root) | no | Scratch output of the run in progress — data from your report, not from the repository. |
| `reports/*.json`, `reports/*.csv` | yes | Permanent history of past `--apply` runs, kept on purpose — see [`reports/README.md`](reports/README.md). |

## Security

- Without `--apply`, no command writes anything to Taiga.
- `.env` and `config.json` are never committed.
- The password is never saved to disk by the script — only the session token
  (in memory, for the duration of the run).

See [SECURITY.md](.github/SECURITY.md) for how to report a vulnerability.

## Contributing

Contributions, bug reports and feature requests are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) for how to get started, and please follow
the [Code of Conduct](CODE_OF_CONDUCT.md).

## Contact

Maintained by **Gabriel Vidal**.

- Email: [gabrielvidalsoda@gmail.com](mailto:gabrielvidalsoda@gmail.com)
- WhatsApp: [+55 (85) 99406-4049](https://bit.ly/4reII3v)
- LinkedIn: [linkedin.com/in/gabrielvidalsoda](https://www.linkedin.com/in/gabrielvidalsoda)

## License

[MIT](LICENSE) © 2026 Gabriel Vidal
