@echo off
setlocal
cd /d "%~dp0"
title RL Tracker

rem --- Python finden (3.12 bevorzugt, wegen der Replay-Bibliothek) ---
set PY=
py -3.12 --version >nul 2>&1 && set PY=py -3.12
if not defined PY ( py -3 --version >nul 2>&1 && set PY=py -3 )
if not defined PY ( python --version >nul 2>&1 && set PY=python )
if not defined PY (
  echo Python wurde nicht gefunden.
  echo Bitte Python 3.12 installieren: https://www.python.org/downloads/
  echo Beim Installieren "Add python.exe to PATH" anhaken.
  pause
  exit /b 1
)

rem --- Beim ersten Start: eigene Umgebung anlegen und Pakete installieren ---
if not exist ".venv\Scripts\python.exe" (
  echo Erster Start: richte die App ein, das dauert 1-2 Minuten ...
  %PY% -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install PySide6 matplotlib numpy || goto :fail
  ".venv\Scripts\python.exe" -m pip install subtr-actor-py || echo Hinweis: Replay-Analyse noch nicht verfuegbar ^(braucht Python 3.12 - dafuer spaeter replay_setup.bat starten^). Der Live-Tracker funktioniert trotzdem.
)

rem --- Pruefen, ob die Umgebung intakt ist (z.B. nach Verschieben des Ordners) ---
".venv\Scripts\python.exe" -c "import PySide6, matplotlib, numpy" >nul 2>&1
if errorlevel 1 (
  echo Pakete fehlen oder sind beschaedigt - installiere neu ...
  ".venv\Scripts\python.exe" -m pip install PySide6 matplotlib numpy || goto :fail
)

del /q crash.log >nul 2>&1
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fail
echo.
echo Installation fehlgeschlagen. Siehe Meldungen oben.
pause
exit /b 1
