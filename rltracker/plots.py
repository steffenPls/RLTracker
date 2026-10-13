"""Alle Diagramme der App (matplotlib, ohne pyplot – laeuft in Qt und headless)."""
from __future__ import annotations

import warnings

import matplotlib
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Polygon, Rectangle

from . import analysis as A

# ---------------------------------------------------------------- Farben
# "Arena bei Nacht": tiefes Marineblau, Rasen-Gruen fuers Feld, Teamfarben wie im Spiel,
# Boost-Gelb als einziger Akzent.
RAIL = "#070b16"        # Seitenleiste
SURFACE = "#0c1322"     # Inhaltsflaeche (= Hintergrund aller Diagramme)
SURFACE_2 = "#131c31"   # Karten/Panels
RAISED = "#1a2540"      # Hover / erhoehte Flaechen
PITCH = "#0e2620"       # Spielfeld-Rasen
PITCH_LINE = "#2c5a4b"  # Feldlinien
LINE = "#26344f"        # Rahmen/Achsen
GRID = "#1b2740"
TEXT = "#eaf0ff"
TEXT_2 = "#a3b2d1"
MUTED = "#6c7c9e"
TEAM = {0: "#2f8cff", 1: "#ff7a1a"}
TEAM_DARK = {0: "#123a75", 1: "#6e3205"}
GOOD = "#2fd27a"
BAD = "#ff5d6c"
ACCENT = "#ffc93c"      # Boost-Gelb
PLAYER_MARKERS = ["o", "s", "^", "D", "v", "P"]

# Bahnschrift (in Windows enthalten) passt zur sportlichen HUD-Schrift des Spiels.
matplotlib.rcParams["font.family"] = ["Bahnschrift", "Segoe UI", "DejaVu Sans"]
warnings.filterwarnings("ignore", message="findfont")
import logging  # noqa: E402
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def _ramp(hex_top: str, name: str) -> LinearSegmentedColormap:
    """Ein-Farben-Rampe: transparent (Spielfeld) -> kraeftig -> fast weiss."""
    r, g, b = to_rgb(hex_top)
    return LinearSegmentedColormap.from_list(name, [
        (0.0, (r, g, b, 0.0)),
        (0.15, (r, g, b, 0.35)),
        (0.6, (r, g, b, 0.85)),
        (1.0, (min(1, r * 0.4 + 0.6), min(1, g * 0.4 + 0.6), min(1, b * 0.4 + 0.6), 1.0)),
    ])


HEAT_BLUE = _ramp(TEAM[0], "heat_blue")
HEAT_ORANGE = _ramp(TEAM[1], "heat_orange")
HEAT_NEUTRAL = _ramp(ACCENT, "heat_neutral")


def heat_cmap(team: int | None):
    return {0: HEAT_BLUE, 1: HEAT_ORANGE}.get(team, HEAT_NEUTRAL)


def style_fig(fig: Figure) -> None:
    fig.set_facecolor(SURFACE)


def style_ax(ax, grid_axis: str = "y") -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.xaxis.label.set_color(TEXT_2)
    ax.yaxis.label.set_color(TEXT_2)
    ax.title.set_color(TEXT)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)


def _title(ax, text: str, sub: str = "") -> None:
    ax.set_title(text, loc="left", color=TEXT, fontsize=12, fontweight="bold", pad=18 if sub else 8)
    if sub:
        ax.text(0, 1.015, sub, transform=ax.transAxes, color=MUTED, fontsize=8.5, va="bottom")


def _legend(ax, **kw) -> None:
    leg = ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_2, **kw)
    return leg


def empty(fig: Figure, text: str) -> None:
    fig.clear()
    style_fig(fig)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.text(0.5, 0.5, text, ha="center", va="center", color=MUTED, fontsize=11, wrap=True,
            transform=ax.transAxes)


# ---------------------------------------------------------------- Spielfeld
# Darstellung quer: horizontale Achse = Spiel-Y (Blaues Tor links), vertikal = Spiel-X.

def draw_field(ax, labels: bool = True) -> None:
    ax.set_facecolor(SURFACE)
    c = 1152.0  # abgeschraegte Ecken
    fx, fy = A.FIELD_X, A.FIELD_Y
    outline = [(-fy + c, -fx), (fy - c, -fx), (fy, -fx + c), (fy, fx - c), (fy - c, fx),
               (-fy + c, fx), (-fy, fx - c), (-fy, -fx + c)]
    pitch = Polygon(outline, closed=True, facecolor=PITCH, edgecolor=PITCH_LINE, lw=1.8, zorder=0)
    ax.add_patch(pitch)
    # Gemaehte Rasenstreifen wie in den Arenen
    for i, y0 in enumerate(np.arange(-fy, fy, fy / 8)):
        if i % 2:
            stripe = Rectangle((y0, -fx), fy / 8, 2 * fx, facecolor="#123029", edgecolor="none", zorder=0)
            ax.add_patch(stripe)
            stripe.set_clip_path(pitch)
    ax._rl_pitch = pitch  # fuer das Zuschneiden der Heatmaps
    for team, sx in ((0, -1), (1, 1)):
        ax.add_patch(Rectangle((fy if sx > 0 else -fy - A.GOAL_DEPTH, -A.GOAL_HALF_W),
                               A.GOAL_DEPTH, 2 * A.GOAL_HALF_W, facecolor=TEAM[team], alpha=0.25,
                               edgecolor=TEAM[team], lw=1.5, zorder=0))
    ax.plot([0, 0], [-fx, fx], color=PITCH_LINE, lw=1.2, zorder=1)
    ax.add_patch(Circle((0, 0), 1000, fill=False, edgecolor=PITCH_LINE, lw=1.2, zorder=1))
    for y in (-A.THIRD, A.THIRD):
        ax.plot([y, y], [-fx, fx], color=PITCH_LINE, lw=0.8, ls=(0, (4, 4)), zorder=1, alpha=0.7)
    ax.set_xlim(-fy - A.GOAL_DEPTH - 80, fy + A.GOAL_DEPTH + 80)
    ax.set_ylim(-fx - 80, fx + 80)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if labels:
        ax.text(-fy + 250, -fx + 200, "Blaues Tor", color=TEAM[0], fontsize=8, va="bottom")
        ax.text(fy - 250, -fx + 200, "Oranges Tor", color=TEAM[1], fontsize=8, va="bottom", ha="right")


def _to_plot(xs, ys, flip=False):
    """Spielkoordinaten -> Plot (quer). flip spiegelt fuer Orange (eigenes Tor links)."""
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    if flip:
        xs, ys = -xs, -ys
    return ys, xs


def _gauss_blur(grid: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return grid
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    g = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, grid)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, g)


