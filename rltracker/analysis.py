"""Berechnet aus einem aufgezeichneten Match alle abgeleiteten Statistiken."""
from __future__ import annotations

from collections import Counter, defaultdict

# Spielfeld (Unreal Units, 1 uu = 1 cm). Blau (Team 0) verteidigt das Tor bei -Y.
FIELD_X = 4096.0
FIELD_Y = 5120.0
GOAL_HALF_W = 893.0
GOAL_DEPTH = 880.0
GOAL_H = 642.0
CEILING = 2044.0
THIRD = FIELD_Y / 3.0
UU_TO_KMH = 0.036
SUPERSONIC = 2200.0
AERIAL_Z = 300.0

PLAYLISTS = {
    1: "Duel (Casual)", 2: "Doubles (Casual)", 3: "Standard (Casual)", 4: "Chaos (Casual)",
    6: "Privates Match", 7: "Season", 8: "Offline", 9: "Lokal", 10: "Duel (Ranked)",
    11: "Doubles (Ranked)", 13: "Standard (Ranked)", 15: "Snow Day (Casual)",
    16: "Rocket Labs", 17: "Hoops (Casual)", 18: "Rumble (Casual)", 19: "Workshop",
    22: "Turnier", 23: "Dropshot (Casual)", 24: "Lokales Match", 27: "Hoops (Ranked)",
    28: "Rumble (Ranked)", 29: "Dropshot (Ranked)", 30: "Snow Day (Ranked)",
    34: "Turnier", 38: "Heatseeker", 41: "Gridiron", 43: "Spike Rush", 48: "Knockout",
    50: "Tag", 52: "Heatseeker Doubles", 54: "Freeplay", 55: "Tutorial", 62: "Tutorial",
}

TEAM_NAMES_DE = {0: "Blau", 1: "Orange"}


def playlist_name(pid) -> str:
    if pid is None:
        return "Unbekannt"
    return PLAYLISTS.get(int(pid), f"Playlist {pid}")


def arena_name(a: str) -> str:
    if not a:
        return "Unbekannte Arena"
    return a.replace("_P", "").replace("_", " ")


def attack_sign(team: int) -> int:
    """+1 wenn das Team Richtung +Y angreift (Blau), sonst -1."""
    return 1 if int(team) == 0 else -1


def zone_of(y: float, team: int) -> str:
    rel = y * attack_sign(team)
    if rel < -THIRD:
        return "def"
    if rel > THIRD:
        return "off"
    return "mid"


def fmt_time(sec: float) -> str:
    sec = max(0, int(round(sec)))
    return f"{sec // 60}:{sec % 60:02d}"


def kmh(uu: float) -> float:
    return uu * UU_TO_KMH


MAX_BALL_KMH = 250.0  # Ball schafft max. ~6000 uu/s = 216 km/h


def to_uu(v) -> float:
    """Ballgeschwindigkeit in Unreal Units/s – egal ob das Spiel km/h oder uu/s schickt.

    Rocket League sendet GoalSpeed und BallLastTouch.Speed bereits in km/h (wie im Spiel
    angezeigt, z.B. 87.3), BallHit dagegen in uu/s (z.B. 1450). Werte bis 250 koennen
    in uu/s praktisch nicht vorkommen (das waeren < 9 km/h) und werden als km/h gelesen.
    """
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        return 0.0
    return v / UU_TO_KMH if 0 < v <= MAX_BALL_KMH else v


def fix_units(match: dict) -> dict:
    """Korrigiert Matches, die mit der alten Version (falsche Torgeschwindigkeit) gespeichert wurden."""
    if match.get("units_v2"):
        return match
    for g in match.get("goals", []):
        g["speed"] = to_uu(g.get("speed"))
        g["last_touch_speed"] = to_uu(g.get("last_touch_speed"))
    for c in match.get("crossbars", []):
        c["speed"] = to_uu(c.get("speed"))
    match["units_v2"] = True
    return match


def _pct(a, b) -> float:
    return 100.0 * a / b if b else 0.0


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def player_order(match: dict) -> list[str]:
    ps = match.get("players", {})
    return sorted(ps, key=lambda k: (ps[k]["team"], -ps[k]["stats"].get("Score", 0), ps[k]["name"].lower()))


