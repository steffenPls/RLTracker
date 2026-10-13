"""Zeichnet ein laufendes Match aus den Stats-API-Nachrichten auf.

Reine Python-Logik ohne Oberflaeche, damit sie auch ohne Spiel getestet werden kann.
Ergebnis ist ein einfaches dict (JSON-faehig), das gespeichert und ausgewertet wird.
"""
from __future__ import annotations

import copy
import time
from collections import Counter
from datetime import datetime

from .analysis import to_uu

SAMPLE_INTERVAL = 0.5  # Sekunden Spielzeit zwischen Zeitreihen-Punkten

STAT_FIELDS = ["Score", "Goals", "Shots", "Assists", "Saves", "Touches", "CarTouches", "Demos"]
LIVE_FIELDS = {
    "Speed": "speed", "Boost": "boost", "bBoosting": "boosting", "bOnGround": "ground",
    "bOnWall": "wall", "bSupersonic": "supersonic", "bDemolished": "demolished",
    "bPowersliding": "powerslide",
}


def pkey(p: dict | None) -> str | None:
    """Eindeutiger Schluessel fuer einen Spieler: 'Team:Name'."""
    if not p or not p.get("Name"):
        return None
    return f"{int(p.get('TeamNum', 0))}:{p['Name']}"


def _loc(d: dict | None) -> tuple[float, float, float] | None:
    if not d:
        return None
    try:
        return float(d.get("X", 0)), float(d.get("Y", 0)), float(d.get("Z", 0))
    except (TypeError, ValueError):
        return None


