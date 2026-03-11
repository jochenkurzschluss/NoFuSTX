#!/usr/bin/env bash
set -euo pipefail

echo "=== NoFuSTX Dependency Installer (Linux/macOS) ==="

# 1) Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 nicht gefunden. Bitte installieren (mind. 3.8+)."
  exit 1
fi

PYTHON=python3

# 2) pip check/install
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip nicht gefunden. Versuche pip zu installieren..."
  "$PYTHON" -m ensurepip --upgrade
fi

# 3) optional: Virtualenv
if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
  echo "kein venv-Modul gefunden. Bitte installiere python3-venv (z.B. apt install python3-venv)."
fi

echo "Installiere Python-Pakete..."
"$PYTHON" -m pip install --upgrade pip

# Liste der benötigten Pakete
PACKAGES=(
  requests
  tkintermapview
  pillow
  aprslib
  pyjs8call
  pyfldigi
  pyserial
  numpy
  pyaudio
  pysstv
)

for pkg in "${PACKAGES[@]}"; do
  echo "-> installiere $pkg"
  "$PYTHON" -m pip install "$pkg" || true
done

echo
echo "=== Systemwerkzeuge (optional) ==="
echo "Für APRS/AX.25 wird z.B. 'axlisten' benötigt (normalerweise aus paket 'ax25-apps' via apt/zypper)."
echo "Für Druckfunktion werden 'lpstat'/'lp' benötigt (CUPS)."
echo
echo "Fertig. Starte NoFuSTX mit: python3 NoFuSTX_1-9-14.py"