def heat_layer(ax, px, py, cmap, sigma_uu: float = 450.0, cell: float = 100.0, weights=None,
               vmax=None, alpha=1.0):
    """Weiche Heatmap aus Punkten (Plot-Koordinaten)."""
    px = np.asarray(px, float)
    py = np.asarray(py, float)
    if px.size == 0:
        return None
    xmax = A.FIELD_Y + A.GOAL_DEPTH
    xe = np.arange(-xmax, xmax + cell, cell)
    ye = np.arange(-A.FIELD_X, A.FIELD_X + cell, cell)
    h, _, _ = np.histogram2d(px, py, bins=[xe, ye], weights=weights)
    h = _gauss_blur(h, sigma_uu / cell)
    if h.max() <= 0:
        return None
    h = h / (vmax if vmax else h.max())
    im = ax.imshow(h.T, origin="lower", extent=[xe[0], xe[-1], ye[0], ye[-1]], cmap=cmap,
                   vmin=0, vmax=1, interpolation="bilinear", zorder=2, alpha=alpha)
    pitch = getattr(ax, "_rl_pitch", None)
    if pitch is not None:
        im.set_clip_path(pitch)
    return im


# ---------------------------------------------------------------- Live-Feld

def plot_live_field(fig: Figure, match: dict | None) -> None:
    fig.clear()
    style_fig(fig)
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.9])
    draw_field(ax)
    if not match:
        ax.set_title("Ballberührungen (live)", color=TEXT, fontsize=10, loc="left")
        return
    touches = [t for t in match["touches"] if t.get("x") is not None]
    for team in (0, 1):
        tt = [t for t in touches if t["team"] == team]
        if tt:
            px, py = _to_plot([t["x"] for t in tt], [t["y"] for t in tt])
            ax.scatter(px, py, s=14, color=TEAM[team], alpha=0.55, edgecolor="none", zorder=3)
    if touches:
        last = touches[-1]
        px, py = _to_plot([last["x"]], [last["y"]])
        ax.scatter(px, py, s=90, facecolor="white", edgecolor=TEAM[last["team"]], lw=2, zorder=5)
    for g in match["goals"]:
        if g.get("x") is not None:
            px, py = _to_plot([g["x"]], [g["y"]])
            ax.scatter(px, py, marker="*", s=160, color=TEAM[g["team"]], edgecolor="white", lw=0.8, zorder=6)
    ax.set_title(f"Ballberührungen live · {len(touches)}", color=TEXT, fontsize=10, loc="left")


# ---------------------------------------------------------------- Heatmaps

def plot_touch_heatmap(fig: Figure, match: dict, keys: list[str] | None, mode: str = "heat",
                       normalize: bool = False) -> None:
    """Heatmap/Punktwolke der Ballberuehrungen ausgewaehlter Spieler."""
    fig.clear()
    style_fig(fig)
    players = match["players"]
    all_players = not keys
    keys = keys or list(players)
    touches = [t for t in match["touches"] if t["player"] in keys and t.get("x") is not None]
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.84])
    draw_field(ax, labels=not normalize)
    teams = {players[k]["team"] for k in keys if k in players}
    team = teams.pop() if len(teams) == 1 else None
    if not touches:
        ax.text(0, 0, "Keine Ballberührungen mit Position", color=MUTED, ha="center", va="center")
    else:
        flips = [normalize and t["team"] == 1 for t in touches]
        pts = [_to_plot([t["x"]], [t["y"]], f) for t, f in zip(touches, flips)]
        px = np.array([p[0][0] for p in pts])
        py = np.array([p[1][0] for p in pts])
        if mode in ("heat", "both"):
            heat_layer(ax, px, py, heat_cmap(team), sigma_uu=550)
        if mode in ("points", "both"):
            for i, k in enumerate(keys):
                idx = [j for j, t in enumerate(touches) if t["player"] == k]
                if not idx:
                    continue
                ax.scatter(px[idx], py[idx], s=26, marker=PLAYER_MARKERS[i % len(PLAYER_MARKERS)],
                           color=TEAM[players[k]["team"]], edgecolor=SURFACE, lw=0.8, zorder=4,
                           label=f"{players[k]['name']} ({len(idx)})")
            if len(keys) > 1:
                _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.0), ncol=min(6, len(keys)))
        if normalize:
            ax.text(-A.FIELD_Y + 250, -A.FIELD_X + 200, "← eigenes Tor", color=TEXT_2, fontsize=8)
            ax.text(A.FIELD_Y - 250, -A.FIELD_X + 200, "gegnerisches Tor →", color=TEXT_2, fontsize=8, ha="right")
    who = "alle Spieler" if all_players else (
        ", ".join(players[k]["name"] for k in keys[:3]) + (" …" if len(keys) > 3 else ""))
    _title(ax, f"Ballberührungen – {who}", f"{len(touches)} Berührungen mit Position"
           + (" · aus Sicht des eigenen Teams" if normalize else ""))
    zones = {"def": 0, "mid": 0, "off": 0}
    for t in touches:
        zones[A.zone_of(t["y"], t["team"])] += 1
    n = max(1, len(touches))
    if normalize or team is not None:
        txt = f"Defensiv {100 * zones['def'] / n:.0f}%   Mitte {100 * zones['mid'] / n:.0f}%   Offensiv {100 * zones['off'] / n:.0f}%"
        ax.text(1, 1.015, txt, transform=ax.transAxes, color=TEXT_2, fontsize=8.5, ha="right", va="bottom")


def plot_event_map(fig: Figure, match: dict, show: set[str]) -> None:
    """Karte von Toren, Schuessen, Saves, Latten-/Pfostentreffern."""
    fig.clear()
    style_fig(fig)
    ax = fig.add_axes([0.02, 0.1, 0.96, 0.78])
    draw_field(ax)
    players = match["players"]
    handles = 0
    if "goals" in show:
        for g in match["goals"]:
            if g.get("x") is None:
                continue
            gx, gy = _to_plot([g["x"]], [g["y"]])
            col = TEAM[g["team"]]
            if g.get("shot_x") is not None:
                sx, sy = _to_plot([g["shot_x"]], [g["shot_y"]])
                ax.annotate("", xy=(gx[0], gy[0]), xytext=(sx[0], sy[0]),
                            arrowprops=dict(arrowstyle="->", color=col, lw=1.6, alpha=0.9), zorder=4)
                ax.scatter(sx, sy, s=40, color=col, edgecolor="white", lw=0.8, zorder=5)
            ax.scatter(gx, gy, marker="*", s=230, color=col, edgecolor="white", lw=0.9, zorder=6,
                       label="Tor" if handles == 0 else None)
            if len(match["goals"]) <= 8 and g.get("shot_x") is not None:
                name = players.get(g["scorer"], {}).get("name", "?")
                ax.annotate(f"{name} {A.fmt_time(g['t'])}", (sx[0], sy[0]), xytext=(0, 9),
                            textcoords="offset points", color=TEXT, fontsize=7.5, ha="center", zorder=7)
            handles += 1
    marks = {"Shot": ("shots", "o", "Schuss"), "Save": ("saves", "s", "Save"),
             "EpicSave": ("saves", "D", "Epic Save"), "Clear": ("clears", "v", "Klärung"),
             "Center": ("centers", "^", "Flanke")}
    seen = set()
    for e in match.get("feed", []):
        if e.get("x") is None:
            continue
        key = next((m for m in marks if e["event"].replace(" ", "").lower() == m.lower()), None)
        if not key or marks[key][0] not in show:
            continue
        team = players.get(e["player"], {}).get("team", 0)
        px, py = _to_plot([e["x"]], [e["y"]])
        lbl = marks[key][2] if key not in seen else None
        seen.add(key)
        ax.scatter(px, py, marker=marks[key][1], s=46, facecolor="none", edgecolor=TEAM[team], lw=1.6,
                   zorder=5, label=lbl)
    if "crossbars" in show:
        for c in match.get("crossbars", []):
            if c.get("x") is None:
                continue
            px, py = _to_plot([c["x"]], [c["y"]])
            ax.scatter(px, py, marker="X", s=60, color=ACCENT, edgecolor=SURFACE, zorder=5,
                       label="Latte/Pfosten" if "cb" not in seen else None)
            seen.add("cb")
    if handles or seen:
        _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.0), ncol=6, markerscale=0.8)
    _title(ax, "Torszenen & Aktionen",
           "Stern = Tor (Pfeil vom letzten Schuss), Ringfarbe = Team")


