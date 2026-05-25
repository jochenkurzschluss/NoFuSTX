@echo off
setlocal enabledelayedexpansion

echo === NoFuSTX Dependency Installer (Windows) ===

REM Python prüfen
where python >nul 2>&1
if errorlevel 1 (
  echo Python nicht gefunden. Bitte Python3 installieren und in PATH aufnehmen.
  exit /b 1
)

echo Prüfe pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
  echo pip nicht gefunden. Versuche, pip zu installieren...
  python -m ensurepip --upgrade
)

echo Upgrade pip...
python -m pip install --upgrade pip

echo Installiere Python-Abhängigkeiten...
if exist requirements.txt (
  python -m pip install -r requirements.txt
) else (
  echo requirements.txt nicht gefunden. Installiere Standardpakete...
  python -m pip install tkintermapview tkterminal customtkinter Pillow aprslib pyjs8call pyfldigi pyserial pyaudio numpy pysstv requests pyvara PyMuPDF PyHam_AX25 meshtastic pubsub matplotlib contourpy kiwisolver cycler fontTools codext markdown2 protobuf psutil packaging darkdetect click charset_normalizer idna certifi dateutil geocoder
)

echo.
echo === Systemhinweise ===
echo - tkinter ist Teil der Standardbibliothek, aber muss bei Windows eventuell durch das Python-Installationsprogramm aktiviert werden.
echo - PyAudio benötigt ggf. Microsoft Visual C++ Build Tools oder eine vorgefertigte Wheel-Datei.
echo.
echo Fertig. Starte NoFuSTX mit: python main.py