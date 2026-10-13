"""Kopiert die Lizenztexte aller mitgelieferten Python-Pakete in den App-Ordner.

Pflicht u.a. fuer Qt/PySide6 (LGPLv3). Aufruf: python installer/collect_licenses.py dist/RLTracker/licenses
"""
import re
import shutil
import sys
from importlib import metadata
from pathlib import Path

NAMES = re.compile(r"(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.I)


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    lines = ["Drittanbieter-Software in RL Tracker", "=" * 38, ""]
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "unbekannt"
        if name.lower() in ("pip", "setuptools", "wheel", "pyinstaller", "pyinstaller-hooks-contrib",
                            "altgraph", "pefile", "pywin32-ctypes", "macholib"):
            continue
        lic = dist.metadata.get("License-Expression") or dist.metadata.get("License") or ""
        lic = lic.splitlines()[0][:80] if lic else ""
        if not lic:
            lic = next((c.split("::")[-1].strip() for c in dist.metadata.get_all("Classifier") or []
                        if c.startswith("License ::")), "siehe Lizenzdatei")
        lines.append(f"{name} {dist.version}  –  {lic}")
        copied = 0
        for f in dist.files or []:
            if NAMES.search(Path(str(f)).name):
                src = Path(dist.locate_file(f))
                if src.is_file():
                    dst = out / f"{name}-{Path(str(f)).name}"
                    if dst.exists():
                        dst = out / f"{name}-{copied}-{Path(str(f)).name}"
                    shutil.copyfile(src, dst)
                    copied += 1
        if not copied:
            lines.append("    (keine Lizenzdatei im Paket, Lizenz siehe Projektseite)")
    lines += ["", "Qt for Python (PySide6) wird unter der GNU LGPL v3 verwendet und ist dynamisch eingebunden;",
              "die Qt-Bibliotheken liegen als eigene Dateien im Programmordner und können ersetzt werden.",
              "Quellcode: https://code.qt.io/cgit/pyside/pyside-setup.git/"]
    (out / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"Lizenzen gesammelt: {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "dist/RLTracker/licenses"))
