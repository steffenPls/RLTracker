"""Gemeinsame Qt-Bausteine: Diagramm-Flaeche, Tabellen-Helfer, Stil."""
from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QFileDialog, QFrame, QHeaderView, QLabel, QSizePolicy, QTableWidget,  # noqa: E402
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import plots as P  # noqa: E402

DISPLAY_FAMILIES = ["Bahnschrift SemiBold SemiConden", "Bahnschrift SemiCondensed", "Bahnschrift",
                    "Segoe UI Semibold", "Segoe UI"]


def display_font(size: float, bold: bool = True, italic: bool = False) -> QFont:
    """Sportliche, leicht schmale Schrift (Bahnschrift ist in Windows 10/11 enthalten)."""
    f = QFont()
    f.setFamilies(DISPLAY_FAMILIES)
    f.setPointSizeF(size)
    f.setBold(bold)
    f.setItalic(italic)
    return f


STYLE = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; color: {P.TEXT}; }}
QMainWindow, QWidget#content, QStackedWidget, QScrollArea > QWidget > QWidget {{ background: {P.SURFACE}; }}
QWidget {{ background: transparent; }}
QMainWindow {{ background: {P.SURFACE}; }}
QToolTip {{ background: {P.RAISED}; color: {P.TEXT}; border: 1px solid {P.LINE}; padding: 4px 6px; }}

/* Seitenleiste */
QFrame#rail {{ background: {P.RAIL}; border-right: 1px solid #141d33; }}
QPushButton#nav {{ background: transparent; border: none; border-left: 3px solid transparent;
    color: {P.TEXT_2}; text-align: left; padding: 11px 18px; font-family: "Bahnschrift", "Segoe UI";
    font-size: 12pt; border-radius: 0; }}
QPushButton#nav:hover {{ color: {P.TEXT}; background: #0d1426; }}
QPushButton#nav:checked {{ color: {P.TEXT}; background: {P.SURFACE}; border-left: 3px solid {P.TEAM[0]}; }}
QLabel#railStatus {{ color: {P.TEXT_2}; font-size: 9pt; }}

/* Unter-Tabs (in Auswertung/Replays) */
QTabWidget::pane {{ border: none; border-top: 1px solid {P.LINE}; top: -1px; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {P.MUTED}; padding: 8px 14px; border: none;
    border-bottom: 2px solid transparent; font-family: "Bahnschrift", "Segoe UI"; font-size: 10.5pt; }}
QTabBar::tab:selected {{ color: {P.TEXT}; border-bottom: 2px solid {P.ACCENT}; }}
QTabBar::tab:hover {{ color: {P.TEXT}; }}

/* Knöpfe */
QPushButton {{ background: {P.SURFACE_2}; color: {P.TEXT}; border: 1px solid {P.LINE}; border-radius: 3px;
    padding: 7px 16px; font-family: "Bahnschrift", "Segoe UI"; font-size: 10.5pt; }}