def plot_boost_map(fig: Figure, match: dict, keys: list[str] | None) -> None:
    fig.clear()
    style_fig(fig)
    players = match["players"]
    keys = keys or list(players)
    bs = [b for b in match.get("boosts", []) if b["player"] in keys]
    ax = fig.add_axes([0.02, 0.1, 0.96, 0.78])
    draw_field(ax)
    if not bs:
        ax.text(0, 0, "Keine Boost-Daten\n(Rocket League sendet Boost-Pickups nur im Zuschauer-Modus "
                      "oder für dein Team)", color=MUTED, ha="center", va="center", fontsize=9)
        _title(ax, "Boost-Pickups")
        return
    # nach Pad gruppieren
    pads: dict[tuple, dict] = {}
    for b in bs:
        k = (round(b["x"] / 200), round(b["y"] / 200), b["big"])
        pads.setdefault(k, {"x": b["x"], "y": b["y"], "big": b["big"], "n": 0, "teams": [0, 0]})
        pads[k]["n"] += 1
        pads[k]["teams"][b["team"]] += 1
    for p in pads.values():
        px, py = _to_plot([p["x"]], [p["y"]])
        team = 0 if p["teams"][0] >= p["teams"][1] else 1
        size = (130 if p["big"] else 30) + 22 * p["n"]
        ax.scatter(px, py, s=size, color=TEAM[team], alpha=0.85 if p["big"] else 0.6,
                   edgecolor="white" if p["big"] else SURFACE, lw=1.0 if p["big"] else 0.6, zorder=4)
        if p["big"] or p["n"] >= 3:
            ax.text(px[0], py[0], str(p["n"]), color="white", fontsize=7.5, ha="center", va="center", zorder=5)
    big = sum(1 for b in bs if b["big"])
    _title(ax, "Boost-Pickups",
           f"{len(bs)} Pickups · {big} große Pads · {len(bs) - big} kleine Pads · Größe = Anzahl, Farbe = Team mit den meisten Pickups")


# ---------------------------------------------------------------- Zeitverlauf

def _goal_lines(ax, match):
    for g in match["goals"]:
        ax.axvline(g["t"], color=TEAM[g["team"]], lw=1, alpha=0.6, ls=(0, (3, 3)))


def _time_axis(ax, tmax):
    ticks = np.arange(0, max(tmax, 60) + 1, 60)
    ax.set_xticks(ticks)
    ax.set_xticklabels([A.fmt_time(t) for t in ticks])
    ax.set_xlim(0, max(tmax, 10))


def plot_timeline(fig: Figure, match: dict) -> None:
    """Spielstand, Ballgeschwindigkeit und Momentum untereinander (gemeinsame Zeitachse)."""
    fig.clear()
    style_fig(fig)
    s = match.get("samples", [])
    tmax = match["meta"].get("duration", 0) or (s[-1]["t"] if s else 0)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1, 0.9], hspace=0.55, left=0.07, right=0.97, top=0.92, bottom=0.07)

    ax = fig.add_subplot(gs[0])
    style_ax(ax)
    for team in (0, 1):
        ts = [0.0] + [g["t"] for g in match["goals"] if g["team"] == team] + [tmax]
        ys = list(range(len(ts) - 1)) + [len(ts) - 2]
        ax.step(ts, ys, where="post", color=TEAM[team], lw=2,
                label=match["meta"]["teams"][str(team)]["name"])
    last_label = {0: -1e9, 1: -1e9}
    for g in match["goals"]:
        n = sum(1 for x in match["goals"] if x["team"] == g["team"] and x["t"] <= g["t"])
        ax.scatter([g["t"]], [n], color=TEAM[g["team"]], s=40, zorder=4, edgecolor=SURFACE, lw=1.5)
        if g["t"] - last_label[g["team"]] > max(tmax, 60) / 12:  # Beschriftungen nicht ueberlappen
            last_label[g["team"]] = g["t"]
            name = match["players"].get(g["scorer"], {}).get("name", "?")
            ax.annotate(name, (g["t"], n), xytext=(4, 4), textcoords="offset points", color=TEXT_2, fontsize=7.5)
    ax.yaxis.get_major_locator().set_params(integer=True)
    _time_axis(ax, tmax)
    _legend(ax, loc="upper left")
    _title(ax, "Spielstand")

    ax2 = fig.add_subplot(gs[1], sharex=ax)
    style_ax(ax2)
    if s:
        ax2.plot([x["t"] for x in s], [A.kmh(x["ball_speed"]) for x in s], color=ACCENT, lw=1.5)
        ax2.fill_between([x["t"] for x in s], [A.kmh(x["ball_speed"]) for x in s], color=ACCENT, alpha=0.12)
    _goal_lines(ax2, match)
    ax2.set_ylabel("km/h")
    _title(ax2, "Ballgeschwindigkeit")

    ax3 = fig.add_subplot(gs[2], sharex=ax)
    _pressure_axis(ax3, match, A.pressure_series(match), compact=True)
    _title(ax3, "Druck", "Wer greift gerade an – Details im Tab „Druckphasen“")
    _time_axis(ax3, tmax)


