@echo off
rem Startet die App MIT sichtbarem Fenster fuer Fehlermeldungen.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Die App ist in diesem Ordner noch nicht eingerichtet. Bitte zuerst start.bat ausfuehren.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
echo.
echo ---- Die App wurde beendet. Wenn oben ein Fehler steht: Screenshot an Claude schicken. ----
pause
