"""Speichert Matches und Einstellungen in Dokumente/RLTracker."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from . import analysis as A


def documents_dir() -> Path:
    if sys.platform == "win32":
        try:  # echter "Dokumente"-Ordner (auch wenn per OneDrive verschoben)
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    d = Path.home() / "Documents"
    return d if d.exists() else Path.home()


def data_dir() -> Path:
    d = Path(os.environ.get("RLTRACKER_HOME", documents_dir() / "RLTracker"))
    (d / "matches").mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_SETTINGS = {
    "player_name": "", "host": "127.0.0.1", "port": 49123, "ini_path": "",
    "auto_show_results": True, "auto_replay": True, "demo_speed": 6.0, "update_check": True,
}


def load_settings() -> dict:
    p = data_dir() / "settings.json"
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    (data_dir() / "settings.json").write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def _summary(match: dict, path: Path) -> dict:
    meta = match["meta"]
    lp = meta.get("local_player")
    p = match["players"].get(lp, {}) if lp else {}
    return {
        "file": path.name, "started_at": meta.get("started_at", ""), "arena": meta.get("arena", ""),
        "playlist_id": meta.get("playlist_id"), "score": [meta["teams"]["0"]["score"], meta["teams"]["1"]["score"]],
        "winner_team": meta.get("winner_team"), "complete": meta.get("complete", False),
        "local_player": lp, "local_name": p.get("name", ""), "local_team": p.get("team"),
        "players": [v["name"] for v in match["players"].values()],
        "duration": meta.get("duration", 0), "source": match.get("source", "live"),
        "demo": match.get("demo", False),
    }


def save_match(match: dict) -> Path:
    meta = match["meta"]
    stamp = re.sub(r"[^0-9T]", "", meta.get("started_at", ""))[:15] or "match"
    arena = re.sub(r"[^A-Za-z0-9]", "", meta.get("arena", ""))[:20] or "Arena"
    guid = (meta.get("guid") or "local")[:8]
    path = data_dir() / "matches" / f"{stamp}_{arena}_{guid}.json"
    path.write_text(json.dumps(match, separators=(",", ":")), encoding="utf-8")
    idx = _load_index()
    idx[path.name] = _summary(match, path)
    _save_index(idx)
    return path


def load_match(name: str) -> dict:
    return A.fix_units(json.loads((data_dir() / "matches" / name).read_text(encoding="utf-8")))


def delete_match(name: str) -> None:
    p = data_dir() / "matches" / name
    if p.exists():
        p.unlink()
    idx = _load_index()
    idx.pop(name, None)
    _save_index(idx)


def _load_index() -> dict:
    try:
        return json.loads((data_dir() / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_index(idx: dict) -> None:
    (data_dir() / "index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")


def list_matches() -> list[dict]:
    """Zusammenfassungen aller gespeicherten Matches, neueste zuerst."""
    idx = _load_index()
    files = {p.name for p in (data_dir() / "matches").glob("*.json")}
    changed = False
    for name in files - set(idx):
        try:
            idx[name] = _summary(load_match(name), data_dir() / "matches" / name)
            changed = True
        except (OSError, ValueError, KeyError):
            pass
    for name in set(idx) - files:
        idx.pop(name)
        changed = True
    if changed:
        _save_index(idx)
    return sorted(idx.values(), key=lambda s: s["started_at"], reverse=True)


def result_text(summary: dict) -> str:
    team = summary.get("local_team")
    if team is None or summary.get("winner_team") is None:
        return "–"
    return "Sieg" if summary["winner_team"] == team else "Niederlage"


def playlist(summary: dict) -> str:
    return A.playlist_name(summary.get("playlist_id"))