def _pressure_axis(ax, match: dict, s: dict, compact: bool = False, phases: list | None = None) -> None:
    """Druck-Index als Flaeche: nach oben = Blau drueckt, nach unten = Orange drueckt."""
    style_ax(ax, grid_axis="")
    t = np.array(s["t"])
    v = np.clip(np.array(s["index"]), -1, 1)
    act = np.array(s["active"], dtype=bool)
    if len(t):
        vv = np.where(act, v, 0.0)
        th = A.PRESSURE_THRESHOLD
        ax.fill_between(t, 0, vv, where=vv >= 0, color=TEAM[0], alpha=0.35, interpolate=True, lw=0)
        ax.fill_between(t, 0, vv, where=vv < 0, color=TEAM[1], alpha=0.35, interpolate=True, lw=0)
        # starker Druck kraeftig hervorheben
        ax.fill_between(t, th, vv, where=vv >= th, color=TEAM[0], alpha=0.9, interpolate=True, lw=0)
        ax.fill_between(t, -th, vv, where=vv <= -th, color=TEAM[1], alpha=0.9, interpolate=True, lw=0)
        ax.plot(t, vv, color=TEXT, lw=0.6, alpha=0.35)
        # Pausen (nach Toren, Anstoss-Countdown) grau hinterlegen
        start = None
        for i, a in enumerate(list(act) + [True]):
            if not a and start is None:
                start = t[i]
            elif a and start is not None:
                ax.axvspan(start, t[min(i, len(t) - 1)], color=GRID, alpha=0.6, lw=0, zorder=0)
                start = None
        for y in (th, -th):
            ax.axhline(y, color=MUTED, lw=0.8, ls=(0, (2, 3)), alpha=0.7)
    ax.axhline(0, color=LINE, lw=1)
    ax.set_ylim(-1.08, 1.08)
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["Orange\ndrückt", "", "Blau\ndrückt"] if not compact else ["Orange", "", "Blau"],
                       fontsize=8.5)
    for lbl, team in zip(ax.get_yticklabels(), (1, None, 0)):
        if team is not None:
            lbl.set_color(TEAM[team])
    # Tore als Marker am Rand
    for g in match.get("goals", []):
        y = 1.0 if g["team"] == 0 else -1.0
        ax.axvline(g["t"], color=TEAM[g["team"]], lw=1, alpha=0.5, ls=(0, (3, 3)))
        ax.scatter([g["t"]], [y], s=70 if not compact else 40, marker="o", color=TEAM[g["team"]],
                   edgecolor="white", lw=1.2, zorder=5, clip_on=False)
    if phases and not compact:
        for n, p in enumerate(phases, 1):
            y = 1.0 if p["team"] == 0 else -1.0
            ax.annotate(str(n), ((p["start"] + p["end"]) / 2, y * 0.62), ha="center", va="center",
                        color="white", fontsize=8, fontweight="bold",
                        bbox=dict(boxstyle="circle,pad=0.25", fc=TEAM_DARK[p["team"]], ec=TEAM[p["team"]], lw=1))


def plot_pressure(fig: Figure, match: dict, summary: dict | None = None) -> None:
    """Grosse Druck-Grafik: wann stand welches Team unter Druck – plus Kennzahlen."""
    fig.clear()
    style_fig(fig)
    sm = summary or A.pressure_summary(match)
    s, phases = sm["series"], sm["phases"]
    if not s["t"] or not (match.get("touches") or match.get("feed")):
        empty(fig, "Für dieses Match gibt es zu wenige Daten für die Druck-Analyse.")
        return
    tmax = match["meta"].get("duration", 0) or s["t"][-1]
    gs = fig.add_gridspec(2, 2, height_ratios=[2.3, 1], width_ratios=[1.35, 1], hspace=0.55, wspace=0.3,
                          left=0.08, right=0.97, top=0.9, bottom=0.08)
    ax = fig.add_subplot(gs[0, :])
    _pressure_axis(ax, match, s, phases=phases)
    _time_axis(ax, tmax)
    names = {t: match["meta"]["teams"][str(t)].get("name") for t in (0, 1)}
    names = {0: "Blau" if str(names[0]).lower() in ("blue", "none", "") else names[0],
             1: "Orange" if str(names[1]).lower() in ("orange", "none", "") else names[1]}
    _title(ax, "Druckphasen",
           f"Fläche nach oben = {names[0]} greift an (Orange unter Druck) · nach unten = {names[1]} greift an · "
           f"kräftig = starker Druck · Kreise = Tore · grau = Pause")

    # Anteil der Spielzeit mit Druck
    ax2 = fig.add_subplot(gs[1, 0])
    style_ax(ax2, grid_axis="")
    tb, to = sm["teams"][0]["pressure_pct"], sm["teams"][1]["pressure_pct"]
    rest = max(0.0, 100 - tb - to)
    ax2.barh([0], [tb], color=TEAM[0], height=0.5)
    ax2.barh([0], [rest], left=[tb], color=RAISED, height=0.5)
    ax2.barh([0], [to], left=[tb + rest], color=TEAM[1], height=0.5)
    if tb >= 6:
        ax2.text(tb / 2, 0, f"{tb:.0f} %", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    if rest >= 10:
        ax2.text(tb + rest / 2, 0, f"ausgeglichen {rest:.0f} %", ha="center", va="center", color=TEXT_2, fontsize=8.5)
    if to >= 6:
        ax2.text(100 - to / 2, 0, f"{to:.0f} %", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    ax2.set_xlim(0, 100)
    ax2.set_ylim(-0.6, 0.6)
    ax2.set_yticks([])
    ax2.set_xticks([])
    for sp in ax2.spines.values():
        sp.set_visible(False)
    _title(ax2, "Wer hat mehr Druck gemacht?", f"Anteil der Spielzeit · {names[0]} links, {names[1]} rechts")

    # Kennzahlen-Tabelle
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.set_axis_off()
    rows = [("Druckphasen", "phases", "{:.0f}"), ("Längste Phase", "longest", "{:.0f} s"),
            ("Schüsse in Phasen", "shots", "{:.0f}"), ("Tore aus Druck", "goals", "{:.0f}")]
    ax3.text(0.0, 1.02, "Kennzahlen", color=TEXT, fontsize=12, fontweight="bold", transform=ax3.transAxes, va="bottom")
    ax3.text(0.62, 0.86, names[0], color=TEAM[0], fontsize=9.5, fontweight="bold", ha="center", transform=ax3.transAxes)
    ax3.text(0.9, 0.86, names[1], color=TEAM[1], fontsize=9.5, fontweight="bold", ha="center", transform=ax3.transAxes)
    for i, (lbl, key, fmt) in enumerate(rows):
        y = 0.66 - i * 0.2
        ax3.text(0.0, y, lbl, color=TEXT_2, fontsize=9.5, transform=ax3.transAxes, va="center")
        for x, team in ((0.62, 0), (0.9, 1)):
            ax3.text(x, y, fmt.format(sm["teams"][team][key]), color=TEXT, fontsize=10.5, ha="center",
                     va="center", transform=ax3.transAxes, fontweight="bold")


def plot_player_series(fig: Figure, match: dict, key: str) -> None:
    """Boost und Geschwindigkeit eines Spielers ueber die Zeit (zwei Diagramme, gleiche Zeitachse)."""
    fig.clear()
    style_fig(fig)
    p = match["players"].get(key)
    rows = [(s["t"], s["players"][key]) for s in match.get("samples", []) if key in s.get("players", {})]
    rows = [(t, r) for t, r in rows if "speed" in r]
    if not p or not rows:
        empty(fig, "Für diesen Spieler sendet Rocket League keine Live-Physikdaten "
                   "(Boost/Tempo gibt es nur für dein Team bzw. im Zuschauer-Modus).\n\n"
                   "Tipp: Die Replay-Analyse liefert diese Werte für alle Spieler.")
        return
    col = TEAM[p["team"]]
    tmax = match["meta"].get("duration", rows[-1][0])
    gs = fig.add_gridspec(2, 1, hspace=0.45, left=0.07, right=0.97, top=0.9, bottom=0.08)
    ax = fig.add_subplot(gs[0])
    style_ax(ax)
    t = [x[0] for x in rows]
    ax.fill_between(t, [x[1].get("boost", 0) for x in rows], color=col, alpha=0.25, lw=0)
    ax.plot(t, [x[1].get("boost", 0) for x in rows], color=col, lw=1.5)
    ax.set_ylim(0, 105)
    _goal_lines(ax, match)
    _title(ax, f"Boost – {p['name']}", "0–100")
    _time_axis(ax, tmax)
    ax2 = fig.add_subplot(gs[1], sharex=ax)
    style_ax(ax2)
    sp = [A.kmh(x[1].get("speed", 0)) for x in rows]
    ax2.plot(t, sp, color=col, lw=1.3)
    ax2.axhline(A.kmh(A.SUPERSONIC), color=ACCENT, lw=1, ls=(0, (4, 3)))
    ax2.text(t[0], A.kmh(A.SUPERSONIC) + 2, "Überschall", color=ACCENT, fontsize=7.5, va="bottom")
    ax2.set_ylabel("km/h")
    _goal_lines(ax2, match)
    _title(ax2, "Geschwindigkeit")
    _time_axis(ax2, tmax)


# ---------------------------------------------------------------- Vergleiche

def _hbars(ax, labels, values, colors, fmt="{:.0f}", title="", sub=""):
    style_ax(ax, grid_axis="x")
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=colors, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=TEXT_2, fontsize=8.5)
    vmax = max(values) if len(values) and max(values) > 0 else 1
    for yi, v in zip(y, values):
        ax.text(v + vmax * 0.02, yi, fmt.format(v), va="center", color=TEXT, fontsize=8)
    ax.set_xlim(0, vmax * 1.18)
    ax.tick_params(axis="y", length=0)
    _title(ax, title, sub)


def plot_compare(fig: Figure, match: dict, an: dict) -> None:
    fig.clear()
    style_fig(fig)
    keys = A.player_order(match)
    ps = an["players"]
    labels = [ps[k]["name"] for k in keys]
    colors = [TEAM[ps[k]["team"]] for k in keys]
    metrics = [("score", "Punkte", "{:.0f}"), ("touches", "Ballkontakte", "{:.0f}"),
               ("avg_hit_speed", "Ø Schussstärke (km/h)", "{:.0f}"), ("max_hit_speed", "Härtester Schuss (km/h)", "{:.0f}"),
               ("boost_collected", "Boost gesammelt", "{:.0f}"), ("aerial_touches", "Luftkontakte", "{:.0f}")]
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.55, left=0.1, right=0.97, top=0.9, bottom=0.06)
    for i, (f, t, fmt) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        _hbars(ax, labels, [ps[k].get(f, 0) for k in keys], colors, fmt, t)


