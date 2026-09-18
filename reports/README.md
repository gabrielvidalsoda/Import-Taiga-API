# Import reports

This folder keeps a permanent, committed history of what was actually
imported into (or updated in) Taiga — one pair of files per real `--apply`
run, so past imports stay auditable even after `config.json`/the source
report change or are deleted.

Unlike the default `taiga-import.json` / `import-log.csv` in the repo root
(scratch working files for the run in progress, git-ignored), files in this
folder are tracked in git on purpose.

## Convention

For each `apply --apply` run you want to keep a record of, use dated,
descriptive filenames instead of the tool's defaults:

```bash
python taiga_import.py extract --report path/to/report.md --config config.json \
  --out reports/taiga-import-YYYY-MM-DD.json

python taiga_import.py apply --input reports/taiga-import-YYYY-MM-DD.json --apply \
  --log reports/import-log-YYYY-MM-DD.csv
```

- `taiga-import-YYYY-MM-DD.json` — the extracted payload sent to Taiga
  (subject/description/severity/tags per item), i.e. *what* was imported.
- `import-log-YYYY-MM-DD.csv` — one row per issue actually created
  (`bug_id`, `taiga_issue_id`, `taiga_ref`, `url`, `timestamp`), i.e. *what
  happened* — the result of the import, with a link back to each Taiga issue.

`YYYY-MM-DD` is the date of the source QA report (execution date), not
necessarily the day the script was run — consistent with the rest of this
project's dated-report convention.

If a later `retag --apply` run changes tags on issues already in one of
these logs, note it in this file's history (or leave the log CSV as-is,
since `retag` doesn't append new rows — it only patches Taiga).

## History

| Date | Source report | Items | Files |
|---|---|---|---|
| 2026-09-15 | `Relatorio-Testes-Manuais-2026-09-15.md` | 32 | [taiga-import-2026-09-15.json](taiga-import-2026-09-15.json), [import-log-2026-09-15.csv](import-log-2026-09-15.csv) |
