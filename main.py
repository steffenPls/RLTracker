"""Startpunkt der App: python main.py

Faengt jeden Startfehler ab, schreibt ihn nach crash.log (neben dieser Datei)
und zeigt ihn in einem Fenster an – statt sich einfach still zu beenden.
"""
import os
import sys
import traceback
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
HERE = Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent
# Installiert (Program Files) darf die App dort nicht schreiben -> Logs nach %LOCALAPPDATA%\RL Tracker
LOGDIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RL Tracker" if FROZEN else HERE
LOG = LOGDIR / "crash.log"


def _show_error(text: str) -> None:
    try:
        LOGDIR.mkdir(parents=True, exist_ok=True)
        LOG.write_text(text, encoding="utf-8")
    except OSError:
        pass
    msg = ("RL Tracker konnte nicht starten.\n\n" + text[-1500:] +
           f"\n\nDer Fehler steht auch in:\n{LOG}\nSchick ihn mir einfach.")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "RL Tracker – Fehler", 0x10)
            return
        except Exception:
            pass
    print(msg, file=sys.__stderr__ or sys.stdout)


def _setup_logging() -> None:
    try:
        LOGDIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    # pythonw hat keine Konsole: Ausgaben und Fehler in eine Logdatei umleiten
    if sys.stdout is None or sys.stderr is None:
        try:
            f = open(LOGDIR / "app.log", "w", encoding="utf-8", buffering=1)
            sys.stdout = sys.stdout or f
            sys.stderr = sys.stderr or f
        except OSError:
            pass
    try:
        import faulthandler
        faulthandler.enable(open(LOGDIR / "fault.log", "w"))
    except Exception:
        pass

    def hook(exc_type, exc, tb):  # Fehler in Knopf-Klicks etc. protokollieren statt abzustuerzen
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(LOGDIR / "app.log", "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError:
            pass
        print(text, file=sys.stderr)
    sys.excepthook = hook


if __name__ == "__main__":
    if any(a in sys.argv for a in ("--ini-enable", "--grant-access", "--revoke-access")):
        # Hilfsaufrufe ohne Fenster (Installer/Deinstallation bzw. mit Adminrechten)
        from rltracker.ini_setup import cli
        sys.exit(cli(sys.argv))
    os.chdir(HERE)
    _setup_logging()
    try:
        from rltracker.app import main
        main()
    except SystemExit:
        raise
    except BaseException:
        _show_error(traceback.format_exc())
        sys.exit(1)
