@echo off
setlocal enabledelayedexpansion

:: NoFuSTX Dependency Installer für Windows (USB-Portable Edition)
:: Script by Michael Herholt DO2ITH, 19.03.2026

:: Dieses Skript installiert die benötigten Python-Pakete für NoFuSTX.
:: Es legt den unterordner "libs" mit lokalen Kopien der Pakete an, damit
:: man nicht alles global installieren muss.
::
:: Achtung: Einige Pakete (z.B. pyserial) könnten trotzdem Systemabhängigkeiten haben.
:: Bitte die Fehlermeldungen genau lesen und ggf. die benötigten Systempakete dazu 
:: installieren (z.B. python3-serial, python3-pyaudio, etc. je nach Linux-Distribution).

:: Nutzung: Einfach dieses Skript ausführen (bash local_lib.sh) und danach NoFuSTX_1-9-14.py starten.

echo ==================================================
echo   NoFuSTX Dependency Installer (Windows)
echo ==================================================

:: 1) Check ob Python installiert ist
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FEHLER] Python wurde nicht gefunden! 
    echo Bitte installiere Python von python.org und aktiviere 
    echo die Option 'Add Python to PATH' im Installer.
    echo.
    pause
    exit /b
)

:: 2) Ordner erstellen
set LIB_DIR=libs
if not exist %LIB_DIR% (
    mkdir %LIB_DIR%
    echo [*] Ordner '%LIB_DIR%' wurde erstellt.
)

:: 3) Standard-Pakete (unkritisch)
set PACKAGES=tkintermapview Pillow aprslib pyjs8call pyfldigi pyserial numpy pysstv requests pyvara

echo [*] Installiere Standard-Pakete nach: %LIB_DIR%
for %%p in (%PACKAGES%) do (
    echo --^> Installiere %%p...
    python -m pip install --target=".\%LIB_DIR%" --upgrade %%p
)

:: 4) Spezieller Check für PyAudio (Kritisch unter Windows)
echo.
echo [*] Installiere PyAudio (Soundkarten-Schnittstelle)...
python -m pip install --target=".\%LIB_DIR%" --upgrade pyaudio
if %errorlevel% neq 0 (
    echo.
    echo [WARNUNG] PyAudio konnte nicht automatisch installiert werden.
    echo Dies liegt meist an fehlenden C++ Build Tools unter Windows.
    echo.
    echo LOESUNG: 
    echo 1. Oeffne eine Eingabeaufforderung (CMD)
    echo 2. Tippe: pip install pipwin
    echo 3. Tippe: pipwin install pyaudio
    echo Danach kopiere die pyaudio-Ordner manuell in den 'libs' Ordner.
    echo Details dazu findest du in der README.md!
    echo.
) else (
    echo [OK] PyAudio erfolgreich installiert.
)

:: 5) __init__.py anlegen
echo. > %LIB_DIR%\__init__.py

echo ==================================================
echo   Fertig! NoFuSTX ist nun einsatzbereit.
echo ==================================================
pause