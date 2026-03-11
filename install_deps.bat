@echo off
setlocal enabledelayedexpansion

echo === NoFuSTX Dependency Installer (Windows) ===

REM Python prüfen
where python >nul 2>&1
if errorlevel 1 (
  echo Python nicht gefunden. Bitte Python3 installieren und in PATH aufnehmen.
  exit /b 1
)

python -m pip --version >nul 2>&1
if errorlevel 1 (
  echo pip nicht gefunden. Versuche, pip zu installieren...
  python -m ensurepip --upgrade
)

echo Upgrade pip...
python -m pip install --upgrade pip

echo Installiere Python-Pakete...
set PACKAGES=requests tkintermapview pillow aprslib pyjs8call pyfldigi pyserial numpy pyaudio pysstv
for %%P in (%PACKAGES%) do (
  echo -> installiere %%P
  python -m pip install %%P
)

echo.
echo Fertig. Starte NoFuSTX mit: python NoFuSTX_1-9-14.py