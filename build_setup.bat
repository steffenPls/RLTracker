@echo off
rem ==========================================================================
rem  Baut den fertigen Installer:  Output\RLTracker-Setup.exe  (Testbuild auf deinem PC;
rem  zum Veroeffentlichen besser ein GitHub-Release anlegen, siehe ANLEITUNG-VEROEFFENTLICHEN.md)
rem  Diese eine Datei kannst du weitergeben / zum Download anbieten.
rem ==========================================================================
setlocal
cd /d "%~dp0"
title RL Tracker - Installer bauen

rem --- 1. Python 3.12 (die Replay-Bibliothek gibt es fuer Windows nur dafuer) ---
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 fehlt. Bitte installieren: "Python 3.12.x - Windows installer (64-bit)"
  start "" "https://www.python.org/downloads/windows/"
  pause
  exit /b 1
)

rem --- 2. Eigene, saubere Build-Umgebung ---
if not exist ".build-venv\Scripts\python.exe" (
  echo [1/5] Lege Build-Umgebung an ...
  py -3.12 -m venv .build-venv || goto :fail
)
set PYB=.build-venv\Scripts\python.exe
echo [2/5] Installiere Pakete ...
%PYB% -m pip install --upgrade pip >nul
%PYB% -m pip install --upgrade PySide6 matplotlib numpy subtr-actor-py pyinstaller || goto :fail

rem --- 3. App bauen ---
for /f %%V in ('%PYB% installer\prepare_version.py') do set VERSION=%%V
echo [3/5] Baue die App, Version %VERSION% (1-3 Minuten) ...
%PYB% -m PyInstaller --noconfirm --clean --windowed --name RLTracker --icon icon.ico ^
  --version-file installer\version_info.generated.txt --collect-all subtr_actor --hidden-import mpl_toolkits.mplot3d ^
  --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore ^
  main.py || goto :fail
%PYB% installer\collect_licenses.py dist\RLTracker\licenses || goto :fail

rem --- 4. Inno Setup suchen (bei Bedarf automatisch installieren) ---
echo [4/5] Suche Inno Setup ...
call :find_iscc
if not defined ISCC (
  echo Inno Setup fehlt - installiere es ueber winget ...
  winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
  call :find_iscc
)
if not defined ISCC (
  echo Inno Setup konnte nicht installiert werden. Bitte von https://jrsoftware.org/isdl.php installieren
  echo und diese Datei erneut starten.
  start "" "https://jrsoftware.org/isdl.php"
  pause
  exit /b 1
)

rem --- 5. Installer bauen ---
echo [5/5] Baue den Installer ...
"%ISCC%" /Q "/DAppVersion=%VERSION%" installer\setup.iss || goto :fail

echo.
echo  ===================================================================
echo   Fertig!  Output\RLTracker-Setup.exe  (Version %VERSION%)
echo   Diese Datei kannst du weitergeben oder zum Download anbieten.
echo  ===================================================================
start "" "%~dp0Output"
pause
exit /b 0

:find_iscc
set ISCC=
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
  if exist %%P set ISCC=%%~P
)
exit /b 0

:fail
echo.
echo Build fehlgeschlagen - bitte Screenshot von diesem Fenster an Claude schicken.
pause
exit /b 1
