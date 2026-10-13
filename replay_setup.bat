@echo off
rem Richtet die Replay-Analyse ein (Bibliothek subtr-actor-py, gibt es fuer Windows nur fuer Python 3.12).
setlocal
cd /d "%~dp0"
title RL Tracker - Replay-Analyse einrichten
echo.
echo  Replay-Analyse fuer RL Tracker einrichten
echo  =========================================
echo.

rem Der App etwas Zeit geben, sich zu schliessen (falls aus der App gestartet)
timeout /t 3 /nobreak >nul

rem --- Python 3.12 vorhanden? ---
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo  Python 3.12 ist nicht installiert - die Replay-Bibliothek gibt es nur fuer diese Version.
  echo.
  echo  1. Gleich oeffnet sich die Python-Downloadseite.
  echo  2. Dort "Python 3.12.x" -^> "Windows installer (64-bit)" herunterladen und installieren.
  echo     Deine andere Python-Version kann bleiben, beide vertragen sich.
  echo  3. Danach diese Datei ^(replay_setup.bat^) noch einmal doppelklicken.
  echo.
  pause
  start "" "https://www.python.org/downloads/windows/"
  exit /b 1
)

rem --- Laeuft die App-Umgebung schon mit 3.12? Sonst neu anlegen ---
set REBUILD=1
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1 && set REBUILD=0
)
if "%REBUILD%"=="1" (
  echo  Stelle die App auf Python 3.12 um ^(deine Matches bleiben erhalten^) ...
  if exist ".venv" rmdir /s /q ".venv"
  if exist ".venv" (
    echo  Der Ordner .venv ist noch in Benutzung. Bitte die App schliessen und erneut starten.
    pause
    exit /b 1
  )
  py -3.12 -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install PySide6 matplotlib numpy || goto :fail
)

echo  Installiere die Replay-Bibliothek ...
".venv\Scripts\python.exe" -m pip install --upgrade subtr-actor-py || goto :fail
".venv\Scripts\python.exe" -c "import subtr_actor" || goto :fail

echo.
echo  Fertig! Die Replay-Analyse ist eingerichtet. Die App startet jetzt.
timeout /t 3 >nul
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fail
echo.
echo  Das hat nicht geklappt - bitte einen Screenshot von diesem Fenster an Claude schicken.
pause
exit /b 1