def plot_zones(fig: Figure, match: dict, an: dict) -> None:
    """Gestapelte Balken: wo hat jeder Spieler den Ball beruehrt (Drittel)."""
    fig.clear()
    style_fig(fig)
    keys = A.player_order(match)
    ps = an["players"]
    ax = fig.add_axes([0.16, 0.14, 0.8, 0.72])
    style_ax(ax, grid_axis="x")
    y = np.arange(len(keys))[::-1]
    shades = {"def": "#1a4f9a", "mid": "#2f8cff", "off": "#a9cdff"}
    left = np.zeros(len(keys))
    for z, lbl in (("def", "Eigenes Drittel"), ("mid", "Mittleres Drittel"), ("off", "Gegnerisches Drittel")):
        tot = np.array([max(1, ps[k]["touches_def"] + ps[k]["touches_mid"] + ps[k]["touches_off"]) for k in keys])
        vals = np.array([ps[k][f"touches_{z}"] for k in keys]) / tot * 100
        ax.barh(y, vals, left=left, color=shades[z], height=0.6, label=lbl, edgecolor=SURFACE, lw=2)
        for yi, l, v in zip(y, left, vals):
            if v >= 9:
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color=SURFACE if z == "off" else TEXT)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([ps[k]["name"] for k in keys], fontsize=9)
    for lab, k in zip(ax.get_yticklabels(), keys):
        lab.set_color(TEAM[ps[k]["team"]])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% der Ballberührungen")
    _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    _title(ax, "Positionsspiel", "In welchem Drittel (aus Sicht des eigenen Teams) wurde der Ball berührt")


def plot_hit_speeds(fig: Figure, match: dict) -> None:
    fig.clear()
    style_fig(fig)
    keys = A.player_order(match)
    ps = match["players"]
    ax = fig.add_axes([0.16, 0.12, 0.8, 0.76])
    style_ax(ax, grid_axis="x")
    rng = np.random.default_rng(1)
    for i, k in enumerate(keys):
        sp = [A.kmh(t["post"]) for t in match["touches"] if t["player"] == k and t["post"] > 0]
        y = len(keys) - 1 - i
        if sp:
            ax.scatter(sp, y + rng.uniform(-0.18, 0.18, len(sp)), s=14, color=TEAM[ps[k]["team"]],
                       alpha=0.6, edgecolor="none")
            ax.plot([np.median(sp)] * 2, [y - 0.3, y + 0.3], color=TEXT, lw=2)
    ax.set_yticks(range(len(keys))[::-1])
    ax.set_yticklabels([ps[k]["name"] for k in keys], fontsize=9)
    ax.set_xlabel("Ballgeschwindigkeit nach dem Treffer (km/h)")
    _title(ax, "Schussstärke jeder Ballberührung", "Punkt = eine Berührung, Strich = Median")


def plot_physics(fig: Figure, match: dict, an: dict) -> None:
    fig.clear()
    style_fig(fig)
    keys = [k for k in A.player_order(match) if an["players"][k]["has_live_physics"]]
    if not keys:
        empty(fig, "Keine Live-Physikdaten in diesem Match.\n\nRocket League sendet Tempo/Boost/Boden-Luft nur "
                   "für dein Team bzw. im Zuschauer-Modus.\nDie Replay-Analyse liefert diese Werte für alle Spieler.")
        return
    ps = an["players"]
    groups = [
        ("Bewegung", [("ground_pct", "Boden", "#a9cdff"), ("wall_pct", "Wand", "#2f8cff"),
                      ("air_pct", "Luft", "#1a4f9a")]),
        ("Tempo", [("slow_pct", "langsam", "#a9cdff"), ("boost_speed_pct", "schnell", "#2f8cff"),
                   ("supersonic_pct", "Überschall", "#1a4f9a")]),
    ]
    gs = fig.add_gridspec(1, 3, wspace=0.6, left=0.1, right=0.97, top=0.82, bottom=0.2)
    y = np.arange(len(keys))[::-1]
    for gi, (title, parts) in enumerate(groups):
        ax = fig.add_subplot(gs[gi])
        style_ax(ax, grid_axis="x")
        left = np.zeros(len(keys))
        for f, lbl, c in parts:
            vals = np.array([ps[k].get(f, 0) for k in keys])
            ax.barh(y, vals, left=left, color=c, height=0.6, label=lbl, edgecolor=SURFACE, lw=2)
            left += vals
        ax.set_yticks(y)
        ax.set_yticklabels([ps[k]["name"] for k in keys], fontsize=8.5)
        ax.set_xlim(0, 100)
        _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
        _title(ax, title, "% der Spielzeit")
    ax = fig.add_subplot(gs[2])
    _hbars(ax, [ps[k]["name"] for k in keys], [ps[k].get("avg_boost", 0) for k in keys],
           [TEAM[ps[k]["team"]] for k in keys], "{:.0f}", "Ø Boost", "0–100")


