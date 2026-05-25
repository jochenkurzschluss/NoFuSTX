# NoFuSTX – Einsatzleitsoftware v1.9.16a

## Kurzbeschreibung

**NoFuSTX** (No Future – System TX) ist eine integrierte Einsatzleitsoftware für Notfunk und Funkamateur-Notfallkommunikation. Die Anwendung bietet eine umfassende GUI mit Unterstützung für multiple Funk-Modi, digitale Betriebsarten, Lagekarten mit APRS, Wetterdaten und LoRa-Mesh-Integration.

### Kernfeatures
- **Lagekarte**: Echtzeit-Positions-Tracking mit APRS-IS und AX.25
- **Funk-Modi**: APRS, JS8Call, VARA, Winlink, MT63, RTTY, SSTV, FAX, AX.25
- **LoRa-Mesh**: Meshtastic-Integration für dezentrale Kommunikation
- **Wetterdaten**: APRS-Wetter-Dekodierung und Anzeige
- **Nachrichtenformat**: IARU-Standard (Notfunkmitteilungen)
- **Offline-Karten**: Lokale Kartenkacheln mit P2P-Sync über LAN
- **Digimode-Terminal**: Fldigi-Integration für digitale Betriebsarten
- **SDR-Unterstützung**: RTL-SDR und weitere
- **Cross-Platform**: Windows, Linux, macOS
- **Einsatz-Session-Log**: Automatische Dokumentation aller Aktivitäten

### Projektlinks
- **Webseite**: https://ithnet.de/h16/view.html
- **Dokumentation**: https://ithnet.de/h16/NoFuSatz_v1-9-3_offiziell.pdf
- **Version**: 1.9.16a (Beta)
- **Lizenz**: GNU General Public License v3.0
- **Autor**: Michael Herholt DO2ITH

## Python-Abhängigkeiten

Alle Abhängigkeiten sind in `requirements.txt` aufgelistet. Die Installation erfolgt automatisch durch `install_deps.sh` oder `install_deps.bat`.

### Kategorien

#### GUI & Benutzeroberfläche
- `tkintermapview` – Kartendarstellung mit Offline-Support
- `tkterminal` – Terminal-Widget für OS-Shell
- `customtkinter` – Moderne UI-Komponenten
- `Pillow` – Bildverarbeitung für Icons und Karten

#### Funk-Modi & Schnittstellen
- `aprslib` – APRS-Protokoll-Dekodierung
- `pyjs8call` – JS8Call API-Integration
- `pyfldigi` – Steuerung digitaler Modi (MT63, RTTY, FAX, CW)
- `pyserial` – PTT/CAT-Steuerung (COM/tty-Ports)
- `pyvara` – VARA-Modem-Integration (Python 3.11+)
- `PyHam_AX25` – AX.25 / Packet Radio

#### Audio & Signal
- `pyaudio` – Soundkarten-Zugriff (SSTV, MT63)
- `numpy` – Mathematik und Signalverarbeitung
- `pysstv` – SSTV-Bildformat-Erzeugung

#### Netzwerk & Internet
- `requests` – HTTP-API-Abfragen

#### LoRa & Mesh
- `meshtastic` – LoRa-Mesh-Integration
- `pubsub` – Publisher-Subscriber für Threads

#### Datenverarbeitung & Export
- `PyMuPDF` (fitz) – PDF-Generierung (Einsatzberichte)
- `markdown2` – Markdown-Konvertierung
- `codext` – Zusätzliche Text-Encodings

#### Grafiken & Visualisierung
- `matplotlib` – Datenvisualisierung
- `contourpy`, `kiwisolver`, `cycler`, `fontTools` – Matplotlib-Abhängigkeiten

#### Sonstige
- `protobuf` – Daten-Serialisierung
- `psutil` – System-Info
- `packaging`, `click`, `charset_normalizer`, `idna`, `certifi` – Utility-Pakete
- `darkdetect` – System-Theme-Erkennung
- `geocoder` – Geolokalisierung

## System-Abhängigkeiten (nicht per pip)

### Linux / macOS

