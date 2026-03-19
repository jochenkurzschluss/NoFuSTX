#!/usr/bin/env bash
#
# Script by Michael Herholt DO2ITH, 19.03.2026
#
# Dieses Skript installiert die benötigten Python-Pakete für NoFuSTX.
# Es legt den unterordner "libs" mit lokalen Kopien der Pakete an, damit
# man nicht alles global installieren muss.
#
# Achtung: Einige Pakete (z.B. pyserial) könnten trotzdem Systemabhängigkeiten haben.
# Bitte die Fehlermeldungen genau lesen und ggf. die benötigten Systempakete dazu 
# installieren (z.B. python3-serial, python3-pyaudio, etc. je nach Linux-Distribution).

# Nutzung: Einfach dieses Skript ausführen (bash local_lib.sh) und danach NoFuSTX_1-9-14.py starten.    
PYTHON=python3
LIB_DIR="libs"

echo "=== NoFuSTX Dependency Installer ==="

# 1) Check Python
if ! command -v $PYTHON >/dev/null 2>&1; then
  echo "Fehler: $PYTHON nicht gefunden!"
  exit 1
fi

# 2) Ordner erstellen
mkdir -p "$LIB_DIR"

# 3) Pakete installieren
PACKAGES=(
  tkintermapview Pillow aprslib pyjs8call 
  pyfldigi pyserial pyaudio numpy 
  pysstv requests pyvara
)

echo "Installiere Pakete direkt nach: $LIB_DIR"

for pkg in "${PACKAGES[@]}"; do
  echo "--> Hole $pkg..."
  # --upgrade sorgt dafür, dass du wirklich die neuste Version (1.29+) bekommst
  $PYTHON -m pip install --target="./$LIB_DIR" --upgrade "$pkg"
done

# 4) __init__.py anlegen, damit libs als Package erkannt wird
echo "=== Fertig! NoFuSTX ist nun 'Portable' ==="
touch libs/__init__.py