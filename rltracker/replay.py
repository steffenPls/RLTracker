"""Replay-Analyse: volle Positionsdaten aller Spieler aus .replay-Dateien.

Nutzt die Bibliothek subtr-actor (pip install subtr-actor-py). Damit gibt es
Heatmaps, wo jeder Spieler das ganze Match ueber war – nicht nur Ballkontakte.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import analysis as A
from .storage import documents_dir

FPS = 10.0
GLOBAL = ["BallRigidBody", "SecondsRemaining"]
PLAYER = ["PlayerRigidBody", "PlayerBoost"]


def available() -> tuple[bool, str]:
    try:
        import subtr_actor  # noqa: F401
        return True, ""
    except Exception as e:  # ImportError oder DLL-Probleme
        return False, str(e)


def demo_dirs() -> list[Path]:
    base = [documents_dir(), Path.home() / "Documents", Path.home() / "OneDrive" / "Documents",
            Path.home() / "OneDrive" / "Dokumente"]
    out = []
    for b in base:
        for sub in ("Demos", "DemosEpic"):
            p = b / "My Games" / "Rocket League" / "TAGame" / sub
            if p.is_dir() and p not in out:
                out.append(p)
    return out


def list_replays() -> list[Path]:
    files = []
    for d in demo_dirs():
        files.extend(d.glob("*.replay"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def newest_replay(since: float = 0.0) -> Path | None:
    for p in list_replays():
        if p.stat().st_mtime >= since:
            return p
        break
    return None


def _col(headers: list[str], name: str) -> int:
    low = [h.lower() for h in headers]
    for i, h in enumerate(low):
        if h == name or h.endswith(name):
            return i
    raise KeyError(name)


def analyze_replay(path: str | Path) -> dict:
    import subtr_actor

    t0 = time.time()
    meta, arr = subtr_actor.get_ndarray_with_info_from_replay_filepath(
        str(path), global_feature_adders=GLOBAL, player_feature_adders=PLAYER, fps=FPS, dtype="float32")
    arr = np.asarray(arr, dtype=np.float64)
    heads = meta.get("column_headers", {})
    gh, ph = heads.get("global_headers", []), heads.get("player_headers", [])
    rmeta = meta.get("replay_meta", {})
    plist = [(p, 0) for p in rmeta.get("team_zero", [])] + [(p, 1) for p in rmeta.get("team_one", [])]

    bx = _col(gh, "position x")
    ball = arr[:, bx:bx + 3]
    try:
        bvx = _col(gh, "linear velocity x")
        ball_vel = arr[:, bvx:bvx + 3]
    except KeyError:
        ball_vel = np.zeros_like(ball)
    try:
        secs = arr[:, _col(gh, "seconds remaining")]
    except KeyError:
        secs = None
    ng, npl = len(gh), len(ph)
    ipx, ivx = _col(ph, "position x"), _col(ph, "linear velocity x")
    try:
        ib = next(i for i, h in enumerate(ph) if "boost" in h.lower())
    except StopIteration:
        ib = None

    players = []
    for i, (pinfo, team) in enumerate(plist):
        off = ng + i * npl
        if off + npl > arr.shape[1]:
            break
        pos = arr[:, off + ipx: off + ipx + 3]
        vel = arr[:, off + ivx: off + ivx + 3]
        boost = arr[:, off + ib] / 2.55 if ib is not None else None
        valid = ~((np.abs(pos).sum(axis=1) < 1e-3) | np.isnan(pos).any(axis=1))
        players.append({"name": pinfo.get("name", f"Spieler {i + 1}"), "team": team,
                        "pos": pos, "vel": vel, "boost": boost, "valid": valid})

    _scale_velocities(players, ball_vel)
    for p in players:
        p["summary"] = _summary(p, players, ball)

    ball_ok = ~(np.abs(ball).sum(axis=1) < 1e-3)
    ball = ball[ball_ok]
    return {
        "path": str(path), "name": Path(path).stem, "fps": FPS, "frames": int(arr.shape[0]),
        "duration": float(arr.shape[0] / FPS), "map": rmeta.get("map_name") or _header(rmeta, "MapName"),
        "players": players, "ball": ball,
        "ball_blue_half_pct": float(100 * np.mean(ball[:, 1] < 0)) if len(ball) else 0.0,
        "ball_air_pct": float(100 * np.mean(ball[:, 2] > 300)) if len(ball) else 0.0,
        "seconds_remaining": secs, "parse_seconds": time.time() - t0,
        "extra": _extra_stats(path),
    }


def _header(rmeta: dict, key: str):
    for item in rmeta.get("all_headers", []) or []:
        try:
            k, v = item
        except (TypeError, ValueError):
            continue
        if k == key:
            return v if not isinstance(v, dict) else next(iter(v.values()), "")
    return ""


def _scale_velocities(players, ball_vel) -> None:
    """Manche Replay-Versionen speichern Geschwindigkeiten x10 – automatisch korrigieren."""
    sp = np.concatenate([np.linalg.norm(p["vel"][p["valid"]], axis=1) for p in players] or [np.zeros(1)])
    if sp.size and np.percentile(sp, 90) > 6000:
        for p in players:
            p["vel"] = p["vel"] / 10.0


def _summary(p: dict, players: list[dict], ball: np.ndarray) -> dict:
    ok = p["valid"]
    n = max(1, int(ok.sum()))
    pos, vel = p["pos"][ok], p["vel"][ok]
    sign = A.attack_sign(p["team"])
    speed = np.linalg.norm(vel, axis=1)
    rel_y = pos[:, 1] * sign
    on_wall = ((np.abs(pos[:, 0]) > 3900) | (np.abs(pos[:, 1]) > 4950)) & (pos[:, 2] > 100)
    in_air = (pos[:, 2] > 100) & ~on_wall
    ball_ok = ball[ok]
    step = np.linalg.norm(np.diff(p["pos"][:, :2], axis=0), axis=1)
    step_ok = ok[1:] & ok[:-1] & (step < 1000)
    dist_ball = np.linalg.norm(pos - ball_ok, axis=1)

    # Naechster am Ball innerhalb des eigenen Teams
    mates = [q for q in players if q["team"] == p["team"]]
    closest = np.zeros(len(ok), bool)
    if len(mates) > 1:
        d = np.stack([np.where(q["valid"], np.linalg.norm(q["pos"] - ball, axis=1), np.inf) for q in mates])
        closest = d.argmin(axis=0) == mates.index(p)
    s = {
        "avg_speed": float(A.kmh(speed.mean())) if speed.size else 0.0,
        "max_speed": float(A.kmh(speed.max())) if speed.size else 0.0,
        "supersonic_pct": float(100 * np.mean(speed > 2200)) if speed.size else 0.0,
        "slow_pct": float(100 * np.mean(speed < 1000)) if speed.size else 0.0,
        "air_pct": float(100 * in_air.sum() / n), "wall_pct": float(100 * on_wall.sum() / n),
        "ground_pct": float(100 * (n - in_air.sum() - on_wall.sum()) / n),
        "def_pct": float(100 * np.mean(rel_y < -A.THIRD)) if n else 0.0,
        "mid_pct": float(100 * np.mean(np.abs(rel_y) <= A.THIRD)) if n else 0.0,
        "off_pct": float(100 * np.mean(rel_y > A.THIRD)) if n else 0.0,
        "own_half_pct": float(100 * np.mean(rel_y < 0)) if n else 0.0,
        "behind_ball_pct": float(100 * np.mean(rel_y < ball_ok[:, 1] * sign)) if n else 0.0,
        "avg_dist_ball": float(dist_ball.mean() / 100) if n else 0.0,
        "closest_to_ball_pct": float(100 * closest[ok].mean()) if n else 0.0,
        "distance_km": float(step[step_ok].sum() / 100000),
        "avg_height": float(pos[:, 2].mean() / 100) if n else 0.0,
        "max_height": float(pos[:, 2].max() / 100) if pos.size else 0.0,
        "hz_ground": float(100 * np.mean((pos[:, 2] < 60) & ~on_wall)) if n else 0.0,
        "hz_low": float(100 * np.mean((pos[:, 2] >= 60) & (pos[:, 2] < 300) & ~on_wall)) if n else 0.0,
        "hz_mid": float(100 * np.mean((pos[:, 2] >= 300) & (pos[:, 2] < 1000) & ~on_wall)) if n else 0.0,
        "hz_high": float(100 * np.mean((pos[:, 2] >= 1000) & ~on_wall)) if n else 0.0,
        "hz_wall": float(100 * np.mean(on_wall)) if n else 0.0,
        "time_played": float(n / FPS),
    }
    if p["boost"] is not None:
        b = p["boost"][ok]
        s.update({"avg_boost": float(b.mean()), "zero_boost_pct": float(100 * np.mean(b < 1)),
                  "full_boost_pct": float(100 * np.mean(b > 99))})
    return s


def _extra_stats(path) -> dict:
    """Zusaetzliche fertige Statistiken von subtr-actor (falls die Version sie anbietet)."""
    try:
        import subtr_actor
        return subtr_actor.get_summed_stats(str(path))
    except Exception:
        return {}


def flatten(d, prefix="") -> list[tuple[str, str]]:
    """Verschachtelte Statistiken als (Pfad, Wert)-Liste fuer die Tabellenansicht."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(d, list):
        if len(d) <= 12 and all(not isinstance(x, (dict, list)) for x in d):
            out.append((prefix, ", ".join(_fmt(x) for x in d)))
        else:
            for i, v in enumerate(d[:50]):
                out.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        out.append((prefix, _fmt(d)))
    return out


def _fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)