# ---------------------------------------------------------------- Karriere

def plot_career(fig: Figure, career: dict) -> None:
    fig.clear()
    style_fig(fig)
    pm = career.get("per_match", [])
    if not pm:
        empty(fig, "Noch keine gespeicherten Matches mit deinem Spielernamen.\n"
                   "Trage deinen Namen in den Einstellungen ein.")
        return
    gs = fig.add_gridspec(2, 1, hspace=0.5, left=0.07, right=0.97, top=0.9, bottom=0.1)
    ax = fig.add_subplot(gs[0])
    style_ax(ax)
    x = np.arange(len(pm))
    cols = [GOOD if m["result"] == "Sieg" else (BAD if m["result"] == "Niederlage" else MUTED) for m in pm]
    ax.bar(x, [m["score"] for m in pm], color=cols, width=0.7)
    if len(pm) >= 3:
        w = min(5, len(pm))
        ma = np.convolve([m["score"] for m in pm], np.ones(w) / w, mode="valid")
        ax.plot(x[w - 1:], ma, color=TEXT, lw=1.5, label=f"Schnitt der letzten {w}")
        _legend(ax, loc="upper left")
    ax.set_xticks([])
    _title(ax, "Punkte pro Match", "grün = Sieg, rot = Niederlage (älteste links)")
    ax2 = fig.add_subplot(gs[1])
    style_ax(ax2)
    wins = np.cumsum([m["result"] == "Sieg" for m in pm])
    rate = wins / (x + 1) * 100
    ax2.plot(x, rate, color=TEAM[0], lw=2)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("%")
    ax2.set_xlabel("Match-Nr.")
    _title(ax2, "Siegquote (kumuliert)")


# ---------------------------------------------------------------- Replay

def plot_replay_heatmap(fig: Figure, rep: dict, idx: int | None, normalize: bool = True,
                        what: str = "player") -> None:
    """Positions-Heatmap aus Replay-Daten (alle Frames)."""
    fig.clear()
    style_fig(fig)
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.84])
    draw_field(ax, labels=not normalize)
    if what == "ball":
        x, y = rep["ball"][:, 0], rep["ball"][:, 1]
        heat_layer(ax, *_to_plot(x, y), HEAT_NEUTRAL, sigma_uu=300)
        _title(ax, "Ball-Heatmap", "Wo sich der Ball das ganze Spiel über aufgehalten hat")
        return
    p = rep["players"][idx]
    pos = p["pos"]
    ok = p["valid"]
    flip = normalize and p["team"] == 1
    heat_layer(ax, *_to_plot(pos[ok, 0], pos[ok, 1], flip), heat_cmap(p["team"]), sigma_uu=300)
    s = p["summary"]
    if normalize:
        ax.text(-A.FIELD_Y + 250, -A.FIELD_X + 200, "← eigenes Tor", color=TEXT_2, fontsize=8)
        ax.text(A.FIELD_Y - 250, -A.FIELD_X + 200, "gegnerisches Tor →", color=TEXT_2, fontsize=8, ha="right")
    _title(ax, f"Positions-Heatmap – {p['name']}",
           f"Defensiv {s['def_pct']:.0f}% · Mitte {s['mid_pct']:.0f}% · Offensiv {s['off_pct']:.0f}% · "
           f"hinter dem Ball {s['behind_ball_pct']:.0f}%")


def plot_replay_compare(fig: Figure, rep: dict) -> None:
    fig.clear()
    style_fig(fig)
    ps = rep["players"]
    labels = [p["name"] for p in ps]
    colors = [TEAM[p["team"]] for p in ps]
    metrics = [("avg_speed", "Ø Tempo (km/h)", "{:.0f}"), ("supersonic_pct", "Überschall (%)", "{:.0f}"),
               ("air_pct", "In der Luft (%)", "{:.0f}"), ("avg_boost", "Ø Boost (0–100)", "{:.0f}"),
               ("zero_boost_pct", "Ohne Boost (%)", "{:.0f}"), ("distance_km", "Strecke (km)", "{:.1f}"),
               ("behind_ball_pct", "Hinter dem Ball (%)", "{:.0f}"), ("avg_dist_ball", "Ø Abstand zum Ball (m)", "{:.0f}"),
               ("off_pct", "Gegn. Drittel (%)", "{:.0f}")]
    gs = fig.add_gridspec(3, 3, hspace=0.75, wspace=0.6, left=0.1, right=0.97, top=0.92, bottom=0.04)
    for i, (f, t, fmt) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        _hbars(ax, labels, [p["summary"].get(f, 0) for p in ps], colors, fmt, t)


# ---------------------------------------------------------------- Hoehe & 3D
import mpl_toolkits.mplot3d  # noqa: E402,F401  (registriert projection="3d"; wichtig fuer den .exe-Build)

HEIGHT_RAMP = LinearSegmentedColormap.from_list("height", ["#7a5c16", "#b8891c", ACCENT, "#fff0c2"])
HEIGHT_COLORS = {"ground": "#a9cdff", "jump": "#6aaeff", "air": "#2f8cff", "high": "#1a4f9a", "wall": "#7d8db0"}


from mpl_toolkits.mplot3d import Axes3D  # noqa: E402
from matplotlib.projections import register_projection  # noqa: E402

ELEV_RANGE = (0.0, 90.0)  # von der Seite (0°) bis senkrecht von oben (90°) – nie von unten


class ArenaAxes3D(Axes3D):
    """3D-Achse, die sich nur seitlich (um die Hochachse) und hoch/runter drehen laesst.

    Kein Kippen/Rollen und kein Blick von unten – die Arena steht immer richtig herum.
    """
    name = "arena3d"

    def view_init(self, elev=None, azim=None, roll=None, **kw):
        if elev is not None:
            elev = min(max(float(elev), ELEV_RANGE[0]), ELEV_RANGE[1])
        return super().view_init(elev=elev, azim=azim, roll=0, **kw)

    def _on_move(self, event):
        # "azel" = einfache Dreh-Steuerung: links/rechts dreht, hoch/runter neigt
        if "axes3d.mouserotationstyle" in matplotlib.rcParams:
            with matplotlib.rc_context({"axes3d.mouserotationstyle": "azel"}):
                return super()._on_move(event)
        return super()._on_move(event)


register_projection(ArenaAxes3D)


def _touch_points(match: dict, keys, normalize: bool):
    players = match["players"]
    keys = keys or list(players)
    pts = []
    for t in match["touches"]:
        if t["player"] in keys and t.get("x") is not None:
            x, y = t["x"], t["y"]
            if normalize and t["team"] == 1:
                x, y = -x, -y
            pts.append((y, x, t["z"], t["player"]))
    return keys, pts