Für die vollständige Funktionalität sollten folgende OS-Pakete installiert sein:

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install \
  python3-tk \
  libportaudio2 portaudio19-dev \
  libasound2-dev \
  ax25-apps \
  cups-client \
  libfuse-dev

# macOS (mit Homebrew)
brew install portaudio
brew install --cask ax25
```

**Erforderliche Systemwerkzeuge:**
- `axlisten` – AX.25-Packet-Radio-Listener (aus Paket `ax25-apps`)
- `lpstat` / `lp` – CUPS-Druckfunktion
- `portaudio` / `portaudio19-dev` – PyAudio-Unterstützung (Sound)
- `tkinter` – Python-Tk-Unterstützung

### Windows

- **Python-Installation**: Python 3.8+ mit Tkinter im Installer aktivieren
- **Visual C++ Build Tools** (optional, für PyAudio-Compilation)
  - Alternative: Vorgefertigte Wheel-Dateien nutzen oder `pipwin` verwenden
- **USB-Treiber** (für Meshtastic, RTL-SDR, serielle Geräte)
  - z.B. CH340-Treiber für LoRa-Module

### Besonderheiten nach Betriebssystem

#### PyAudio unter Windows
Falls `pip install pyaudio` fehlschlägt:
```powershell
pip install pipwin
pipwin install pyaudio
```

#### Meshtastic-Hardware
- Requires libusb driver (Windows: zadig.exe)
- Linux: Meist automatisch erkannt
- macOS: Homebrew oder manueller Treiber

#### RTL-SDR
- Windows: Zadig für LibUSB-Treiber
- Linux: `sudo apt install librtlsdr-dev`
- macOS: `brew install librtlsdr`

## Installation

### Schnellstart (Empfohlen: Virtuelle Umgebung)

#### 1. Virtuelle Python-Umgebung erstellen

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (cmd)
python -m venv venv
venv\Scripts\activate
```

#### 2. Pip aktualisieren

```bash
python -m pip install --upgrade pip setuptools wheel
```

#### 3. Abhängigkeiten installieren

**Option A: Mit requirements.txt (empfohlen)**
```bash
python -m pip install -r requirements.txt
```

**Option B: Mit Installationsskript**

Linux/macOS:
```bash
bash install_deps.sh
```

Windows:
```powershell
.\install_deps.bat
```

#### 4. Abhängigkeiten prüfen

```bash
python check_requirements.py
```

Diese Funktion überprüft alle optionalen Module und zeigt, welche Features verfügbar sind.

### Portable Installation (Lokale libs/)

Für eine portable Variante, die nicht die Systemumgebung benötigt:

```bash
bash local_lib.sh
```

Dies installiert alle Pakete lokal in `libs/` und erstellt `libs/__init__.py`. Das Hauptskript priorisiert diese Lokale Installation automatisch.

**Vorteil**: 
- Keine globalen Abhängigkeiten
- Portabel auf USB-Sticks oder Netzwerk-Shares
- Mehrere Versionen parallel möglich

### Installation einzelner Module (optional)

Falls nur spezifische Features benötigt werden:

```bash
# Nur APRS
python -m pip install aprslib tkintermapview Pillow

# Nur digitale Modi
python -m pip install pyfldigi pyaudio numpy

# Nur LoRa-Mesh
python -m pip install meshtastic pubsub

# Mit matplotlib für Wetter-Graphen
python -m pip install matplotlib
```

**Hinweis**: Viele Features funktionieren auch ohne alle optionalen Abhängigkeiten. Die App startet mit reduzierter Funktionalität.

---

## Konfiguration

Nach der ersten Inbetriebnahme wird ein Konfigurationsfenster angezeigt.

### Hauptkonfiguration (config/nofustx_config.json)

