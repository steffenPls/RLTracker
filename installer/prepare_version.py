"""Eine Versionsnummer fuer alles.

  python installer/prepare_version.py 1.2.0   -> setzt die Version (z.B. aus dem GitHub-Release-Tag)
  python installer/prepare_version.py         -> nimmt die Version aus rltracker/__init__.py

Schreibt danach installer/version_info.generated.txt (Datei-Infos der .exe) und gibt die Version aus.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT = ROOT / "rltracker" / "__init__.py"
TEMPLATE = ROOT / "installer" / "version_info.txt"
OUT = ROOT / "installer" / "version_info.generated.txt"


def main() -> None:
    text = INIT.read_text(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1].strip():
        version = sys.argv[1].strip().lstrip("vV")
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            sys.exit(f"Ungueltige Version '{sys.argv[1]}' – erwartet z.B. v1.2.0")
        text = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', text)
        INIT.write_text(text, encoding="utf-8")
    version = re.search(r'__version__ = "([^"]+)"', text).group(1)
    nums = ", ".join(version.split(".") + ["0"])
    tpl = TEMPLATE.read_text(encoding="utf-8")
    tpl = re.sub(r"filevers=\([^)]*\)", f"filevers=({nums})", tpl)
    tpl = re.sub(r"prodvers=\([^)]*\)", f"prodvers=({nums})", tpl)
    tpl = re.sub(r"(StringStruct\('(?:File|Product)Version', ')[^']*'", rf"\g<1>{version}'", tpl)
    OUT.write_text(tpl, encoding="utf-8")
    print(version)


if __name__ == "__main__":
    main()