class MatchRecorder:
    def __init__(self) -> None:
        self.match: dict | None = None
        self.last_finished: dict | None = None
        self._reset_clock()

    # ------------------------------------------------------------------ Zeit
    def _reset_clock(self) -> None:
        self._clock: int | None = None
        self._ot = False
        self._initial: int = 0
        self._clock_wall = time.monotonic()
        self._active = False
        self._last_sample_t = -1e9
        self._targets: Counter = Counter()
        self._last_ball_team = 255

    def game_time(self) -> float:
        """Gespielte Sekunden seit Anpfiff (aus der Spieluhr abgeleitet)."""
        if self._clock is None:
            return 0.0
        base = (self._initial + self._clock) if self._ot else (self._initial - self._clock)
        frac = 0.0
        if self._active:
            frac = min(time.monotonic() - self._clock_wall, 0.99)
            if not self._ot and self._clock == 0:
                frac = 0.0
        return max(0.0, base + frac)

    def _update_clock(self, seconds, overtime) -> None:
        if seconds is None:
            return
        seconds = int(seconds)
        overtime = bool(overtime)
        if not overtime and seconds > self._initial:
            self._initial = seconds
        if seconds != self._clock or overtime != self._ot:
            self._clock_wall = time.monotonic()
        self._clock, self._ot = seconds, overtime
        if self.match is not None:
            self.match["meta"]["overtime"] = self.match["meta"]["overtime"] or overtime
            self.match["meta"]["match_length"] = self._initial

    # ----------------------------------------------------------- Lebenszyklus
    def _new_match(self, guid: str = "") -> None:
        self._reset_clock()
        self.match = {
            "version": 1,
            "source": "live",
            "meta": {
                "guid": guid, "arena": "", "playlist_id": None,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "ended_at": None, "duration": 0.0, "overtime": False, "match_length": 0,
                "winner_team": None, "complete": False, "local_player": None,
                "teams": {"0": {"name": "Blue", "score": 0, "color": "3D8BFF"},
                          "1": {"name": "Orange", "score": 0, "color": "FF8C1A"}},
            },
            "players": {},
            "samples": [], "touches": [], "goals": [], "boosts": [],
            "crossbars": [], "feed": [], "demos": [], "events": [],
            "units_v2": True,
        }

    def _ensure_match(self, guid: str = "") -> dict:
        if self.match is None:
            self._new_match(guid)
        elif guid and self.match["meta"]["guid"] and guid != self.match["meta"]["guid"]:
            self._finish(complete=False)
            self._new_match(guid)
        elif guid and not self.match["meta"]["guid"]:
            self.match["meta"]["guid"] = guid
        return self.match

    def _finish(self, complete: bool) -> dict | None:
        m = self.match
        self.match = None
        if m is None:
            return None
        meta = m["meta"]
        meta["ended_at"] = datetime.now().isoformat(timespec="seconds")
        meta["complete"] = complete or meta["complete"]
        if self._targets:
            meta["local_player"] = self._targets.most_common(1)[0][0]
        if meta["duration"] < 20 and not m["goals"] and len(m["touches"]) < 5:
            return None  # zu kurz – vermutlich nur Menue/Freeplay-Schnipsel
        if len(m["players"]) < 2:
            return None  # Freeplay/Training – kein echtes Match
        self.last_finished = m
        return m

    def _player(self, key: str, team: int, name: str) -> dict:
        players = self.match["players"]
        if key not in players:
            players[key] = {"name": name, "team": team, "primary_id": "", "shortcut": None,
                            "stats": {f: 0 for f in STAT_FIELDS}, "loadout": [], "left": False}
        return players[key]

    def _stamp(self) -> float:
        t = round(self.game_time(), 2)
        if self.match is not None:
            self.match["meta"]["duration"] = max(self.match["meta"]["duration"], t)
        return t

    # ---------------------------------------------------------------- Events
    def handle(self, msg: dict) -> list[tuple[str, object]]:
        """Verarbeitet eine Nachricht. Gibt Signale fuer die Oberflaeche zurueck."""
        ev, d = msg.get("Event"), msg.get("Data") or {}
        guid = d.get("MatchGuid", "") if isinstance(d, dict) else ""
        signals: list[tuple[str, object]] = []
        fn = getattr(self, f"_on_{ev}", None)

        if ev in ("MatchCreated", "MatchInitialized"):
            if self.match is None or (guid and guid != self.match["meta"]["guid"]) or \
                    (ev == "MatchCreated" and self.match["meta"]["duration"] > 5):
                if self.match is not None:
                    done = self._finish(complete=False)
                    if done:
                        signals.append(("match_ended", done))
                self._new_match(guid)
                signals.append(("match_started", self.match))
            return signals

        if ev == "MatchDestroyed":
            if self.match is not None:
                done = self._finish(complete=self.match["meta"]["complete"])
                if done:
                    signals.append(("match_ended", done))
            return signals

        if ev == "MatchEnded":
            if self.match is not None:
                self.match["meta"]["winner_team"] = d.get("WinnerTeamNum")
                self.match["meta"]["complete"] = True
                self._stamp()
                self._active = False
                self.match["events"].append({"t": self._stamp(), "event": "MatchEnded"})
                # Match bleibt offen, damit finale UpdateStates (Podium) noch einfliessen;
                # die Oberflaeche zeigt die Auswertung sofort an.
                snapshot = copy.deepcopy(self.match)
                if self._targets:
                    snapshot["meta"]["local_player"] = self._targets.most_common(1)[0][0]
                snapshot["meta"]["ended_at"] = datetime.now().isoformat(timespec="seconds")
                self.last_finished = snapshot
                signals.append(("match_ended", snapshot))
                self._ended_guid = self.match["meta"]["guid"]
                self.match = None
            return signals

        if ev in ("PodiumStart",):
            return signals

        if self.match is None:
            if ev == "UpdateState" and not self._looks_like_new_match(d):
                return signals
            if ev not in ("UpdateState", "RoundStarted", "CountdownBegin", "BallHit", "GoalScored"):
                return signals
            self._new_match(guid)
            signals.append(("match_started", self.match))
        else:
            self._ensure_match(guid)

        if fn:
            fn(d)
        signals.append(("update", ev))
        return signals

    def _looks_like_new_match(self, d: dict) -> bool:
        guid = d.get("MatchGuid", "")
        if guid and guid == getattr(self, "_ended_guid", None):
            return False  # Podium/Nachspiel des gerade beendeten Matches
        game = d.get("Game") or {}
        if game.get("bHasWinner") or game.get("bReplay"):
            return False
        return len(d.get("Players") or []) >= 1

    def _on_UpdateState(self, d: dict) -> None:
        m = self.match
        game = d.get("Game") or {}
        meta = m["meta"]
        self._update_clock(game.get("TimeSeconds"), game.get("bOvertime"))
        if game.get("Arena"):
            meta["arena"] = game["Arena"]
        if game.get("PlaylistId") is not None:
            meta["playlist_id"] = game["PlaylistId"]
        for team in game.get("Teams") or []:
            tn = str(team.get("TeamNum", 0))
            meta["teams"][tn] = {"name": team.get("Name") or meta["teams"][tn]["name"],
                                 "score": int(team.get("Score", 0)),
                                 "color": team.get("ColorPrimary") or meta["teams"][tn]["color"]}
        ball = game.get("Ball") or {}
        if ball.get("TeamNum") is not None:
            self._last_ball_team = int(ball["TeamNum"])
        if game.get("bHasTarget") and game.get("Target") and not game.get("bReplay"):
            k = pkey(game["Target"])
            if k:
                self._targets[k] += 1

        live = {}
        for p in d.get("Players") or []:
            k = pkey(p)
            if not k:
                continue
            pl = self._player(k, int(p.get("TeamNum", 0)), p["Name"])
            pl["left"] = False
            if p.get("PrimaryId"):
                pl["primary_id"] = p["PrimaryId"]
            if p.get("Shortcut") is not None:
                pl["shortcut"] = p["Shortcut"]
            if p.get("Loadout"):
                pl["loadout"] = p["Loadout"]
            for f in STAT_FIELDS:
                if f in p:
                    pl["stats"][f] = int(p[f] or 0)
            row = {"score": pl["stats"]["Score"], "goals": pl["stats"]["Goals"],
                   "touches": pl["stats"]["Touches"]}
            for src, dst in LIVE_FIELDS.items():
                if src in p:
                    v = p[src]
                    row[dst] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else bool(v)
            if p.get("Attacker"):
                row["attacker"] = pkey(p["Attacker"])
            live[k] = row

        if game.get("bReplay"):
            return  # waehrend Tor-Wiederholungen keine Zeitreihe aufzeichnen
        t = self._stamp()
        if t - self._last_sample_t >= SAMPLE_INTERVAL:
            self._last_sample_t = t
            m["samples"].append({
                "t": t, "clock": self._clock, "ot": self._ot,
                "score": [meta["teams"]["0"]["score"], meta["teams"]["1"]["score"]],
                "ball_speed": float(ball.get("Speed", 0) or 0),
                "ball_team": self._last_ball_team,
                "active": self._active,
                "players": live,
            })

    def _on_ClockUpdatedSeconds(self, d: dict) -> None:
        self._update_clock(d.get("TimeSeconds"), d.get("bOvertime"))

    def _on_RoundStarted(self, d: dict) -> None:
        self._active = True
        self._clock_wall = time.monotonic()
        self.match["events"].append({"t": self._stamp(), "event": "RoundStarted"})

    def _on_CountdownBegin(self, d: dict) -> None:
        self._active = False
        self.match["events"].append({"t": self._stamp(), "event": "Kickoff"})

    def _on_MatchPaused(self, d: dict) -> None:
        self._active = False

    def _on_MatchUnpaused(self, d: dict) -> None:
        self._active = True

    def _on_BallHit(self, d: dict) -> None:
        ball = d.get("Ball") or {}
        loc = _loc(ball.get("Location"))
        t = self._stamp()
        for p in d.get("Players") or []:
            k = pkey(p)
            if not k:
                continue
            self._player(k, int(p.get("TeamNum", 0)), p["Name"])
            self.match["touches"].append({
                "t": t, "player": k, "team": int(p.get("TeamNum", 0)),
                "x": loc[0] if loc else None, "y": loc[1] if loc else None, "z": loc[2] if loc else None,
                "pre": float(ball.get("PreHitSpeed", 0) or 0),
                "post": float(ball.get("PostHitSpeed", 0) or 0),
            })

    def _on_BoostPickup(self, d: dict) -> None:
        if d.get("bReplay"):
            return
        p = d.get("Player") or {}
        k = pkey(p)
        loc = _loc(d.get("Location"))
        if not k or not loc:
            return
        self._player(k, int(p.get("TeamNum", 0)), p["Name"])
        self.match["boosts"].append({
            "t": self._stamp(), "player": k, "team": int(p.get("TeamNum", 0)),
            "x": loc[0], "y": loc[1], "z": loc[2],
            "amount": float(d.get("BoostAmount", 0) or 0),
            "big": "Pill" in str(d.get("BoostType", "")),
        })

    def _on_GoalScored(self, d: dict) -> None:
        self._active = False
        loc = _loc(d.get("ImpactLocation")) or (None, None, None)
        scorer = d.get("Scorer") or {}
        last = (d.get("BallLastTouch") or {})
        g = {
            "t": self._stamp(), "clock": self._clock, "ot": self._ot,
            "scorer": pkey(scorer), "team": int(scorer.get("TeamNum", 0)),
            "assister": pkey(d.get("Assister")),
            "speed": to_uu(d.get("GoalSpeed")),
            "round_length": float(d.get("GoalTime", 0) or 0),
            "x": loc[0], "y": loc[1], "z": loc[2],
            "last_touch": pkey(last.get("Player")),
            "last_touch_speed": to_uu(last.get("Speed")),
        }
        # Schussposition = letzte Beruehrung des Torschuetzen vor dem Tor
        for tch in reversed(self.match["touches"]):
            if tch["player"] == g["scorer"] and g["t"] - tch["t"] < 6:
                g["shot_x"], g["shot_y"], g["shot_z"] = tch["x"], tch["y"], tch["z"]
                break
        self.match["goals"].append(g)
        tn = str(g["team"])
        self.match["meta"]["teams"][tn]["score"] = max(
            self.match["meta"]["teams"][tn]["score"],
            sum(1 for x in self.match["goals"] if x["team"] == g["team"]))

    def _on_CrossbarHit(self, d: dict) -> None:
        loc = _loc(d.get("BallLocation")) or (None, None, None)
        last = d.get("BallLastTouch") or {}
        self.match["crossbars"].append({
            "t": self._stamp(), "x": loc[0], "y": loc[1], "z": loc[2],
            "speed": to_uu(d.get("BallSpeed")), "force": float(d.get("ImpactForce", 0) or 0),
            "player": pkey(last.get("Player")),
        })

    def _on_StatfeedEvent(self, d: dict) -> None:
        main, sec = pkey(d.get("MainTarget")), pkey(d.get("SecondaryTarget"))
        t = self._stamp()
        e = {"t": t, "event": d.get("EventName", ""), "type": d.get("Type", ""),
             "player": main, "target": sec}
        # Position: letzte Beruehrung dieses Spielers kurz davor (fuer Schuss-/Save-Karte)
        for tch in reversed(self.match["touches"]):
            if t - tch["t"] > 3:
                break
            if tch["player"] == main and tch["x"] is not None:
                e["x"], e["y"], e["z"] = tch["x"], tch["y"], tch["z"]
                break
        self.match["feed"].append(e)
        if "demol" in e["event"].lower() or "demol" in e["type"].lower():
            self.match["demos"].append({"t": t, "attacker": main, "victim": sec})

    def _on_GoalReplayStart(self, d: dict) -> None:
        self._active = False

    def _on_PlayerJoined(self, d: dict) -> None:
        self.match["events"].append({"t": self._stamp(), "event": "PlayerJoined",
                                     "name": d.get("PlayerName", "")})

    def _on_PlayerLeft(self, d: dict) -> None:
        name = d.get("PlayerName", "")
        for pl in self.match["players"].values():
            if pl["name"] == name:
                pl["left"] = True
        self.match["events"].append({"t": self._stamp(), "event": "PlayerLeft", "name": name})