```json
{
  "MODES": {
    "AX25_PORTS": [
      {
        "active": true,
        "device": "ax0",
        "nickname": "CB-APRS",
        "call": "NOCALL"
      }
    ],
    "APRS_IS": {
      "active": true,
      "server": "euro.aprs2.net",
      "port": "14580",
      "call": "NOCALL",
      "passcode": "00000",
      "range_km": "20",
      "view_range": "13"
    },
    "LORA_MESH": {
      "active": false,
      "Device": "MeshID",
      "modem": "LongFast",
      "ConnectionMode": "/dev/ttyACM0"
    },
    "RTTY": {
      "active": false,
      "bps": "45.45",
      "shift": "170",
      "soundcard": "System"
    },
    "SSTV": {
      "active": false,
      "mode": "Martin 1",
      "soundcard": "System Standard"
    }
  },
  "USERCALL": {
    "CALLSINGEN": "NOCALL"
  },
  "MAP": {
    "center_lat": 51.9621817,
    "center_lon": 9.6509120,
    "zoom": 10,
    "home_lat": null,
    "home_lon": null
  },
  "PRINTER": {
    "name": "Standard-Thermo",
    "auto_print": false
  }
}
```

### Frequenzdefinitionen (config/notfunk_freqs.json)

Hier werden die verwendeten Frequenzen, Modi und Beschreibungen definiert.

### Bandplan (config/band_plan.json)

Regionale Frequenzzuordnungen und Betriebsarten nach IARU-Region.

### Wichtige Einstellungen

**HOME-Position**:
- Durch Rechtsklick auf der Karte → "Eigene Position hier setzen"
- Wird in der Konfiguration gespeichert
- Dient als Referenz für APRS-Filter (Empfangsbereich)

**Rufzeichen**:
- Wichtig für APRS-IS-Verbindung
- Wird beim Start abgefragt, falls nicht konfiguriert
- Muss ein gültiges Amateur-Rufzeichen sein

**Soundkarte**:
- Für digitale Modi (SSTV, MT63, RTTY) erforderlich
- Auto-Erkennung beim Start

---

### Normale Ausführung

```bash
python NoFuSTX_1-9-15b.py
```

### Mit Umgebungsvariablen (Linux/macOS)

```bash
PYTHONPATH=libs python NoFuSTX_1-9-15b.py
```

### Debug-Modus

```bash
python -u NoFuSTX_1-9-15b.py 2>&1 | tee debug.log
```

---

## Dateistruktur

```
NoFuSTX_Project/
├── NoFuSTX_1-9-15b.py          # Hauptanwendung
├── README.md                    # Diese Datei
├── requirements.txt             # Python-Abhängigkeiten
├── check_requirements.py         # Abhängigkeits-Checker
├── check_db.py                  # Datenbank-Prüfung
│
├── install_deps.sh              # Auto-Installation (Linux/macOS)
├── install_deps.bat             # Auto-Installation (Windows)
├── local_lib.sh                 # Portable-Installation
├── start_script.sh              # Start-Wrapper (Linux)
│
├── config/
│   ├── nofustx_config.json      # Hauptkonfiguration
│   ├── notfunk_freqs.json       # Frequenzdefinitionen
│   └── band_plan.json           # Bandplan
│
├── libs/                        # Lokale Abhängigkeiten (portable)
│   └── __init__.py
│
├── icons/                       # Benutzer-Icons & APRS-Symbole
│   ├── NoFuSTX.png
│   ├── home.png
│   └── aprs_*.png
│
├── msg/                         # Nachrichtenarchiv
├── logs/                        # Einsatz-Session-Logs
├── assets/                      # Verschiedene Ressourcen
└── off_Maps/                    # Offline-Kartendaten
```

---

## Funktionsübersicht

### Tab: Lagekarte
- Kartendarstellung mit Offline-Support
- APRS-Positionen (APRS-IS und AX.25)
- HOME-Position setzen (Rechtsklick)
- Marker-Management
- Zoom und Pan-Funktionen

### Tab: Fundus / Personal
- Verwaltung von Einsatzpersonal und Ressourcen
- Einheiten-Status

### Tab: Not-Mitteilung (IARU)
- IARU-Nachrichtenformat
- Automatische Nummerierung
- Vorlagen
- Druck-Funktion

### Tab: Wetter
- APRS-Wetterdaten
- Durchschnittswerte
- Historie

### Tab: Digimodes Terminal
- Fldigi-Integration
- MT63, RTTY, FAX, CW etc.
- Soundkarten-Verwaltung

