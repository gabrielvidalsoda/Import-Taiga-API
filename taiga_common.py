"""Utilidades compartilhadas pelos scripts de import do Taiga."""
import os
from pathlib import Path

import requests


def load_env(path: Path) -> dict:
    """Lê um arquivo .env aceitando tanto `CHAVE=valor` quanto `CHAVE: valor`.
    Variáveis já definidas no ambiente do processo têm prioridade sobre o arquivo.
    """
    values = {}
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
            elif ":" in line:
                key, _, value = line.partition(":")
            else:
                continue
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in list(values):
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def require(env: dict, *keys: str) -> list:
    missing = [k for k in keys if not env.get(k)]
    if missing:
        raise SystemExit(
            f"Faltam variáveis no .env: {', '.join(missing)} "
            f"(ver .env.example nesta pasta)"
        )
    return [env[k] for k in keys]


class TaigaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def login(self, username: str, password: str) -> None:
        r = self.session.post(
            f"{self.base_url}/api/v1/auth",
            json={"type": "normal", "username": username, "password": password},
        )
        r.raise_for_status()
        token = r.json()["auth_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get(self, path: str, params: dict = None):
        r = self.session.get(f"{self.base_url}{path}", params=params)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict):
        r = self.session.post(f"{self.base_url}{path}", json=payload)
        r.raise_for_status()
        return r.json()

    def patch(self, path: str, payload: dict):
        r = self.session.patch(f"{self.base_url}{path}", json=payload)
        r.raise_for_status()
        return r.json()

    def project_by_slug(self, slug: str) -> dict:
        return self.get("/api/v1/projects/by_slug", params={"slug": slug})


def find_id_by_name(items: list, name: str, kind: str) -> int:
    for item in items:
        if item["name"].strip().lower() == name.strip().lower():
            return item["id"]
    available = ", ".join(item["name"] for item in items)
    raise SystemExit(f'{kind} "{name}" não encontrado no projeto. Disponíveis: {available}')


def issue_url(base_url: str, project_slug: str, ref) -> str:
    return f"{base_url.rstrip('/')}/project/{project_slug}/issue/{ref}"
