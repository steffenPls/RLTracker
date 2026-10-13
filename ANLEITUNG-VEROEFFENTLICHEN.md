# RL Tracker veröffentlichen – Schritt für Schritt

Am Ende hast du:
- eine Webseite, die rund um die Uhr online ist: `https://DEINNAME.github.io/rltracker/`
- einen Download-Knopf, der immer die neueste Version liefert
- Updates mit wenigen Klicks; die App deiner Nutzer meldet sich dann von selbst

Alles läuft kostenlos über GitHub (gehört zu Microsoft): die Webseite über **GitHub Pages**, die Setup-Datei
über **GitHub Releases**, das Bauen der Setup-Datei über **GitHub Actions**. Du brauchst keinen eigenen Server.

---

## Einmalig einrichten (ca. 20 Minuten)

### 1. GitHub-Konto anlegen
Auf <https://github.com/signup> registrieren. Dein Benutzername taucht später in der Webadresse auf.

### 2. Zwei Stellen im Projekt anpassen
Ersetze `DEIN-GITHUB-NAME` durch deinen GitHub-Benutzernamen:
- `rltracker/__init__.py` → Zeile `GITHUB_REPO = "DEIN-GITHUB-NAME/rltracker"`
- `docs/index.html` → ganz unten `const REPO = "DEIN-GITHUB-NAME/rltracker";`

Außerdem in `docs/impressum.html` und `docs/datenschutz.html` die gelb markierten Platzhalter ausfüllen
(Name, Anschrift, E-Mail) und die Markierungen entfernen.

### 3. Projekt hochladen mit GitHub Desktop
1. **GitHub Desktop** installieren: <https://desktop.github.com> und mit deinem Konto anmelden.
2. *File → Add local repository* → den Ordner `RLTracker` wählen → *create a repository* klicken
   (Name: `rltracker`) → *Create repository*.
3. Oben *Publish repository* → Haken bei *Keep this code private* **entfernen** (für die kostenlose Webseite
   muss das Projekt öffentlich sein) → *Publish repository*.

Die Ordner `.venv`, `.build-venv`, `dist`, `build` und `Output` werden dabei automatisch weggelassen.

### 4. Webseite einschalten
Auf github.com in deinem Projekt: *Settings → Pages* → bei *Source* „Deploy from a branch“ →
Branch `main`, Ordner `/docs` → *Save*. Nach 1–2 Minuten ist die Seite unter
`https://DEINNAME.github.io/rltracker/` online.

### 5. Erste Version veröffentlichen
Im Projekt rechts auf *Releases* → *Draft a new release*:
- *Choose a tag*: `v1.0.0` eintippen → *Create new tag*
- Titel: `RL Tracker 1.0.0`
- Beschreibung: was neu ist, am besten als Liste mit `- ` am Zeilenanfang (erscheint so auch auf der Webseite)
- *Publish release*

Jetzt baut GitHub die Setup-Datei. Den Fortschritt siehst du unter *Actions* (ca. 5–10 Minuten).
Danach hängt `RLTracker-Setup.exe` am Release, und der Download-Knopf auf deiner Webseite funktioniert.

---

## Ein Update veröffentlichen

1. Änderungen am Code machen (oder von Claude machen lassen und die Dateien in den Ordner kopieren).
2. In GitHub Desktop: unten links kurz beschreiben, was du geändert hast → *Commit to main* → oben *Push origin*.
3. Auf github.com: *Releases* → *Draft a new release* → neue, höhere Versionsnummer als Tag, z. B. `v1.1.0`
   → Änderungen eintragen → *Publish release*.

Das war's. Nach ein paar Minuten
- bekommt jeder Download-Klick auf der Webseite die neue Version,
- zeigt die Webseite unter „Was neu ist“ die neue Versionsnummer und deine Änderungen,
- meldet die App bei deinen Nutzern beim nächsten Start „Version 1.1.0 ist da“ und installiert sie mit einem Klick.

Versionsnummern: bei kleinen Korrekturen die letzte Zahl erhöhen (`1.0.1`), bei neuen Funktionen die mittlere
(`1.1.0`). Die Nummer musst du nur im Release-Tag eintragen – den Rest erledigt der Build.

Nur die Webseite ändern (Texte, Bilder): Dateien in `docs/` ändern → *Commit* → *Push*. Kein Release nötig.

---

## Gut zu wissen

- **Echte Screenshots:** Ersetze die Bilder in `docs/assets/` durch Screenshots aus der echten App, gleiche
  Dateinamen behalten (`live.png`, `heatmap.png`, `torszenen.png`, `replay.png`, `verlauf.png`).
- **Eigene Domain** (z. B. `rltracker.de`, ab ca. 1 € im Monat): unter *Settings → Pages → Custom domain*
  eintragen. Keine Marken wie „Rocket League“ im Domainnamen verwenden.
- **Testbuild ohne Release:** *Actions → Installer bauen → Run workflow*. Die Datei liegt dann beim Lauf
  unter *Artifacts*.
- **Windows-Warnung beim Download** verschwindet erst mit einer Code-Signatur (z. B. Microsoft Trusted Signing).
- Kosten: Für öffentliche Projekte sind Pages, Releases und Actions bei GitHub kostenlos.
