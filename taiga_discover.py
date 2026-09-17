#!/usr/bin/env python3
"""Read-only discovery: resolves the project_id and lists the issue-types,
severities and issue-statuses configured on the Taiga project (via .env in this folder).

Usage:
    python taiga_discover.py
"""
import sys
from pathlib import Path

from taiga_common import TaigaClient, load_env, require

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent


def main():
    env = load_env(HERE / ".env")
    base_url, slug, user, password = require(
        env, "TAIGA_URL", "TAIGA_PROJECT_SLUG", "TAIGA_USER", "TAIGA_PASSWORD"
    )

    client = TaigaClient(base_url)
    client.login(user, password)

    project = client.project_by_slug(slug)
    project_id = project["id"]
    print(f"Project: {project['name']} (id={project_id}, slug={slug})\n")

    def show(title: str, path: str):
        print(f"== {title} ==")
        items = client.get(path, params={"project": project_id})
        for item in items:
            print(f"  id={item['id']:<4} name={item['name']}")
        print()

    show("Issue types", "/api/v1/issue-types")
    show("Severities", "/api/v1/severities")
    show("Issue statuses", "/api/v1/issue-statuses")


if __name__ == "__main__":
    main()
