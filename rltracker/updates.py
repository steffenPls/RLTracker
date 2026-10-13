"""Update-Pruefung ueber GitHub Releases.

Die App fragt beim Start https://api.github.com/repos/<GITHUB_REPO>/releases/latest ab.
Gibt es eine neuere Version, kann sie den Installer laden und starten (er aktualisiert in place).
Uebertragen wird dabei nur die normale Web-Anfrage (IP-Adresse) – keine Spiel- oder Nutzerdaten.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path

from . import GITHUB_REPO, __version__

API = "https://api.github.com"
ASSET = "RLTracker-Setup.exe"


def configured(repo: str = GITHUB_REPO) -> bool:
    return bool(repo) and "/" in repo and "DEIN" not in repo.upper()


def parse_version(v: str) -> tuple[int, ...]:
    nums = [int(x) for x in re.findall(r"\d+", v or "")[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(latest: str, current: str = __version__) -> bool:
    return parse_version(latest) > parse_version(current)


def latest_release(repo: str = GITHUB_REPO, api: str = API, timeout: float = 6.0) -> dict | None:
    """Neuestes Release: {'version', 'download', 'page', 'notes', 'size'} oder None."""
    req = urllib.request.Request(f"{api}/repos/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": f"RLTracker/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET), None)
    if not asset:
        return None  # Release existiert, aber der Installer wird noch gebaut
    return {"version": data.get("tag_name", "").lstrip("vV"), "download": asset["browser_download_url"],
            "page": data.get("html_url", ""), "notes": data.get("body") or "", "size": asset.get("size", 0)}


def check(repo: str = GITHUB_REPO) -> dict | None:
    """Gibt das Release zurueck, wenn es neuer ist als die laufende Version – sonst None."""
    if not configured(repo):
        return None
    rel = latest_release(repo)
    return rel if rel and is_newer(rel["version"]) else None


def download(url: str, progress=None, dest: Path | None = None) -> Path:
    """Laedt den Installer herunter; progress(geladen, gesamt) wird zwischendurch aufgerufen."""
    dest = dest or Path(tempfile.gettempdir()) / ASSET
    req = urllib.request.Request(url, headers={"User-Agent": f"RLTracker/{__version__}"})
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as fh:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if total and done != total:
        raise OSError("Download unvollständig – bitte erneut versuchen")
    os.replace(tmp, dest)
    return dest
