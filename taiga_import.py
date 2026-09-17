#!/usr/bin/env python3
"""Extrai issues de um relatório .md e os cria/atualiza no Taiga via API.

A extração é guiada por um arquivo de configuração (ver config.example.json)
que descreve: como reconhecer o cabeçalho de cada item, como extrair a
severidade, e como mapear seções do relatório para tags do Taiga. Nada disso
fica fixo no código — cada relatório/projeto usa o seu próprio config.

Uso:
    python taiga_import.py extract --report relatorio.md --config config.json
    python taiga_import.py apply --input taiga-import.json                 # dry-run
    python taiga_import.py apply --input taiga-import.json --only BUG-01   # dry-run de 1 item
    python taiga_import.py apply --input taiga-import.json --apply --only BUG-01
    python taiga_import.py apply --input taiga-import.json --apply         # cria todos os pendentes
    python taiga_import.py retag --input taiga-import.json --apply         # corrige tags de issues já criados
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from taiga_common import TaigaClient, find_id_by_name, issue_url, load_env, require

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent
DEFAULT_JSON = HERE / "taiga-import.json"
DEFAULT_LOG = HERE / "import-log.csv"

# Links relativos para arquivos locais (ex.: [Anotações.md](Anotações.md)) não
# resolvem dentro do Taiga — viram texto simples, mantendo a referência legível.
MD_LOCAL_LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://)[^)]+\)")


def load_config(path: Path) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    heading_tag_rules = [
        (re.compile(rule["pattern"]), rule.get("tag"), rule.get("transversal", False))
        for rule in raw.get("heading_tag_rules", [])
    ]
    fallback_tag_by_keyword = [
        (item["keyword"], item["tag"]) for item in raw.get("fallback_tag_by_keyword", [])
    ]
    return {
        "source_label": raw.get("source_label", Path(path).stem),
        "bug_heading_re": re.compile(raw["bug_heading_pattern"]),
        "severity_re": re.compile(raw["severity_pattern"]),
        "base_tags": raw.get("base_tags", []),
        "transversal_tag": raw.get("transversal_tag", "transversal"),
        "heading_tag_rules": heading_tag_rules,
        "fallback_tag_by_keyword": fallback_tag_by_keyword,
        "default_tag": raw.get("default_tag", raw.get("base_tags", ["geral"])[0]),
    }


def extract_bugs(markdown_text: str, config: dict) -> list:
    current_tag = None
    current_transversal = False
    current = None
    bugs = []

    def finalize(entry: dict) -> dict:
        severity = None
        desc_lines = []
        for line in entry["body_lines"]:
            m = config["severity_re"].search(line)
            if m:
                severity = int(m.group(1))
                continue
            desc_lines.append(line)
        body = "\n".join(desc_lines).strip()
        body = MD_LOCAL_LINK_RE.sub(r"\1", body)

        tag = entry["tag"]
        transversal = entry["transversal"]
        if tag is None:
            tag = config["default_tag"]
            for keyword, kw_tag in config["fallback_tag_by_keyword"]:
                if keyword in body:
                    tag = kw_tag
                    break

        tags = list(config["base_tags"])
        if tag not in tags:
            tags.append(tag)
        if transversal and config["transversal_tag"] not in tags:
            tags.append(config["transversal_tag"])

        description = f"_Fonte: {config['source_label']}, {entry['id']}_\n\n{body}"

        return {
            "id": entry["id"],
            "subject": f"{entry['id']} — {entry['title']}",
            "description": description,
            "severity_scale": severity,
            "tags": tags,
        }

    for line in markdown_text.splitlines():
        for pattern, tag, transversal in config["heading_tag_rules"]:
            if pattern.match(line):
                current_tag = tag
                current_transversal = transversal
                break

        m = config["bug_heading_re"].match(line)
        if m:
            if current is not None:
                bugs.append(finalize(current))
            current = {
                "id": m.group(1),
                "title": m.group(2).strip(),
                "tag": current_tag,
                "transversal": current_transversal,
                "body_lines": [],
            }
            continue

        if current is not None:
            if re.match(r"^#{2,4}\s", line) or line.strip() == "---":
                bugs.append(finalize(current))
                current = None
                continue
            current["body_lines"].append(line)

    if current is not None:
        bugs.append(finalize(current))

    return bugs


def cmd_extract(args):
    text = Path(args.report).read_text(encoding="utf-8")
    config = load_config(Path(args.config))
    bugs = extract_bugs(text, config)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(bugs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(bugs)} itens extraídos -> {out_path}")
    sem_severidade = [b["id"] for b in bugs if b["severity_scale"] is None]
    if sem_severidade:
        print(f"AVISO: sem severidade detectada em: {', '.join(sem_severidade)}")


def load_already_imported(log_path: Path) -> set:
    already = set()
    if log_path.exists():
        with log_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                already.add(row["bug_id"])
    return already


def append_log(log_path: Path, row: dict):
    is_new = not log_path.exists()
    with log_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["bug_id", "taiga_issue_id", "taiga_ref", "url", "timestamp"])
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def cmd_apply(args):
    env = load_env(HERE / ".env")
    base_url, slug, user, password = require(
        env, "TAIGA_URL", "TAIGA_PROJECT_SLUG", "TAIGA_USER", "TAIGA_PASSWORD"
    )
    web_url = env.get("TAIGA_WEB_URL") or base_url

    bugs = json.loads(Path(args.input).read_text(encoding="utf-8"))
    only = set(args.only) if args.only else None
    already = load_already_imported(Path(args.log))

    client = TaigaClient(base_url)
    client.login(user, password)
    project = client.project_by_slug(slug)
    project_id = project["id"]

    type_id = find_id_by_name(client.get("/api/v1/issue-types", params={"project": project_id}), args.issue_type, "Issue type")
    severities = client.get("/api/v1/severities", params={"project": project_id})
    severity_id_by_scale = {
        1: find_id_by_name(severities, args.sev1, "Severity"),
        2: find_id_by_name(severities, args.sev2, "Severity"),
        3: find_id_by_name(severities, args.sev3, "Severity"),
    }

    created, skipped = 0, 0
    for bug in bugs:
        if only and bug["id"] not in only:
            continue
        if bug["id"] in already:
            print(f"[skip] {bug['id']} já consta em {args.log}")
            skipped += 1
            continue

        payload = {
            "project": project_id,
            "subject": bug["subject"],
            "description": bug["description"],
            "type": type_id,
            "tags": bug["tags"],
        }
        if bug["severity_scale"] in severity_id_by_scale:
            payload["severity"] = severity_id_by_scale[bug["severity_scale"]]

        if not args.apply:
            print(f"[dry-run] {bug['id']}")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue

        result = client.post("/api/v1/issues", payload)
        url = issue_url(web_url, slug, result["ref"])
        append_log(Path(args.log), {
            "bug_id": bug["id"],
            "taiga_issue_id": result["id"],
            "taiga_ref": result["ref"],
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        print(f"[criado] {bug['id']} -> #{result['ref']} ({url})")
        created += 1

    mode = "aplicado" if args.apply else "dry-run"
    print(f"\n{mode}: {created} criados, {skipped} já existentes.")


def load_log_rows(log_path: Path) -> dict:
    rows = {}
    if log_path.exists():
        with log_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows[row["bug_id"]] = row
    return rows


def cmd_retag(args):
    env = load_env(HERE / ".env")
    base_url, user, password = require(env, "TAIGA_URL", "TAIGA_USER", "TAIGA_PASSWORD")

    bugs = {b["id"]: b for b in json.loads(Path(args.input).read_text(encoding="utf-8"))}
    log_rows = load_log_rows(Path(args.log))
    only = set(args.only) if args.only else None

    client = TaigaClient(base_url)
    client.login(user, password)

    updated, skipped = 0, 0
    for bug_id, row in log_rows.items():
        if only and bug_id not in only:
            continue
        bug = bugs.get(bug_id)
        if bug is None:
            print(f"[skip] {bug_id} não está no JSON de entrada ({args.input})")
            skipped += 1
            continue

        issue_id = row["taiga_issue_id"]
        current = client.get(f"/api/v1/issues/{issue_id}")
        current_tag_names = sorted(t if isinstance(t, str) else t[0] for t in current["tags"])
        if current_tag_names == sorted(bug["tags"]):
            print(f"[skip] {bug_id} já está com as tags corretas")
            skipped += 1
            continue

        if not args.apply:
            print(f"[dry-run] {bug_id} (#{row['taiga_ref']}): {current['tags']} -> {bug['tags']}")
            continue

        client.patch(f"/api/v1/issues/{issue_id}", {"tags": bug["tags"], "version": current["version"]})
        print(f"[atualizado] {bug_id} (#{row['taiga_ref']}): {current['tags']} -> {bug['tags']}")
        updated += 1

    mode = "aplicado" if args.apply else "dry-run"
    print(f"\n{mode}: {updated} atualizados, {skipped} pulados.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Lê o relatório .md e gera o JSON intermediário")
    p_extract.add_argument("--report", required=True, help="Caminho do relatório .md de origem")
    p_extract.add_argument("--config", required=True, help="Caminho do arquivo de configuração (ver config.example.json)")
    p_extract.add_argument("--out", default=str(DEFAULT_JSON))
    p_extract.set_defaults(func=cmd_extract)

    p_apply = sub.add_parser("apply", help="Cria os issues no Taiga a partir do JSON")
    p_apply.add_argument("--input", default=str(DEFAULT_JSON))
    p_apply.add_argument("--log", default=str(DEFAULT_LOG))
    p_apply.add_argument("--only", action="append", help="Restringe a um BUG-ID específico (repetível)")
    p_apply.add_argument("--apply", action="store_true", help="Sem esta flag, roda em dry-run")
    p_apply.add_argument("--issue-type", default="Bug")
    p_apply.add_argument("--sev1", default="Minor", help="Nome da severidade Taiga para escala 1 (cosmético)")
    p_apply.add_argument("--sev2", default="Normal", help="Nome da severidade Taiga para escala 2 (funcional/layout)")
    p_apply.add_argument("--sev3", default="Critical", help="Nome da severidade Taiga para escala 3 (severo)")
    p_apply.set_defaults(func=cmd_apply)

    p_retag = sub.add_parser("retag", help="Corrige as tags de issues já criados, usando o log de import")
    p_retag.add_argument("--input", default=str(DEFAULT_JSON))
    p_retag.add_argument("--log", default=str(DEFAULT_LOG))
    p_retag.add_argument("--only", action="append", help="Restringe a um BUG-ID específico (repetível)")
    p_retag.add_argument("--apply", action="store_true", help="Sem esta flag, roda em dry-run")
    p_retag.set_defaults(func=cmd_retag)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