def _arena_3d(ax) -> None:
    fx, fy, c, top = A.FIELD_X, A.FIELD_Y, 1152.0, A.CEILING
    ring = [(-fy + c, -fx), (fy - c, -fx), (fy, -fx + c), (fy, fx - c), (fy - c, fx),
            (-fy + c, fx), (-fy, fx - c), (-fy, -fx + c), (-fy + c, -fx)]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    ax.computed_zorder = False  # feste Zeichenreihenfolge: Boden immer unter den Punkten
    floor = Poly3DCollection([[(x, y, 0) for x, y in ring[:-1]]], facecolor=PITCH, edgecolor="none", alpha=0.85)
    floor.set_zorder(0)
    ax.add_collection3d(floor)
    ax.plot(xs, ys, [0] * len(ring), color=PITCH_LINE, lw=1.4)
    ax.plot(xs, ys, [top] * len(ring), color=LINE, lw=0.8, alpha=0.6)
    for x, y in ring[:-1]:
        ax.plot([x, x], [y, y], [0, top], color=LINE, lw=0.6, alpha=0.45)
    ax.plot([0, 0], [-fx, fx], [0, 0], color=PITCH_LINE, lw=0.9)
    for team, sx in ((0, -1), (1, 1)):  # Tore als Rahmen an den Stirnwaenden
        gx = sx * fy
        g = A.GOAL_HALF_W
        ax.plot([gx, gx, gx, gx], [-g, -g, g, g], [0, A.GOAL_H, A.GOAL_H, 0], color=TEAM[team], lw=2)
    ax.set_xlim(-fy, fy)
    ax.set_ylim(-fx, fx)
    ax.set_zlim(0, top)
    try:
        ax.set_box_aspect((2 * fy, 2 * fx, top * 1.6), zoom=1.02)
    except TypeError:  # aeltere matplotlib-Versionen ohne zoom
        ax.set_box_aspect((2 * fy, 2 * fx, top * 1.6))
    ax.set_axis_off()
    ax.set_facecolor(SURFACE)


def plot_touch_3d(fig: Figure, match: dict, keys, normalize: bool = False, elev: float = 24, azim: float = -62) -> None:
    """Drehbare 3D-Ansicht aller Ballberuehrungen, eingefaerbt nach Hoehe."""
    fig.clear()
    style_fig(fig)
    keys, pts = _touch_points(match, keys, normalize)
    ax = fig.add_axes([0.0, 0.02, 0.9, 0.9], projection="arena3d")
    _arena_3d(ax)
    ax.view_init(elev=elev, azim=azim)
    if pts:
        px = np.array([p[0] for p in pts])
        py = np.array([p[1] for p in pts])
        pz = np.array([p[2] for p in pts])
        for x, y, z in zip(px, py, pz):  # Lot auf den Boden: macht die Hoehe ablesbar
            ax.plot([x, x], [y, y], [0, z], color=TEXT_2, lw=0.5, alpha=0.3, zorder=2)
        ax.scatter(px, py, np.zeros_like(pz), s=5, color=TEXT_2, alpha=0.35, depthshade=False, zorder=2)
        order = np.argsort(pz)  # hohe Punkte zuletzt zeichnen
        sc = ax.scatter(px[order], py[order], pz[order], c=pz[order] / 100.0, cmap=HEIGHT_RAMP, vmin=0,
                        vmax=A.CEILING / 100.0, s=34, edgecolor=SURFACE, linewidth=0.5, depthshade=False, zorder=3)
        cax = fig.add_axes([0.91, 0.18, 0.015, 0.6])
        cb = fig.colorbar(sc, cax=cax)
        cb.set_label("Höhe (m)", color=TEXT_2, fontsize=9)
        cb.ax.tick_params(colors=TEXT_2, labelsize=8)
        cb.outline.set_edgecolor(LINE)
    for g in match.get("goals", []):
        if g.get("x") is None or (keys and g["scorer"] not in keys):
            continue
        x, y = (g["x"], g["y"]) if not (normalize and g["team"] == 1) else (-g["x"], -g["y"])
        ax.scatter([y], [x], [g["z"]], marker="*", s=180, color=TEAM[g["team"]], edgecolor="white",
                   linewidth=0.8, depthshade=False, zorder=4)
    fig.text(0.02, 0.95, "Ballberührungen in 3D", color=TEXT, fontsize=12, fontweight="bold", va="top")
    fig.text(0.02, 0.905, f"{len(pts)} Berührungen · Farbe = Höhe · Maus links/rechts = drehen, hoch/runter = neigen",
             color=MUTED, fontsize=8.5, va="top")


def _heat2d(ax, px, py, xedges, yedges, cmap, sigma_cells=2.5, zorder=2):
    if len(px) == 0:
        return
    h, _, _ = np.histogram2d(px, py, bins=[xedges, yedges])
    h = _gauss_blur(h, sigma_cells)
    if h.max() <= 0:
        return
    im = ax.imshow((h / h.max()).T, origin="lower", extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
                   cmap=cmap, vmin=0, vmax=1, interpolation="bilinear", aspect="auto", zorder=zorder)
    clip = getattr(ax, "_rl_side", None)
    if clip is not None:
        im.set_clip_path(clip)


def _side_frame(ax, labels: bool = True) -> None:
    fy, top = A.FIELD_Y, A.CEILING
    ax.set_facecolor(SURFACE)
    room = Rectangle((-fy, 0), 2 * fy, top, facecolor=PITCH, edgecolor=PITCH_LINE, lw=1.5, zorder=0)
    ax.add_patch(room)
    ax._rl_side = room  # Heatmaps an den Waenden abschneiden
    for team, sx in ((0, -1), (1, 1)):
        ax.add_patch(Rectangle((fy if sx > 0 else -fy - A.GOAL_DEPTH, 0), A.GOAL_DEPTH, A.GOAL_H,
                               facecolor=TEAM[team], alpha=0.25, edgecolor=TEAM[team], lw=1.5, zorder=0))
    for zline in (180, 450, 1300):
        ax.plot([-fy, fy], [zline, zline], color=PITCH_LINE, lw=0.7, ls=(0, (4, 4)), zorder=1)
    if labels:  # Beschriftung mittig in der jeweiligen Zone
        for zmid, name in ((70, "Boden"), (300, "Sprunghöhe"), (860, "Luft"), (1650, "Hoch")):
            ax.text(-fy + 90, zmid, name, color=TEXT_2, fontsize=7.5, va="center", zorder=5)
    ax.plot([0, 0], [0, top], color=PITCH_LINE, lw=1, zorder=1)
    ax.set_xlim(-fy - A.GOAL_DEPTH - 60, fy + A.GOAL_DEPTH + 60)
    ax.set_ylim(0, top + 40)
    ax.set_xticks([])
    yt = [0, 500, 1000, 1500, 2000]
    ax.set_yticks(yt)
    ax.set_yticklabels([f"{v / 100:.0f} m" for v in yt], color=TEXT_2, fontsize=8)
    for s in ax.spines.values():
        s.set_visible(False)