def analyze(match: dict) -> dict:
    """Liefert {'players': {key: {...}}, 'teams': {0: {...}, 1: {...}}, 'match': {...}}."""
    players = match.get("players", {})
    samples = [s for s in match.get("samples", [])]
    touches = match.get("touches", [])
    boosts = match.get("boosts", [])
    goals = match.get("goals", [])
    feed = match.get("feed", [])
    demos = match.get("demos", [])

    res_p: dict[str, dict] = {}
    for k, p in players.items():
        st = p["stats"]
        team = p["team"]
        my_t = [t for t in touches if t["player"] == k]
        loc_t = [t for t in my_t if t.get("x") is not None]
        zones = Counter(zone_of(t["y"], team) for t in loc_t)
        my_b = [b for b in boosts if b["player"] == k]
        my_g = [g for g in goals if g["scorer"] == k]
        posts = [t["post"] for t in my_t if t["post"] > 0]
        gains = [t["post"] - t["pre"] for t in my_t]

        r = {
            "name": p["name"], "team": team, "left": p.get("left", False),
            "score": st.get("Score", 0), "goals": st.get("Goals", 0), "assists": st.get("Assists", 0),
            "saves": st.get("Saves", 0), "shots": st.get("Shots", 0), "demos": st.get("Demos", 0),
            "touches": st.get("Touches", 0) or len(my_t), "car_touches": st.get("CarTouches", 0),
            "shooting_pct": _pct(st.get("Goals", 0), st.get("Shots", 0)),
            "demos_taken": sum(1 for d in demos if d["victim"] == k),
            "touches_recorded": len(my_t),
            "aerial_touches": sum(1 for t in loc_t if t["z"] > AERIAL_Z),
            "avg_hit_speed": kmh(_mean(posts)),
            "max_hit_speed": kmh(max(posts) if posts else 0),
            "avg_speed_gain": kmh(_mean(gains)),
            "touches_def": zones["def"], "touches_mid": zones["mid"], "touches_off": zones["off"],
            "goal_speed_avg": kmh(_mean(g["speed"] for g in my_g)),
            "goal_speed_max": kmh(max((g["speed"] for g in my_g), default=0)),
            "boost_pickups": len(my_b),
            "boost_big": sum(1 for b in my_b if b["big"]),
            "boost_small": sum(1 for b in my_b if not b["big"]),
            "boost_collected": sum(b["amount"] for b in my_b),
            "boost_stolen": sum(1 for b in my_b if b["big"] and b["y"] * attack_sign(team) > 0),
            "feed": dict(Counter(e["event"] or e["type"] for e in feed if e["player"] == k)),
            "has_live_physics": False,
        }

        # Zeitreihen-Werte (nur verfuegbar, wenn die API sie fuer diesen Spieler sendet)
        rows = [s["players"][k] for s in samples if k in s.get("players", {}) and s.get("active", True)]
        sp = [x["speed"] for x in rows if "speed" in x]
        if sp:
            r["has_live_physics"] = True
            bo = [x["boost"] for x in rows if "boost" in x]
            n = len(rows)
            r.update({
                "avg_speed": kmh(_mean(sp)),
                "max_speed": kmh(max(sp)),
                "supersonic_pct": _pct(sum(1 for x in rows if x.get("supersonic")), n),
                "ground_pct": _pct(sum(1 for x in rows if x.get("ground") and not x.get("wall")), n),
                "wall_pct": _pct(sum(1 for x in rows if x.get("wall")), n),
                "air_pct": _pct(sum(1 for x in rows if not x.get("ground") and not x.get("wall")
                                    and not x.get("demolished")), n),
                "boosting_pct": _pct(sum(1 for x in rows if x.get("boosting")), n),
                "powerslide_pct": _pct(sum(1 for x in rows if x.get("powerslide")), n),
                "avg_boost": _mean(bo),
                "zero_boost_pct": _pct(sum(1 for b in bo if b <= 0), len(bo)),
                "full_boost_pct": _pct(sum(1 for b in bo if b >= 100), len(bo)),
                "slow_pct": _pct(sum(1 for v in sp if v < 1000), len(sp)),
                "boost_speed_pct": _pct(sum(1 for v in sp if 1000 <= v < SUPERSONIC), len(sp)),
                "demolished_pct": _pct(sum(1 for x in rows if x.get("demolished")), n),
            })
        res_p[k] = r

    # ---------------------------------------------------------------- Teams
    res_t = {}
    active = [s for s in samples if s.get("active", True)]
    poss = Counter(s.get("ball_team", 255) for s in active if s.get("ball_team", 255) in (0, 1))
    poss_total = poss[0] + poss[1]
    for team in (0, 1):
        tp = [r for r in res_p.values() if r["team"] == team]
        tt = [t for t in touches if t["team"] == team]
        loc = [t for t in tt if t.get("x") is not None]
        res_t[team] = {
            "name": match["meta"]["teams"].get(str(team), {}).get("name", TEAM_NAMES_DE[team]),
            "goals": int(match["meta"]["teams"].get(str(team), {}).get("score", 0)),
            "shots": sum(r["shots"] for r in tp), "saves": sum(r["saves"] for r in tp),
            "assists": sum(r["assists"] for r in tp), "demos": sum(r["demos"] for r in tp),
            "touches": sum(r["touches"] for r in tp), "score": sum(r["score"] for r in tp),
            "possession_pct": _pct(poss[team], poss_total),
            "avg_hit_speed": kmh(_mean(t["post"] for t in tt if t["post"] > 0)),
            "boost_collected": sum(r["boost_collected"] for r in tp),
            "boost_big": sum(r["boost_big"] for r in tp),
            "touches_in_off_third_pct": _pct(sum(1 for t in loc if zone_of(t["y"], team) == "off"), len(loc)),
            "touches_in_def_third_pct": _pct(sum(1 for t in loc if zone_of(t["y"], team) == "def"), len(loc)),
        }
        res_t[team]["shooting_pct"] = _pct(res_t[team]["goals"], res_t[team]["shots"])

    # Ballhaelften aus Beruehrungen (die API liefert die Ballposition nur bei Kontakt)
    loc_all = [t for t in touches if t.get("y") is not None]
    ball_blue_half = _pct(sum(1 for t in loc_all if t["y"] < 0), len(loc_all))

    hardest = max(touches, key=lambda t: t["post"], default=None)
    fastest_goal = max(goals, key=lambda g: g["speed"], default=None)
    ball_speeds = [s["ball_speed"] for s in active]
    res_m = {
        "duration": match["meta"].get("duration", 0),
        "avg_ball_speed": kmh(_mean(ball_speeds)),
        "max_ball_speed": kmh(max(ball_speeds, default=0)),
        "ball_in_blue_half_pct": ball_blue_half,
        "hardest_hit": hardest, "fastest_goal": fastest_goal,
        "total_touches": len(touches), "crossbars": len(match.get("crossbars", [])),
        "has_live_physics": any(r["has_live_physics"] for r in res_p.values()),
    }
    return {"players": res_p, "teams": res_t, "match": res_m}


