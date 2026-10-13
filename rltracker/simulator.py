"""Demo-Modus: simuliert ein 3v3-Match und sendet es wie Rocket League ueber TCP.

So laesst sich die App ohne laufendes Spiel testen:
    python -m rltracker.simulator --speed 8
und in der App einfach verbinden (gleicher Port 49123).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import socket
import threading
import time

BIG_PADS = [(sx * 3072, sy * 4096) for sx in (-1, 1) for sy in (-1, 1)] + [(-3584, 0), (3584, 0)]
_SMALL = [(0, 4240), (1792, 4184), (-1792, 4184), (940, 3308), (-940, 3308), (0, 2816),
          (3584, 2484), (-3584, 2484), (1788, 2300), (-1788, 2300), (2048, 1036), (-2048, 1036),
          (0, 1024)]
SMALL_PADS = _SMALL + [(x, -y) for x, y in _SMALL] + [(1024, 0), (-1024, 0)]

NAMES = [("Du", 0), ("Kumpel", 0), ("Bot Jonny", 0), ("xXRocketXx", 1), ("Turbo_Tim", 1), ("Lisa.RL", 1)]


class Car:
    def __init__(self, name, team, idx):
        self.name, self.team, self.idx = name, team, idx
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.z = 17.0
        self.boost = 33.0
        self.boosting = False
        self.demo_timer = 0.0
        self.stats = dict(Score=0, Goals=0, Shots=0, Assists=0, Saves=0, Touches=0, CarTouches=0, Demos=0)
        self.role = idx % 3  # 0 = Angreifer, 1 = Mitte, 2 = Hinten
        self.skill = random.uniform(0.75, 1.15)

    def ref(self):
        return {"Name": self.name, "Shortcut": self.idx + 1, "TeamNum": self.team}


class MatchSim:
    def __init__(self, length=300, seed=None):
        self.rng = random.Random(seed)
        self.cars = [Car(n, t, i) for i, (n, t) in enumerate(NAMES)]
        self.length = length
        self.clock = float(length)
        self.ot = False
        self.score = [0, 0]
        self.ball = [0.0, 0.0, 93.0]
        self.bv = [0.0, 0.0, 0.0]
        self.last_touch = None
        self.prev_touch = None
        self.touch_cd = 0.0
        self.pad_cd = {}
        self.guid = "".join(self.rng.choice("0123456789ABCDEF") for _ in range(32))
        self.out: list[dict] = []
        self.state = "countdown"
        self.timer = 3.0

    def emit(self, ev, data):
        data = dict(data)
        data.setdefault("MatchGuid", self.guid)
        self.out.append({"Event": ev, "Data": data})

    def kickoff(self):
        self.ball = [0.0, 0.0, 93.0]
        self.bv = [0.0, 0.0, 0.0]
        spots = [(-2048, -2560), (256, -3840), (0, -4608)]
        for c in self.cars:
            sx, sy = spots[c.role]
            sign = 1 if c.team == 0 else -1
            c.x, c.y = sx * sign, sy * sign
            c.vx = c.vy = 0
            c.boost = 33
            c.demo_timer = 0
        self.state, self.timer = "countdown", 3.0
        self.emit("CountdownBegin", {})

    def start(self):
        self.emit("MatchCreated", {})
        for c in self.cars:
            self.emit("PlayerJoined", {"PlayerName": c.name, "PrimaryId": f"Epic|{1000 + c.idx}|0"})
        self.emit("MatchInitialized", {})
        self.kickoff()

    # ------------------------------------------------------------------
    def step(self, dt):
        r = self.rng
        if self.state == "ended":
            return
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "live"
                self.emit("RoundStarted", {})
            return
        if self.state == "goal":
            self.timer -= dt
            if self.timer <= 0:
                self.emit("GoalReplayEnd", {})
                if self.ot or (self.clock <= 0 and self.score[0] != self.score[1]):
                    self.end()
                else:
                    self.kickoff()
            return

        # Uhr
        old = int(math.ceil(self.clock)) if not self.ot else int(self.clock)
        if self.ot:
            self.clock += dt
        else:
            self.clock = max(0.0, self.clock - dt)
        new = int(math.ceil(self.clock)) if not self.ot else int(self.clock)
        if new != old:
            self.emit("ClockUpdatedSeconds", {"TimeSeconds": new, "bOvertime": self.ot})
        if not self.ot and self.clock <= 0 and self.ball[2] < 120:
            if self.score[0] != self.score[1]:
                self.end()
                return
            self.ot = True
            self.clock = 0
            self.kickoff()
            return

        # Ball
        bx, by, bz = self.ball
        self.bv[2] -= 650 * dt
        for i in range(3):
            self.ball[i] += self.bv[i] * dt
        if self.ball[2] < 93:
            self.ball[2] = 93
            self.bv[2] = -self.bv[2] * 0.6
        if self.ball[2] > 1950:
            self.ball[2] = 1950
            self.bv[2] = -abs(self.bv[2])
        for i, lim in ((0, 4000.0), (1, 5030.0)):
            if abs(self.ball[i]) > lim:
                if i == 1 and abs(self.ball[0]) < 893 and self.ball[2] < 642:
                    self.goal()
                    return
                if i == 1 and abs(self.ball[0]) < 1100 and 600 < self.ball[2] < 700:
                    lt = self.last_touch
                    self.emit("CrossbarHit", {"BallLocation": self._bl(), "BallSpeed": self._bs(),
                                              "ImpactForce": r.uniform(50, 300),
                                              "BallLastTouch": {"Player": lt.ref() if lt else {}, "Speed": self._bs()}})
                self.ball[i] = math.copysign(lim, self.ball[i])
                self.bv[i] = -self.bv[i] * 0.7
        for i in (0, 1):
            self.bv[i] *= (1 - 0.15 * dt)
        self.touch_cd -= dt

        # Autos: je Team faehrt der naechste Spieler direkt zum Ball
        chasers = set()
        for team in (0, 1):
            alive = [c for c in self.cars if c.team == team and c.demo_timer <= 0]
            if alive:
                chasers.add(min(alive, key=lambda c: math.hypot(self.ball[0] - c.x, self.ball[1] - c.y)
                                * (0.8 if c.role == 0 else 1.0)).name)
        for c in self.cars:
            if c.demo_timer > 0:
                c.demo_timer -= dt
                if c.demo_timer <= 0:
                    c.x, c.y = (r.uniform(-2000, 2000), -4600 if c.team == 0 else 4600)
                continue
            sign = 1 if c.team == 0 else -1
            # Zielpunkt je nach Rolle: hinter dem Ball, Richtung gegnerisches Tor
            behind = 60 if c.name in chasers else [900, 1600, 2600][c.role] * c.skill
            tx = self.ball[0] if c.name in chasers else self.ball[0] * (0.7 if c.role < 2 else 0.35)
            ty = self.ball[1] - sign * behind
            if c.role == 2 and c.name not in chasers:
                ty = min(ty, -1500) if sign > 0 else max(ty, 1500)
            if c.boost < 25 and r.random() < 0.02:
                px, py = min(BIG_PADS, key=lambda p: (p[0] - c.x) ** 2 + (p[1] - c.y) ** 2)
                tx, ty = px, py
            dx, dy = tx - c.x, ty - c.y
            d = math.hypot(dx, dy) or 1
            want = 1400 if d < 800 else 2300
            c.boosting = d > 1200 and c.boost > 0 and r.random() < 0.7
            if c.boosting:
                c.boost = max(0.0, c.boost - 33 * dt)
            acc = 2500 if c.boosting else 1200
            c.vx += (dx / d * want - c.vx) * min(1, acc / 2300 * dt * 2)
            c.vy += (dy / d * want - c.vy) * min(1, acc / 2300 * dt * 2)
            c.vx += r.gauss(0, 300) * dt
            c.vy += r.gauss(0, 300) * dt
            c.x = max(-4000, min(4000, c.x + c.vx * dt))
            c.y = max(-5000, min(5000, c.y + c.vy * dt))
            c.z = 17 if self.ball[2] < 300 or math.hypot(self.ball[0] - c.x, self.ball[1] - c.y) > 600 \
                else min(self.ball[2], 1500)
            # Boost-Pads
            for pads, big in ((BIG_PADS, True), (SMALL_PADS, False)):
                for p in pads:
                    if self.pad_cd.get(p, 0) > self.clock_abs() and True:
                        continue
                    if (p[0] - c.x) ** 2 + (p[1] - c.y) ** 2 < (208 if big else 144) ** 2:
                        if c.boost >= 100:
                            continue
                        amt = 100 if big else 12
                        c.boost = min(100, c.boost + amt)
                        self.pad_cd[p] = self.clock_abs() + (10 if big else 4)
                        self.emit("BoostPickup", {"Player": c.ref(), "Location": {"X": p[0], "Y": p[1], "Z": 73},
                                                  "BoostAmount": amt,
                                                  "BoostType": "BoostType_Pill" if big else "BoostType_Pad",
                                                  "bReplay": False})
            # Ballkontakt
            if self.touch_cd <= 0 and math.hypot(self.ball[0] - c.x, self.ball[1] - c.y) < 220 * c.skill:
                self.hit(c)
            # Demo
            for o in self.cars:
                if o.team != c.team and o.demo_timer <= 0 and math.hypot(o.x - c.x, o.y - c.y) < 120 \
                        and math.hypot(c.vx, c.vy) > 2100 and r.random() < 0.3:
                    o.demo_timer = 3.0
                    c.stats["Demos"] += 1
                    c.stats["Score"] += 25
                    self.emit("StatfeedEvent", {"EventName": "Demolish", "Type": "Demolition",
                                                "MainTarget": c.ref(), "SecondaryTarget": o.ref()})

    def clock_abs(self):
        return (self.length - self.clock) if not self.ot else self.length + self.clock

    def _bl(self):
        return {"X": round(self.ball[0], 1), "Y": round(self.ball[1], 1), "Z": round(self.ball[2], 1)}

    def _bs(self):
        return math.sqrt(sum(v * v for v in self.bv))

    def hit(self, c):
        r = self.rng
        sign = 1 if c.team == 0 else -1
        pre = self._bs()
        gx, gy = r.gauss(0, 1300), 5120 * sign
        dx, dy = gx - self.ball[0], gy - self.ball[1]
        d = math.hypot(dx, dy) or 1
        power = r.uniform(900, 3600) * c.skill
        if r.random() < 0.3:  # Fehlschuss/Abpraller
            ang = r.uniform(0, 2 * math.pi)
            dx, dy, d = math.cos(ang), math.sin(ang), 1
            power *= 0.6
        self.bv = [dx / d * power, dy / d * power, r.uniform(0, 1100) if r.random() < 0.6 else 0]
        if c.z > 300:
            self.bv[2] += 200
        self.touch_cd = 0.35
        c.stats["Touches"] += 1
        c.stats["Score"] += 2
        if self.last_touch is not c:
            self.prev_touch = self.last_touch
        self.last_touch = c
        self.emit("BallHit", {"Players": [c.ref()],
                              "Ball": {"PreHitSpeed": round(pre, 1), "PostHitSpeed": round(self._bs(), 1),
                                       "Location": self._bl()}})
        # Schuss aufs Tor? (Ballrichtung zeigt aufs Tor und nicht zu weit weg)
        if abs(self.ball[1] - gy) < 3500 and dy * sign > 0 and abs(gx) < 893 and power > 1500:
            c.stats["Shots"] += 1
            c.stats["Score"] += 20
            self.emit("StatfeedEvent", {"EventName": "Shot", "Type": "Shot on Goal", "MainTarget": c.ref()})
        # Save: Ball war auf dem Weg ins eigene Tor
        if abs(self.ball[1] + 5120 * sign) < 1500 and pre > 1500 and r.random() < 0.6:
            c.stats["Saves"] += 1
            c.stats["Score"] += 50
            ev = "EpicSave" if pre > 3000 else "Save"
            self.emit("StatfeedEvent", {"EventName": ev, "Type": "Epic Save" if ev == "EpicSave" else "Save",
                                        "MainTarget": c.ref()})
        if abs(self.ball[1]) < 1700 and r.random() < 0.05:
            self.emit("StatfeedEvent", {"EventName": "Clear", "Type": "Clear", "MainTarget": c.ref()})

    def goal(self):
        lt = self.last_touch
        team = 0 if self.ball[1] > 0 else 1
        scorer = lt if lt and lt.team == team else next(c for c in self.cars if c.team == team)
        assister = self.prev_touch if self.prev_touch and self.prev_touch.team == team and self.prev_touch is not scorer else None
        self.score[team] += 1
        scorer.stats["Goals"] += 1
        scorer.stats["Shots"] = max(scorer.stats["Shots"], scorer.stats["Goals"])
        scorer.stats["Score"] += 100
        data = {"GoalSpeed": round(self._bs() * 0.036, 1), "GoalTime": 0.0, "ImpactLocation": self._bl(),
                "Scorer": scorer.ref(), "BallLastTouch": {"Player": (lt or scorer).ref(), "Speed": round(self._bs() * 0.036, 1)}}
        if assister:
            assister.stats["Assists"] += 1
            assister.stats["Score"] += 50
            data["Assister"] = assister.ref()
        self.emit("GoalScored", data)
        self.emit("StatfeedEvent", {"EventName": "Goal", "Type": "Goal", "MainTarget": scorer.ref()})
        if assister:
            self.emit("StatfeedEvent", {"EventName": "Assist", "Type": "Assist", "MainTarget": assister.ref()})
        self.emit("GoalReplayStart", {})
        self.state, self.timer = "goal", 3.0
        self.last_touch = self.prev_touch = None

    def end(self):
        self.state = "ended"
        winner = 0 if self.score[0] > self.score[1] else 1
        self.emit("MatchEnded", {"WinnerTeamNum": winner})
        self.emit("PodiumStart", {})

    def update_state(self):
        players = []
        for c in self.cars:
            sp = math.hypot(c.vx, c.vy)
            p = {"Name": c.name, "PrimaryId": f"Epic|{1000 + c.idx}|0", "Shortcut": c.idx + 1, "TeamNum": c.team,
                 **c.stats, "Loadout": ["body_octane", "None"], "bHasCar": c.demo_timer <= 0,
                 "Speed": round(sp, 1), "Boost": int(c.boost), "bBoosting": c.boosting,
                 "bOnGround": c.z < 50, "bOnWall": abs(c.x) > 3950, "bPowersliding": False,
                 "bDemolished": c.demo_timer > 0, "bSupersonic": sp > 2200}
            players.append(p)
        winner = ""
        if self.state == "ended":
            winner = "Blue" if self.score[0] > self.score[1] else "Orange"
        return {"Event": "UpdateState", "Data": {
            "MatchGuid": self.guid, "Players": players,
            "Game": {"Teams": [{"Name": "Blue", "TeamNum": 0, "Score": self.score[0], "ColorPrimary": "1873FF"},
                               {"Name": "Orange", "TeamNum": 1, "Score": self.score[1], "ColorPrimary": "C26418"}],
                     "PlaylistId": 13, "TimeSeconds": int(math.ceil(self.clock)) if not self.ot else int(self.clock),
                     "bOvertime": self.ot,
                     "Ball": {"Speed": round(self._bs(), 1),
                              "TeamNum": self.last_touch.team if self.last_touch else 255},
                     "bReplay": self.state == "goal", "bHasWinner": self.state == "ended", "Winner": winner,
                     "Arena": "Stadium_P", "bHasTarget": True, "Target": self.cars[0].ref()}}}


def generate_messages(length=300, rate=10, seed=1) -> list[dict]:
    """Komplettes Match als Nachrichtenliste (fuer Tests, ohne Netzwerk)."""
    sim = MatchSim(length, seed)
    sim.start()
    msgs = []
    dt = 1.0 / rate
    while sim.state != "ended" and len(msgs) < 400000:
        sim.step(dt)
        msgs.extend(sim.out)
        sim.out.clear()
        msgs.append(sim.update_state())
    msgs.extend(sim.out)
    msgs.append(sim.update_state())
    msgs.append({"Event": "MatchDestroyed", "Data": {"MatchGuid": sim.guid}})
    return msgs


def serve(port=49123, speed=6.0, length=300, rate=30, stop: threading.Event | None = None, log=print,
          matches: int | None = None):
    """TCP-Server, der wie Rocket League Matches sendet (matches=None: endlos, sonst genau so viele)."""
    stop = stop or threading.Event()
    played = 0
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(0.5)
    log(f"Demo-Server läuft auf 127.0.0.1:{port} (Tempo x{speed})")
    try:
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            log("Tracker verbunden – starte Demo-Match")
            try:
                while not stop.is_set():
                    sim = MatchSim(length, seed=random.randint(0, 10 ** 6))
                    sim.start()
                    dt_real = 1.0 / rate
                    while not stop.is_set() and sim.state != "ended":
                        for _ in range(max(1, int(speed))):
                            sim.step(dt_real * speed / max(1, int(speed)))
                        msgs = sim.out + [sim.update_state()]
                        sim.out = []
                        conn.sendall("".join(json.dumps(m) for m in msgs).encode())
                        time.sleep(dt_real)
                    conn.sendall("".join(json.dumps(m) for m in sim.out + [sim.update_state()]).encode())
                    stop.wait(4)
                    conn.sendall(json.dumps({"Event": "MatchDestroyed", "Data": {"MatchGuid": sim.guid}}).encode())
                    played += 1
                    if matches is not None and played >= matches:
                        log("Demo-Match fertig")
                        return
                    stop.wait(2)
            except OSError:
                log("Tracker getrennt")
            finally:
                conn.close()
    finally:
        srv.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Rocket League Stats-API Simulator")
    ap.add_argument("--port", type=int, default=49123)
    ap.add_argument("--speed", type=float, default=6.0, help="Zeitraffer-Faktor")
    ap.add_argument("--length", type=int, default=300, help="Spiellänge in Sekunden")
    a = ap.parse_args()
    serve(a.port, a.speed, a.length)
