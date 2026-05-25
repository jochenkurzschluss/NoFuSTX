#!/usr/bin/env bash
set -euo pipefail

# Script by Michael Herholt DO2ITH, 16.04.2026
# Dieses Skript installiert die NoFuSTX-Abhängigkeiten in einen lokalen "libs"-Ordner.
# Dadurch kann NoFuSTX portabel gestartet werden, ohne alle Pakete global zu installieren.
#
# Hinweis: Einige Pakete benötigen zusätzlich Systemabhängigkeiten (z.B. portaudio für pyaudio).
# Bitte bei Bedarf die Fehlermeldungen lesen und die entsprechenden OS-Pakete nachinstallieren.

PYTHON=${PYTHON:-python3}
LIB_DIR="libs"

PACKAGES=(
  # GUI & Benutzeroberfläche
  tkintermapview
  tkterminal
  customtkinter
  Pillow
  
  # Funk-Modi & Schnittstellen
  aprslib
  pyjs8call
  pyfldigi
  pyserial
  pyvara
  
  # Audio & Signal
  pyaudio
  numpy
  pysstv
  
  # Netzwerk
  requests
  
  # Datenverarbeitung
  PyMuPDF
  PyHam_AX25
  
  # LoRa Mesh
  meshtastic
  pubsub
  
  # Grafiken & Plots
  matplotlib
  contourpy
  kiwisolver
  cycler
  fontTools
  
  # Sonstige
  codext
  markdown2
  protobuf
  psutil
  packaging
  darkdetect
  click
  charset_normalizer
  idna
  certifi
  dateutil
  geocoder
)

echo "=== NoFuSTX Portable Dependency Installer ==="

echo "Benutze Python: $PYTHON"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Fehler: $PYTHON nicht gefunden!"
  exit 1
fi

mkdir -p "$LIB_DIR"

if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip nicht gefunden. Versuche, pip zu installieren..."
  "$PYTHON" -m ensurepip --upgrade
fi

for pkg in "${PACKAGES[@]}"; do
  echo "--> installiere $pkg in $LIB_DIR"
  "$PYTHON" -m pip install --upgrade --target="$LIB_DIR" "$pkg"
done

# __init__.py anlegen, damit libs als Package erkannt wird
mkdir -p "$LIB_DIR"
touch "$LIB_DIR/__init__.py"

echo "=== Fertig! Nutze NoFuSTX mit lokalem libs-Ordner. ==="
echo "Starte: $PYTHON main.py"