def momentum_series(match: dict, window: float = 20.0) -> tuple[list[float], list[float]]:
    """Ballbesitz-Momentum: +1 = Blau hat Kontrolle, -1 = Orange (gleitendes Fenster)."""
    s = [x for x in match.get("samples", []) if x.get("ball_team") in (0, 1)]
    ts, vals = [], []
    j = 0
    for i, x in enumerate(s):
        while s[j]["t"] < x["t"] - window:
            j += 1
        seg = [1 if y["ball_team"] == 0 else -1 for y in s[j:i + 1]]
        ts.append(x["t"])
        vals.append(sum(seg) / len(seg))
    return ts, vals


def local_player_key(match: dict, preferred_name: str = "") -> str | None:
    ps = match.get("players", {})
    if preferred_name:
        for k, p in ps.items():
            if p["name"].lower() == preferred_name.lower():
                return k
    lp = match.get("meta", {}).get("local_player")
    return lp if lp in ps else None


def match_result_for(match: dict, key: str | None) -> str:
    """'Sieg', 'Niederlage' oder '–' aus Sicht des Spielers."""
    meta = match.get("meta", {})
    if key is None or key not in match.get("players", {}):
        return "–"
    team = match["players"][key]["team"]
    winner = meta.get("winner_team")
    if winner is None:
        s0 = meta["teams"]["0"]["score"]
        s1 = meta["teams"]["1"]["score"]
        if s0 == s1 or not meta.get("complete"):
            return "–"
        winner = 0 if s0 > s1 else 1
    return "Sieg" if int(winner) == team else "Niederlage"


def career_summary(matches: list[dict], name: str) -> dict:
    """Gesamtstatistik ueber viele Matches fuer einen Spielernamen."""
    agg = defaultdict(float)
    n = wins = 0
    per_match = []
    for m in matches:
        k = local_player_key(m, name)
        if not k:
            continue
        a = analyze(m)["players"][k]
        n += 1
        res = match_result_for(m, k)
        wins += res == "Sieg"
        for f in ("score", "goals", "assists", "saves", "shots", "demos", "touches", "boost_collected"):
            agg[f] += a[f]
        per_match.append({"date": m["meta"]["started_at"], "score": a["score"], "goals": a["goals"],
                          "result": res, "saves": a["saves"]})
    out = {"matches": n, "wins": wins, "winrate": _pct(wins, n), "per_match": per_match}
    for f, v in agg.items():
        out[f] = v
        out[f"{f}_avg"] = v / n if n else 0
    return out
