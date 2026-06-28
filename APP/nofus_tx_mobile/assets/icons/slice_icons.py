import os
from PIL import Image

# Konfiguration
SOURCE_FILES = [
    {"file": "Primary Symbol Table.gif", "table_char": "/"},
    {"file": "Secondary Symbol Table.gif", "table_char": "\\"}
]
OUTPUT_DIR = "./icons"

# --- JUSTIERUNG ---
# Falls die Icons immer noch verschoben sind, ändere diese Werte:
ICON_W = 18  # Breite eines Icons
ICON_H = 18  # Höhe eines Icons
STEP_X = 19  # Abstand von Icon-Start zu Icon-Start (Icon + Gitterlinie)
STEP_Y = 19  # Abstand vertikal
OFFSET_X = 2 # Start-Pixel links (um den ersten Rahmen zu überspringen)
OFFSET_Y = 2 # Start-Pixel oben
# ------------------

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_hex_name(table_char, symbol_char):
    t_hex = hex(ord(table_char))[2:]
    s_hex = hex(ord(symbol_char))[2:]
    return f"aprs_{t_hex}_{s_hex}.png"

CHARS = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"

for entry in SOURCE_FILES:
    if not os.path.exists(entry["file"]):
        print(f"Datei {entry['file']} nicht gefunden.")
        continue

    img = Image.open(entry["file"]).convert("RGBA")
    
    count = 0
    # APRS Tabellen haben meist 16 Spalten (c) und 6-9 Zeilen (r)
    for r in range(10): # Sicherheitshalber 10 Zeilen prüfen
        for c in range(16): # 16 Spalten pro Reihe
            if count >= len(CHARS):
                break
            
            # Präzise Berechnung mit Offset und Gitter-Schrittweite
            left = OFFSET_X + (c * STEP_X)
            top = OFFSET_Y + (r * STEP_Y)
            right = left + ICON_W
            bottom = top + ICON_H
            
            # Prüfen, ob wir noch im Bild sind
            if right > img.width or bottom > img.height:
                continue

            icon = img.crop((left, top, right, bottom))
            
            symbol_char = CHARS[count]
            filename = get_hex_name(entry["table_char"], symbol_char)
            icon.save(os.path.join(OUTPUT_DIR, filename))
            count += 1

print(f"Fertig! Icons wurden mit Gitter-Korrektur in {OUTPUT_DIR} gespeichert.")
