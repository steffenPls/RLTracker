"""Auswertung eines Matches: Uebersicht, Heatmaps, Torszenen, Boost, Verlauf, Spieler …"""
from __future__ import annotations

import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QSplitter, QTabWidget, QVBoxLayout, QWidget)

from . import analysis as A
from . import plots as P
from .widgets import Canvas, ScoreBug, StatTile, display_font, fill_table, make_table

SCOREBOARD_COLS = [
    ("Spieler", None), ("Punkte", "score"), ("Tore", "goals"), ("Vorlagen", "assists"), ("Paraden", "saves"),
    ("Schüsse", "shots"), ("Trefferquote %", "shooting_pct"), ("Ballkontakte", "touches"),
    ("Luftkontakte", "aerial_touches"), ("Ø Schuss km/h", "avg_hit_speed"), ("Max. Schuss km/h", "max_hit_speed"),
    ("Demos", "demos"), ("Demoliert", "demos_taken"), ("Boost gesammelt", "boost_collected"),
    ("Große Pads", "boost_big"), ("Kleine Pads", "boost_small"), ("Geklaute Pads", "boost_stolen"),
    ("Ø Tempo km/h", "avg_speed"), ("Überschall %", "supersonic_pct"), ("Luft %", "air_pct"),
    ("Ø Boost", "avg_boost"), ("0 Boost %", "zero_boost_pct"),
]

DETAIL_LABELS = {
    "score": "Punkte", "goals": "Tore", "assists": "Vorlagen", "saves": "Paraden", "shots": "Schüsse",
    "shooting_pct": "Trefferquote (%)", "touches": "Ballkontakte (Spiel)", "car_touches": "Auto-Kontakte",
    "touches_recorded": "Aufgezeichnete Kontakte", "aerial_touches": "Luftkontakte (>3 m)",
    "touches_def": "Kontakte eigenes Drittel", "touches_mid": "Kontakte Mitte", "touches_off": "Kontakte gegn. Drittel",
    "avg_touch_height": "Ø Höhe der Ballkontakte (m)", "max_touch_height": "Höchste Ballberührung (m)",
    "height_ground": "Kontakte am Boden", "height_jump": "Kontakte in Sprunghöhe", "height_air": "Kontakte in der Luft",
    "height_high": "Kontakte hoch / an der Decke", "height_wall": "Kontakte an der Wand",
    "avg_hit_speed": "Ø Ballgeschw. nach Kontakt (km/h)", "max_hit_speed": "Härtester Schuss (km/h)",
    "avg_speed_gain": "Ø Tempo-Zuwachs pro Kontakt (km/h)", "goal_speed_avg": "Ø Torgeschwindigkeit (km/h)",
    "goal_speed_max": "Schnellstes Tor (km/h)", "demos": "Demos verteilt", "demos_taken": "Selbst demoliert",
    "boost_pickups": "Boost-Pickups", "boost_big": "Große Pads", "boost_small": "Kleine Pads",
    "boost_collected": "Boost gesammelt", "boost_stolen": "Große Pads beim Gegner",
    "avg_speed": "Ø Tempo (km/h)", "max_speed": "Höchsttempo (km/h)", "supersonic_pct": "Überschall (%)",
    "slow_pct": "Langsam < 36 km/h (%)", "boost_speed_pct": "Schnell (%)", "ground_pct": "Am Boden (%)",
    "wall_pct": "An der Wand (%)", "air_pct": "In der Luft (%)", "boosting_pct": "Boost gedrückt (%)",
    "powerslide_pct": "Powerslide (%)", "avg_boost": "Ø Boost", "zero_boost_pct": "Ohne Boost (%)",
    "full_boost_pct": "Voller Boost (%)", "demolished_pct": "Zeit zerstört (%)",
}

