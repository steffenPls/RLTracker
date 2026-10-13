# RL Tracker

Inoffizielle Fan-App für Windows: zeichnet deine Rocket-League-Matches live auf und zeigt danach
Statistiken, Heatmaps und Diagramme. Kostenlos, ohne Konto, alle Daten bleiben auf deinem PC.

> Nicht mit Psyonix, Epic Games oder Valve verbunden.
> Portions of the materials used are trademarks and/or copyrighted works of Epic Games, Inc.
> All rights reserved by Epic. This material is not official and is not endorsed by Epic.

## Für Nutzer

1. `RLTracker-Setup.exe` von der Webseite herunterladen und starten.
2. Den Hinweisen folgen. Auf der Seite **„Zugriff auf Rocket League“** auswählen, ob die App die
   Stats-Schnittstelle des Spiels einschalten darf (empfohlen).
3. Rocket League (neu) starten, in ein Match oder ins Freeplay gehen. Fertig.

Deinstallieren: Windows-Einstellungen → Apps → RL Tracker. Dabei wird die Stats-Schnittstelle wieder
ausgeschaltet. Deine gespeicherten Matches in `Dokumente\RLTracker` bleiben erhalten.

## Veröffentlichen und Updates

Schritt für Schritt in **[ANLEITUNG-VEROEFFENTLICHEN.md](ANLEITUNG-VEROEFFENTLICHEN.md)**: Webseite (GitHub Pages,
Ordner `docs/`), Setup-Datei (GitHub Releases, wird automatisch gebaut) und wie du Updates live stellst.

Testbuild auf dem eigenen PC: `build_setup.bat` (braucht Python 3.12) → `Output\RLTracker-Setup.exe`.

### Windows-Warnung „Der Computer wurde durch Windows geschützt“

Kommt bei jeder neuen, nicht signierten Software. Wegbekommen nur mit Code-Signierung, z. B. über
Microsoft *Trusted Signing* (günstigste Variante, monatliches Abo) oder ein klassisches Code-Signing-Zertifikat.
Bis dahin: *Weitere Informationen* → *Trotzdem ausführen*.

## Was die App kann

- **Live:** Anzeigetafel, Werte aller Spieler, Ticker, Live-Karte der Ballkontakte
- **Auswertung** nach jedem Match: Statistik-Tabelle, Teamvergleich, Heatmaps, Torszenen, Boost-Karte,
  Spielverlauf, Spieler-Details, Schussstärke, Positionsspiel, Bewegung, Export als PNG/CSV
- **Verlauf:** alle Matches, Siegquote und Entwicklung
- **Replays:** komplette Laufweg-Heatmap aller Spieler aus gespeicherten Replays
- **Demo:** ein simuliertes Match zum Ausprobieren ohne Spiel

## Für Entwickler

- `start.bat` startet die App aus dem Quellcode (legt `.venv` an), `debug.bat` mit Konsole.
- Code: `statsapi.py` (Verbindung) → `recorder.py` (Aufzeichnung) → `analysis.py` (Statistiken) →
  `plots.py` (Diagramme); Oberfläche in `app.py`, `match_view.py`, `widgets.py`; Replays in `replay.py`.
- Hilfsaufrufe ohne Fenster: `RLTracker.exe --grant-access` / `--revoke-access` (nutzt der Installer).