QPushButton:hover {{ background: {P.RAISED}; border-color: #34466b; }}
QPushButton:pressed {{ background: #0f1729; }}
QPushButton:disabled {{ color: #4d5b78; border-color: #1c2740; }}
QPushButton#primary {{ border: none; color: white; font-weight: 600;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2f8cff, stop:1 #1f6be0); }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a9cff, stop:1 #2f7cf0); }}

/* Eingaben */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: #0a1020; border: 1px solid {P.LINE};
    border-radius: 3px; padding: 6px 8px; selection-background-color: {P.TEAM[0]}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {P.TEAM[0]}; }}
QComboBox QAbstractItemView {{ background: {P.SURFACE_2}; border: 1px solid {P.LINE};
    selection-background-color: {P.RAISED}; outline: 0; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #3a4c72; border-radius: 3px; background: #0a1020; }}
QCheckBox::indicator:checked {{ background: {P.TEAM[0]}; border-color: {P.TEAM[0]}; }}

/* Tabellen & Listen */
QTableWidget, QListWidget, QTreeWidget {{ background: {P.SURFACE_2}; alternate-background-color: #16203a;
    border: 1px solid {P.LINE}; border-radius: 4px; gridline-color: transparent; outline: 0; }}
QTableWidget::item, QListWidget::item {{ padding: 4px 6px; border: none; }}
QTableWidget::item:selected, QListWidget::item:selected {{ background: #1d3560; color: white; }}
QHeaderView::section {{ background: {P.SURFACE_2}; color: {P.MUTED}; border: none;
    border-bottom: 1px solid {P.LINE}; padding: 7px 6px; font-family: "Bahnschrift", "Segoe UI"; font-size: 9.5pt; }}
QTableCornerButton::section {{ background: {P.SURFACE_2}; border: none; }}

/* Bildlaufleisten */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: #26365a; border-radius: 3px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: #34497a; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {P.LINE}; }}

/* Texte */
QLabel#h1 {{ font-family: "Bahnschrift", "Segoe UI"; font-size: 22pt; font-weight: 700; }}
QLabel#h2 {{ font-family: "Bahnschrift", "Segoe UI"; font-size: 13.5pt; font-weight: 600; }}
QLabel#muted {{ color: {P.MUTED}; }}
QGroupBox {{ background: {P.SURFACE_2}; border: 1px solid {P.LINE}; border-radius: 4px; margin-top: 22px;
    padding: 14px 12px 12px 12px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 2px; top: 0px; padding: 0 2px; color: {P.TEXT};
    font-family: "Bahnschrift", "Segoe UI"; font-size: 12pt; }}
QStatusBar {{ background: {P.RAIL}; color: {P.TEXT_2}; border-top: 1px solid #141d33; }}
QMessageBox {{ background: {P.SURFACE_2}; }}
"""


def app_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(P.TEAM[0]))
    p.setPen(Qt.NoPen)
    p.drawPie(4, 4, 56, 56, 90 * 16, 180 * 16)
    p.setBrush(QColor(P.TEAM[1]))
    p.drawPie(4, 4, 56, 56, 270 * 16, 180 * 16)
    p.setBrush(QColor(P.SURFACE))
    p.drawEllipse(20, 20, 24, 24)
    p.end()
    return QIcon(pm)


class Canvas(QWidget):
    """Matplotlib-Flaeche, die mit einer Zeichenfunktion befuellt wird."""

    def __init__(self, parent=None, height: float = 6.0):
        super().__init__(parent)
        self.figure = Figure(figsize=(10, height), dpi=100)
        P.style_fig(self.figure)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)

    def draw(self, fn, *args, **kw) -> None:
        try:
            fn(self.figure, *args, **kw)
        except Exception as e:  # ein Diagramm-Fehler soll nie die App abstuerzen lassen
            P.empty(self.figure, f"Diagramm konnte nicht erstellt werden:\n{e}")
        self.canvas.draw_idle()

    def export_png(self, parent, default_name: str) -> None:
        path, _ = QFileDialog.getSaveFileName(parent, "Diagramm speichern", default_name, "PNG-Bild (*.png)")
        if path:
            self.figure.savefig(path, dpi=150, facecolor=self.figure.get_facecolor())


class NumItem(QTableWidgetItem):
    """Tabellenzelle, die numerisch sortiert."""

    def __init__(self, value, text: str | None = None):
        super().__init__(text if text is not None else str(value))
        self._v = value
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, NumItem):
            try:
                return float(self._v) < float(other._v)
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


def make_table(headers: list[str], sortable: bool = True) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSortingEnabled(sortable)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setHighlightSections(False)
    t.verticalHeader().setDefaultSectionSize(30)
    t.setShowGrid(False)
    return t


def fill_table(t: QTableWidget, rows: list[list], colors: list[str | None] | None = None,
               bold_first: bool = True) -> None:
    sorting = t.isSortingEnabled()
    t.setSortingEnabled(False)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if isinstance(v, tuple):  # (Wert, Anzeigetext)
                item = NumItem(v[0], v[1])
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                item = NumItem(v, f"{v:.0f}" if isinstance(v, int) or float(v).is_integer() else f"{v:.1f}")
            else:
                item = QTableWidgetItem(str(v))
            if c == 0 and colors and colors[r]:
                item.setForeground(QBrush(QColor(colors[r])))
                if bold_first:
                    f = QFont()
                    f.setBold(True)
                    item.setFont(f)
            t.setItem(r, c, item)
    t.setSortingEnabled(sorting)



# =================================================================== Spiel-Optik
def _poly(*pts) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in pts])


class ScoreBug(QWidget):
    """Anzeigetafel im Stil des Rocket-League-HUDs: schraege Teamplatten, Uhr in der Mitte."""

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self.compact = compact
        self.names = ["Blau", "Orange"]
        self.scores = [0, 0]
        self.clock = "5:00"
        self.overtime = False
        self.sub = ""
        self.winner: int | None = None
        self.colors = [QColor(P.TEAM[0]), QColor(P.TEAM[1])]
        self.setMinimumHeight(74 if compact else 112)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_state(self, names=None, scores=None, clock=None, overtime=None, sub=None, winner="keep"):
        if names:
            self.names = [names[0] or "Blau", names[1] or "Orange"]
        if scores is not None:
            self.scores = [int(scores[0]), int(scores[1])]
        if clock is not None:
            self.clock = clock
        if overtime is not None:
            self.overtime = bool(overtime)
        if sub is not None:
            self.sub = sub
        if winner != "keep":
            self.winner = winner
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        ph = 46.0 if self.compact else 64.0      # Plattenhoehe
        top = 4.0
        s = ph * 0.28                             # Schraege
        cw = ph * 2.3                             # Uhr-Box
        sw = ph * 1.45                            # Torplatte
        nw = max(60.0, min(240.0, (w - cw - 2 * sw) / 2 - 8))  # Namensplatte
        cx = w / 2
        cl, cr = cx - cw / 2, cx + cw / 2

        # Uhr-Box (Trapez nach unten schmaler)
        p.setPen(QPen(QColor("#2a3b60"), 1))
        p.setBrush(QColor("#060a14"))
        p.drawPolygon(_poly((cl, top), (cr, top), (cr - s, top + ph), (cl + s, top + ph)))

        for team in (0, 1):
            col = self.colors[team]
            dim = self.winner is not None and self.winner != team
            # Torplatte: Parallelogramm, schliesst buendig an die Uhr-Box an
            if team == 0:
                plate = _poly((cl - sw, top), (cl, top), (cl + s, top + ph), (cl - sw + s, top + ph))
                name = _poly((cl - sw - nw, top + ph * 0.18), (cl - sw - 3, top + ph * 0.18),
                             (cl - sw - 3 + s * 0.82, top + ph), (cl - sw - nw + s * 0.82, top + ph))
                prect = QRectF(cl - sw + s * 0.5, top, sw, ph)
                nrect = QRectF(cl - sw - nw + s, top + ph * 0.18, nw - s - 10, ph * 0.82)
                align = Qt.AlignRight | Qt.AlignVCenter
            else:
                plate = _poly((cr, top), (cr + sw, top), (cr + sw - s, top + ph), (cr - s, top + ph))
                name = _poly((cr + sw + 3, top + ph * 0.18), (cr + sw + nw, top + ph * 0.18),
                             (cr + sw + nw - s * 0.82, top + ph), (cr + sw + 3 - s * 0.82, top + ph))
                prect = QRectF(cr - s * 0.5, top, sw, ph)
                nrect = QRectF(cr + sw + 10, top + ph * 0.18, nw - s - 10, ph * 0.82)
                align = Qt.AlignLeft | Qt.AlignVCenter
            g = QLinearGradient(0, top, 0, top + ph)
            c1 = QColor(col)
            c2 = QColor(col).darker(165)
            if dim:
                c1.setAlpha(110)
                c2.setAlpha(110)
            g.setColorAt(0, c1)
            g.setColorAt(1, c2)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawPolygon(plate)
            nb = QColor(P.TEAM_DARK[team])
            nb.setAlpha(150 if dim else 235)
            p.setBrush(nb)
            p.drawPolygon(name)
            # Glanzkante oben
            p.setPen(QPen(QColor(255, 255, 255, 70 if not dim else 25), 1.2))
            if team == 0:
                p.drawLine(QPointF(cl - sw + 1, top + 1), QPointF(cl - 1, top + 1))
            else:
                p.drawLine(QPointF(cr + 1, top + 1), QPointF(cr + sw - 1, top + 1))
            # Zahlen und Namen
            p.setPen(QColor(255, 255, 255, 140 if dim else 255))
            p.setFont(display_font(ph * 0.46, True, True))
            p.drawText(prect, Qt.AlignCenter, str(self.scores[team]))
            p.setPen(QColor(P.TEXT if not dim else P.MUTED))
            p.setFont(display_font(ph * 0.21, True, False))
            p.drawText(nrect, align, self._elide(p, self.names[team], nrect.width()))

        # Uhr
        p.setPen(QColor(P.ACCENT) if self.overtime else QColor(P.TEXT))
        p.setFont(display_font(ph * 0.36, True, False))
        p.drawText(QRectF(cl + s * 0.4, top, cw - s * 0.8, ph), Qt.AlignCenter,
                   ("+" if self.overtime else "") + self.clock)
        # Unterzeile
        if self.sub and not self.compact:
            p.setPen(QColor(P.TEXT_2))
            p.setFont(display_font(10, False, False))
            p.drawText(QRectF(0, top + ph + 8, w, 26), Qt.AlignHCenter | Qt.AlignTop, self.sub)
        p.end()

    @staticmethod
    def _elide(p: QPainter, text: str, width: float) -> str:
        return p.fontMetrics().elidedText(text, Qt.ElideRight, int(width))


class PressureMeter(QWidget):
    """Live-Druckanzeige als Tauziehen: der Balken wandert Richtung des Teams, das unter Druck steht."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0.0      # -1 (Orange drueckt) .. +1 (Blau drueckt)
        self._shown = 0.0     # weich nachgefuehrt
        self.names = ["Blau", "Orange"]
        self.setMinimumHeight(62)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, v: float, names=None) -> None:
        self.value = max(-1.0, min(1.0, float(v)))
        self._shown += (self.value - self._shown) * 0.35
        if names:
            self.names = list(names)
        self.update()

    def reset(self) -> None:
        self.value = self._shown = 0.0
        self.update()

    def paintEvent(self, _):
        from .analysis import PRESSURE_THRESHOLD
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        v = self._shown
        # Beschriftung
        if v >= PRESSURE_THRESHOLD:
            text, col = f"{self.names[0]} macht Druck – {self.names[1]} unter Druck", QColor(P.TEAM[0])
        elif v <= -PRESSURE_THRESHOLD:
            text, col = f"{self.names[1]} macht Druck – {self.names[0]} unter Druck", QColor(P.TEAM[1])
        else:
            text, col = "Ausgeglichen", QColor(P.TEXT_2)
        p.setFont(display_font(10, True, False))
        p.setPen(QColor(P.MUTED))
        p.drawText(QRectF(0, 0, w, 20), Qt.AlignLeft | Qt.AlignVCenter, "DRUCK")
        p.setPen(col)
        p.drawText(QRectF(0, 0, w, 20), Qt.AlignHCenter | Qt.AlignVCenter, text)
        # Schiene
        top, bh = 26.0, 16.0
        sk = 6.0
        rail = _poly((sk, top), (w, top), (w - sk, top + bh), (0, top + bh))
        p.setPen(QPen(QColor(P.LINE), 1))
        p.setBrush(QColor("#0a1020"))
        p.drawPolygon(rail)
        cx = w / 2
        # Schwellen-Markierungen
        p.setPen(QPen(QColor(P.MUTED), 1, Qt.DashLine))
        for s in (-PRESSURE_THRESHOLD, PRESSURE_THRESHOLD):
            x = cx + s * (w / 2 - sk)
            p.drawLine(QPointF(x, top + 2), QPointF(x, top + bh - 2))
        # Fuellung: Blau drueckt -> Balken waechst nach rechts (Richtung Orange-Tor) und umgekehrt
        x = cx + v * (w / 2 - sk)
        team = 0 if v >= 0 else 1
        g = QLinearGradient(cx, 0, x if abs(x - cx) > 1 else cx + 1, 0)
        c1 = QColor(P.TEAM[team])
        c1.setAlpha(60)
        g.setColorAt(0, c1)
        g.setColorAt(1, QColor(P.TEAM[team]))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        l, r = min(cx, x), max(cx, x)
        if r - l > 0.5:
            p.drawPolygon(_poly((l + sk * 0.5, top + 1), (r + sk * 0.5, top + 1),
                                (r - sk * 0.5, top + bh - 1), (l - sk * 0.5, top + bh - 1)))
        # Mitte + Zeiger
        p.setPen(QPen(QColor(P.TEXT_2), 1.2))
        p.drawLine(QPointF(cx, top - 3), QPointF(cx, top + bh + 3))
        p.setPen(QPen(QColor("white"), 2.2))
        p.drawLine(QPointF(x, top - 4), QPointF(x, top + bh + 4))
        # Teamnamen an den Enden
        p.setFont(display_font(8.5, True, False))
        p.setPen(QColor(P.TEAM[0]))
        p.drawText(QRectF(0, top + bh + 2, w / 2, 14), Qt.AlignLeft | Qt.AlignTop, "◀ " + self.names[0] + "-Tor")
        p.setPen(QColor(P.TEAM[1]))
        p.drawText(QRectF(w / 2, top + bh + 2, w / 2, 14), Qt.AlignRight | Qt.AlignTop, self.names[1] + "-Tor ▶")
        p.end()


class StatTile(QFrame):
    """Kennzahl-Kachel mit abgeschraegter Ecke und Farbkante – wie die Spielfeldecken."""

    def __init__(self, title: str, value: str, sub: str = "", color: str | None = None, parent=None):
        super().__init__(parent)
        self.color = QColor(color or P.TEXT_2)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 18, 10)
        lay.setSpacing(0)
        t = QLabel(title)
        t.setStyleSheet(f"color:{P.MUTED};font-size:9pt;")
        v = QLabel(value)
        v.setFont(display_font(19, True, True))
        v.setStyleSheet(f"color:{color or P.TEXT};")
        lay.addWidget(t)
        lay.addWidget(v)
        if sub:
            u = QLabel(sub)
            u.setStyleSheet(f"color:{P.TEXT_2};font-size:9pt;")
            lay.addWidget(u)
        self.setMinimumWidth(150)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, c = self.width() - 1, self.height() - 1, 12.0
        path = QPainterPath()
        path.moveTo(0.5, 0.5)
        path.lineTo(w - c, 0.5)
        path.lineTo(w, c)
        path.lineTo(w, h)
        path.lineTo(c, h)
        path.lineTo(0.5, h - c)
        path.closeSubpath()
        p.setPen(QPen(QColor(P.LINE), 1))
        p.setBrush(QColor(P.SURFACE_2))
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(self.color)
        p.drawRect(QRectF(0.5, 6, 3, h - c - 6))  # Farbkante links
        p.end()
