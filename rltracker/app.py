"""Hauptfenster: Live-Ansicht, Auswertung, Verlauf, Replay-Analyse, Einrichtung."""
from __future__ import annotations

import os
import queue
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QColor, QDesktopServices  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,  # noqa: E402
                               QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QSplitter, QTabWidget, QVBoxLayout, QWidget)

from . import analysis as A  # noqa: E402
from . import ini_setup, plots as P, replay as R, simulator, storage, updates  # noqa: E402
from .match_view import MatchView, feed_name  # noqa: E402
from .recorder import MatchRecorder  # noqa: E402
from .statsapi import StatsApiClient  # noqa: E402
from .widgets import STYLE, Canvas, ScoreBug, app_icon, display_font, fill_table, make_table  # noqa: E402

from . import APP_NAME, EPIC_DISCLAIMER, PUBLISHER, __version__  # noqa: E402


class AboutDialog(QDialog):
    """Über die App: Version, Hinweis 'inoffiziell', Datenschutz, Lizenzen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Über {APP_NAME}")
        self.setMinimumWidth(560)
        self.setStyleSheet(f"QDialog {{ background: {P.SURFACE_2}; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(12)
        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(48, 48))
        title = QLabel(f"{APP_NAME}")
        title.setFont(display_font(20, True, True))
        ver = QLabel(f"Version {__version__}")
        ver.setObjectName("muted")
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(title)
        col.addWidget(ver)
        head.addWidget(icon)
        head.addSpacing(8)
        head.addLayout(col)
        head.addStretch()
        lay.addLayout(head)
        body = QLabel(
            "Live-Statistiken, Heatmaps und Match-Analyse für Rocket League.<br><br>"
            "<b>Inoffizielle Fan-App.</b> RL Tracker ist ein unabhängiges, kostenloses Fan-Projekt und steht in "
            "keiner Verbindung zu Psyonix, Epic Games, Valve oder Steam. Die Daten kommen aus der offiziellen, "
            "lokalen Stats-Schnittstelle des Spiels; es werden keine Spieldateien verändert und keine Mods "
            "installiert.<br><br>"
            "<b>Datenschutz.</b> Alles bleibt auf deinem PC: Matches und Einstellungen liegen in "
            f"<code>{storage.data_dir()}</code>. Die App sendet keine Spiel- oder Nutzerdaten ins Internet. "
            "Nur die Update-Prüfung fragt beim Start bei GitHub nach einer neuen Version (dabei wird wie bei "
            "jedem Webseitenaufruf deine IP-Adresse übertragen); abschaltbar unter Einrichtung.<br><br>"
            f"<span style='color:{P.MUTED}'>{EPIC_DISCLAIMER}</span><br><br>"
            f"<span style='color:{P.MUTED}'>Verwendet Qt for Python (PySide6, LGPLv3), matplotlib, NumPy und "
            "subtr-actor (MIT). Lizenztexte liegen im Installationsordner unter <code>licenses</code>.</span><br>"
            f"<span style='color:{P.MUTED}'>© {PUBLISHER}</span>")
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body)
        row = QHBoxLayout()
        row.addStretch()
        ok = QPushButton("Schließen")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)


class UpdateDialog(QDialog):
    """Erscheint beim Start, wenn es eine neue Version gibt."""

    def __init__(self, rel: dict, parent=None):
        super().__init__(parent)
        self.mandatory = updates.is_mandatory(rel.get("notes", ""))
        self.setWindowTitle("Neue Version verfügbar")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"QDialog {{ background: {P.SURFACE_2}; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(10)
        t = QLabel(f"Version {rel['version']} ist da")
        t.setFont(display_font(19, True, True))
        lay.addWidget(t)
        size = f", {rel['size'] / 1e6:.0f} MB" if rel.get("size") else ""
        sub = QLabel(f"Du hast Version {__version__}{size}. Deine Matches und Einstellungen bleiben erhalten.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        if self.mandatory:
            warn = QLabel("Dieses Update ist wichtig und muss installiert werden, damit RL Tracker weiter funktioniert.")
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color:{P.ACCENT}; font-weight:600;")
            lay.addWidget(warn)
        head = QLabel("Was ist neu")
        head.setObjectName("h2")
        lay.addWidget(head)
        notes = QLabel(updates.notes_html(rel.get("notes", "")))
        notes.setTextFormat(Qt.RichText)
        notes.setWordWrap(True)
        notes.setStyleSheet(f"color:{P.TEXT_2};")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(260)
        scroll.setWidget(notes)
        lay.addWidget(scroll)
        row = QHBoxLayout()
        row.addStretch()
        if not self.mandatory:
            later = QPushButton("Später")
            later.clicked.connect(self.reject)
            row.addWidget(later)
        go = QPushButton("Jetzt aktualisieren")
        go.setObjectName("primary")
        go.setDefault(True)
        go.clicked.connect(self.accept)
        row.addWidget(go)
        lay.addLayout(row)


class AccessDialog(QDialog):
    """Einmalige Zustimmung, bevor die App Einstellungen von Rocket League ändert."""

    def __init__(self, installs: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zugriff auf Rocket League")
        self.setMinimumWidth(560)
        self.setStyleSheet(f"QDialog {{ background: {P.SURFACE_2}; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(12)
        t = QLabel("RL Tracker braucht deine Erlaubnis")
        t.setFont(display_font(17, True, False))
        lay.addWidget(t)
        where = "<br>".join(f"&nbsp;&nbsp;{d}" for d in installs) or "&nbsp;&nbsp;(noch keine Installation gefunden)"
        txt = QLabel(
            "Damit die App deine Matches aufzeichnen kann, schaltet sie die offizielle Stats-Schnittstelle von "
            "Rocket League ein. Dafür wird in diesen Ordnern die Datei <code>TAGame\\Config\\DefaultStatsAPI.ini</code> "
            f"angepasst (vorher wird eine Sicherung angelegt):<br><br>{where}<br><br>"
            "Es werden keine Spieldateien verändert und keine Daten verschickt. Du kannst das jederzeit unter "
            "Einrichtung ändern; beim Deinstallieren wird es automatisch zurückgenommen.<br><br>"
            "Danach Rocket League einmal neu starten.")
        txt.setWordWrap(True)
        txt.setTextFormat(Qt.RichText)
        lay.addWidget(txt)
        row = QHBoxLayout()
        row.addStretch()
        later = QPushButton("Nicht jetzt")
        later.clicked.connect(self.reject)
        allow = QPushButton("Zugriff erlauben")
        allow.setObjectName("primary")
        allow.clicked.connect(self.accept)
        allow.setDefault(True)
        row.addWidget(later)
        row.addWidget(allow)
        lay.addLayout(row)


# ============================================================================ Live
class LiveView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(14)

        self.bug = ScoreBug()
        self.bug.set_state(sub="Warte auf ein Match – starte Rocket League und geh ins Freeplay oder in ein Match")
        lay.addWidget(self.bug)

        split = QSplitter(Qt.Vertical)
        split.setHandleWidth(10)
        top = QSplitter(Qt.Horizontal)
        top.setHandleWidth(10)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        t = QLabel("Spieler")
        t.setObjectName("h2")
        ll.addWidget(t)
        self.table = make_table(["Spieler", "Punkte", "Tore", "Vorlagen", "Paraden", "Schüsse", "Kontakte",
                                 "Demos", "Boost", "km/h", "Gerade"], sortable=False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        ll.addWidget(self.table)
        top.addWidget(left)
        feedbox = QWidget()
        fl = QVBoxLayout(feedbox)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)
        t = QLabel("Ticker")
        t.setObjectName("h2")
        fl.addWidget(t)
        self.feed = QListWidget()
        self.feed.setFont(display_font(10.5, False))
        fl.addWidget(self.feed)
        top.addWidget(feedbox)
        top.setSizes([900, 380])
        split.addWidget(top)
        self.field = Canvas(height=4.5)
        split.addWidget(self.field)
        split.setSizes([300, 440])
        lay.addWidget(split, 1)

    def clock_text(self) -> str:
        return ("+" if self.bug.overtime else "") + self.bug.clock

    def add_feed(self, text: str, color: str | None = None) -> None:
        it = QListWidgetItem(text)
        if color:
            it.setForeground(QColor(color))
        self.feed.insertItem(0, it)
        while self.feed.count() > 200:
            self.feed.takeItem(self.feed.count() - 1)

    def update_state(self, state: dict, recorder: MatchRecorder) -> None:
        game = state.get("Game") or {}
        teams = {t.get("TeamNum"): t for t in game.get("Teams") or []}
        names = [_team_name(teams.get(0, {}).get("Name"), 0), _team_name(teams.get(1, {}).get("Name"), 1)]
        secs = game.get("TimeSeconds")
        sub = [A.playlist_name(game.get("PlaylistId")), A.arena_name(game.get("Arena", ""))]
        if game.get("bReplay"):
            sub.append("Wiederholung")
        winner = None
        if game.get("bHasWinner"):
            sub.append(f"Sieger: {game.get('Winner', '')}")
            w = str(game.get("Winner", "")).lower()
            winner = 0 if w == str(teams.get(0, {}).get("Name", "blue")).lower() else (
                1 if w == str(teams.get(1, {}).get("Name", "orange")).lower() else None)
        self.bug.set_state(names=names, scores=[teams.get(0, {}).get("Score", 0), teams.get(1, {}).get("Score", 0)],
                           clock=A.fmt_time(secs) if secs is not None else None,
                           overtime=game.get("bOvertime"), sub="   |   ".join(x for x in sub if x), winner=winner)

        players = sorted(state.get("Players") or [], key=lambda p: (p.get("TeamNum", 0), -p.get("Score", 0)))
        rows, colors = [], []
        for p in players:
            status = []
            if p.get("bDemolished"):
                status.append("zerstört")
            if p.get("bSupersonic"):
                status.append("Überschall")
            if p.get("bOnWall"):
                status.append("Wand")
            elif p.get("bOnGround") is False:
                status.append("Luft")
            rows.append([p.get("Name", "?"), p.get("Score", 0), p.get("Goals", 0), p.get("Assists", 0),
                         p.get("Saves", 0), p.get("Shots", 0), p.get("Touches", 0), p.get("Demos", 0),
                         p["Boost"] if "Boost" in p else ("", "–"),
                         round(A.kmh(p["Speed"])) if "Speed" in p else ("", "–"), ", ".join(status)])
            colors.append(P.TEAM.get(p.get("TeamNum", 0), P.TEXT))
        fill_table(self.table, rows, colors)

    def reset(self) -> None:
        self.feed.clear()
        self.bug.set_state(scores=[0, 0], clock="5:00", overtime=False, sub="", winner=None)


def _team_name(name, team: int) -> str:
    """Spiel sendet 'Blue'/'Orange' – auf Deutsch anzeigen, eigene Teamnamen behalten."""
    if not name or str(name).lower() in ("blue", "blau"):
        return "Blau" if team == 0 else (name or "Orange")
    if str(name).lower() == "orange":
        return "Orange"
    return str(name)


# ========================================================================= Verlauf
class HistoryView(QWidget):
    def __init__(self, settings: dict, open_cb, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.open_cb = open_cb
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 14)
        head = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setObjectName("h2")
        head.addWidget(self.summary, 1)
        self.only_real = QCheckBox("Demo-Matches ausblenden")
        self.only_real.setChecked(True)
        self.only_real.toggled.connect(self.refresh)
        head.addWidget(self.only_real)
        b_open = QPushButton("Öffnen")
        b_open.setObjectName("primary")
        b_del = QPushButton("Löschen")
        b_dir = QPushButton("Ordner öffnen")
        b_open.clicked.connect(self._open_selected)
        b_del.clicked.connect(self._delete_selected)
        b_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(storage.data_dir()))))
        for b in (b_open, b_del, b_dir):
            head.addWidget(b)
        lay.addLayout(head)
        split = QSplitter(Qt.Vertical)
        self.table = make_table(["Datum", "Modus", "Arena", "Ergebnis", "Spielstand", "Dein Team", "Dauer", "Spieler"])
        self.table.doubleClicked.connect(self._open_selected)
        split.addWidget(self.table)
        self.career = Canvas(height=4)
        split.addWidget(self.career)
        split.setSizes([380, 380])
        lay.addWidget(split, 1)
        self._items: list[dict] = []

    def refresh(self) -> None:
        items = storage.list_matches()
        if self.only_real.isChecked():
            items = [s for s in items if not s.get("demo")]
        name = self.settings.get("player_name", "").strip()
        rows, colors = [], []
        for s in items:
            team = s.get("local_team")
            if name:  # eingestellter Name hat Vorrang
                lk = s.get("local_player") or ""
                if lk.split(":", 1)[-1].lower() != name.lower():
                    team = None
            res = "–"
            if team is not None and s.get("winner_team") is not None:
                res = "Sieg" if s["winner_team"] == team else "Niederlage"
            rows.append([s["started_at"].replace("T", " "), A.playlist_name(s.get("playlist_id")),
                         A.arena_name(s.get("arena", "")), res, f"{s['score'][0]} : {s['score'][1]}",
                         {0: "Blau", 1: "Orange"}.get(team, "–"), (s.get("duration", 0), A.fmt_time(s.get("duration", 0))),
                         ", ".join(s.get("players", []))])
            colors.append(P.GOOD if res == "Sieg" else (P.BAD if res == "Niederlage" else None))
        self._items = items
        self.table.setSortingEnabled(False)
        fill_table(self.table, rows, colors, bold_first=False)
        for r, s in enumerate(items):
            self.table.item(r, 0).setData(Qt.UserRole, s["file"])
        self.table.setSortingEnabled(True)

        # Karriere fuer den eingestellten Namen (bzw. erkannten lokalen Spieler)
        who = name or next((s.get("local_name") for s in items if s.get("local_name")), "")
        if who:
            matches = []
            for s in reversed(items[:200]):
                try:
                    matches.append(storage.load_match(s["file"]))
                except Exception:
                    pass
            car = A.career_summary(matches, who)
            self.summary.setText(
                f"{who}: {car['matches']} Matches · {car['wins']} Siege ({car['winrate']:.0f} %) · "
                f"Ø {car.get('goals_avg', 0):.1f} Tore · Ø {car.get('saves_avg', 0):.1f} Paraden · "
                f"Ø {car.get('score_avg', 0):.0f} Punkte")
            self.career.draw(P.plot_career, car)
        else:
            self.summary.setText(f"{len(items)} gespeicherte Matches")
            self.career.draw(P.plot_career, {"per_match": []})

    def _selected_file(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, 0)
        return it.data(Qt.UserRole) if it else None

    def _open_selected(self, *_):
        f = self._selected_file()
        if f:
            self.open_cb(storage.load_match(f))

    def _delete_selected(self):
        f = self._selected_file()
        if f and QMessageBox.question(self, APP_NAME, "Dieses Match wirklich löschen?") == QMessageBox.Yes:
            storage.delete_match(f)
            self.refresh()


# ==================================================================== Replay-Analyse
class ReplayView(QWidget):
    def __init__(self, pool: ThreadPoolExecutor, status_cb, parent=None):
        super().__init__(parent)
        self.pool = pool
        self.status_cb = status_cb
        self.rep: dict | None = None
        self._future = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 14)
        ok, err = R.available()
        head = QHBoxLayout()
        self.title = QLabel("Replay-Analyse")
        self.title.setObjectName("h2")
        head.addWidget(self.title, 1)
        self.b_latest = QPushButton("Neuestes Replay analysieren")
        self.b_latest.setObjectName("primary")
        self.b_open = QPushButton("Replay-Datei öffnen …")
        self.b_latest.clicked.connect(self.analyze_latest)
        self.b_open.clicked.connect(self._choose)
        head.addWidget(self.b_latest)
        head.addWidget(self.b_open)
        lay.addLayout(head)
        if not ok:
            py = f"{sys.version_info.major}.{sys.version_info.minor}"
            need = "" if sys.version_info[:2] == (3, 12) else (
                f"<br>Die App läuft gerade mit Python {py}, die Bibliothek gibt es für Windows aber nur für "
                "<b>Python 3.12</b>. Der Knopf stellt die App automatisch um (deine Matches bleiben erhalten). "
                "Falls Python 3.12 fehlt, öffnet sich die Download-Seite.")
            msg = QLabel(
                "<b>Die Replay-Analyse ist noch nicht eingerichtet.</b><br><br>"
                "Für Heatmaps deiner kompletten Laufwege (nicht nur Ballkontakte) braucht die App die "
                "Bibliothek <code>subtr-actor-py</code>." + need +
                "<br><br>Klick auf den Knopf – die App schließt sich kurz, installiert alles in einem "
                "Fenster und startet danach neu."
                f"<br><br><span style='color:{P.MUTED}'>Technisch: {err}</span>")
            msg.setWordWrap(True)
            msg.setTextFormat(Qt.RichText)
            lay.addWidget(msg)
            b_inst = QPushButton("Replay-Analyse einrichten")
            b_inst.setObjectName("primary")
            b_inst.clicked.connect(self._install)
            row = QHBoxLayout()
            row.addWidget(b_inst)
            row.addStretch()
            lay.addLayout(row)
            lay.addStretch()
            self.b_latest.setVisible(False)
            self.b_open.setVisible(False)
            self.enabled = False
            return
        self.enabled = True
        self.hint = QLabel("Nach dem Match in Rocket League „Replay speichern“ klicken – die App findet "
                           "neue Replays automatisch (Ordner: " + ", ".join(str(d) for d in R.demo_dirs()) + ").")
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        hm = QWidget()
        hl = QVBoxLayout(hm)
        bar = QHBoxLayout()
        self.who = QComboBox()
        self.norm = QCheckBox("Aus Sicht des eigenen Teams")
        self.norm.setChecked(True)
        bar.addWidget(QLabel("Heatmap von:"))
        bar.addWidget(self.who)
        bar.addWidget(self.norm)
        bar.addStretch()
        hl.addLayout(bar)
        self.cv_heat = Canvas()
        hl.addWidget(self.cv_heat, 1)
        self.who.currentIndexChanged.connect(self._draw_heat)
        self.norm.toggled.connect(self._draw_heat)
        self.tabs.addTab(hm, "Positions-Heatmap")
        hz = QWidget()
        hzl = QVBoxLayout(hz)
        hzl.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Seitenansicht für die oben bei „Heatmap von“ gewählte Person bzw. den Ball.")
        hint.setObjectName("muted")
        hzl.addWidget(hint)
        hsplit = QSplitter(Qt.Vertical)
        self.cv_side = Canvas(height=4)
        self.cv_heights = Canvas(height=3.5)
        hsplit.addWidget(self.cv_side)
        hsplit.addWidget(self.cv_heights)
        hzl.addWidget(hsplit, 1)
        self.tabs.addTab(hz, "Höhe")
        self.cv_cmp = Canvas()
        self.tabs.addTab(self.cv_cmp, "Vergleich")
        self.table = make_table(["Spieler", "Ø Tempo", "Max. Tempo", "Überschall %", "Boden %", "Wand %", "Luft %",
                                 "Ø Höhe m", "Max. Höhe m",
                                 "Ø Boost", "0 Boost %", "100 Boost %", "Strecke km", "Def. Drittel %", "Mitte %",
                                 "Off. Drittel %", "Hinter Ball %", "Am nächsten am Ball %", "Ø Abstand Ball m"])
        self.tabs.addTab(self.table, "Tabelle")
        self.raw = make_table(["Statistik", "Wert"])
        self.tabs.addTab(self.raw, "Alle Rohwerte")
        self.tabs.currentChanged.connect(lambda _: self._draw_tab())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(200)

    def _install(self):
        if getattr(sys, "frozen", False):
            QMessageBox.information(self, APP_NAME, "In dieser .exe ist die Replay-Analyse nicht enthalten.\n\n"
                                    "Im App-Ordner (mit start.bat) zuerst replay_setup.bat ausführen und danach "
                                    "build_exe.bat erneut starten – die neue .exe enthält sie dann.")
            return
        bat = Path(__file__).resolve().parent.parent / "replay_setup.bat"
        if not bat.exists() or sys.platform != "win32":
            QMessageBox.warning(self, APP_NAME, f"replay_setup.bat nicht gefunden:\n{bat}")
            return
        if QMessageBox.question(self, APP_NAME, "Die App schließt sich jetzt, richtet die Replay-Analyse ein "
                                                "und startet danach neu. Weiter?") != QMessageBox.Yes:
            return
        os.startfile(str(bat))  # eigenes Konsolenfenster
        QApplication.quit()

    def _choose(self):
        start = str(R.demo_dirs()[0]) if R.demo_dirs() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Replay öffnen", start, "Rocket League Replay (*.replay)")
        if path:
            self.analyze(path)

    def analyze_latest(self):
        reps = R.list_replays()
        if not reps:
            QMessageBox.information(self, APP_NAME, "Kein Replay gefunden. Speichere nach einem Match das Replay "
                                                    "in Rocket League oder öffne eine Datei manuell.")
            return
        self.analyze(reps[0])

    def analyze(self, path) -> None:
        if not self.enabled or (self._future and not self._future.done()):
            return
        self.title.setText(f"Analysiere {Path(path).name} …")
        self.status_cb(f"Replay wird analysiert: {Path(path).name}")
        self._future = self.pool.submit(R.analyze_replay, path)

    def _poll(self):
        f = self._future
        if not f or not f.done():
            return
        self._future = None
        try:
            self.show_replay(f.result())
        except Exception as e:
            traceback.print_exc()
            self.title.setText("Replay-Analyse fehlgeschlagen")
            QMessageBox.warning(self, APP_NAME, f"Das Replay konnte nicht gelesen werden:\n{e}")

    def show_replay(self, rep: dict):
        self.rep = rep
        self.title.setText(f"Replay: {rep['name']}  ·  {A.arena_name(str(rep.get('map') or ''))}  ·  "
                           f"{A.fmt_time(rep['duration'])}  ·  Ball {rep['ball_blue_half_pct']:.0f} % in Blaus Hälfte")
        self.status_cb(f"Replay analysiert ({rep['parse_seconds']:.1f} s)")
        self.who.blockSignals(True)
        self.who.clear()
        for i, p in enumerate(rep["players"]):
            self.who.addItem(f"{p['name']} ({'Blau' if p['team'] == 0 else 'Orange'})", i)
        self.who.addItem("Ball", "ball")
        self.who.blockSignals(False)
        rows, colors = [], []
        for p in rep["players"]:
            s = p["summary"]
            rows.append([p["name"]] + [s.get(k, 0.0) for k in (
                "avg_speed", "max_speed", "supersonic_pct", "ground_pct", "wall_pct", "air_pct",
                "avg_height", "max_height", "avg_boost",
                "zero_boost_pct", "full_boost_pct", "distance_km", "def_pct", "mid_pct", "off_pct",
                "behind_ball_pct", "closest_to_ball_pct", "avg_dist_ball")])
            colors.append(P.TEAM[p["team"]])
        fill_table(self.table, rows, colors)
        fill_table(self.raw, [list(x) for x in R.flatten(rep.get("extra") or {})][:5000])
        self._draw_heat()
        self._draw_tab()

    def _draw_heat(self, *_):
        if not self.rep:
            return
        d = self.who.currentData()
        if d == "ball":
            self.cv_heat.draw(P.plot_replay_heatmap, self.rep, None, True, "ball")
        elif d is not None:
            self.cv_heat.draw(P.plot_replay_heatmap, self.rep, d, self.norm.isChecked())
        if self.tabs.currentIndex() == 1:
            self._draw_tab()

    def _draw_tab(self):
        if not self.rep:
            return
        i = self.tabs.currentIndex()
        if i == 1:
            d = self.who.currentData()
            self.cv_side.draw(P.plot_replay_side, self.rep, "ball" if d == "ball" else d, self.norm.isChecked())
            self.cv_heights.draw(P.plot_replay_heights, self.rep)
        elif i == 2:
            self.cv_cmp.draw(P.plot_replay_compare, self.rep)


# ======================================================================= Einrichtung
class SetupView(QWidget):
    def __init__(self, win: "MainWindow", parent=None):
        super().__init__(parent)
        self.win = win
        s = win.settings
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(16, 16, 16, 16)

        g0 = QGroupBox("Verbindung prüfen")
        f0 = QVBoxLayout(g0)
        row = QHBoxLayout()
        self.b_diag = QPushButton("Verbindung prüfen")
        self.b_diag.setObjectName("primary")
        self.b_diag.clicked.connect(self.run_diagnose)
        self.b_fix = QPushButton("Automatisch reparieren")
        self.b_fix.clicked.connect(self.apply_fix)
        self.b_fix.setVisible(False)
        self.b_port = QPushButton("")
        self.b_port.clicked.connect(self.apply_port)
        self.b_port.setVisible(False)
        row.addWidget(self.b_diag)
        row.addWidget(self.b_fix)
        row.addWidget(self.b_port)
        row.addStretch()
        f0.addLayout(row)
        self.diag = QLabel("Klicke auf „Verbindung prüfen“, während Rocket League läuft.")
        self.diag.setObjectName("muted")
        self.diag.setWordWrap(True)
        self.diag.setTextFormat(Qt.RichText)
        self.diag.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f0.addWidget(self.diag)
        lay.addWidget(g0)
        self._diag_future = None
        self._diag_result = None
        self._diag_timer = QTimer(self)
        self._diag_timer.timeout.connect(self._diag_poll)

        g1 = QGroupBox("1 · Rocket League vorbereiten (einmalig)")
        f1 = QVBoxLayout(g1)
        txt = QLabel("Rocket League hat eine offizielle Stats-Schnittstelle, die standardmäßig aus ist. "
                     "Die App trägt dafür <code>PacketSendRate</code> in die Datei "
                     "<code>TAGame\\Config\\TAStatsAPI.ini</code> bzw. <code>DefaultStatsAPI.ini</code> "
                     "in deinem Rocket-League-Ordner ein. <b>Danach Rocket League neu starten.</b>")
        txt.setWordWrap(True)
        txt.setTextFormat(Qt.RichText)
        f1.addWidget(txt)
        row = QHBoxLayout()
        self.ini_path = QLineEdit(s.get("ini_path", ""))
        self.ini_path.setPlaceholderText("Pfad zur INI-Datei")
        b_find = QPushButton("Automatisch suchen")
        b_pick = QPushButton("Rocket-League-Ordner wählen …")
        b_find.clicked.connect(self.find_ini)
        b_pick.clicked.connect(self.pick_dir)
        row.addWidget(self.ini_path, 1)
        row.addWidget(b_find)
        row.addWidget(b_pick)
        f1.addLayout(row)
        row = QHBoxLayout()
        self.rate = QSpinBox()
        self.rate.setRange(1, 120)
        self.rate.setValue(30)
        self.rate.setSuffix(" Updates/s")
        b_enable = QPushButton("Stats API aktivieren")
        b_enable.setObjectName("primary")
        b_enable.clicked.connect(self.enable_api)
        self.ini_status = QLabel("")
        self.ini_status.setWordWrap(True)
        row.addWidget(QLabel("Datenrate:"))
        row.addWidget(self.rate)
        row.addWidget(b_enable)
        row.addWidget(self.ini_status, 1)
        f1.addLayout(row)
        lay.addWidget(g1)

        g2 = QGroupBox("2 · Einstellungen")
        f2 = QFormLayout(g2)
        self.name = QLineEdit(s.get("player_name", ""))
        self.name.setPlaceholderText("Dein Spielername (für Sieg/Niederlage und Karriere-Statistik)")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(s.get("port", 49123)))
        self.auto_show = QCheckBox("Nach dem Match automatisch die Auswertung öffnen")
        self.auto_show.setChecked(s.get("auto_show_results", True))
        self.auto_rep = QCheckBox("Neue Replays automatisch analysieren (nach „Replay speichern“)")
        self.auto_rep.setChecked(s.get("auto_replay", True))
        self.upd = QCheckBox("Beim Start nach neuen Versionen suchen (fragt bei GitHub nach)")
        self.upd.setChecked(s.get("update_check", True))
        f2.addRow("Spielername:", self.name)
        f2.addRow("Port:", self.port)
        f2.addRow("", self.auto_show)
        f2.addRow("", self.auto_rep)
        f2.addRow("", self.upd)
        b_save = QPushButton("Speichern")
        b_save.setObjectName("primary")
        b_save.clicked.connect(self.save)
        f2.addRow("", b_save)
        lay.addWidget(g2)

        g3 = QGroupBox("3 · Demo-Modus (ohne Rocket League testen)")
        f3 = QHBoxLayout(g3)
        d = QLabel("Simuliert ein 3-gegen-3 im Zeitraffer und sendet es wie das echte Spiel.")
        d.setWordWrap(True)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(1, 30)
        self.speed.setValue(float(s.get("demo_speed", 6)))
        self.speed.setPrefix("Tempo ×")
        self.b_demo = QPushButton("Demo starten")
        self.b_demo.clicked.connect(win.toggle_demo)
        f3.addWidget(d, 1)
        f3.addWidget(self.speed)
        f3.addWidget(self.b_demo)
        lay.addWidget(g3)

        g4 = QGroupBox("Hinweise")
        f4 = QVBoxLayout(g4)
        h = QLabel(
            "• Die App muss nur laufen – sie verbindet sich automatisch, sobald ein Match startet.<br>"
            "• Rocket League sendet Tempo/Boost/Luft-Werte nur für Spieler deines Teams und im Zuschauer-Modus. "
            "Ballkontakte, Tore, Schüsse, Paraden, Demos und Punkte gibt es für alle.<br>"
            "• Für die vollständige Bewegungs-Heatmap aller Spieler: Replay nach dem Match speichern "
            "(Tab „Replay-Analyse“).<br>"
            f"• Deine Matches werden gespeichert in: <code>{storage.data_dir()}</code>")
        h.setWordWrap(True)
        h.setTextFormat(Qt.RichText)
        f4.addWidget(h)
        lay.addWidget(g4)
        lay.addStretch()
        if not self.ini_path.text():
            self.find_ini(silent=True)
        else:
            self._show_ini_status()

    def find_ini(self, silent=False):
        p = ini_setup.find_ini()
        if p:
            self.ini_path.setText(str(p))
            self._show_ini_status()
        elif not silent:
            QMessageBox.information(self, APP_NAME, "Rocket League wurde nicht automatisch gefunden. Wähle den "
                                                    "Installationsordner (z.B. C:\\Program Files\\Epic Games\\rocketleague) manuell.")
        else:
            self.ini_status.setText("Rocket League nicht automatisch gefunden – Ordner bitte manuell wählen.")

    def pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Rocket-League-Installationsordner wählen")
        if d:
            if not (Path(d) / "TAGame" / "Config").is_dir():
                QMessageBox.warning(self, APP_NAME, "In diesem Ordner gibt es kein TAGame\\Config. Bitte den "
                                                    "Hauptordner von Rocket League wählen (enthält Binaries und TAGame).")
                return
            self.ini_path.setText(str(ini_setup.ini_for_install(Path(d))))
            self._show_ini_status()

    def _show_ini_status(self):
        p = self.ini_path.text().strip()
        if not p:
            return
        st = ini_setup.read_settings(Path(p))
        if st["PacketSendRate"] > 0:
            self.ini_status.setText(f"<span style='color:{P.GOOD}'>✔ Aktiv</span> – {st['PacketSendRate']:g} "
                                    f"Updates/s auf Port {st['Port']}")
        elif st["exists"]:
            self.ini_status.setText("✖ Noch deaktiviert – auf „Stats API aktivieren“ klicken.")
        else:
            self.ini_status.setText("Datei existiert noch nicht – wird beim Aktivieren angelegt.")

    def enable_api(self):
        p = self.ini_path.text().strip()
        if not p:
            self.find_ini()
            p = self.ini_path.text().strip()
            if not p:
                return
        if self._write_ini(Path(p).parent.parent.parent):
            self.save()
            QMessageBox.information(self, APP_NAME, "Stats API aktiviert!\n\nJetzt Rocket League KOMPLETT beenden "
                                                    "und neu starten, dann ein Match oder Freeplay starten.")

    def _write_ini(self, install_dir: Path) -> bool:
        """Schreibt die Einstellung; fragt bei fehlenden Rechten nach Adminrechten."""
        try:
            paths = ini_setup.enable_install(install_dir, self.rate.value(), self.port.value())
        except PermissionError:
            ok = QMessageBox.question(
                self, APP_NAME, "Der Rocket-League-Ordner ist geschützt (Program Files).\n\n"
                                "Soll die App die Einstellung mit Administratorrechten schreiben? "
                                "Windows fragt dann kurz nach.") == QMessageBox.Yes
            if not ok or not ini_setup.elevate_enable(install_dir, self.rate.value(), self.port.value()):
                QMessageBox.warning(self, APP_NAME, "Nicht geschrieben. Alternative: RL Tracker per Rechtsklick → "
                                                    "„Als Administrator ausführen“ starten und erneut klicken.")
                return False
            time.sleep(2.5)  # Adminprozess arbeiten lassen
            paths = [str(install_dir / "TAGame" / "Config" / n) for n in ini_setup.INI_NAMES]
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Konnte die Datei nicht schreiben:\n{e}")
            return False
        active = [q for q in paths if ini_setup.read_settings(Path(q))["PacketSendRate"] > 0]
        if not active:
            QMessageBox.warning(self, APP_NAME, "Die Einstellung ist nicht in der Datei angekommen. "
                                                "Bitte „Verbindung prüfen“ klicken und mir das Ergebnis schicken.")
            return False
        self.ini_path.setText(active[0])
        self._show_ini_status()
        return True

    # ------------------------------------------------------------ Diagnose
    def run_diagnose(self):
        if self._diag_future and not self._diag_future.done():
            return
        from . import diagnose
        self.diag.setText("Prüfe …")
        self.b_fix.setVisible(False)
        self.b_port.setVisible(False)
        errs = dict(self.win.client.last_errors) if self.win.client else {}
        self._diag_future = self.win.pool.submit(diagnose.run, dict(self.win.settings), errs)
        self._diag_timer.start(200)

    def _diag_poll(self):
        f = self._diag_future
        if not f or not f.done():
            return
        self._diag_timer.stop()
        try:
            res = f.result()
        except Exception as e:
            self.diag.setText(f"Diagnose fehlgeschlagen: {e}")
            return
        self._diag_result = res
        icons = {"ok": (P.GOOD, "✔"), "bad": (P.BAD, "✖"), "warn": (P.ACCENT, "!"), "info": (P.MUTED, "·")}
        html = []
        for level, text in res["lines"]:
            col, ic = icons.get(level, (P.MUTED, "·"))
            html.append(f"<span style='color:{col};font-weight:700'>{ic}</span> "
                        f"<span style='color:{P.TEXT if level != 'info' else P.MUTED}'>{text}</span>")
        self.diag.setText("<br>".join(html))
        if self.win.client and self.win.client.connected:
            self.diag.setText(f"<span style='color:{P.GOOD};font-weight:700'>✔ Verbunden – alles in Ordnung.</span><br>"
                              + "<br>".join(html))
        dirs = res.get("fix_dirs") or ([res["fix_dir"]] if res.get("fix_dir") else [])
        if dirs:
            labels = ["Steam" if "steamapps" in str(d).lower() else ("Epic" if "epic" in str(d).lower() else Path(d).name)
                      for d in dirs]
            self.b_fix.setText(f"Automatisch reparieren ({', '.join(labels)})")
            self.b_fix.setToolTip("\n".join(str(d) for d in dirs))
            self.b_fix.setVisible(True)
        port = res.get("port")
        if port and port != int(self.win.settings.get("port", 49123)):
            self.b_port.setText(f"Port {port} übernehmen")
            self.b_port.setVisible(True)

    def apply_fix(self):
        res = self._diag_result or {}
        dirs = res.get("fix_dirs") or ([res["fix_dir"]] if res.get("fix_dir") else [])
        if not dirs:
            return
        if all([self._write_ini(Path(d)) for d in dirs]):
            msg = "Repariert."
            if res.get("rl_running"):
                msg += ("\n\nRocket League läuft noch mit der alten Einstellung: Spiel jetzt komplett beenden "
                        "und neu starten, dann ein Freeplay oder Match starten.")
            QMessageBox.information(self, APP_NAME, msg)
            self.run_diagnose()

    def apply_port(self):
        port = (self._diag_result or {}).get("port")
        if port:
            self.port.setValue(int(port))
            self.save()
            self.run_diagnose()

    def save(self):
        s = self.win.settings
        old_port = s.get("port")
        s.update(player_name=self.name.text().strip(), port=self.port.value(), ini_path=self.ini_path.text().strip(),
                 auto_show_results=self.auto_show.isChecked(), auto_replay=self.auto_rep.isChecked(),
                 update_check=self.upd.isChecked(),
                 demo_speed=self.speed.value())
        storage.save_settings(s)
        if old_port != s["port"]:
            self.win.restart_client()
        self.win.history.refresh()
        self.win.statusBar().showMessage("Einstellungen gespeichert", 3000)


# ====================================================================== Hauptfenster
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = storage.load_settings()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(app_icon())
        self.resize(1380, 900)
        self.setMinimumSize(1100, 720)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.recorder = MatchRecorder()
        self.client: StatsApiClient | None = None
        self.last_state: dict | None = None
        self._live_dirty = False
        self._field_dirty = False
        self._demo_stop: threading.Event | None = None
        self._replay_watch_until = 0.0
        self._replay_since = 0.0
        self._replay_seen: set[str] = set()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Seitenleiste
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(220)
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(0, 22, 0, 16)
        rl.setSpacing(2)
        brand = QHBoxLayout()
        brand.setContentsMargins(18, 0, 18, 0)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(30, 30))
        word = QLabel("RL Tracker")
        word.setFont(display_font(17, True, True))
        brand.addWidget(logo)
        brand.addSpacing(6)
        brand.addWidget(word)
        brand.addStretch()
        rl.addLayout(brand)
        rl.addSpacing(26)

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.tabs.setDocumentMode(True)
        self.live = LiveView()
        self.matchview = MatchView(self.settings)
        self.history = HistoryView(self.settings, self.open_match)
        self.replayview = ReplayView(self.pool, lambda t: self.statusBar().showMessage(t, 6000))
        self.setup = SetupView(self)
        self._nav: list[QPushButton] = []
        for widget, label in ((self.live, "Live"), (self.matchview, "Auswertung"), (self.history, "Verlauf"),
                              (self.replayview, "Replays"), (self.setup, "Einrichtung")):
            self.tabs.addTab(widget, label)
            b = QPushButton(label)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            idx = self.tabs.count() - 1
            b.clicked.connect(lambda _=False, i=idx: self.tabs.setCurrentIndex(i))
            rl.addWidget(b)
            self._nav.append(b)
        self._nav[0].setChecked(True)
        self.tabs.currentChanged.connect(lambda i: [b.setChecked(j == i) for j, b in enumerate(self._nav)])
        rl.addStretch()

        # Update-Hinweis (nur sichtbar, wenn eine neuere Version auf GitHub liegt)
        self.update_box = QFrame()
        self.update_box.setStyleSheet(f"QFrame {{ background: #13233f; border: 1px solid #23406e; border-radius: 4px; }}"
                                      f"QLabel {{ border: none; background: transparent; }}")
        ub = QVBoxLayout(self.update_box)
        ub.setContentsMargins(12, 10, 12, 10)
        ub.setSpacing(6)
        self.update_label = QLabel("")
        self.update_label.setWordWrap(True)
        self.update_btn = QPushButton("Jetzt aktualisieren")
        self.update_btn.setObjectName("primary")
        self.update_btn.clicked.connect(self._install_update)
        ub.addWidget(self.update_label)
        ub.addWidget(self.update_btn)
        self.update_box.setVisible(False)
        wrap = QHBoxLayout()
        wrap.setContentsMargins(14, 0, 14, 14)
        wrap.addWidget(self.update_box)
        rl.addLayout(wrap)
        self._update = None
        self._update_future = None
        self._dl_future = None
        self._dl_progress = (0, 0)

        status = QVBoxLayout()
        status.setContentsMargins(18, 0, 18, 0)
        status.setSpacing(8)
        self.conn = QLabel("")
        self.conn.setObjectName("railStatus")
        self.conn.setWordWrap(True)
        status.addWidget(self.conn)
        b_check = QPushButton("Verbindung prüfen")
        b_check.clicked.connect(self._check_connection)
        status.addWidget(b_check)
        status.addSpacing(10)
        about = QPushButton(f"Inoffizielle Fan-App · v{__version__}")
        about.setFlat(True)
        about.setCursor(Qt.PointingHandCursor)
        about.setToolTip("Über RL Tracker, Datenschutz und Lizenzen")
        about.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {P.MUTED}; "
                            f"font-size: 8.5pt; padding: 0; text-align: left; }} "
                            f"QPushButton:hover {{ color: {P.TEXT_2}; }}")
        about.clicked.connect(lambda: AboutDialog(self).exec())
        status.addWidget(about)
        rl.addLayout(status)
        root.addWidget(rail)

        content = QWidget()
        content.setObjectName("content")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.tabs)
        root.addWidget(content, 1)
        self.tabs.currentChanged.connect(self._tab_changed)
        self._set_conn("waiting", "Warte auf Rocket League …")

        self.history.refresh()
        self.live.field.draw(P.plot_live_field, None)
        self.restart_client()

        self.t_poll = QTimer(self)
        self.t_poll.timeout.connect(self._poll)
        self.t_poll.start(40)
        self.t_ui = QTimer(self)
        self.t_ui.timeout.connect(self._refresh_live)
        self.t_ui.start(250)
        self.t_field = QTimer(self)
        self.t_field.timeout.connect(self._refresh_field)
        self.t_field.start(1500)
        self.t_replay = QTimer(self)
        self.t_replay.timeout.connect(self._watch_replays)
        self.t_replay.start(4000)
        self.t_demo = QTimer(self)
        self.t_demo.timeout.connect(self._check_demo)
        self.t_demo.start(1000)

        QTimer.singleShot(500, self._first_start)
        self.t_update = QTimer(self)
        self.t_update.timeout.connect(self._poll_update)
        self.t_update.start(300)
        if self.settings.get("update_check", True) and updates.configured():
            QTimer.singleShot(2500, lambda: setattr(self, "_update_future", self.pool.submit(updates.check)))

    # ---------------------------------------------------------------- Updates
    def _poll_update(self):
        f = self._update_future
        if f is not None and f.done():
            self._update_future = None
            try:
                rel = f.result()
            except Exception:
                rel = None  # offline o.ae. – still ignorieren
            if rel:
                self._update = rel
                size = f" · {rel['size'] / 1e6:.0f} MB" if rel.get("size") else ""
                self.update_label.setText(f"<b>Version {rel['version']} ist da</b><br>"
                                          f"<span style='color:{P.TEXT_2}'>Du hast {__version__}{size}</span>")
                self.update_label.setToolTip(rel.get("notes", "")[:1500])
                self.update_box.setVisible(True)
                self._offer_update(rel)
        d = self._dl_future
        if d is not None:
            done, total = self._dl_progress
            if not d.done():
                pct = f"{100 * done / total:.0f} %" if total else f"{done / 1e6:.0f} MB"
                self.update_btn.setText(f"Lade … {pct}")
                return
            self._dl_future = None
            try:
                path = d.result()
            except Exception as e:
                self.update_btn.setEnabled(True)
                self.update_btn.setText("Erneut versuchen")
                QMessageBox.warning(self, APP_NAME, f"Download fehlgeschlagen:\n{e}")
                return
            self.update_btn.setText("Starte Installation …")
            os.startfile(str(path))  # Installer aktualisiert die App und startet sie neu
            QApplication.quit()

    def _offer_update(self, rel: dict):
        """Update-Fenster beim Start; Pflicht-Updates ([wichtig]) lassen sich nicht wegklicken."""
        dlg = UpdateDialog(rel, self)
        if dlg.exec() == QDialog.Accepted:
            self._install_update(confirm=False)
        elif dlg.mandatory:
            QMessageBox.information(self, APP_NAME, "Ohne dieses wichtige Update kann RL Tracker nicht genutzt "
                                                    "werden. Die App wird jetzt beendet – beim nächsten Start "
                                                    "kannst du das Update installieren.")
            QApplication.quit()

    def _install_update(self, confirm: bool = True):
        rel = self._update
        if not rel:
            return
        if not getattr(sys, "frozen", False) or sys.platform != "win32":
            QDesktopServices.openUrl(QUrl(rel.get("page") or rel["download"]))
            return
        if confirm and QMessageBox.question(
                self, APP_NAME, f"Version {rel['version']} herunterladen und installieren?\n\n"
                                "Die App schließt sich dafür kurz und startet danach neu. "
                                "Deine Matches bleiben erhalten.") != QMessageBox.Yes:
            return
        self.update_btn.setEnabled(False)

        def progress(done, total):
            self._dl_progress = (done, total)
        self._dl_future = self.pool.submit(updates.download, rel["download"], progress)

    def _first_start(self):
        """Beim ersten Start einmal um Erlaubnis fragen (falls der Installer das nicht schon erledigt hat)."""
        installs = ini_setup.candidate_install_dirs()
        active = [d for d in installs if any(
            ini_setup.read_settings(d / "TAGame" / "Config" / n)["PacketSendRate"] > 0 for n in ini_setup.INI_NAMES)]
        if active:
            self.settings["access_asked"] = True
            if not self.settings.get("ini_path"):
                self.settings["ini_path"] = str(ini_setup.ini_for_install(active[0]))
            storage.save_settings(self.settings)
            return
        if self.settings.get("access_asked"):
            self.tabs.setCurrentWidget(self.setup)
            return
        self.settings["access_asked"] = True
        storage.save_settings(self.settings)
        if AccessDialog([str(d) for d in installs], self).exec() == QDialog.Accepted:
            if not installs:
                QMessageBox.information(self, APP_NAME, "Rocket League wurde nicht automatisch gefunden. "
                                                        "Wähle den Spielordner unter Einrichtung aus.")
                self.tabs.setCurrentWidget(self.setup)
                return
            ok = all([self.setup._write_ini(d) for d in installs])
            if ok:
                QMessageBox.information(self, APP_NAME, "Fertig! Starte Rocket League jetzt (neu) und geh in "
                                                        "ein Match oder ins Freeplay.")
        else:
            self.tabs.setCurrentWidget(self.setup)

    # ---------------------------------------------------------------- Verbindung
    def restart_client(self, port: int | None = None, web_port: int = 49124):
        """(Neu) verbinden. Mit port=... z.B. auf den Demo-Server statt auf Rocket League."""
        if self.client:
            self.client.stop()
        host = self.settings.get("host", "127.0.0.1")
        self.client = StatsApiClient(host, int(port or self.settings.get("port", 49123)), web_port=web_port)
        self.client.start()

    def _check_connection(self):
        self.tabs.setCurrentWidget(self.setup)
        self.setup.run_diagnose()

    def _set_conn(self, state: str, text: str):
        col = {"connected": P.GOOD, "waiting": P.ACCENT, "disconnected": P.BAD}.get(state, P.MUTED)
        head = {"connected": "Verbunden", "waiting": "Wartet auf das Spiel",
                "disconnected": "Verbindung getrennt"}.get(state, state)
        if self._demo_stop is not None and state == "connected":
            head = "Demo läuft"
        self.conn.setToolTip(text)
        hint = "" if state == "connected" else "<br>Starte ein Match oder Freeplay."
        self.conn.setText(f"<span style='color:{col};font-size:13pt'>●</span> "
                          f"<span style='color:{P.TEXT};font-weight:600'>{head}</span>"
                          f"<span style='color:{P.MUTED}'>{hint}</span>")

    def _poll(self):
        c = self.client
        if not c:
            return
        try:
            while True:
                st, text = c.status.get_nowait()
                self._set_conn(st, text)
        except queue.Empty:
            pass
        deadline = time.monotonic() + 0.03
        n = 0
        while time.monotonic() < deadline and n < 3000:
            try:
                msg = c.events.get_nowait()
            except queue.Empty:
                break
            n += 1
            self._handle(msg)

    def _handle(self, msg: dict):
        ev, d = msg["Event"], msg.get("Data") or {}
        if ev == "UpdateState":
            self.last_state = d
            self._live_dirty = True
        for sig, payload in self.recorder.handle(msg):
            if sig == "match_started":
                self.live.reset()
                self.live.add_feed("Neues Match gestartet", P.TEXT)
                self._field_dirty = True
            elif sig == "match_ended":
                self._match_finished(payload)
        self._feed_text(ev, d)
        if ev in ("BallHit", "GoalScored"):
            self._field_dirty = True

    def _feed_text(self, ev: str, d: dict):
        clock = self.live.clock_text()

        def nm(p):
            return (p or {}).get("Name", "?")

        def col(p):
            return P.TEAM.get((p or {}).get("TeamNum", 0), P.TEXT)

        if ev == "GoalScored":
            s = f"{clock}  TOR! {nm(d.get('Scorer'))}  ({A.kmh(A.to_uu(d.get('GoalSpeed'))):.0f} km/h)"
            if d.get("Assister"):
                s += f"  · Vorlage {nm(d['Assister'])}"
            self.live.add_feed(s, col(d.get("Scorer")))
        elif ev == "StatfeedEvent" and d.get("EventName") not in ("Goal",):
            s = f"{clock}  {feed_name(d.get('EventName') or d.get('Type', ''))}: {nm(d.get('MainTarget'))}"
            if d.get("SecondaryTarget"):
                s += f" → {nm(d['SecondaryTarget'])}"
            self.live.add_feed(s, col(d.get("MainTarget")))
        elif ev == "CrossbarHit":
            self.live.add_feed(f"{clock}  Latte! ({A.kmh(A.to_uu(d.get('BallSpeed'))):.0f} km/h)", P.ACCENT)
        elif ev == "MatchEnded":
            self.live.add_feed("Match beendet", P.TEXT)
        elif ev == "PlayerLeft":
            self.live.add_feed(f"{clock}  {d.get('PlayerName', '?')} hat das Spiel verlassen", P.MUTED)
        elif ev == "BallHit":
            b = d.get("Ball") or {}
            if b.get("PostHitSpeed", 0) > 2800:  # nur harte Schuesse erwaehnen
                p = (d.get("Players") or [{}])[0]
                self.live.add_feed(f"{clock}  Hammer von {nm(p)}: {A.kmh(b['PostHitSpeed']):.0f} km/h", col(p))

    def _refresh_live(self):
        if self._live_dirty and self.last_state and self.tabs.currentWidget() is self.live:
            self._live_dirty = False
            self.live.update_state(self.last_state, self.recorder)

    def _refresh_field(self):
        if self._field_dirty and self.tabs.currentWidget() is self.live:
            self._field_dirty = False
            self.live.field.draw(P.plot_live_field, self.recorder.match or self.recorder.last_finished)

    def _tab_changed(self, _):
        if self.tabs.currentWidget() is self.live:
            self._live_dirty = self._field_dirty = True
        elif self.tabs.currentWidget() is self.history:
            self.history.refresh()

    # ---------------------------------------------------------------- Match-Ende
    def _match_finished(self, match: dict):
        name = self.settings.get("player_name", "")
        lk = A.local_player_key(match, name)
        if lk:
            match["meta"]["local_player"] = lk
        if self._demo_stop is not None:
            match["demo"] = True
        try:
            path = storage.save_match(match)
            self.statusBar().showMessage(f"Match gespeichert: {path.name}", 8000)
        except OSError as e:
            self.statusBar().showMessage(f"Speichern fehlgeschlagen: {e}", 8000)
        self.matchview.show_match(match)
        self.history.refresh()
        self._field_dirty = True
        if self.settings.get("auto_show_results", True):
            self.tabs.setCurrentWidget(self.matchview)
            self.matchview.tabs.setCurrentIndex(0)
        if self.settings.get("auto_replay", True) and self.replayview.enabled and self._demo_stop is None:
            self._replay_since = time.time() - 5
            self._replay_watch_until = time.time() + 600  # 10 Minuten auf "Replay speichern" warten

    def _watch_replays(self):
        if time.time() > self._replay_watch_until:
            return
        p = R.newest_replay(self._replay_since)
        if p and str(p) not in self._replay_seen:
            self._replay_seen.add(str(p))
            self._replay_watch_until = 0
            time.sleep(0.5)  # Spiel schreibt die Datei evtl. noch
            self.replayview.analyze(p)
            self.statusBar().showMessage(f"Neues Replay gefunden: {p.name} – wird analysiert", 8000)

    def open_match(self, match: dict):
        self.matchview.show_match(match)
        self.tabs.setCurrentWidget(self.matchview)

    # ---------------------------------------------------------------- Demo
    def _end_demo(self, finished: bool = False):
        if self._demo_stop is None:
            return
        self._demo_stop.set()
        self._demo_stop = None
        self._demo_thread = None
        self.setup.b_demo.setText("Demo starten")
        self.recorder = MatchRecorder()
        self.restart_client()  # zurueck zu Rocket League
        self.statusBar().showMessage("Demo-Match fertig – die Auswertung ist offen. Verbinde wieder mit "
                                     "Rocket League." if finished else "Demo beendet", 8000)

    def _check_demo(self):
        t = getattr(self, "_demo_thread", None)
        if self._demo_stop is not None and t is not None and not t.is_alive():
            self._end_demo(finished=True)

    def toggle_demo(self):
        if self._demo_stop is not None:
            self._end_demo()
            return
        self.setup.save()
        stop = threading.Event()
        # Eigener freier Port: 49123 kann von Rocket League belegt sein (z.B. nach Freeplay)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        speed = float(self.settings.get("demo_speed", 6.0))
        errors: list[str] = []

        def run():
            try:
                simulator.serve(port, speed, 300, 30, stop, log=lambda t: None, matches=1)
            except OSError as e:
                errors.append(str(e))

        self._demo_thread = threading.Thread(target=run, daemon=True)
        self._demo_thread.start()
        time.sleep(0.3)
        if errors:
            QMessageBox.warning(self, APP_NAME, f"Demo konnte nicht starten:\n{errors[0]}")
            return
        self._demo_stop = stop
        self.recorder = MatchRecorder()  # offenes Freeplay o.ae. verwerfen
        self.restart_client(port, web_port=0)  # waehrend der Demo nur den Demo-Server hoeren
        self.setup.b_demo.setText("Demo stoppen")
        self.tabs.setCurrentWidget(self.live)
        self.statusBar().showMessage("Demo-Match läuft im Zeitraffer …", 6000)

    def closeEvent(self, e):
        if self._demo_stop:
            self._demo_stop.set()
        if self.client:
            self.client.stop()
        self.pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(e)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(app_icon())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
