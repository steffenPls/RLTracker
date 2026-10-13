"""Findet die Rocket-League-Installation und aktiviert die Stats API in der INI-Datei.

Laut offizieller Doku: <Installationsordner>\\TAGame\\Config\\TAStatsAPI.ini
(oder DefaultStatsAPI.ini, falls die erste nicht existiert), Abschnitt
[TAGame.MatchStatsExporter_TA], Schluessel PacketSendRate (>0 = an, max. 120) und Port.
Aenderungen wirken erst nach einem Neustart von Rocket League.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import string
import sys
from pathlib import Path

SECTION = "TAGame.MatchStatsExporter_TA"
INI_NAMES = ("TAStatsAPI.ini", "DefaultStatsAPI.ini")


def _epic_installs() -> list[Path]:
    out = []
    pd = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    for f in glob.glob(os.path.join(pd, "Epic", "EpicGamesLauncher", "Data", "Manifests", "*.item")):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8", errors="ignore"))
            if "rocket" in (d.get("DisplayName", "") + d.get("AppName", "")).lower() or \
                    "sugar" in d.get("AppName", "").lower():
                out.append(Path(d["InstallLocation"]))
        except (OSError, ValueError, KeyError):
            pass
    return out


def _steam_installs() -> list[Path]:
    roots = [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam",
             Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Steam",
             Path.home() / ".steam" / "steam", Path.home() / ".local" / "share" / "Steam"]
    libs = []
    for r in roots:
        vdf = r / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            libs.append(r)
            try:
                for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
                    libs.append(Path(m.group(1).replace("\\\\", "\\")))
            except OSError:
                pass
    return [lib / "steamapps" / "common" / "rocketleague" for lib in libs]


def candidate_install_dirs() -> list[Path]:
    c = _epic_installs() + _steam_installs()
    if sys.platform == "win32":
        for drive in string.ascii_uppercase[2:8]:
            for sub in (r"Program Files\Epic Games\rocketleague", r"Epic Games\rocketleague",
                        r"Games\Epic Games\rocketleague", r"SteamLibrary\steamapps\common\rocketleague",
                        r"Program Files (x86)\Steam\steamapps\common\rocketleague"):
                c.append(Path(f"{drive}:\\") / sub)
    seen, out = set(), []
    for p in c:
        key = str(p).lower()
        if key not in seen and (p / "TAGame" / "Config").is_dir():
            seen.add(key)
            out.append(p)
    return out


def ini_for_install(install_dir: Path) -> Path:
    cfg = Path(install_dir) / "TAGame" / "Config"
    for n in INI_NAMES:
        if (cfg / n).exists():
            return cfg / n
    return cfg / INI_NAMES[1]


def find_ini() -> Path | None:
    for d in candidate_install_dirs():
        return ini_for_install(d)
    return None


def read_settings(ini: Path) -> dict:
    """Liest PacketSendRate/Port/WebPort aus dem Exporter-Abschnitt."""
    out = {"PacketSendRate": 0.0, "Port": 49123, "WebPort": 49124, "exists": False}
    try:
        text = Path(ini).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    out["exists"] = True
    sec = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1]
            continue
        if sec == SECTION and "=" in s and not s.startswith(";"):
            k, v = (x.strip() for x in s.split("=", 1))
            if k in ("PacketSendRate",):
                try:
                    out[k] = float(v)
                except ValueError:
                    pass
            elif k in ("Port", "WebPort"):
                try:
                    out[k] = int(float(v))
                except ValueError:
                    pass
    return out


def enable(ini: Path, rate: float = 30.0, port: int = 49123) -> str:
    """Setzt PacketSendRate/Port. Legt vorher eine .bak-Sicherung an."""
    ini = Path(ini)
    rate = max(1.0, min(120.0, float(rate)))
    text = ini.read_text(encoding="utf-8", errors="ignore") if ini.exists() else ""
    if ini.exists() and not ini.with_suffix(ini.suffix + ".bak").exists():
        shutil.copy2(ini, ini.with_suffix(ini.suffix + ".bak"))
    values = {"PacketSendRate": f"{rate:g}", "Port": str(port)}
    lines = text.splitlines()
    out, sec, in_target, found_sec, done = [], None, False, False, set()
    for line in lines:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if in_target:
                out.extend(f"{k}={v}" for k, v in values.items() if k not in done)
                done.update(values)
            sec = s[1:-1]
            in_target = sec == SECTION
            found_sec = found_sec or in_target
            out.append(line)
            continue
        if in_target and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in values:
                out.append(f"{k}={values[k]}")
                done.add(k)
                continue
        out.append(line)
    if in_target:
        out.extend(f"{k}={v}" for k, v in values.items() if k not in done)
    if not found_sec:
        if out and out[-1].strip():
            out.append("")
        out.append(f"[{SECTION}]")
        out.extend(f"{k}={v}" for k, v in values.items())
    ini.parent.mkdir(parents=True, exist_ok=True)
    ini.write_text("\r\n".join(out) + "\r\n", encoding="utf-8")
    return str(ini)


def enable_install(install_dir: Path, rate: float = 30.0, port: int = 49123) -> list[str]:
    """Aktiviert die API in ALLEN vorhandenen Stats-INIs eines Installationsordners.

    Rocket League liest TAStatsAPI.ini, falls vorhanden, sonst DefaultStatsAPI.ini.
    Damit es egal ist, welche das Spiel nimmt, werden beide angepasst.
    """
    cfg = Path(install_dir) / "TAGame" / "Config"
    targets = [cfg / n for n in INI_NAMES if (cfg / n).exists()] or [cfg / INI_NAMES[1]]
    return [enable(t, rate, port) for t in targets]


def elevate_enable(install_dir: Path, rate: float = 30.0, port: int = 49123) -> bool:
    """Schreibt die INI mit Administratorrechten (Windows-UAC-Abfrage).

    Noetig, wenn Rocket League unter C:\\Program Files liegt. Startet die App kurz
    erneut mit --ini-enable; main.py erledigt das und beendet sich sofort.
    """
    if sys.platform != "win32":
        return False
    import ctypes
    args = f'--ini-enable "{install_dir}" {rate:g} {int(port)}'
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, args
    else:
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        exe, params = sys.executable, f'"{main_py}" {args}'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, str(Path(exe).parent), 0)
    return rc > 32


def disable_install(install_dir: Path) -> list[str]:
    """Schaltet die Stats API wieder aus (PacketSendRate=0) – andere Einstellungen bleiben."""
    cfg = Path(install_dir) / "TAGame" / "Config"
    done = []
    for n in INI_NAMES:
        f = cfg / n
        if f.exists() and read_settings(f)["PacketSendRate"] > 0:
            text = f.read_text(encoding="utf-8", errors="ignore")
            text = re.sub(r"(?im)^(\s*PacketSendRate\s*=\s*).*$", r"\g<1>0", text)
            f.write_text(text, encoding="utf-8")
            done.append(str(f))
    return done


def _log(line: str) -> None:
    """Protokoll fuer Installer-Aufrufe (ohne Fenster), z.B. C:\\ProgramData\\RL Tracker\\setup.log"""
    try:
        d = Path(os.environ.get("PROGRAMDATA", Path.home())) / "RL Tracker"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "setup.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def cli(argv: list[str]) -> int:
    """Hilfsaufrufe ohne Oberflaeche (vom Installer bzw. mit Adminrechten):

    --ini-enable <Ordner> <Rate> <Port>   Stats API in einem Ordner einschalten
    --grant-access                         in allen gefundenen Installationen einschalten (Installer)
    --revoke-access                        in allen wieder ausschalten (Deinstallation)
    """
    try:
        if "--ini-enable" in argv:
            i = argv.index("--ini-enable")
            enable_install(Path(argv[i + 1]), float(argv[i + 2]), int(argv[i + 3]))
            return 0
        if "--grant-access" in argv:
            dirs = candidate_install_dirs()
            _log(f"grant-access: {len(dirs)} Installation(en) gefunden")
            for d in dirs:
                for f in enable_install(d, 30, 49123):
                    _log(f"  aktiviert: {f}")
            return 0
        if "--revoke-access" in argv:
            for d in candidate_install_dirs():
                for f in disable_install(d):
                    _log(f"  deaktiviert: {f}")
            return 0
    except Exception as e:
        _log(f"Fehler: {type(e).__name__}: {e}")
        return 1
    return 2


CLI_FLAGS = ("--ini-enable", "--grant-access", "--revoke-access")
