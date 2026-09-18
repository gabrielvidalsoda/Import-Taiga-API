#!/usr/bin/env python3
"""Assigns Taiga issues to a project member by email, using an import-log CSV
(as produced by `taiga_import.py apply`) to map each BUG-ID to its Taiga issue.

Usage:
    python taiga_assign.py --log import-log-2026-09-15.csv --name "Henrique Lima"               # dry-run
    python taiga_assign.py --log import-log-2026-09-15.csv --name "Henrique Lima" --apply        # applies
    python taiga_assign.py --log import-log-2026-09-15.csv --name "Henrique Lima" --only BUG-20260915-01 --apply
"""
import argparse
import csv
import sys
from pathlib import Path

from taiga_common import TaigaClient, load_env, require

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent


def load_log_rows(log_path: Path) -> list:
    with log_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_member(client: TaigaClient, project_id: int, name: str = None, email: str = None) -> dict:
    """Resolves a project member by name or email.

    The Taiga memberships endpoint does not expose member emails for privacy
    reasons (`user_email` is only populated for pending, not-yet-accepted
    invitations) — so matching is done by `full_name` instead. `email` is kept
    only as a label for the console output.
    """
    memberships = client.get("/api/v1/memberships", params={"project": project_id})
    if name:
        matches = [m for m in memberships if m.get("full_name", "").strip().lower() == name.strip().lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise SystemExit(f'Multiple project members named "{name}": {[m["user"] for m in matches]}')
    available = ", ".join(sorted(m.get("full_name") or "?" for m in memberships))
    raise SystemExit(f'No project member found with name "{name}". Members: {available}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", required=True, help="Path to an import-log CSV")
    parser.add_argument("--name", required=True, help="Full name of the project member to assign the issues to (as shown in Taiga memberships)")
    parser.add_argument("--email", help="Email of the assignee, used only as a label in the output (Taiga's API does not expose member emails)")
    parser.add_argument("--only", action="append", help="Restrict to a specific BUG-ID (repeatable)")
    parser.add_argument("--apply", action="store_true", help="Without this flag, runs in dry-run mode")
    args = parser.parse_args()

    env = load_env(HERE / ".env")
    base_url, slug, user, password = require(
        env, "TAIGA_URL", "TAIGA_PROJECT_SLUG", "TAIGA_USER", "TAIGA_PASSWORD"
    )

    client = TaigaClient(base_url)
    client.login(user, password)
    project = client.project_by_slug(slug)
    project_id = project["id"]

    member = find_member(client, project_id, name=args.name, email=args.email)
    assignee_id = member["user"]
    display_name = member.get("full_name") or args.name
    label = f"{display_name} <{args.email}>" if args.email else display_name
    print(f"Assignee: {label} (user id={assignee_id})\n")

    only = set(args.only) if args.only else None
    rows = load_log_rows(Path(args.log))

    updated, skipped = 0, 0
    for row in rows:
        bug_id = row["bug_id"]
        if only and bug_id not in only:
            continue

        issue_id = row["taiga_issue_id"]
        current = client.get(f"/api/v1/issues/{issue_id}")

        if current.get("assigned_to") == assignee_id:
            print(f"[skip] {bug_id} (#{row['taiga_ref']}) already assigned to {display_name}")
            skipped += 1
            continue

        if not args.apply:
            extra = current.get("assigned_to_extra_info") or {}
            prev = extra.get("full_name_display") or "unassigned"
            print(f"[dry-run] {bug_id} (#{row['taiga_ref']}): {prev} -> {display_name}")
            continue

        client.patch(
            f"/api/v1/issues/{issue_id}",
            {"assigned_to": assignee_id, "version": current["version"]},
        )
        print(f"[updated] {bug_id} (#{row['taiga_ref']}) -> {display_name}")
        updated += 1

    mode = "applied" if args.apply else "dry-run"
    print(f"\n{mode}: {updated} updated, {skipped} skipped.")


if __name__ == "__main__":
    main()