### Tab: Hilfreiches & Konzepte
- Dokumentation
- Referenzen
- Best Practices

### Tab: SDR
- RTL-SDR Spektrumanalyzer
- Frequenzscan
- Direct Sampling

### Tab: OS-Terminal
- Eingebettetes Terminal
- Shell-Zugriff

### Tab: Einsatz-Log
- Chronologische Aufzeichnung
- Session-basiert
- Auto-Finalisierung beim Beenden

---

## Troubleshooting

### Installation & Abhängigkeiten

| Problem | Lösung |
|---------|--------|
| `ModuleNotFoundError: No module named 'tkinter'` | Linux: `sudo apt install python3-tk` |
| `ModuleNotFoundError: No module named 'pyaudio'` | Installiere PortAudio, dann: `pip install pyaudio` oder `pipwin install pyaudio` (Windows) |
| `Cannot find axlisten` | Linux: `sudo apt install ax25-apps` |
| Import-Fehler bei optional Modulen | Normal! App startet mit reduzierter Funktionalität. Nutze `check_requirements.py` |
| "Kein SDR gefunden" | RTL-SDR Treiber prüfen, USB-Verbindung checken |

### Laufzeitfehler

| Problem | Lösung |
|---------|--------|
| Lagekarte zeigt keine Marker | APRS-IS Konfiguration prüfen, HOME-Position setzen |
| "APRS-IS nicht aktiv" | Rufzeichen muss gesetzt sein (nicht "NOCALL") |
| Soundkarte wird nicht erkannt | `pyaudio` testen: `python -c "import pyaudio; print(pyaudio.PyAudio().get_device_count())"` |
| Meshtastic nicht erkannt | USB-Treiber (Zadig auf Windows), libusb auf Linux |

### Konfigurationsprobleme

| Problem | Lösung |
|---------|--------|
| Einstellungen werden nicht gespeichert | Prüfe Write-Permissions in `config/` |
| Alte config.json wird ignoriert | Lösche `config/nofustx_config.json` um Defaults zu laden |
| Frequenzen nicht sichtbar | `config/notfunk_freqs.json` prüfen |

### Performance

| Problem | Lösung |
|---------|--------|
| Karte ist langsam | Offline-Kacheln begrenzen, Zoom-Level anpassen |
| Hohe CPU-Last | Weniger APRS-Filter, Weniger Marker |
| Memory-Leak | Logdateien regelmäßig archivieren |

---

## Entwicklung & Beitrag

### Code-Struktur

Die Hauptklasse `NoFuSTX` verwaltet:
- **UI-Setup**: `setup_ui()`, `setup_*_tab()`
- **APRS-System**: `init_aprs_system()`, Hintergrund-Worker-Threads
- **Konfiguration**: `load_settings()`, `save_settings()`
- **Logging**: `init_session_log()`, `write_session_log()`

### Erweiterung um neue Modi

1. Neuen Modus in `default_config["MODES"]` hinzufügen
2. Worker-Thread implementieren (z.B. `new_mode_worker()`)
3. UI-Tab in `setup_ui()` und entsprechende Setup-Methode
4. Config-Parameter in `load_settings()` ergänzen

### Bug-Reports & Feature-Requests

Bitte auf der Projektseite einreichen: https://ithnet.de/h16/view.html

---

## Lizenz

```
NoFuS-TX - Emergency Communication Suite
Copyright (C) 2026  Michael Herholt DO2ITH

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

---

## Kontakt & Support

- **Autor**: Michael Herholt (DO2ITH)
- **E-Mail**: Kontakt über Projektseite
- **Dokumentation**: https://ithnet.de/h16/view.html

---

## Version-Historie

### v1.9.16a (25.05.2026) – Aktuell
- Meshtastic/LoRa-Mesh Unterstützung
- Erweiterte Abhängigkeiten (matplotlib, customtkinter)
- Wetter-Daten APRS-Integration
- P2P-Kartensync über LAN
- Verbesserte Session-Logging

### v1.9.15b
- Initiale stabilitätsversion

---

*Hinweis: Diese Dokumentation wird regelmäßig aktualisiert.*


