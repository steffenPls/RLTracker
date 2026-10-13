"""Verbindungs-Diagnose: Warum kommen keine Daten von Rocket League an?

Prueft (unter Windows):
  * laeuft RocketLeague.exe, wo ist es installiert, wann wurde es gestartet
  * auf welchen Ports lauscht das Spiel tatsaechlich
  * welche Stats-API-INI-Dateien es gibt und was drinsteht
  * wurde die INI nach dem Spielstart geaendert (=> Neustart noetig)
  * kann man sich auf die erwarteten Ports verbinden
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import ini_setup

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _run(cmd: list[str], timeout: float = 8.0) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=_NO_WINDOW)
        for enc in ("utf-8", "cp850", "cp1252"):
            try:
                return r.stdout.decode(enc)
            except UnicodeDecodeError:
                continue
        return r.stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return ""


def rl_processes() -> list[dict]:
    """Laufende RocketLeague.exe-Prozesse mit Pfad und Startzeit."""
    if sys.platform != "win32":
        return []
    ps = ("Get-Process -Name RocketLeague -ErrorAction SilentlyContinue | ForEach-Object { "
          "\"$($_.Id)|$($_.Path)|$(if ($_.StartTime) { (Get-Date $_.StartTime).ToString('o') })\" }")
    out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps])
    procs = []
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 2 and parts[0].isdigit():
            start = None
            if len(parts) > 2 and parts[2]:
                try:
                    start = datetime.fromisoformat(parts[2][:26].rstrip("Z")).replace(tzinfo=None)
                except ValueError:
                    start = None
            procs.append({"pid": int(parts[0]), "path": parts[1], "start": start})
    if not procs:  # Fallback ohne PowerShell
        out = _run(["tasklist", "/FI", "IMAGENAME eq RocketLeague.exe", "/FO", "CSV", "/NH"])
        for m in re.finditer(r'"RocketLeague\.exe","(\d+)"', out, re.I):
            procs.append({"pid": int(m.group(1)), "path": "", "start": None})
    return procs


def _exe_path_cim(pid: int) -> str:
    ps = f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').ExecutablePath"
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps]).strip()


def listening_ports(pid: int) -> list[tuple[str, int]]:
    """Ports, auf denen der Prozess lauscht (sprachunabhaengig aus netstat)."""
    out = _run(["netstat", "-ano"])
    ports = []
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[-1] == str(pid):
            local, remote = cols[1], cols[2]
            if remote in ("0.0.0.0:0", "[::]:0", "*:*"):
                addr, _, port = local.rpartition(":")
                if port.isdigit():
                    ports.append((addr, int(port)))
    return sorted(set(ports), key=lambda x: x[1])


def install_dir_from_exe(path: str) -> Path | None:
    if not path:
        return None
    p = Path(path)
    for parent in p.parents:
        if (parent / "TAGame" / "Config").is_dir():
            return parent
    parts = [x.lower() for x in p.parts]
    if "binaries" in parts:  # ...\rocketleague\Binaries\Win64\RocketLeague.exe
        return Path(*p.parts[:parts.index("binaries")])
    return None


def can_connect(host: str, port: int) -> str | None:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return None
    except OSError as e:
        return type(e).__name__


def run(settings: dict, client_errors: dict | None = None) -> dict:
    """Fuehrt alle Pruefungen aus. Ergebnis: {'lines': [(level, text)], 'fix_dir', 'port'}."""
    lines: list[tuple[str, str]] = []
    fix_dir: Path | None = None
    found_port: int | None = None
    want_port = int(settings.get("port", 49123))

    def add(level, text):
        lines.append((level, text))

    procs = rl_processes()
    install = None
    if sys.platform != "win32":
        add("info", "Diagnose der Spiel-Prozesse geht nur unter Windows.")
    elif not procs:
        add("bad", "Rocket League läuft gerade nicht. Starte das Spiel und prüfe dann erneut.")
    else:
        pr = procs[0]
        if not pr["path"]:
            pr["path"] = _exe_path_cim(pr["pid"])
        install = install_dir_from_exe(pr["path"])
        add("ok", f"Rocket League läuft (Prozess {pr['pid']})."
            + (f" Installiert in: {install}" if install else ""))
        ports = listening_ports(pr["pid"])
        if ports:
            add("ok", "Das Spiel lauscht auf: " + ", ".join(f"{a}:{p}" for a, p in ports))
            stats_ports = [p for _, p in ports if p in (want_port, 49123, 49124)]
            if stats_ports:
                found_port = stats_ports[0]
            else:
                add("bad", f"Aber nicht auf dem Stats-Port {want_port} → die Stats API ist im laufenden Spiel AUS "
                           "(die anderen Ports gehören zu etwas anderem, z.B. Online-Dienste).")
        else:
            add("bad", "Das Spiel lauscht auf keinem Port → die Stats API ist im laufenden Spiel AUS. "
                       "Entweder steht die Einstellung in der falschen Datei, oder Rocket League wurde vor der "
                       "Änderung gestartet. Bist du in einem Match? (Zum Testen Freeplay starten.)")

    # INI-Dateien prüfen
    dirs = []
    if install:
        dirs.append(install)
    if settings.get("ini_path"):
        d = Path(settings["ini_path"]).parent.parent.parent
        if d not in dirs:
            dirs.append(d)
    for d in ini_setup.candidate_install_dirs():
        if d not in dirs:
            dirs.append(d)
    if not dirs:
        add("bad", "Keinen Rocket-League-Ordner gefunden. Wähle ihn in der Einrichtung manuell.")
    fix_dirs: list[Path] = []
    for d in dirs:
        tag = " (das laufende Spiel)" if install and d == install else ""
        tag += " [Steam]" if "steamapps" in str(d).lower() else (" [Epic]" if "epic" in str(d).lower() else "")
        cfg = d / "TAGame" / "Config"
        any_file = False
        for name in ini_setup.INI_NAMES:
            f = cfg / name
            if not f.exists():
                continue
            any_file = True
            st = ini_setup.read_settings(f)
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if st["PacketSendRate"] > 0:
                add("ok", f"{f}{tag}: aktiv ({st['PacketSendRate']:g}/s, Port {st['Port']}, WebPort {st['WebPort']})")
                if st["Port"] != want_port and st["Port"] > 0:
                    add("warn", f"Die App sucht auf Port {want_port}, die Datei sagt Port {st['Port']}.")
                    found_port = found_port or st["Port"]
            else:
                add("bad", f"{f}{tag}: PacketSendRate ist 0 → Stats API aus.")
                if d not in fix_dirs:
                    fix_dirs.append(d)
            if procs and procs[0]["start"] and mtime > procs[0]["start"] and (not install or d == install):
                add("warn", f"{name} wurde NACH dem Spielstart geändert ({mtime:%H:%M}) → Rocket League komplett "
                            "beenden und neu starten (auch im Epic/Steam-Launcher prüfen, dass es zu ist).")
        if not any_file:
            add("bad", f"{cfg}{tag}: keine Stats-API-INI vorhanden.")
            if d not in fix_dirs:
                fix_dirs.append(d)
    if len(dirs) > 1 and not install:
        add("info", f"{len(dirs)} Rocket-League-Installationen gefunden (z.B. Steam und Epic). "
                    "„Reparieren“ stellt alle ein – egal, welche du startest.")
    # Spiel laeuft, Stats-Port zu -> im Ordner des laufenden Spiels (erneut) schreiben
    if install and procs and found_port is None and install not in fix_dirs:
        fix_dirs.insert(0, install)
    fix_dir = fix_dirs[0] if fix_dirs else None

    # Verbindungsversuche
    for host in ("127.0.0.1", "::1"):
        err = can_connect(host, want_port)
        if err is None:
            add("ok", f"Verbindung zu {host}:{want_port} klappt.")
            found_port = found_port or want_port
        else:
            add("info", f"{host}:{want_port}: {err}")
    for name, err in (client_errors or {}).items():
        add("info", f"Letzter Versuch {name}: {err}")

    if procs and not any(l[0] == "bad" for l in lines) and found_port is None:
        add("warn", "Alles sieht richtig aus, aber es kommen keine Daten. Rocket League öffnet den Port evtl. erst "
                    "in einem Match – starte zum Testen ein Freeplay.")
    return {"lines": lines, "fix_dir": fix_dir, "fix_dirs": fix_dirs, "port": found_port,
            "rl_running": bool(procs), "install": install}