FEED_DE = {"Goal": "Tor", "Assist": "Vorlage", "Save": "Parade", "EpicSave": "Epische Parade",
           "Shot": "Schuss", "Demolish": "Demo", "Clear": "Klärung", "Center": "Flanke",
           "AerialGoal": "Luft-Tor", "BicycleGoal": "Fallrückzieher-Tor", "LongGoal": "Weitschuss-Tor",
           "TurtleGoal": "Turtle-Tor", "HatTrick": "Hattrick", "Playmaker": "Spielmacher", "Savior": "Retter",
           "MVP": "MVP", "Win": "Sieg", "OwnGoal": "Eigentor", "FirstTouch": "Erster Kontakt",
           "PoolShot": "Poolshot", "BackwardsGoal": "Rückwärts-Tor", "OvertimeGoal": "Overtime-Tor",
           "HighFive": "High Five", "LowFive": "Low Five", "Juggle": "Jonglieren", "BreakoutDamage": "Schaden"}


def feed_name(e: str) -> str:
    return FEED_DE.get(e.replace(" ", ""), e)


class MatchView(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.match: dict | None = None
        self.an: dict | None = None
        self._dirty: set[int] = set()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        self.result = QLabel("Noch kein Match")
        self.result.setFont(display_font(24, True, True))
        self.info = QLabel("Spiel ein Match – die Auswertung erscheint hier automatisch.")
        self.info.setObjectName("muted")
        col.addWidget(self.result)
        col.addWidget(self.info)
        head.addLayout(col)
        self.bug = ScoreBug(compact=True)
        self.bug.setVisible(False)
        head.addWidget(self.bug, 1)
        self.btn_png = QPushButton("Diagramm als PNG")
        self.btn_csv = QPushButton("Tabelle als CSV")
        self.btn_png.clicked.connect(self._export_png)
        self.btn_csv.clicked.connect(self._export_csv)
        head.addWidget(self.btn_png)
        head.addWidget(self.btn_csv)
        lay.addLayout(head)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.tabs.currentChanged.connect(self._render_current)

        # 0 Uebersicht ---------------------------------------------------------
        ov = QWidget()
        ol = QVBoxLayout(ov)
        self.highlights = QGridLayout()
        self.highlights.setHorizontalSpacing(12)
        ol.addLayout(self.highlights)
        self.scoreboard = make_table([c for c, _ in SCOREBOARD_COLS])
        ol.addWidget(self.scoreboard, 3)
        tl = QHBoxLayout()
        self.teamtable = make_table(["Teamvergleich", "Blau", "Orange"], sortable=False)
        tl.addWidget(self.teamtable, 1)
        self.awards = make_table(["Spieler", "Auszeichnung", "Anzahl"])
        tl.addWidget(self.awards, 1)
        ol.addLayout(tl, 2)
        self.tabs.addTab(ov, "Übersicht")

        # 1 Heatmaps -----------------------------------------------------------
        hm = QWidget()
        hl = QVBoxLayout(hm)
        bar = QHBoxLayout()
        self.hm_who = QComboBox()
        self.hm_mode = QComboBox()
        self.hm_mode.addItems(["Heatmap", "Punkte", "Heatmap + Punkte"])
        self.hm_mode.setCurrentIndex(2)
        self.hm_norm = QCheckBox("Aus Sicht des eigenen Teams (eigenes Tor links)")
        for w in (QLabel("Spieler:"), self.hm_who, QLabel("Ansicht:"), self.hm_mode, self.hm_norm):
            bar.addWidget(w)
        bar.addStretch()
        hl.addLayout(bar)
        self.cv_heat = Canvas()
        hl.addWidget(self.cv_heat, 1)
        note = QLabel("Live-Daten von Rocket League enthalten die Ballposition bei jeder Berührung. "
                      "Eine Heatmap deiner kompletten Laufwege liefert der Tab „Replay-Analyse“.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        hl.addWidget(note)
        self.hm_who.currentIndexChanged.connect(lambda: self._redraw(1))
        self.hm_mode.currentIndexChanged.connect(lambda: self._redraw(1))
        self.hm_norm.toggled.connect(lambda: self._redraw(1))
        self.tabs.addTab(hm, "Heatmaps")

        # 2 Torszenen ----------------------------------------------------------
        ev = QWidget()
        el = QVBoxLayout(ev)
        bar = QHBoxLayout()
        self.ev_checks = {}
        for key, lbl in (("goals", "Tore"), ("shots", "Schüsse"), ("saves", "Paraden"),
                         ("clears", "Klärungen"), ("centers", "Flanken"), ("crossbars", "Latte/Pfosten")):
            cb = QCheckBox(lbl)
            cb.setChecked(key in ("goals", "shots", "saves", "crossbars"))
            cb.toggled.connect(lambda _=None: self._redraw(2))
            self.ev_checks[key] = cb
            bar.addWidget(cb)
        bar.addStretch()
        el.addLayout(bar)
        self.cv_events = Canvas()
        el.addWidget(self.cv_events, 1)
        self.tabs.addTab(ev, "Torszenen")

        # 3 Boost --------------------------------------------------------------
        bo = QWidget()
        bl = QVBoxLayout(bo)
        bar = QHBoxLayout()
        self.bo_who = QComboBox()
        bar.addWidget(QLabel("Spieler:"))
        bar.addWidget(self.bo_who)
        bar.addStretch()
        bl.addLayout(bar)
        self.cv_boost = Canvas()
        bl.addWidget(self.cv_boost, 1)
        self.bo_who.currentIndexChanged.connect(lambda: self._redraw(3))
        self.tabs.addTab(bo, "Boost")

        # 4 Spielverlauf -------------------------------------------------------
        self.cv_timeline = Canvas()
        self.tabs.addTab(self.cv_timeline, "Spielverlauf")

        # 5 Spieler ------------------------------------------------------------
        pl = QWidget()
        pll = QVBoxLayout(pl)
        bar = QHBoxLayout()
        self.pl_who = QComboBox()
        bar.addWidget(QLabel("Spieler:"))
        bar.addWidget(self.pl_who)
        bar.addStretch()
        pll.addLayout(bar)
        split = QSplitter(Qt.Horizontal)
        self.pl_table = make_table(["Wert", ""], sortable=False)
        split.addWidget(self.pl_table)
        self.cv_player = Canvas()
        split.addWidget(self.cv_player)
        split.setSizes([330, 900])
        pll.addWidget(split, 1)
        self.pl_who.currentIndexChanged.connect(lambda: self._redraw(5))
        self.tabs.addTab(pl, "Spieler")

        # 6-9 weitere Diagramme -----------------------------------------------
        self.cv_compare = Canvas()
        self.tabs.addTab(self.cv_compare, "Vergleich")
        self.cv_zones = Canvas()
        self.tabs.addTab(self.cv_zones, "Positionsspiel")
        self.cv_hits = Canvas()
        self.tabs.addTab(self.cv_hits, "Schussstärke")
        self.cv_phys = Canvas()
        self.tabs.addTab(self.cv_phys, "Bewegung")

        # 10 Hoehe & 3D --------------------------------------------------------
        h3 = QWidget()
        h3l = QVBoxLayout(h3)
        bar = QHBoxLayout()
        self.h3_who = QComboBox()
        self.h3_view = QComboBox()
        self.h3_view.addItems(["3D-Ansicht (drehbar)", "Seitenansicht", "Höhenverteilung"])
        self.h3_norm = QCheckBox("Aus Sicht des eigenen Teams")
        for w in (QLabel("Ansicht:"), self.h3_view, QLabel("Spieler:"), self.h3_who, self.h3_norm):
            bar.addWidget(w)
        bar.addStretch()
        h3l.addLayout(bar)
        self.cv_height = Canvas()
        h3l.addWidget(self.cv_height, 1)
        self.h3_hint = QLabel("Tipp: In der 3D-Ansicht mit gedrückter linker Maustaste drehen, mit der rechten zoomen.")
        self.h3_hint.setObjectName("muted")
        h3l.addWidget(self.h3_hint)
        self.h3_who.currentIndexChanged.connect(lambda: self._redraw(10))
        self.h3_view.currentIndexChanged.connect(lambda: self._redraw(10))
        self.h3_norm.toggled.connect(lambda: self._redraw(10))
        self.tabs.addTab(h3, "Höhe & 3D")

        # 10 Ereignisse --------------------------------------------------------
        self.events = make_table(["Zeit", "Ereignis", "Spieler", "Details"])
        self.tabs.addTab(self.events, "Ereignisse")

    # ------------------------------------------------------------------ Daten
    def show_match(self, match: dict) -> None:
        self.match = match
        self.an = A.analyze(match)
        self._fill_header()
        self._fill_selectors()
        self._fill_overview()
        self._fill_events()
        self._dirty = set(range(self.tabs.count()))
        self._render_current()

    def _local_key(self):
        return A.local_player_key(self.match, self.settings.get("player_name", ""))

    def _fill_header(self) -> None:
        m, meta = self.match, self.match["meta"]
        s0, s1 = meta["teams"]["0"]["score"], meta["teams"]["1"]["score"]
        res = A.match_result_for(m, self._local_key())
        text = {"Sieg": "Sieg", "Niederlage": "Niederlage"}.get(res, "Match")
        color = {"Sieg": P.GOOD, "Niederlage": P.BAD}.get(res, P.TEXT)
        self.result.setText(text)
        self.result.setStyleSheet(f"color:{color};")
        winner = meta.get("winner_team")
        if winner is None and meta.get("complete") and s0 != s1:
            winner = 0 if s0 > s1 else 1
        self.bug.set_state(names=[meta["teams"]["0"].get("name"), meta["teams"]["1"].get("name")],
                           scores=[s0, s1], clock=A.fmt_time(meta.get("duration", 0)),
                           overtime=meta.get("overtime"), winner=winner)
        self.bug.names = [("Blau" if self.bug.names[0].lower() == "blue" else self.bug.names[0]),
                          ("Orange" if self.bug.names[1].lower() == "orange" else self.bug.names[1])]
        self.bug.setVisible(True)
        parts = [A.playlist_name(meta.get("playlist_id")), A.arena_name(meta.get("arena", "")),
                 meta.get("started_at", "").replace("T", " "), f"Dauer {A.fmt_time(meta.get('duration', 0))}"]
        if meta.get("overtime"):
            parts.append("mit Verlängerung")
        if not meta.get("complete"):
            parts.append("unvollständig aufgezeichnet")
        if m.get("demo"):
            parts.append("Demo-Daten")
        self.info.setText("   |   ".join(parts))

    def _fill_selectors(self) -> None:
        keys = A.player_order(self.match)
        ps = self.match["players"]
        lk = self._local_key()
        for combo, with_groups in ((self.hm_who, True), (self.bo_who, True), (self.pl_who, False),
                                   (self.h3_who, True)):
            combo.blockSignals(True)
            combo.clear()
            if with_groups:
                combo.addItem("Alle Spieler", None)
                combo.addItem("Team Blau", [k for k in keys if ps[k]["team"] == 0])
                combo.addItem("Team Orange", [k for k in keys if ps[k]["team"] == 1])
            for k in keys:
                label = ps[k]["name"] + (" (du)" if k == lk else "")
                combo.addItem(label, [k] if with_groups else k)
            if lk:
                idx = combo.findText(ps[lk]["name"] + " (du)")
                combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(False)

    def _fill_overview(self) -> None:
        keys = A.player_order(self.match)
        ps = self.an["players"]
        lk = self._local_key()
        rows, colors = [], []
        for k in keys:
            r = ps[k]
            row = [r["name"] + (" ★" if k == lk else "") + (" (verlassen)" if r["left"] else "")]
            for _, f in SCOREBOARD_COLS[1:]:
                v = r.get(f)
                row.append(("", "–") if v is None else v)
            rows.append(row)
            colors.append(P.TEAM[r["team"]])
        fill_table(self.scoreboard, rows, colors)

        t = self.an["teams"]
        trows = [
            ("Tore", "goals", "{:.0f}"), ("Schüsse", "shots", "{:.0f}"), ("Trefferquote", "shooting_pct", "{:.0f} %"),
            ("Paraden", "saves", "{:.0f}"), ("Vorlagen", "assists", "{:.0f}"), ("Ballbesitz (letzter Kontakt)", "possession_pct", "{:.0f} %"),
            ("Ballkontakte", "touches", "{:.0f}"), ("Ø Schussstärke", "avg_hit_speed", "{:.0f} km/h"),
            ("Kontakte im Angriffsdrittel", "touches_in_off_third_pct", "{:.0f} %"),
            ("Kontakte im eigenen Drittel", "touches_in_def_third_pct", "{:.0f} %"),
            ("Demos", "demos", "{:.0f}"), ("Boost gesammelt", "boost_collected", "{:.0f}"), ("Große Pads", "boost_big", "{:.0f}"),
        ]
        fill_table(self.teamtable, [[n, fmt.format(t[0][f]), fmt.format(t[1][f])] for n, f, fmt in trows])

        arows, acolors = [], []
        for k in keys:
            for ev, n in sorted(ps[k]["feed"].items(), key=lambda x: -x[1]):
                arows.append([ps[k]["name"], feed_name(ev), n])
                acolors.append(P.TEAM[ps[k]["team"]])
        fill_table(self.awards, arows, acolors, bold_first=False)

        # Highlights-Kacheln
        while self.highlights.count():
            w = self.highlights.takeAt(0).widget()
            if w:
                w.deleteLater()
        mm = self.an["match"]
        names = self.match["players"]
        best = max(ps.values(), key=lambda r: r["score"], default=None)
        tiles = []
        if best:
            tiles.append(("Bester Spieler", best["name"], f"{best['score']} Punkte", P.TEAM[best["team"]]))
        if mm["hardest_hit"]:
            h = mm["hardest_hit"]
            tiles.append(("Härtester Schuss", f"{A.kmh(h['post']):.0f} km/h",
                          names.get(h["player"], {}).get("name", "?"), P.TEAM[h["team"]]))
        if mm["fastest_goal"]:
            g = mm["fastest_goal"]
            tiles.append(("Schnellstes Tor", f"{A.kmh(g['speed']):.0f} km/h",
                          names.get(g["scorer"], {}).get("name", "?"), P.TEAM[g["team"]]))
        tiles.append(("Ballbesitz Blau", f"{self.an['teams'][0]['possession_pct']:.0f} %",
                      "nach letztem Kontakt", P.TEAM[0]))
        tiles.append(("Ø Ballgeschwindigkeit", f"{mm['avg_ball_speed']:.0f} km/h",
                      f"max. {mm['max_ball_speed']:.0f} km/h", P.TEXT_2))
        tiles.append(("Ballkontakte", str(mm["total_touches"]), f"{mm['crossbars']}× Latte/Pfosten", P.TEXT_2))
        for i, (title, big, sub, col) in enumerate(tiles):
            self.highlights.addWidget(StatTile(title, big, sub, col), 0, i)

    def _fill_events(self) -> None:
        m = self.match
        ps = m["players"]

        def nm(k):
            return ps.get(k, {}).get("name", "") if k else ""

        rows, colors = [], []
        for g in m["goals"]:
            det = f"{A.kmh(g['speed']):.0f} km/h"
            if g.get("assister"):
                det += f", Vorlage {nm(g['assister'])}"
            rows.append([(g["t"], A.fmt_time(g["t"])), "TOR", nm(g["scorer"]), det])
            colors.append(None)
        for e in m.get("feed", []):
            if e["event"] in ("Goal",):
                continue
            rows.append([(e["t"], A.fmt_time(e["t"])), feed_name(e["event"] or e["type"]), nm(e["player"]),
                         f"gegen {nm(e['target'])}" if e.get("target") else ""])
            colors.append(None)
        for c in m.get("crossbars", []):
            rows.append([(c["t"], A.fmt_time(c["t"])), "Latte/Pfosten", nm(c.get("player")),
                         f"{A.kmh(c['speed']):.0f} km/h"])
            colors.append(None)
        for e in m.get("events", []):
            if e["event"] in ("PlayerJoined", "PlayerLeft"):
                rows.append([(e["t"], A.fmt_time(e["t"])), "Beigetreten" if e["event"] == "PlayerJoined" else "Verlassen",
                             e.get("name", ""), ""])
                colors.append(None)
        rows.sort(key=lambda r: r[0][0])
        fill_table(self.events, rows)

    # ------------------------------------------------------------- Zeichnen
    def _redraw(self, idx: int) -> None:
        self._dirty.add(idx)
        if self.tabs.currentIndex() == idx:
            self._render_current()

    def _render_current(self, *_):
        idx = self.tabs.currentIndex()
        if self.match is None or idx not in self._dirty:
            return
        self._dirty.discard(idx)
        m, an = self.match, self.an
        if idx == 1:
            mode = ["heat", "points", "both"][self.hm_mode.currentIndex()]
            self.cv_heat.draw(P.plot_touch_heatmap, m, self.hm_who.currentData(), mode, self.hm_norm.isChecked())
        elif idx == 2:
            self.cv_events.draw(P.plot_event_map, m, {k for k, cb in self.ev_checks.items() if cb.isChecked()})
        elif idx == 3:
            self.cv_boost.draw(P.plot_boost_map, m, self.bo_who.currentData())
        elif idx == 4:
            self.cv_timeline.draw(P.plot_timeline, m)
        elif idx == 5:
            k = self.pl_who.currentData()
            if k:
                r = an["players"][k]
                rows = [[DETAIL_LABELS[f], (r[f], f"{r[f]:.1f}" if isinstance(r[f], float) else str(r[f]))]
                        for f in DETAIL_LABELS if f in r]
                rows += [[f"Statfeed: {feed_name(e)}", n] for e, n in sorted(r["feed"].items())]
                fill_table(self.pl_table, rows)
                self.cv_player.draw(P.plot_player_series, m, k)
        elif idx == 6:
            self.cv_compare.draw(P.plot_compare, m, an)
        elif idx == 7:
            self.cv_zones.draw(P.plot_zones, m, an)
        elif idx == 8:
            self.cv_hits.draw(P.plot_hit_speeds, m)
        elif idx == 9:
            self.cv_phys.draw(P.plot_physics, m, an)
        elif idx == 10:
            view = self.h3_view.currentIndex()
            self.h3_who.setEnabled(view != 2)
            self.h3_norm.setEnabled(view != 2)
            self.h3_hint.setVisible(view == 0)
            if view == 0:
                self.cv_height.draw(P.plot_touch_3d, m, self.h3_who.currentData(), self.h3_norm.isChecked())
            elif view == 1:
                self.cv_height.draw(P.plot_side_view, m, self.h3_who.currentData(), self.h3_norm.isChecked())
            else:
                self.cv_height.draw(P.plot_height_breakdown, m, an)

    def _current_canvas(self):
        w = self.tabs.currentWidget()
        if isinstance(w, Canvas):
            return w
        cs = w.findChildren(Canvas)
        return cs[0] if cs else None

    def _export_png(self):
        c = self._current_canvas()
        if c and self.match:
            c.export_png(self, f"rl_{self.tabs.tabText(self.tabs.currentIndex())}.png")

    def _export_csv(self):
        if not self.match:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Statistik als CSV speichern", "rl_match.csv", "CSV (*.csv)")
        if not path:
            return
        keys = A.player_order(self.match)
        fields = ["name", "team"] + [f for f in DETAIL_LABELS]
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Spieler", "Team"] + [DETAIL_LABELS[f] for f in fields[2:]])
            for k in keys:
                r = self.an["players"][k]
                w.writerow([r["name"], "Blau" if r["team"] == 0 else "Orange"] +
                           [str(round(r[f], 2)).replace(".", ",") if isinstance(r.get(f), float) else r.get(f, "")
                            for f in fields[2:]])