def plot_side_view(fig: Figure, match: dict, keys, normalize: bool = False) -> None:
    """Spielfeld von der Seite: Laenge (Tor zu Tor) gegen Hoehe."""
    fig.clear()
    style_fig(fig)
    keys, pts = _touch_points(match, keys, normalize)
    players = match["players"]
    ax = fig.add_axes([0.07, 0.12, 0.9, 0.74])
    _side_frame(ax)
    if pts:
        px = np.array([p[0] for p in pts])
        pz = np.array([p[2] for p in pts])
        xe = np.arange(-A.FIELD_Y - A.GOAL_DEPTH, A.FIELD_Y + A.GOAL_DEPTH + 100, 100)
        ze = np.arange(0, A.CEILING + 50, 50)
        teams = {players[k]["team"] for k in keys if k in players}
        _heat2d(ax, px, pz, xe, ze, heat_cmap(teams.pop() if len(teams) == 1 else None), sigma_cells=4)
        for i, k in enumerate(keys):
            idx = [j for j, p in enumerate(pts) if p[3] == k]
            if idx:
                ax.scatter(px[idx], pz[idx], s=22, marker=PLAYER_MARKERS[i % len(PLAYER_MARKERS)],
                           color=TEAM[players[k]["team"]], edgecolor=SURFACE, lw=0.7, zorder=4,
                           label=players[k]["name"] if len(keys) > 1 else None)
        if 1 < len(keys) <= 6:
            _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=len(keys))
    left, right = ("eigenes Tor", "gegnerisches Tor") if normalize else ("Blaues Tor", "Oranges Tor")
    ax.text(-A.FIELD_Y, -90, f"← {left}", color=TEXT_2, fontsize=8, va="top")
    ax.text(A.FIELD_Y, -90, f"{right} →", color=TEXT_2, fontsize=8, va="top", ha="right")
    hmax = max((p[2] for p in pts), default=0)
    _title(ax, "Seitenansicht der Ballberührungen",
           f"{len(pts)} Berührungen · höchste in {hmax / 100:.1f} m Höhe · Decke bei {A.CEILING / 100:.1f} m")


def plot_height_breakdown(fig: Figure, match: dict, an: dict) -> None:
    """Wie hoch jeder Spieler den Ball beruehrt (Anteile) und seine hoechste Beruehrung."""
    fig.clear()
    style_fig(fig)
    keys = A.player_order(match)
    ps = an["players"]
    gs = fig.add_gridspec(1, 2, width_ratios=[2.2, 1], wspace=0.35, left=0.13, right=0.97, top=0.84, bottom=0.2)
    ax = fig.add_subplot(gs[0])
    style_ax(ax, grid_axis="x")
    y = np.arange(len(keys))[::-1]
    left = np.zeros(len(keys))
    tot = np.array([max(1, sum(ps[k][f"height_{z}"] for z, _ in A.HEIGHT_ZONES)) for k in keys])
    for z, lbl in A.HEIGHT_ZONES:
        vals = np.array([ps[k][f"height_{z}"] for k in keys]) / tot * 100
        ax.barh(y, vals, left=left, color=HEIGHT_COLORS[z], height=0.6, label=lbl, edgecolor=SURFACE, lw=2)
        for yi, l, v in zip(y, left, vals):
            if v >= 10:
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color=SURFACE if z in ("ground", "jump") else TEXT)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([ps[k]["name"] for k in keys], fontsize=9)
    for lab, k in zip(ax.get_yticklabels(), keys):
        lab.set_color(TEAM[ps[k]["team"]])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% der Ballberührungen")
    _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=5)
    _title(ax, "In welcher Höhe wird der Ball berührt",
           "Boden < 1,8 m · Sprunghöhe < 4,5 m · Luft < 13 m · darüber hoch")
    ax2 = fig.add_subplot(gs[1])
    _hbars(ax2, [ps[k]["name"] for k in keys], [ps[k]["max_touch_height"] for k in keys],
           [TEAM[ps[k]["team"]] for k in keys], "{:.1f} m", "Höchste Berührung")


# ---------------------------------------------------------------- Replay: Hoehe

REPLAY_HEIGHTS = [("hz_ground", "Boden", "#a9cdff"), ("hz_low", "bis 3 m", "#6aaeff"),
                  ("hz_mid", "3–10 m", "#2f8cff"), ("hz_high", "über 10 m", "#1a4f9a"),
                  ("hz_wall", "Wand", "#7d8db0")]


def plot_replay_side(fig: Figure, rep: dict, idx, normalize: bool = True) -> None:
    """Seitenansicht der kompletten Fahr- und Flugwege aus dem Replay."""
    fig.clear()
    style_fig(fig)
    ax = fig.add_axes([0.07, 0.1, 0.9, 0.76])
    _side_frame(ax)
    xe = np.arange(-A.FIELD_Y - A.GOAL_DEPTH, A.FIELD_Y + A.GOAL_DEPTH + 100, 100)
    ze = np.arange(0, A.CEILING + 50, 50)
    if idx in (None, "ball"):
        b = rep["ball"]
        _heat2d(ax, b[:, 1], b[:, 2], xe, ze, HEAT_NEUTRAL, sigma_cells=3)
        _title(ax, "Ball von der Seite", "Wo und wie hoch der Ball das ganze Match über war")
        return
    p = rep["players"][idx]
    pos = p["pos"][p["valid"]]
    y, z = pos[:, 1], pos[:, 2]
    if normalize and p["team"] == 1:
        y = -y
    _heat2d(ax, y, z, xe, ze, heat_cmap(p["team"]), sigma_cells=3)
    s = p["summary"]
    _title(ax, f"Fahr- und Flugwege von der Seite – {p['name']}",
           f"Ø Höhe {s.get('avg_height', 0):.1f} m · höchster Punkt {s.get('max_height', 0):.1f} m · "
           f"{s.get('air_pct', 0):.0f} % der Zeit in der Luft")


def plot_replay_heights(fig: Figure, rep: dict) -> None:
    fig.clear()
    style_fig(fig)
    ps = rep["players"]
    ax = fig.add_axes([0.16, 0.2, 0.8, 0.64])
    style_ax(ax, grid_axis="x")
    y = np.arange(len(ps))[::-1]
    left = np.zeros(len(ps))
    for f, lbl, col in REPLAY_HEIGHTS:
        vals = np.array([p["summary"].get(f, 0) for p in ps])
        ax.barh(y, vals, left=left, color=col, height=0.6, label=lbl, edgecolor=SURFACE, lw=2)
        for yi, l, v in zip(y, left, vals):
            if v >= 8:
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color=SURFACE if f in ("hz_ground", "hz_low") else TEXT)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([p["name"] for p in ps], fontsize=9)
    for lab, p in zip(ax.get_yticklabels(), ps):
        lab.set_color(TEAM[p["team"]])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% der Spielzeit")
    _legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=5)
    _title(ax, "Wie viel Zeit jeder Spieler auf welcher Höhe verbringt", "aus den Replay-Positionen")
