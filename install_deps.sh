#!/usr/bin/env bash
set -euo pipefail

echo "=== NoFuSTX Dependency Installer (Linux/macOS) ==="

PYTHON=python3
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python3 nicht gefunden. Bitte installieren (mindestens Python 3.8+)."
  exit 1
fi

if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip nicht gefunden. Versuche, pip zu installieren..."
  "$PYTHON" -m ensurepip --upgrade
fi

if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
  echo "Das venv-Modul ist nicht verfügbar. Bitte installiere python3-venv."
fi

echo "Aktualisiere pip..."
"$PYTHON" -m pip install --upgrade pip

echo "Installiere Python-Abhängigkeiten..."
if [ -f requirements.txt ]; then
  "$PYTHON" -m pip install -r requirements.txt
else
  echo "requirements.txt nicht gefunden. Installiere Standardpakete..."
  "$PYTHON" -m pip install \
    tkintermapview tkterminal customtkinter Pillow aprslib pyjs8call pyfldigi pyserial pyaudio numpy pysstv requests pyvara PyMuPDF PyHam_AX25 meshtastic pubsub matplotlib contourpy kiwisolver cycler fontTools codext markdown2 protobuf psutil packaging darkdetect click charset_normalizer idna certifi dateutil geocoder
fi

echo
 echo "=== Systemwerkzeuge (optional) ==="
echo "Für APRS/AX.25 wird z.B. 'axlisten' benötigt (normalerweise aus Paket 'ax25-apps')."
echo "Für Druckfunktionen sind 'lpstat' / 'lp' (CUPS) hilfreich."
echo
 echo "Fertig. Starte NoFuSTX mit: $PYTHON main.py"