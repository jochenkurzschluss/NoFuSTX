# =============================================================================
# NoFuS-TX - Emergency Communication Suite
# Copyright (C) 2026  [Michael Herholt DO2ITH]
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# =============================================================================
# =============================================================================
# NoFuS-TX - IMPORT SEKTION (v1.9.15b)
# Unterstützt: APRS, JS8Call, VARA, Winlink, MT63, RTTY, SSTV, FAX, AX.25
# Plattformen: Windows, Linux, macOS
# =============================================================================
#
# --- 1. Python Standard-Bibliotheken (Immer vorhanden) ---
import sys
import os
# Ermittle den Pfad, wo dieses Script liegt
base_path = os.path.dirname(os.path.abspath(__file__))
libs_path = os.path.join(base_path, 'libs')
# Existiert der libs Ordner ? Wenn ja, schieben wir ihn an den Anfang der sys.path, damit unsere lokalen Versionen der Module Vorrang haben
if os.path.exists(libs_path):
    # Wir schieben unseren libs-Ordner an Position 0 der Suchliste
    sys.path.insert(0, libs_path)
    # Debug-Ausgabe in der Konsole
    print(f"[*] NoFuS-TX Portable-Modus: Nutze lokale Libs aus {libs_path}")
# Jetzt können wir die Module importieren, die in libs liegen (z.B. pyjs8call, pyvara, etc.)
import datetime
import json
import subprocess
import platform
import tempfile
import threading
import socket           # Essentiell für VARA, JS8Call, Winlink & KISS TCP
import queue            # Thread-sichere Datenübergabe (z.B. APRS-Pakete)
import re
import time
import sqlite3
import math  # Neu: Für Kreisberechnungen (Radius)
import glob
# --- 2. Grafische Benutzeroberfläche & Karten (GUI) ---
import tkinter as tk
from tkinter import ttk, messagebox
try:
    import tkintermapview   # Die Karten-Engine
    from tkintermapview.offline_loading import OfflineLoader
except ImportError:
    tkintermapview = None
try:
    from PIL import Image, ImageTk  # Bildverarbeitung für Icons und Karten
except ImportError:
    Image = None
    ImageTk = None
# --- Die Terminals im OS nutzen
from tkterminal import Terminal
try:
    import tkterminal
except ImportError:
    tkterminal = None
# --- 3. Funk- & Modem-Schnittstellen (Externe Module) ---
# Hinweis: Diese müssen über den check_dependencies() geprüft werden
try:
    import aprslib      # APRS-Protokoll Dekodierung
except ImportError:
    aprslib = None
try:
    import pyjs8call    # API-Schnittstelle zu JS8Call
except ImportError:
    pyjs8call = None
try:
    import pyfldigi     # Steuerung für fldigi (MT63, RTTY, FAX, CW, uvm.)
except ImportError:
    pyfldigi = None
try:
    import serial       # pyserial für PTT/CAT-Steuerung (COM/tty-Ports)
except ImportError:
    serial = None
try:
    import pyaudio      # Soundkarten-Zugriff für SSTV & MT63 Audio
    import numpy as np  # Mathematik für Signalverarbeitung
except ImportError:
    pyaudio = None
    np = None
try:
    import pysstv       # Erzeugung von SSTV-Bildsignalen
except ImportError:
    pysstv = None
# --- 4. Netzwerk & Internet ---
try:
    import requests         # API-Abfragen für Wetter, Gateways oder Online-Logs
except ImportError:
    requests = None
# --- 3. Funk- & Modem-Schnittstellen (Externe Module) ---
# Hinweis: Diese müssen über den check_dependencies() geprüft werden
try:
    import pyjs8call  # API-Schnittstelle zu JS8Call
except ImportError:
    pyjs8call = None
try:
    import pyvara  # Für VARA-Modem Klappt erst ab Python 3.11, da es die neuen Async-Funktionen nutzt # type: ignore
except ImportError:
    pyvara = None
try:
    import fitz  # Für PDF-Generierung (z.B. Einsatzberichte)
except ImportError:
    fitz = None
import glob
'''
try:
     import pymt63  # Falls eine spezifische MT63-Bibliothek existiert
except ImportError:
     pymt63 = None
'''
try:
    import ax25
except ImportError:
    ax25 = None
try:
    import ax25.netrom
except ImportError:
    ax25 = None
try:
    import ax25.ports
except ImportError:
    ax25 = None
try:
    import ax25.socket
except ImportError:
    ax25 = None
# Hauptklasse der Anwendung
class NoFuSTX:
    def __init__(self, root):
        self.root = root
        self.root.title("NoFuS-TX - Einsatzleitsoftware v1.9.15b")
        try:
            # Wir laden das PNG als PhotoImage
            icon_img = tk.PhotoImage(file="icons/NoFuSTX.png")
            self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Programm-Icon Fehler: {e}")
        self.root.geometry("1250x950")
        self.config_file = "nofustx_config.json"
        self.frequency_file = "notfunk_freqs.json"
        self.counter_number_msg = 1

        # Einsatz-Session-Log (pro Programmstart eine Datei)
        self.session_log_file = None
        self.session_log_start_utc = None
        self.session_log_path = None

        # APRS-Lage: Marker- und Update-Verwaltung
        self.aprs_update_queue = queue.Queue()
        self.aprs_markers = {}
        self.aprs_icon_cache = {}
        self.home_marker = None

        self.options = {
            "RTTY_BPS": ["45.45", "50", "75", "100", "200"],
            "SSTV_MODES": ["Martin 1", "Martin 2", "Scottie 1", "Scottie 2", "Robot 36", "Robot 72"],
            "AX25_DEVICES": ["ax0", "ax1", "ax2", "kiss0", "udp0"],
            "LORA_MODEMS": ["LongFast", "LongSlow", "ShortFast"]
        }

        # Vollständige Default-Config inkl. neuer Felder für Modi oder Ergänungen
        self.default_config = {
            "MODES": {
                "AX25_PORTS": [
                    {"active": True, "device": "ax0", "nickname": "CB-APRS", "call": "NOCALL"},
                    {"active": True, "device": "ax1", "nickname": "AFU-Packet", "call": "NOCALL"}
                ],
                "APRS_IS": {
                    "active": True,
                    "server": "euro.aprs2.net",
                    "port": "14580",
                    "call": "NOCALL",
                    "passcode": "00000",
                    "range_km": "20",
                    "view_range": "13",
                },
                "WINLINK": {
                    "active": True,
                    "rms_server": "cms.winlink.org",
                    "port": "8772",
                    "call": "NOCALL",
                },
                "LORA_MESH": {"active": True, "freq": "868.0 MHz", "modem": "LongFast"},
                "RTTY": {
                    "active": False,
                    "bps": "45.45",
                    "shift": "170",
                    "soundcard": "System",
                },
                "SSTV": {
                    "active": False,
                    "mode": "Martin 1",
                    "soundcard": "System Standard",
                },
                "FAX": {"active": False, "lpm": "120", "ioc": "576"},
                "JS8CALL": {
                    "active": False,
                    "frequency": "7.078 MHz",  # Typische JS8Call-Frequenz
                    "callsign": "NOCALL",
                    "soundcard": "System",
                },
                "VARA": {
                    "active": False,
                    "frequency": "14.105 MHz",  # Typische VARA-Frequenz
                    "callsign": "NOCALL",
                    "soundcard": "System",
                },
                "MT63": {
                    "active": False,
                    "frequency": "7.040 MHz",  # Typische MT63-Frequenz
                    "bandwidth": "1k",  # z. B. 500Hz, 1k, 2k
                    "soundcard": "System",
                },
            },
            "PRINTER": {"name": "Standard-Thermo", "auto_print": False},
            "UNITS": [
                {"name": "Zentrale (NoFuS-E)", "type": "NoFuS-E", "status": True},
                {"name": "Mobil 1", "type": "NoFuS-M", "status": True},
                {"name": "Trupp A", "type": "NoFuS-P", "status": False},
                {"name": "Trupp B", "type": "NoFuS-P", "status": False},
            ],
            # Standard-Lagekarte: ca. 10 km Radius um 51.9621817 / 9.6509120
            "MAP": {
                "center_lat": 51.9621817,
                "center_lon": 9.6509120,
                "zoom": 10,
            },
            # Abhängigkeiten: Hier kann später den Status der optionalen Module speichern, damit die App nicht jedes Mal neu prüfen muss (z.B. nach einem fehlgeschlagenen Start)
            "DEPENDENCIES": {
                "is_read": 0,
            }
        }
        # Vollständige Default-Frequenzen mit Beschreibungen in .jason für jede Guppe zu Ändern!
        self.default_frequencies = {
            "FREQUENCIES": [
                ["FM / Fonie", "145.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / AFSK","144.800 MHz", "APRS zur Positionsermittlung"],
                ["FM / Fonie","149.050 MHz", "Freenet in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / Fonie","446.03125 MHz", "PMR in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / Fonie","430.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / Fonie","433.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / Fonie","28.325 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / Fonie","27.065 MHz", "CB in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM / AFSK","27.235 MHz", "CB AFSK/APRS zur Positionsermittlung und Datenübertragung"],
                ["USB / Fonie","14.300 MHz", "in Fonie zur Kommunikation über sehr große Entfernungen (Grenzübergreifend)"],
                ["LSB / Fonie","7.110 kHz", "LSB in Fonie zur Kommunikation über sehr große Entfernungen (Deutschland weit)"],
                ["LSB / Fonie","3.760 kHz", "LSB in Fonie zur Kommunikation über sehr große Entfernungen (Deutschland weit)"],
                ]
        }

        self.load_settings()
        self.load_frequencies()
        if not self.config.get("DEPENDENCIES", {}).get("is_read", 0):
            self.check_dependencies()
            self.config["DEPENDENCIES"]["is_read"] = 1
            self.save_settings()
        self.setup_ui()
        self.init_session_log()
        self.init_aprs_system()
    # --------- KONFIGURATIONSLADUNG & -SPEICHERUNG ----------
    def load_settings(self):
        if not os.path.exists(self.config_file):
            self.config = self.default_config
            self.save_settings()
        else:
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)

                # Fehlende Bereiche aus Default ergänzen
                if "MODES" not in self.config:
                    self.config["MODES"] = self.default_config["MODES"]
                else:
                    # Fehlende Modi hinzufügen
                    for mode, params in self.default_config["MODES"].items():
                        if mode not in self.config["MODES"]:
                            self.config["MODES"][mode] = params
                if "PRINTER" not in self.config:
                    self.config["PRINTER"] = self.default_config["PRINTER"]
                if "MAP" not in self.config:
                    self.config["MAP"] = self.default_config["MAP"]

                # APRS Passcode sicherstellen
                if (
                    "APRS_IS" in self.config["MODES"]
                    and "passcode" not in self.config["MODES"]["APRS_IS"]
                ):
                    self.config["MODES"]["APRS_IS"]["passcode"] = "00000"

                # SSTV Soundkarte sicherstellen
                if (
                    "SSTV" in self.config["MODES"]
                    and "soundcard" not in self.config["MODES"]["SSTV"]
                ):
                    self.config["MODES"]["SSTV"]["soundcard"] = "System Standard"

                # RTTY Soundkarte sicherstellen
                if (
                    "RTTY" in self.config["MODES"]
                    and "soundcard" not in self.config["MODES"]["RTTY"]
                ):
                    self.config["MODES"]["RTTY"]["soundcard"] = "System"
            except Exception:
                self.config = self.default_config
    def check_dependencies(self):
        missing = []
        # GUI / Karten
        if tkintermapview is None:
            missing.append("tkintermapview")
        if Image is None or ImageTk is None:
            missing.append("Pillow")
        # optionale Funkmodule
        if aprslib is None:
            missing.append("aprslib")
        if pyjs8call is None:
            missing.append("pyjs8call")
        if pyfldigi is None:
            missing.append("pyfldigi")
        if serial is None:
            missing.append("pyserial")
        if pyaudio is None or np is None:
            missing.append("pyaudio + numpy")
        if pysstv is None:
            missing.append("pysstv")
        if requests is None:
            missing.append("requests")
        if pyvara is None:
            missing.append("pyvara")
###############
        #if pymt63 is None:  
        #    missing.append("pymt63")
###############
        if tkterminal is None: 
            missing.append("tkterminal")
        if ax25 is None:  
            missing.append("PyHam_AX25")
        if fitz is None:
            missing.append("PyMuPDF (fitz)")
        if missing:
            install_cmd = "python -m pip install " + " ".join(
                m.replace(" + ", " ").split()[0] for m in missing
            )
            msg = (
                "Einige optionale Abhängigkeiten fehlen:\n\n"
                + "\n".join(f"• {m}" for m in missing)
                + "\n\nInstallieren mit:\n\n"
                + install_cmd
                + "\n\n(Die App kann auch ohne diese Pakete starten, aber bestimmte Funktionen sind dann deaktiviert.)\n\n\n"
                + "Achtung unter Linux ist wichtig das Sie auch Folgende Pakete benötigen:\n\nsudo apt install libasound2-dev portaudio19-dev"
            )
            try:
                # Anstatt Messagebox ein kopierbares Textfeld öffnen !!!
                win = tk.Toplevel()
                win.title("NoFuS-TX: fehlende Abhängigkeiten")
                win.geometry("500x300")

                text = tk.Text(win, wrap="word", height=12, padx=10, pady=10, bg="lightgray", fg="black", font=("Arial", 10))
                text.insert("1.0", msg)
                text.pack(expand=True, fill="both")
                
                button = tk.Button(win, text="Schließen", command=win.destroy, bg="lightgray", fg="black", font=("Arial", 10))
                button.pack()
            except Exception:
                print(msg)
    # --------- FREQUENZENLADUNG & -SPEICHERUNG ----------
    def load_frequencies(self):
        if not os.path.exists(self.frequency_file):
            self.frequencies = self.default_frequencies
            with open(self.frequency_file, "w") as f:
                json.dump(self.frequencies, f, indent=4)
        else:
            try:
                with open(self.frequency_file, "r") as f:
                    self.frequencies = json.load(f)
            except Exception:
                self.frequencies = self.default_frequencies

    def save_settings(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    # ---------- EINSATZ-SESSION-LOG ----------
    def init_session_log(self):
        """
        Erstellt zu Programmstart eine Einsatz-Logdatei mit Startzeit im Namen.
        Beim späteren Programmende wird die Datei auf einen Namen mit Start- und
        Stop-Zeit umbenannt.
        Dateinamensschema:
            einsatz-YYYYMMDD-HHMMSSUTC_...txt
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        self.session_log_start_utc = datetime.datetime.utcnow()
        # start_str = self.session_log_start_utc.strftime("%Y-%m-%d_%H-%M-%S-UTC")
        start_str = self.session_log_start_utc.strftime("%d-%m-%Y_%H-%M-%S-UTC")

        # Initialer Dateiname nur mit Startzeit; beim Beenden wird umbenannt
        filename = f"einsatz-{start_str}_RUNNING.txt"
        self.session_log_path = os.path.join(logs_dir, filename)

        try:
            self.session_log_file = open(self.session_log_path, "a", encoding="utf-8")
            self.session_log_file.write(
                f"Einsatz gestartet (UTC): {self.session_log_start_utc.isoformat()}Z\n"
            )
            self.session_log_file.flush()
        except Exception:
            self.session_log_file = None

        # Eigenen Close-Handler registrieren, damit wir die Stop-Zeit sauber eintragen können
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception:
            pass

    def write_session_log(self, text):
        """
        Schreibt eine Zeile in die aktuelle Einsatz-Session-Datei.
        """
        if not self.session_log_file:
            return
        try:
            self.session_log_file.write(text + "\n")
            self.session_log_file.flush()
        except Exception:
            pass

    def finalize_session_log(self):
        """
        Ergänzt beim Programmende die Stop-Zeit und benennt die Datei auf
        'einsatz-STARTUTC_STOPUTC.txt' um.
        """
        if not self.session_log_path or not self.session_log_start_utc:
            return

        stop_utc = datetime.datetime.utcnow()
        # stop_str = stop_utc.strftime("%Y-%m-%d_%H-%M-%S-UTC") # Änderung: Datum im Format DD-MM-YYYY
        stop_str = stop_utc.strftime("%d-%m-%Y_%H-%M-%S-UTC")

        try:
            if self.session_log_file:
                self.session_log_file.write(
                    f"Einsatz beendet (UTC): {stop_utc.isoformat()}Z\n"
                )
                self.session_log_file.flush()
                self.session_log_file.close()
        except Exception:
            # Im Fehlerfall versuchen wir trotzdem, die Datei umzubenennen
            pass
        finally:
            self.session_log_file = None

        # Neuen Dateinamen mit Start- und Stopzeit erzeugen
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "logs")
        start_str = self.session_log_start_utc.strftime("%d-%m-%Y_%H-%M-%S-UTC")
        new_name = os.path.join(
            logs_dir, f"einsatz-{start_str}_{stop_str}.txt"
        )

        try:
            if os.path.exists(self.session_log_path):
                os.rename(self.session_log_path, new_name)
        except Exception:
            # Wenn Umbenennen scheitert, bleibt die RUNNING-Datei erhalten
            pass

    def on_close(self):
        """
        Wird beim Schließen des Hauptfensters aufgerufen.
        Sorgt dafür, dass das Einsatz-Session-Log sauber abgeschlossen wird.
        """
        self.finalize_session_log()
        self.root.destroy()

    # ---------- APRS GRUND-INITIALISIERUNG ----------
    def init_aprs_system(self):
        """
        Initialisiert das passive APRS-Lagesystem:
        - Start der Empfangsthreads (APRS-IS und AX.25)
        - periodische Verarbeitung der Update-Queue im GUI-Thread
        - Laden/Setzen eines optional gespeicherten HOME-Markers
        """
        # Ohne aprslib kein APRS – Hinweis im Log und sauber abbrechen
        if aprslib is None:
            try:
                self.log_list.insert(
                    0,
                    f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : APRS deaktiviert (aprslib nicht installiert).",
                )
            except Exception:
                pass
            return

        # Rechtsklick-Menü für HOME-Position auf der Karte
        try:
            self.map_widget.add_right_click_menu_command(
                label="Eigene Position hier setzen",
                command=self.set_home_position_from_click,
                pass_coords=True,
            )
        except Exception:
            # Falls die verwendete tkintermapview-Version diese Funktion nicht kennt,
            # läuft das Programm trotzdem weiter – nur ohne Rechtsklickkomfort.
            pass

        # Bereits gespeicherte HOME-Position laden und Marker setzen
        map_conf = self.config.get("MAP", {})
        home_lat = map_conf.get("home_lat", 51.9621817)
        home_lon = map_conf.get("home_lon", 9.650912)
        if home_lat is not None and home_lon is not None:
            try:
                lat = float(home_lat)
                lon = float(home_lon)
                home_image = self.get_home_image()
                marker_kwargs = {}
                if home_image is not None:
                    marker_kwargs["image"] = home_image
                self.home_marker = self.map_widget.set_marker(
                    lat, lon, text="HOME", **marker_kwargs
                )
                self._apply_icon_to_marker(self.home_marker, home_image)
            except Exception:
                self.home_marker = None

        # Empfangs-Threads starten (listen-only Weil kein Lizens checkt) – die Threads stellen Pakete in die aprs_update_queue, die im GUI-Thread arbeitet
        modes = self.config.get("MODES", [])

        aprs_is_conf = modes.get("APRS_IS", {})
        if aprs_is_conf.get("active"):
            t_is = threading.Thread(target=self.aprs_is_worker, daemon=True)
            t_is.start()

        for port in modes.get("AX25_PORTS", []):
            if port.get("active"):
                device = port.get("device") or "ax0"
                t_ax = threading.Thread(
                    target=self.ax25_worker, args=(device,), daemon=True
                )
                t_ax.start()

        # Queue im GUI-Thread regelmäßig abarbeiten
        self.root.after(500, self.process_aprs_queue)

    # ---------- APRS HILFSFUNKTIONEN ----------
    def get_home_image(self):
        """
        Liefert (und cached) ein spezielles HOME-Icon, falls vorhanden.
        Erwarteter Dateiname im Unterordner ./icons:
            - home.png oder home.gif
        """
        key = "HOME_ICON"
        if key in self.aprs_icon_cache:
            return self.aprs_icon_cache[key]

        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(base_dir, "icons")
        for ext in (".png", ".gif"):
            path = os.path.join(icons_dir, "home" + ext)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    self.aprs_icon_cache[key] = img
                    return img
                except Exception:
                    break
        self.aprs_icon_cache[key] = None
        return None

    def get_symbol_image(self, symbol_table, symbol_code):
        """
        Verbesserte Suche: Erzwingt gültige APRS-Tabellen (Hex 2f oder 5c).
        """
        if not symbol_table or not symbol_code:
            return None

        # --- KORREKTUR: Nur echte APRS-Tabellen erlauben ---
        # Falls symbol_table kein / oder \ ist, benutzt / als Standard.
        actual_table = symbol_table if symbol_table in ['/', '\\'] else '/'
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(base_dir, "icons")
        icon_log = os.path.join(base_dir, "icon.log")

        key = f"{actual_table}{symbol_code}"
        if key in self.aprs_icon_cache:
            return self.aprs_icon_cache[key]

        # Hex-Berechnung basierend auf der korrigierten Tabelle
        t_hex = f"{ord(actual_table):02x}"
        s_hex = f"{ord(symbol_code):02x}"

        candidates = [
            f"aprs_{t_hex}_{s_hex}.png",
            f"aprs_{t_hex}_{s_hex}.gif",
        ]
        
        for filename in candidates:
            path = os.path.join(icons_dir, filename)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    self.aprs_icon_cache[key] = img
                    return img
                except Exception:
                    continue

        self.aprs_icon_cache[key] = None
        return None

    def _apply_icon_to_marker(self, marker, image):
        """
        Versteckt den Standard-Kartenmarker (Kreis/Dreieck) und
        justiert das Icon (unten-mittig).
        """
        if not marker:
            return

        # 1) Default-Shape ausblenden (je nach tkintermapview-Version könnte das ein Kreis oder Dreieck sein)
        try:
            # if hasattr(marker, "canvas_icon"): # Muss hier weiter geprüft werden ob es bei der Finlen Version schon andere Methoden gibt!
                # self.map_widget.canvas.itemconfig(marker.canvas_icon, state="hidden")
            if hasattr(marker, "big_circle"):
                self.map_widget.canvas.itemconfig(marker.big_circle, state="hidden")
        except Exception:
            pass

        # 2) Icon am Punkt, Text darunter
        if image is not None:
            try:
                w = image.width()
                h = image.height()

                # **Icon als Icon (nicht image)**
                marker.icon = image
                marker.icon_anchor = "center"  # punktgenau in der Mitte
                marker.calculate_text_y_offset()  # damit die interne Offset-Berechnung passt

                # Draw + danach Text neu platzieren
                def draw_and_place(event=None):
                    # Original zeichnen
                    orig_draw(event)

                    # Text nach unten verschieben (unter das Icon)
                    if getattr(marker, "canvas_text", None) and getattr(marker, "canvas_icon", None):
                        self.map_widget.canvas.itemconfig(marker.canvas_text, anchor="n")
                        x, y = self.map_widget.canvas.coords(marker.canvas_icon)
                        self.map_widget.canvas.coords(
                            marker.canvas_text,
                            x,
                            y + (h // 2) + 4,  # 4px Abstand unterhalb des Icons
                        )

                orig_draw = marker.draw
                marker.draw = draw_and_place

                # Erstmal Zeichen
                marker.draw()

            except Exception:
                pass

    def extract_aprs_position(self, packet):
        """
        Extrahiert aus einem von aprslib gelieferten Packet-Dict
        die für die Lagedarstellung relevanten Daten.
        Erwartete Struktur (typisch aprslib.parse / IS consumer):
            - latitude / longitude
            - from (Rufzeichen)
            - symbol_table, symbol
        Gibt None zurück, falls keine Positionsinformation enthalten ist.
        """
        if not isinstance(packet, dict):
            return None

        lat = packet.get("latitude")
        lon = packet.get("longitude")
        if lat is None or lon is None:
            return None

        src = packet.get("from") or packet.get("source") or "UNKN"
        ident = packet.get("name") or src

        symbol_table = packet.get("symbol_table") or packet.get("symbol_table_id") or "/"
        symbol_code = packet.get("symbol") or packet.get("symbol_code") or ">"

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            return None

        return {
            "lat": lat_f,
            "lon": lon_f,
            "src": src,
            "id": ident,
            "symbol_table": symbol_table,
            "symbol_code": symbol_code,
        }
    
    def extract_aprs_weather(self, packet):
        """Verbesserte Extraktion, die auch Unter-Dicts von aprslib prüft."""
        if not isinstance(packet, dict):
            return None
        
        # Wetterdaten holen
        wx_sub = packet.get("weather", {})
        
        # Daten Sammeln
        temp = packet.get("temperature") or wx_sub.get("temperature") or packet.get("temp")
        hum = packet.get("humidity") or wx_sub.get("humidity") or packet.get("hum")
        press = packet.get("pressure") or wx_sub.get("pressure") or packet.get("press")
        wind_s = packet.get("wind_speed") or wx_sub.get("wind_speed")
        wind_d = packet.get("wind_direction") or wx_sub.get("wind_direction")
        rain = packet.get("rain_24h") or wx_sub.get("rain_24h")

        # Nur wenn mindestens ein relevanter Wert da ist
        if all(v is None for v in [temp, hum, press, wind_s]):
            # Sonderfall: Wenn nichts gefunden wurde, prüfen kurz im Kommentar
            # Manche Stationen senden Wetter nur als Text im Kommentar
            comment = packet.get("comment", "")
            if "t" not in comment.lower(): # Grober Check
                return None

        return {
            "temp": temp,
            "hum": hum,
            "press": press,
            "wind_speed": wind_s,
            "wind_dir": wind_d,
            "rain_24h": rain,
            "src": packet.get("from") or packet.get("source") or "UNKN"
        }


    def handle_weather_event(self, event):
        """
        Nimmt die Wetterdaten aus der Queue entgegen und aktualisiert die 
        Labels im Wetter-Tab (tab_wx).
        """
        wx = event.get("wx_data", {})
        callsign = event.get("callsign", "Unbekannt")

        try:
            # 1. Die UI-Variablen (tk.StringVar) aktualisieren
            # Prüfen mit .get(), ob der Wert existiert, sonst nutzen wir "--"
            
            temp = wx.get("temp")
            if temp is not None:
                self.wx_vars["temp"].set(f"{float(temp):.1f} °C")
            
            hum = wx.get("hum")
            if hum is not None:
                self.wx_vars["hum"].set(f"{hum} %")
                
            press = wx.get("press")
            if press is not None:
                self.wx_vars["press"].set(f"{float(press):.1f} hPa")

            wind_s = wx.get("wind_speed")
            if wind_s is not None:
                # Umrechnung m/s in km/h falls nötig, aprslib liefert oft m/s
                self.wx_vars["wind"].set(f"{float(wind_s) * 3.6:.1f} km/h")

            rain = wx.get("rain_24h")
            if rain is not None:
                self.wx_vars["rain"].set(f"{rain} mm")

            self.wx_vars["station"].set(callsign)

            # 2. Eintrag in die Listbox auf der rechten Seite
            timestamp = datetime.datetime.now().strftime("%H:%M")
            entry_text = f"{timestamp} | {callsign} | {self.wx_vars['temp'].get()}"
            self.wx_listbox.insert(0, entry_text)

            # Liste auf 50 Einträge begrenzen
            if self.wx_listbox.size() > 50:
                self.wx_listbox.delete(tk.END)

        except Exception as e:
            print(f"Fehler bei der Wetter-Anzeige: {e}")

    # ---------- APRS HINTERGRUND-THREADS ----------
    def aprs_is_worker(self):
        """
        Empfang von APRS-IS über aprslib.IS (listen-only).
        Keine Beacon- oder Sende-Funktion – reine Auswertung eingehender Pakete.
        """
        if aprslib is None:
            return

        modes = self.config.get("MODES", {})
        conf = modes.get("APRS_IS", {})
        call = conf.get("call", "NOCALL")
        server = conf.get("server", "euro.aprs2.net")
        port = int(conf.get("port", "14580"))
        passwd = conf.get("passcode", "-1")
        range_km = conf.get("range_km", 20)  # Empfangsbereich in Kilometern um die HOME-Position

        if not call or call == "NOCALL":
            # Ohne gültiges Rufzeichen nicht verbinden mit APRS-IS. Kein call check möglich, in der 3.0 umsetzen ?!
            self.aprs_update_queue.put(
                {
                    "type": "log",
                    "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : APRS-IS nicht aktiv (Rufzeichen NOCALL).",
                }
            )
            return

        def _callback(packet):
            # 1. Wetter checken
            wx = self.extract_aprs_weather(packet)
            if wx:
                self.aprs_update_queue.put({
                    "type": "weather",
                    "callsign": wx["src"],
                    "wx_data": wx
                })

            # 2. Position checken (bestehender Code)
            try:
                pos = self.extract_aprs_position(packet)
                if pos:
                    pos["source_type"] = "APRS-IS"
                    self.aprs_update_queue.put({"type": "position", **pos})
            except Exception:
                return

        while True:
            try:
                is_conn = aprslib.IS(
                    call,
                    passwd=passwd,
                    host=server,
                    port=port,
                    # Filter optional, z.B. nur Positionen in der Nähe;
                    # hier generischer Empfang, da reine Lagedarstellung.
                )
                map_conf = self.config.get("MAP", {})
                home_lat = map_conf.get("home_lat", 51.9621817)
                home_lon = map_conf.get("home_lon", 9.650912)
                
                filter_str = f"r/{home_lat:.4f}/{home_lon:.4f}/{range_km}"
                # print(f"APRS-IS Filter: {filter_str}") # Debug-Ausgabe
                
                is_conn.set_filter(filter_str)  # Beispiel: Filter auf 100 km um HOME-Position
                is_conn.connect()
                self.aprs_update_queue.put(
                    {
                        "type": "log",
                        "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : APRS-IS verbunden ({server}:{port}).",
                    }
                )
                # consumer() blockiert in dieser Thread-Funktion, liefert Pakete an _callback
                is_conn.consumer(callback=_callback, raw=False)
                
            except Exception:
                self.aprs_update_queue.put(
                    {
                        "type": "log",
                        "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : APRS-IS Verbindung fehlgeschlagen – neuer Versuch in 30 s.",
                    }
                )
                time.sleep(30)

    def ax25_worker(self, device):
        """
        Empfang lokaler APRS-Pakete über AX.25.
        Implementierung nutzt das Systemtool 'axlisten' im Passivmodus.
        Erwartet, dass das jeweilige AX.25-Interface (z.B. ax0, ax1, kiss0) bereits
        im System korrekt konfiguriert ist. 
        ### ein Debug gedanke print(f"RAW PACKET KEYS: {packet.keys()}") auch für die _callback?
        """
        if aprslib is None:
            return

        # Nur unter POSIX-Systemen sinnvoll
        if os.name != "posix":
            return

        cmd = ["axlisten", "-a", "-c", device]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except Exception:
            self.aprs_update_queue.put(
                {
                    "type": "log",
                    "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : AX.25-Listener für {device} konnte nicht gestartet werden.",
                }
            )
            return

        self.aprs_update_queue.put(
            {
                "type": "log",
                "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : AX.25-Listener aktiv auf {device}.",
            }
        )

        # Zeilenweise Ausgabe von axlisten auswerten
        for line in proc.stdout: # type: ignore
            line = line.strip()
            if not line:
                continue

            # Typische Form: SRCCALL>DEST,PATH1,PATH2:PAYLOAD
            if ">" not in line or ":" not in line:
                continue

            try:
                # Direkt an aprslib.parse übergeben – es versteht das APRS-Frameformat.
                pkt = aprslib.parse(line)
                # NEU: Wetter zuerst
                wx = self.extract_aprs_weather(pkt)
                if wx:
                    self.aprs_update_queue.put({
                        "type": "weather",
                        "callsign": wx["src"],
                        "wx_data": wx
                    })
                pos = self.extract_aprs_position(pkt)
                if not pos:
                    continue
                pos["source_type"] = f"AX25:{device}"
                self.aprs_update_queue.put(
                    {
                        "type": "position",
                        **pos,
                    }
                )
            except Exception:
                # Einzelne fehlerhafte Zeilen ignorieren
                continue

    # ---------- APRS QUEUE & UI-INTEGRATION ----------
    def process_aprs_queue(self):
        """
        Wird regelmäßig im GUI-Thread aufgerufen und verarbeitet alle
        bis dahin eingegangenen APRS-Events aus den Hintergrund-Threads.
        """
        try:
            while True:
                event = self.aprs_update_queue.get_nowait()
                etype = event.get("type")

                # --- DEBUG ZEILE: Zeigt jedes Paket in der Konsole ---
                # print(f"DEBUG APRS: {event}")

                if etype == "position":
                    self.handle_aprs_position_event(event)
                elif etype == "weather": # <--- NEU
                    self.handle_weather_event(event) # Diese Funktion füllt den Wetter-Tab
                elif etype == "log":
                    msg = event.get("message")
                    if msg and hasattr(self, "log_list"):
                        try:
                            self.log_list.insert(0, msg)
                        except Exception:
                            pass
        except queue.Empty:
            pass

        self.root.after(500, self.process_aprs_queue)

    def handle_aprs_position_event(self, event):
        """
        Legt Marker auf der Karte an oder aktualisiert bestehende Marker.
        Außerdem kurzer Eintrag im Einsatz-Log mit Rufzeichen und Symboltyp.
        """
        lat = event.get("lat")
        lon = event.get("lon")
        src = event.get("src", "UNKN")
        ident = event.get("id", src)
        symbol_table = event.get("symbol_table", "/")
        symbol_code = event.get("symbol_code", ">")
        source_type = event.get("source_type", "")

        if lat is None or lon is None:
            return

        display_text = src
        if ident and ident != src:
            display_text = f"{src} ({ident})"

        # Marker-Schlüssel: pro Rufzeichen/Objekt eindeutig halten
        key = f"{src}:{ident}"

        image = self.get_symbol_image(symbol_table, symbol_code)

        marker = self.aprs_markers.get(key)
        try:
            # Alten Marker vorher löschen, falls Position sich ändert
            if marker is not None:
                self._remove_marker(marker)
                del self.aprs_markers[key]
                marker = None

            marker = self.map_widget.set_marker(
                lat, lon, text=display_text, icon=image
            )
            self._apply_icon_to_marker(marker, image)
            self.aprs_markers[key] = marker

        except Exception:
            # Kartenfehler sollen keinen Absturz verursachen
            return 

        # Kurzer Eintrag im Einsatz-Log
        if hasattr(self, "log_list"):
            log_text = (
                f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : "
                f"APRS {src} ({source_type}) -> {symbol_table}{symbol_code} "
                f"@ {lat:.5f},{lon:.5f}"
            )
            try:
                self.log_list.insert(0, log_text)
            except Exception:
                pass

    # ---------- HOME-POSITION ----------
    def set_home_position_from_click(self, coords):
        """
        Callback für das Rechtsklick-Menü der Karte.
        Erwartet von tkintermapview ein Tupel (lat, lon).
        """
        try:
            lat, lon = coords
        except Exception:
            return

        # In Config ablegen
        map_conf = self.config.setdefault("MAP", {})
        map_conf["home_lat"] = float(lat)
        map_conf["home_lon"] = float(lon)
        self.save_settings()

        # Vorhandenen HOME-Marker entfernen
        if self.home_marker is not None:
            
            self._remove_marker(self.home_marker)
            self.home_marker = None

        # Neuen HOME-Marker setzen
        home_image = self.get_home_image()
        marker_kwargs = {}
        if home_image is not None:
            marker_kwargs["image"] = home_image

        try:
            # 1. Marker erstellen
            self.home_marker = self.map_widget.set_marker(lat, lon, text="HOME", icon=home_image)

            # 2. Icon setzen / anpassen / Default-Symbol ausblenden
            self._apply_icon_to_marker(self.home_marker, home_image)

        except Exception:
            self.home_marker = None

        # Log-Eintrag
        if hasattr(self, "log_list"):
            msg = (
                f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : "
                f"HOME-Position gesetzt @ {lat:.5f},{lon:.5f}"
            )
            try:
                self.log_list.insert(0, msg)
            except Exception:
                pass

    def _remove_marker(self, marker):
        """Versucht, einen Marker vom Kartenlayer zu entfernen."""
        if not marker:
            return
        try:
            if hasattr(marker, "delete"):
                marker.delete()
            elif hasattr(marker, "remove"):
                marker.remove()
        except Exception:
            pass

    def get_system_printers(self):
        """
        Liefert eine Liste verfügbarer Systemdrucker zurück (sofern ermittelbar).
        - Unter Linux/macOS wird `lpstat -p` genutzt.
        - Unter Windows wird zuerst `wmic printer get name`, danach
          `powershell Get-Printer` versucht.
        In allen Fällen gibt es einen sinnvollen Fallback auf den konfigurierten Namen.
        """
        printers = []

        system = platform.system()

        if system == "Windows":
            # 1. Versuch: wmic (auf vielen Systemen noch vorhanden)
            try:
                output = subprocess.check_output(
                    ["wmic", "printer", "get", "name"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                for line in output.splitlines():
                    name = line.strip()
                    if name and name.lower() != "name":
                        printers.append(name)
            except Exception:
                pass

            # 2. Versuch: PowerShell Get-Printer
            if not printers:
                try:
                    output = subprocess.check_output(
                        [
                            "powershell",
                            "-Command",
                            "Get-Printer | Select-Object -ExpandProperty Name",
                        ],
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    for line in output.splitlines():
                        name = line.strip()
                        if name:
                            printers.append(name)
                except Exception:
                    pass

        else:
            # Versuch über CUPS / lpstat (typisch unter Linux/macOS)
            try:
                output = subprocess.check_output(
                    ["lpstat", "-p"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                for line in output.splitlines():
                    line = line.strip()
                    # Deutsche Lokalisierung: "Drucker", englische: "printer"
                    if line.startswith("printer ") or line.startswith("Drucker "):
                        parts = line.split()
                        if len(parts) >= 2:
                            printers.append(parts[1])
            except Exception:
                # lpstat nicht vorhanden oder Fehler -> still zurückfallen
                pass

        # Falls nichts gefunden wurde, aktuelle Konfiguration als Fallback nutzen
        current = self.config.get("PRINTER", {}).get("name")
        if current:
            printers.append(current)

        if not printers:
            printers.append("Standard-Thermo")

        # Doppelte Einträge entfernen, sortiert zurückgeben
        # (Reihenfolge ist hier nicht kritisch)
        unique = list(dict.fromkeys(printers))
        return unique

    def print_message(self, text):
        """
        Versucht, die übergebene Meldung auf den ausgewählten Systemdrucker zu drucken.
        - Unter Linux/macOS wird `lp` verwendet (mit gesetztem Druckernamen, falls vorhanden).
        - Unter Windows wird ein einfacher Notepad-Druckversuch unternommen.
        Fehler werden per Messagebox gemeldet, damit die Anwendung nicht abstürzt.
        """
        printer = self.config.get("PRINTER", {}).get("name", "")
        system = platform.system()

        try:
            # Temporäre Datei mit dem Meldungstext erzeugen
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
                tmp.write(text)
                tmp_path = tmp.name

            if system == "Windows":
                # Einfache Variante: Notepad den Druck übernehmen lassen
                try:
                    subprocess.Popen(["notepad", "/p", tmp_path])
                except Exception as e:
                    messagebox.showerror("Drucken", f"Drucken unter Windows fehlgeschlagen:\n{e}")
            else:
                # POSIX: lp nutzen, optional mit -d <printer>
                cmd = ["lp"]
                if printer:
                    cmd.extend(["-d", printer])
                cmd.append(tmp_path)
                subprocess.check_call(cmd)
        except Exception as e:
            messagebox.showerror("Drucken", f"Druckfehler:\n{e}")

    # --------- UI-AUFBAU & -ELEMENTE ----------
    def setup_ui(self):
        self.setup_menu()

        self.status_bar = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.time_label = tk.Label(self.status_bar, text="", font=("Courier", 10, "bold"))
        self.time_label.pack(side=tk.RIGHT, padx=10)
        self.update_clock()

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(expand=1, fill="both")

        self.tab_map = ttk.Frame(self.tabs)
        self.tab_fundus = ttk.Frame(self.tabs)
        self.tab_msg = ttk.Frame(self.tabs)
        self.tab_wx = ttk.Frame(self.tabs)
        self.tab_digi = ttk.Frame(self.tabs)
        self.tab_help_main = ttk.Frame(self.tabs)
        self.tab_sdr = ttk.Frame(self.tabs)
        self.tab_os_terminal = ttk.Frame(self.tabs)
        self.tab_log = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_map, text="Lagekarte")
        self.tabs.add(self.tab_fundus, text="Fundus / Personal")
        self.tabs.add(self.tab_msg, text="Not-Mitteilung (IARU)")
        self.tabs.add(self.tab_wx, text="Wetter")
        self.tabs.add(self.tab_digi, text="Digimodes Terminal")
        self.tabs.add(self.tab_help_main, text="Hilfreiches & Konzepte")
        self.tabs.add(self.tab_sdr, text="SDR")
        self.tabs.add(self.tab_os_terminal, text="OS-Terminal")
        self.tabs.add(self.tab_log, text="Einsatz-Log")

        self.setup_map_view()
        self.setup_fundus_tab()
        self.setup_message_tab()
        self.setup_weather_tab()
        self.setup_digimode_terminals()
        self.setup_help_and_info_tabs()
        self.setup_sdr_tab()
        self.setup_os_terminal_tab()
        self.setup_log_tab()

        # Wenn APRS-IS konfiguriert ist, beim Start automatisch Marker setzen
        self.update_aprs_on_map_initial()

    
    def setup_weather_tab(self):
        # Einfacher Platzhalter-Text, damit der Tab nicht leer ist
        label = tk.Label(self.tab_wx, text="Wetterinformationen werden hier angezeigt.", font=("Arial", 12))
        label.pack(pady=20)
        
        for widget in self.tab_wx.winfo_children():
            widget.destroy()

        # Haupt-Container
        self.wx_main_frame = ttk.Frame(self.tab_wx)
        self.wx_main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # LINKER BEREICH: Aktuelle Messwerte (Großanzeige)
        self.wx_display_frame = ttk.LabelFrame(self.wx_main_frame, text=" Aktuelle Wetterdaten (APRS-WX) ")
        self.wx_display_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=5)

        # Variablen für die Anzeige
        self.wx_vars = {
            "temp": tk.StringVar(value="-- °C"),
            "hum": tk.StringVar(value="-- %"),
            "press": tk.StringVar(value="---- hPa"),
            "wind": tk.StringVar(value="-- km/h"),
            "rain": tk.StringVar(value="-- mm"),
            "station": tk.StringVar(value="Warte auf Daten...")
        }

        # Schicke Grid-Anordnung
        labels = [
            ("Temperatur:", self.wx_vars["temp"]),
            ("Feuchtigkeit:", self.wx_vars["hum"]),
            ("Luftdruck:", self.wx_vars["press"]),
            ("Windgeschw.:", self.wx_vars["wind"]),
            ("Niederschlag:", self.wx_vars["rain"]),
            ("Letzte Station:", self.wx_vars["station"])
        ]

        for i, (txt, var) in enumerate(labels):
            tk.Label(self.wx_display_frame, text=txt, font=("Arial", 11, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=10)
            tk.Label(self.wx_display_frame, textvariable=var, font=("Arial", 11), fg="white", bg="black").grid(row=i, column=1, sticky="w", padx=10, pady=10)

        # RECHTER BEREICH: Liste der WX-Stationen in der Nähe
        self.wx_list_frame = ttk.LabelFrame(self.wx_main_frame, text=" Empfangene Stationen ")
        self.wx_list_frame.pack(side=tk.RIGHT, fill="y", padx=5)

        self.wx_listbox = tk.Listbox(self.wx_list_frame, width=30, font=("Courier", 10))
        self.wx_listbox.pack(expand=True, fill="both", padx=5, pady=5)

    def setup_sdr_tab(self):
        # Einfacher Platzhalter-Text, damit der Tab nicht leer ist
        label = tk.Label(self.tab_sdr, text="SDR-Funktionen werden hier integriert.", font=("Arial", 12))
        label.pack(pady=20)
    
    # --------- UI-GRUNDSTRUKTUR & -ELEMENTE & Menü ----------
    def setup_menu(self):
        m = tk.Menu(self.root)
        self.root.config(menu=m)

        # DATEI
        datei_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Datei", menu=datei_m)
        datei_m.add_command(label="Beenden", command=self.root.quit)
        datei_m.add_command(label="Einsatz-Log drucken", command=lambda: self.print_message("\n".join(self.log_list.get(0, tk.END))))
        datei_m.add_command(label="...Abhängigkeiten erneut Prüfen !", command=self.check_dependencies)

        # EINSTELLUNGEN
        settings_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Einstellungen", menu=settings_m)
        settings_m.add_command(label="Hardware & Modi", command=self.show_config_window)
        settings_m.add_command(label="Externe Konsole", command=self.show_external_terminal_window)

        # Hilfe-Menü
        help_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Hilfe", menu=help_m)
        help_m.add_command(label="Hilfe & Handbuch", command=self.show_manual_window)
        help_m.add_command(label="Über NoFuS-TX", command=self.show_about_window)      

    def show_manual_window(self):
        try:
            self.help_notebook.select(self.sub_tab_manual)
            self.tabs.select(self.tab_help_main)
        except Exception:       
            messagebox.showinfo("Hilfe", "Der Hilfebereich ist derzeit nicht verfügbar.")

    def show_external_terminal_window(self):
        
        messagebox.showinfo("Externe Konsole", "Eine externe Konsole wird geöffnet. Bitte beachten Sie, dass dies von Ihrem Betriebssystem abhängt und möglicherweise nicht auf allen Systemen funktioniert.")

        sys_name = platform.system()
        
        try:
            if sys_name == "Linux":
                # Versuche xterm, da es meistens vorhanden ist
                subprocess.Popen(["xterm -bg black -fg green"], start_new_session=True)
            elif sys_name == "Windows":
                # Startet die CMD in einem neuen Fenster
                os.system("start cmd")
            elif sys_name == "Darwin": # Mac
                subprocess.Popen(["open", "-a", "Terminal"])
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Terminal nicht öffnen: {e}")

   # --- OS-Terminal Tab einrichten ---
    
    def setup_os_terminal_tab(self):
        # Haupt-Container für den Tab
        self.term_container = ttk.Frame(self.tab_os_terminal)
        self.term_container.pack(fill=tk.BOTH, expand=True)

        # Zuerst nur den Disclaimer zeigen
        self.show_terminal_disclaimer()

    def show_terminal_disclaimer(self):
        # Ein Frame für die Warnung, schön mittig platziert
        self.discl_frame = ttk.Frame(self.term_container)
        self.discl_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        msg = (
            "! SYSTEM-TERMINAL (INTEGRIERT)\n\n"
            "Dieses Terminal ist nur für einfache Systemabfragen gedacht.\n"
            "Nutzen Sie hier KEINE interaktiven Programme wie:\n"
            "nano, vi, mc, htop oder sudo-Abfragen.\n\n"
            "Für volle Funktionalität nutzen Sie bitte das 'Externe Terminal'\n"
            "über das Menü 'Einstellungen'."
        )
        
        tk.Label(self.discl_frame, text=msg, justify=tk.CENTER, font=("Arial", 10)).pack(pady=10)
        
        start_btn = ttk.Button(self.discl_frame, text="Ich habe verstanden - Konsole starten", 
                            command=self.activate_terminal)
        start_btn.pack(pady=10)

    def activate_terminal(self):
        # 1. Warnung entfernen
        if hasattr(self, 'discl_frame'):
            self.discl_frame.destroy()
        
        # 2. Dein funktionierendes tkterminal laden
        
        self.terminal = Terminal(self.term_container)
        self.terminal.pack(expand=True, fill='both')
        
        # 3. Konfiguration (shell=True für Linux/Win Befehle)
        self.terminal.shell = True 
        self.terminal.basename = "NoFuS-TX # "
        
        # Fokus setzen, damit man sofort tippen kann
        self.terminal.focus_set()
        
    # --- NEU: Unter-Notebook für den Hilfe-Bereich mit drei Tabs ---
    def setup_help_and_info_tabs(self):
        """Erstellt das Unter-Notebook für den Hilfe-Bereich."""
        self.help_notebook = ttk.Notebook(self.tab_help_main)
        self.help_notebook.pack(expand=1, fill="both", padx=5, pady=5)

        # Definition der Unter-Tabs
        self.sub_tab_check = ttk.Frame(self.help_notebook)
        self.sub_tab_bands = ttk.Frame(self.help_notebook)
        self.sub_tab_manual = ttk.Frame(self.help_notebook)

        self.help_notebook.add(self.sub_tab_check, text=" [*] Checkliste ")
        self.help_notebook.add(self.sub_tab_bands, text=" i Bandpläne / Frequenzen ")
        self.help_notebook.add(self.sub_tab_manual, text=" ? Hilfe ")

        # Funktionen die die Tabs füllen
        self.build_checklist_content(self.sub_tab_check)
        self.build_frequency_tables(self.sub_tab_bands)
        self.setup_manual_tab_content(self.sub_tab_manual)

    # --- NEU: Inhalte für den "Hilfe"-Tab mit PDF-Auswahl und externem Öffnen ---

    def setup_manual_tab_content(self, parent_frame):
        
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # --- LINKS: Anzeige & Scrollbar ---
        self.left_info_frame = ttk.Frame(main_frame)
        self.left_info_frame.pack(side=tk.LEFT, expand=True, fill="both")

        # Steuerung für Seiten (ÜBER dem Canvas für bessere Sichtbarkeit)
        self.page_ctrl_frame = ttk.Frame(self.left_info_frame)
        self.page_ctrl_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.btn_prev = ttk.Button(self.page_ctrl_frame, text="◀ Zurück", command=lambda: self.change_page(-1), state="disabled")
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        
        self.page_label = tk.Label(self.page_ctrl_frame, text="Seite: - / -", font=("Arial", 10))
        self.page_label.pack(side=tk.LEFT, expand=True)
        
        self.btn_next = ttk.Button(self.page_ctrl_frame, text="Weiter ▶", command=lambda: self.change_page(1), state="disabled")
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Canvas-Setup (unverändert)
        self.pdf_scroll = ttk.Scrollbar(self.left_info_frame, orient=tk.VERTICAL)
        self.pdf_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pdf_canvas = tk.Canvas(self.left_info_frame, bg="gray70", yscrollcommand=self.pdf_scroll.set)
        self.pdf_canvas.pack(side=tk.LEFT, expand=True, fill="both")
        self.pdf_scroll.config(command=self.pdf_canvas.yview)

        self.info_label = tk.Label(self.pdf_canvas, text="Keine Datei gewählt", 
                                   font=("Arial", 11, "italic"), fg="gray", bg="white")
        self.canvas_window = self.pdf_canvas.create_window((0, 0), window=self.info_label, anchor="nw")

        # --- RECHTER BEREICH: Buttons ---
        self.right_button_frame = ttk.Frame(main_frame)
        self.right_button_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(self.right_button_frame, text="Handbücher / Pläne / Informatives", 
                  font=("Arial", 10, "bold")).pack(pady=(0, 10))

        # Hier werden die PDF-Buttons via refresh_pdf_buttons reingeladen
        self.current_selected_pdf = None
        self.refresh_pdf_buttons()
        
        # Der "Extern Öffnen" Button (jetzt rechts unten!)
        self.btn_open_extern = ttk.Button(self.right_button_frame, text="Dokument extern öffnen", 
                                        command=self.open_current_pdf, state="disabled")
        self.btn_open_extern.pack(side=tk.BOTTOM, pady=20, ipadx=10, ipady=5)

    def refresh_pdf_buttons(self):
        # Assets Pfad prüfen
        assets_path = os.path.join(os.getcwd(), "assets")
        if not os.path.exists(assets_path):
            os.makedirs(assets_path)

        # Alle PDFs holen
        
        pdf_files = glob.glob(os.path.join(assets_path, "*.pdf"))

        if not pdf_files:
            tk.Label(self.right_button_frame, text="Ordner 'assets/'\nist leer.", fg="red", font=("Arial", 9)).pack()
        else:
            for pdf in pdf_files:
                name = os.path.basename(pdf)
                # Button mit dynamischem Abstand (pady=5)
                btn = ttk.Button(self.right_button_frame, text=name, 
                                command=lambda p=pdf, n=name: self.select_pdf(p, n))
                btn.pack(fill="x", padx=5, pady=3)

    
    def select_pdf(self, path, name):
        self.current_selected_pdf = path
        self.btn_open_extern.config(state="normal")
        
        # PDF im Tool anzeigen
        self.display_pdf_preview(path)

    def display_pdf_preview(self, path, page_num=0):
        try:
            doc = fitz.open(path) # type: ignore
            self.total_pages = len(doc)
            self.current_page = page_num
            
            page = doc[self.current_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)) # Dein Zoom 1.2 # type: ignore
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples) # type: ignore
            self.tk_img = ImageTk.PhotoImage(img) # type: ignore
            
            self.info_label.config(image=self.tk_img, text="") 
            self.pdf_canvas.config(scrollregion=(0, 0, pix.width, pix.height))
            self.pdf_canvas.yview_moveto(0)
            
            # Label & Button-Zustände aktualisieren
            self.page_label.config(text=f"Seite: {self.current_page + 1} / {self.total_pages}")
            self.btn_prev.config(state="normal" if self.current_page > 0 else "disabled")
            self.btn_next.config(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
            
            doc.close()
        except Exception as e:
            messagebox.showerror("Fehler", f"Vorschau fehlgeschlagen: {e}")

    def change_page(self, delta):
        if hasattr(self, 'current_selected_pdf') and self.current_selected_pdf:
            new_page = self.current_page + delta
            if 0 <= new_page < self.total_pages:
                self.display_pdf_preview(self.current_selected_pdf, new_page)

    def open_current_pdf(self):
        if self.current_selected_pdf:
            p = self.current_selected_pdf
            try:
                if platform.system() == "Windows":
                    os.startfile(p) # type: ignore
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", p])
                else:
                    subprocess.Popen(["xdg-open", p])
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte PDF nicht öffnen: {e}")

    # --- NEU: Inhalte für die Checklisten- und Frequenz-Tabs ---
    def build_checklist_content(self, parent):
        # Ein Rahmen für die Hardware
        frame_hw = ttk.LabelFrame(parent, text=" Hardware & Funk ")
        frame_hw.pack(fill="x", padx=10, pady=5)

        # Die einzelnen Punkte
        items_hw = [
            "Funkgerät & Ersatzgerät geprüft",
            "Antennen & Kabel (SWR-Check)",
            "Stromversorgung (Akkus geladen, Netzteil)",
            "Laptop & Interface-Kabel (Oder Tablet mit APK's)",
            "Handfunkgeräte & Ersatzbatterien",
            "Notfall-APRS-Tracker (z.B. SPOT, Garmin InReach)"
        ]

        for item in items_hw:
            var = tk.BooleanVar()
            # WICHTIG: master=frame_hw, damit es im Rahmen landet
            cb = ttk.Checkbutton(frame_hw, text=item, variable=var)
            cb.pack(anchor="w", padx=5, pady=2)

        # Ein Rahmen für die Dokumente
        frame_doc = ttk.LabelFrame(parent, text=" Dokumentation ")
        frame_doc.pack(fill="x", padx=10, pady=5)

        items_doc = [
            "NoFu-Satz PDF / Ausdruck",
            "Frequenzliste (Lokal)",
            "Logbuch & Stifte",
            "Bandpläne",
            "IARU Not-Mitteilungsvorlage",
            "Karten"
        ]
        for item in items_doc:
            var = tk.BooleanVar()
            ttk.Checkbutton(frame_doc, text=item, variable=var).pack(anchor="w", padx=5, pady=2)

    # --- Bandpläne und Frequenzübersichten ---
    def build_frequency_tables(self,parent):
        self.freq_tree = ttk.Treeview(parent, columns=("Mode", "Frequenz", "Beschreibung"), show="headings")
        self.freq_tree.heading("Mode", text="Mode")
        self.freq_tree.heading("Frequenz", text="Frequenz",)
        self.freq_tree.heading("Beschreibung", text="Beschreibung")
        self.freq_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.freq_tree.column("Mode", width=50, anchor="center")
        self.freq_tree.column("Frequenz", width=90, anchor="w")
        self.freq_tree.column("Beschreibung", width=650, anchor="w")
        
        freq_list = self.frequencies.get("FREQUENCIES", [])

        for zeile in freq_list:
            self.freq_tree.insert("", "end", values=(zeile[0], zeile[1], zeile[2]))

        # Ein Trenner für die Optik
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(parent, text="Grafische Bandübersicht", font=("Arial", 10, "bold")).pack()

        # Das Unter-Notebook für die einzelnen Bänder
        self.bandplan_notebook = ttk.Notebook(parent)
        self.bandplan_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.load_and_build_bandplans(self.bandplan_notebook)

    # --- NEU: Dynamisches Laden der Bandpläne aus JSON und grafische Darstellung ---
    def load_and_build_bandplans(self, parent_notebook):
        # Datei laden (Fehlerbehandlung mit try/except wäre gut)
        with open("band_plan.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for band in data.get("BANDS", []):
            # 1. Frame für den Tab erstellen
            tab_frame = ttk.Frame(parent_notebook)
            parent_notebook.add(tab_frame, text=f" {band['name']} ")
            
            # 2. Grafik zeichnen (bestehende Funktion)
            # Übergeben der Segmente direkt aus der JSON
            self.draw_band_diagram(tab_frame, band.get("segments", []))
            
            # 3. Kommentare/Infotext hinzufügen (falls vorhanden)
            comment_text = band.get("comments", "")
            if comment_text:
                lbl = ttk.Label(tab_frame, text=comment_text, 
                                font=("Arial", 8, "italic"), justify="left")
                lbl.pack(pady=10, padx=10, anchor="w")

    # --- Bandplan grafik zeichnen ---
    def draw_band_diagram(self, parent, segments):
        """
        Zeigt einen farbigen Balken an. 
        'segments' ist eine Liste von (Start, Ende, Farbe, Label)
        """
        canvas = tk.Canvas(parent, height=60, bg="white", highlightthickness=1, relief="sunken")
        canvas.pack(fill="x", padx=10, pady=5)

        # Wir berechnen die Breite dynamisch
        def update_width(event):
            canvas.delete("all")
            w = event.width
            # Start- und Endfrequenz des Segments bestimmen (für die Skalierung)
            min_f = segments[0][0]
            max_f = segments[-1][1]
            range_f = max_f - min_f

            for start, end, color, label in segments:
                # Berechne Position auf dem Balken
                x1 = ((start - min_f) / range_f) * w
                x2 = ((end - min_f) / range_f) * w
                
                # Zeichne das farbige Rechteck (DARC-Stil)
                canvas.create_rectangle(x1, 0, x2, 40, fill=color, outline="black")
                # Beschriftung (nur wenn Platz ist)
                if (x2 - x1) > 40:
                    canvas.create_text((x1 + x2) / 2, 20, text=label, font=("Arial", 8, "bold"))
            
            # Skala unten drunter
            canvas.create_text(5, 52, text=f"{min_f} MHz", anchor="w")
            canvas.create_text(w-5, 52, text=f"{max_f} MHz", anchor="e")

        canvas.bind("<Configure>", update_width)

    def on_closing(self):
        print("[System] Beende NoFuSTX...")
        if hasattr(self, 'map_widget'):
            
            try:
                self.map_widget.database_path = None # type: ignore
                print("[Map] Datenbank sauber synchronisiert.")
            except:
                pass
        self.root.destroy()

    def is_online(self):
        """Prüft robust, ob eine Internetverbindung besteht."""
        try:
            # Test um zu sehen, ob eine Verbindung zum Internet besteht, via Google
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except (socket.timeout, socket.error, OSError):
            return False

    def setup_map_view(self):
        """Initialisiert die Karte stabil ohne fehlerhaftes Pre-Caching."""
        
        if tkintermapview is None:
            tk.Label(self.tab_map, text="Karte nicht verfügbar").pack(expand=1)
            return

        # 1. Pfade
        map_folder = os.path.join(base_path, "off_Maps")
        os.makedirs(map_folder, exist_ok=True)
        db_path = os.path.join(map_folder, "offline_tiles.db")

        # 2. Online-Check
        online_status = False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1.0)
            online_status = True
        except: online_status = False
        
        print(f"[Map] {'🌐 ONLINE' if online_status else '🔌 OFFLINE'} aktiv.")

        # 3. Widget erstellen (Stabilster Weg)
        
        try:
            self.map_widget = tkintermapview.TkinterMapView(
                self.tab_map, 
                corner_radius=0,
                database_path=db_path,
                use_database_only=(not online_status),
                max_zoom=19
            )
        except Exception as e:
            print(f"[Map] Fehler beim Erstellen: {e}")
            self.map_widget = tkintermapview.TkinterMapView(self.tab_map, corner_radius=0)

        self.map_widget.pack(expand=1, fill="both")

        # 4. Start-Position
        map_conf = self.config.get("MAP", {})
        lat = float(map_conf.get("home_lat", 51.9621))
        lon = float(map_conf.get("home_lon", 9.6509))
        zoom = int(map_conf.get("zoom", 13))

        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(zoom)

        # 5. DB-Größe zur Kontrolle ausgeben
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"[Map] Status DB: {size / 1024:.1f} KB")
        
        # 6. Manueller Save-Button (unten rechts auf der Karte)
        self.btn_save_map = tk.Button(
            self.map_widget, 
            text="Region Cachen", 
            command=self.manual_tile_save,
            bg="#f0f0f0",
            fg="black",
            font=("Arial", 9, "bold"),
            relief="raised"
        )
        # Positionierung: 10 Pixel vom rechten und unteren Rand entfernt
        self.btn_save_map.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

    def manual_tile_save(self):
        """Startet den Offline-Download in einem Hintergrund-Thread."""
        db_path = os.path.join(base_path, "off_Maps", "offline_tiles.db")
        current_pos = self.map_widget.get_position()
        zoom = int(self.map_widget.zoom)

        def download_thread():
            from tkintermapview import OfflineLoader
            try:
                loader = OfflineLoader(path=db_path)
                
                # Bereich definieren (ca. 5-10km Radius)
                offset = 0.25 
                top_left = (current_pos[0] + offset, current_pos[1] - offset)
                bottom_right = (current_pos[0] - offset, current_pos[1] + offset)

                print(f"[*] Hintergrund-Download gestartet für Zoom {zoom}...")
                # Hier startet die Multithread-Action der Library
                loader.save_offline_tiles(top_left, bottom_right, zoom, zoom + 6)
                
                print(f"[*] Download beendet. DB: {os.path.getsize(db_path)/1024/1024:.2f} MB")
                # GUI Button wieder zurücksetzen (muss via after geschehen!)
                self.root.after(0, lambda: self.btn_save_map.config(bg="#27ae60", text="✅ Fertig"))
            except Exception as e:
                print(f" Fehler im Download-Thread: {e}")

        # Button auf "Beschäftigt" setzen
        self.btn_save_map.config(bg="#f39c12", text="⏳ Lädt im Hintergrund...")
        
        # Den Thread starten und "daemon" machen, damit er beim Schließen der App mit stirbt
        bg_thread = threading.Thread(target=download_thread, daemon=True)
        bg_thread.start()

    def update_aprs_on_map(self):
        # dieser Button ist obsolet; APRS-Marker werden stattdessen aus den eingehenden Positionsdaten erzeugt

        pass

    def update_aprs_on_map_initial(self):
        """
        Startet – falls konfiguriert – mit einem APRS-Marker, ohne den Nutzer
        mit Warnmeldungen zu stören. Wird einmalig beim Programmstart aufgerufen.
        """
        # Kein automatischer "Station: ..." Marker mehr
        return
    # ---------- FUNDUS / UNITS ----------
    def setup_fundus_tab(self):
        # Vollständiger Fundus mit Status-Umschaltung und Löschen
        for w in self.tab_fundus.winfo_children():
            w.destroy()

        lbl = tk.Label(
            self.tab_fundus,
            text="Einheitenübersicht & Personal (Fundus)",
            font=("Arial", 12, "bold"),
        )
        lbl.pack(pady=10)

        cols = ("Name", "Typ", "Status")
        self.tree = ttk.Treeview(
            self.tab_fundus, columns=cols, show="headings", height=15
        )
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=20, pady=5)

        self.refresh_unit_tree()

        btn_f = ttk.Frame(self.tab_fundus)
        btn_f.pack(pady=10)

        ttk.Button(
            btn_f,
            text="Einheit hinzufügen",
            # command=lambda: messagebox.showinfo("Info", "Funktion in v1.9.14 geplant."),
            command=self.add_unit
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Status ändern", command=self.toggle_unit_status
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Einheit löschen", command=self.delete_unit
        ).pack(side="left", padx=5)

    # --- Neue Einheit hinzufügen ---
    def add_unit(self):
        """Erstellt eine neue Einheit und speichert sie in der Config."""
        # 1. Ein kleines Eingabefenster öffnen
        dialog = tk.Toplevel(self.root)
        dialog.title("Neue Einheit")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="Name/Rufname:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(padx=10, fill="x")

        # 2. Typ als Dropdown (Combobox)
        ttk.Label(dialog, text="Typ der Einheit:").pack(pady=5)
        
        # Vorab Deffinition der Einheiten
        fzg_typen = [
            "NoFuS-SE (Stationäre Einsatzleitung)",
            "NoFuS-S (Mobile Einsatzleitung)",
            "NoFuS-M (Mobile Einheit)",
            "NoFuS-M+ (Mobile Einheit mit Rettungsdienstlicher / Feuerwehrtechnischer o.ä. Ausbildung)",
            "NoFuS-M-F (Mobile Einheit Ohne Afu Lizensierung)",
            "NoFuS-M-F+ (Mobile Einheit Ohne Afu Lizensierung, mit Rettungsdienstlicher / Feuerwehrtechnischer o.ä. Ausbildung)",
            "NoFuS-P (Portabel Einheit)",
            "NoFuS-P+ (Portabel Einheit mit Rettungsdienstlicher / Feuerwehrtechnischer o.ä. Ausbildung)",
            "NoFuS-P-F (Portabel Einheit Ohne Afu Lizensierung)",
            "NoFuS-P-F+ (Portabel Einheit Ohne Afu Lizensierung, mit Rettungsdienstlicher / Feuerwehrtechnischer o.ä. Ausbildung)"
        ]
        
        type_dropdown = ttk.Combobox(dialog, values=fzg_typen, state="readonly")
        type_dropdown.pack(padx=20, fill="x")
        type_dropdown.set("NoFuS-SE (Stationäre Einsatzleitung)") # Standardwert

        # --- 3. Speichern-Button mit Funktionalität
        def save():
            name = name_entry.get().strip()
            u_type = type_dropdown.get().strip()
            
            if name and u_type:
                # Neue Einheit als Dict anlegen
                new_entry = {"name": name, "type": u_type, "status": "True"}
                
                # In die Liste in der Config einfügen
                if "UNITS" not in self.config:
                    self.config["UNITS"] = []
                
                self.config["UNITS"].append(new_entry)
                
                # Genau wie beim Löschen: Speichern und Liste neu zeichnen
                self.save_settings()
                self.refresh_unit_tree()
                
                dialog.destroy()
            else:
                messagebox.showwarning("Fehler", "Bitte alles ausfüllen!")

        ttk.Button(dialog, text="Hinzufügen", command=save).pack(pady=15)

    # --- Einheitstabelle aktualisieren --
    def refresh_unit_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in self.config.get("UNITS", []):
            stat_text = "EINSATZBEREIT" if u.get("status") else "NICHT AKTIV"
            self.tree.insert("", "end", values=(u["name"], u["type"], stat_text))

    # --- Status wechseln ---
    def toggle_unit_status(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self.config["UNITS"][idx]["status"] = not self.config["UNITS"][idx]["status"]
            self.save_settings()
            self.refresh_unit_tree()

    # --- Einheit löschen ---
    def delete_unit(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Löschen", "Einheit entfernen?"):
            idx = self.tree.index(sel[0])
            del self.config["UNITS"][idx]
            self.save_settings()
            self.refresh_unit_tree()

    # ---------- IARU MELDUNG ----------
    def setup_message_tab(self):
        # IARU-Formular, das sich dynamisch mit dem Hauptfenster mitskaliert
        for w in self.tab_msg.winfo_children():
            w.destroy()

        # Grid-Layout für den ganzen Tab aktivieren
        self.tab_msg.rowconfigure(0, weight=0)   # Kopfzeile
        self.tab_msg.rowconfigure(1, weight=0)   # Wichtigkeit
        self.tab_msg.rowconfigure(2, weight=1)   # Meldungstext (soll wachsen)
        self.tab_msg.rowconfigure(3, weight=0)   # Buttonzeile
        self.tab_msg.columnconfigure(0, weight=1)
        
        # Kopfdaten
        header_f = ttk.LabelFrame(self.tab_msg, text="Kopfdaten (IARU Standard)")
        header_f.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        titles = ["Nummer", "Quelle / Station", "Wort-Zähler", "Herkunft", "Zeit (UTC)", "Datum"]
        self.msg_fields = {}

        for i, title in enumerate(titles):
            header_f.columnconfigure(i, weight=1)
            tk.Label(header_f, text=title).grid(row=0, column=i, padx=5, sticky="w")
            
            if title == "Zeit (UTC)":
                # Container für Feld + Checkbox
                time_container = ttk.Frame(header_f)
                time_container.grid(row=1, column=i, sticky="ew")
                time_container.columnconfigure(0, weight=1) # Entry soll wachsen

                ent = ttk.Entry(time_container)
                ent.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="ew")
                self.msg_fields[title] = ent

                self.auto_time_var = tk.BooleanVar(value=True)
                cb = tk.Checkbutton(time_container, text="Auto", variable=self.auto_time_var)
                cb.grid(row=0, column=1, padx=(0, 5))
            else:
                ent = ttk.Entry(header_f)
                ent.grid(row=1, column=i, padx=5, pady=5, sticky="ew")
                self.msg_fields[title] = ent

        # Zeit & Datum vorbelegen (UTC)
        self.msg_fields["Zeit (UTC)"].insert(
            0, datetime.datetime.utcnow().strftime("%H:%M:%S")
        )
        self.msg_fields["Datum"].insert(
            0, datetime.datetime.utcnow().strftime("%d.%m.%Y")
        )

        self.msg_fields["Nummer"].insert(0, str(self.counter_number_msg))  # Standard-Nummer 1 für die erste Meldung
        self.update_iaru_time()

        # Wichtigkeit
        prio_f = ttk.LabelFrame(self.tab_msg, text="Wichtigkeit")
        prio_f.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self.prio_var = tk.StringVar(value="Routine")
        for p in ["Routine", "Priorität", "RETTUNG / HILFE"]:
            ttk.Radiobutton(prio_f, text=p, variable=self.prio_var, value=p).pack(
                side="left", padx=20
            )

        # Meldungstext + Scrollbar
        body_f = ttk.LabelFrame(self.tab_msg, text="Meldung (Druckbuchstaben)")
        body_f.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        body_f.rowconfigure(0, weight=1)
        body_f.columnconfigure(0, weight=1)

        self.msg_text = tk.Text(body_f, font=("Courier", 12), wrap="word")
        self.msg_text.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)

        text_scroll = ttk.Scrollbar(
            body_f, orient="vertical", command=self.msg_text.yview
        )
        text_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        self.msg_text.configure(yscrollcommand=text_scroll.set)

        # Untere Steuerleiste: Digimode-Auswahl, Druck-Option, Buttons
        control_f = ttk.Frame(self.tab_msg)
        control_f.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        for i in range(5):
            control_f.columnconfigure(i, weight=0)
        control_f.columnconfigure(2, weight=1)

        ttk.Label(control_f, text="Digimode:").grid(row=0, column=0, padx=5, sticky="w")

        modes = ["Nur Log"]
        for mode, data in self.config["MODES"].items():
            # Alle aktiven Modi für Text-Übertragung anbieten
            if mode in ("RTTY", "WINLINK", "JS8CALL", "VARA", "MT63") and data.get("active"):
                modes.append(mode)

        self.send_mode_var = tk.StringVar(value=modes[0])
        self.send_mode_combo = ttk.Combobox(
            control_f, values=modes, textvariable=self.send_mode_var, state="readonly", width=12
        )
        self.send_mode_combo.grid(row=0, column=1, padx=5, sticky="w")

        self.print_on_send = tk.BooleanVar(
            value=self.config.get("PRINTER", {}).get("auto_print", False)
        )
        tk.Checkbutton(
            control_f, text="Beim Senden drucken", variable=self.print_on_send
        ).grid(row=0, column=2, padx=10, sticky="w")

        ttk.Button(
            control_f, text="Nur ins Log", command=self.log_iaru_msg
        ).grid(row=0, column=3, padx=5, sticky="e")

        ttk.Button(
            control_f, text="Senden & Loggen", command=self.send_iaru_msg
        ).grid(row=0, column=4, padx=5, sticky="e")

        ttk.Button(
            control_f, text="Leeren", command=self.clear_iaru_form
        ).grid(row=0, column=5, padx=5, sticky="e")

        self.msg_text.bind("<KeyRelease>", self.update_word_count)

    # --- Meldungstext leeren und Formular für neue Meldung vorbereiten ---
    def clear_iaru_form(self):
        """Leert alle Felder des IARU-Formulars für eine neue Meldung."""

        self.counter_number_msg += 1  # Nummer für die nächste Meldung erhöhen
        # print(f"Vorbereitet für Meldung Nr. {self.counter_number_msg}.")  # Debug-Ausgabe
        # Alle Entry-Felder in der Kopfzeile leeren
        for title, field in self.msg_fields.items():
            field.delete(0, tk.END)
        
        # Das große Textfeld leeren
        self.msg_text.delete("1.0", tk.END)
        
        # Wichtigkeit auf Standard zurücksetzen
        self.prio_var.set("Routine")
        
        # Datum und Zeit sofort wieder neu belegen
        self.msg_fields["Datum"].insert(0, datetime.datetime.utcnow().strftime("%d.%m.%Y"))
        # Die Zeit wird durch update_iaru_time automatisch befüllt, wenn Auto aktiv ist
        
        # Wort-Zähler auf 0 setzen
        self.update_word_count()
        
        self.msg_fields["Nummer"].insert(0, str(self.counter_number_msg))  # Neue Nummer eintragen
        # print("IARU-Formular wurde geleert.")

    # --- Wort-Zähler aktualisieren ---
    def update_word_count(self, event=None):
     """Zählt die Wörter im Textfeld und schreibt sie in das Feld 'Wort-Zähler'."""
     content = self.msg_text.get("1.0", tk.END).strip()
     if not content:
         count = 0
     else:
         # Zählt alles, was durch Leerzeichen getrennt ist
         count = len(content.split())

     field = self.msg_fields["Wort-Zähler"]
     field.delete(0, tk.END)
     field.insert(0, str(count))

    # --- Automatische UTC-Zeitaktualisierung ---
    def update_iaru_time(self):
        """Aktualisiert die UTC-Zeit im Formular, wenn Auto-Zeit aktiv ist."""
        # Prüfen, ob das Tab/Feld überhaupt noch existiert (vermeidet Fehler beim Schließen)
        if "Zeit (UTC)" in self.msg_fields and self.msg_fields["Zeit (UTC)"].winfo_exists():
            if self.auto_time_var.get():
                now = datetime.datetime.utcnow().strftime("%H:%M:%S")
                # Feld leeren und neue Zeit rein
                self.msg_fields["Zeit (UTC)"].delete(0, tk.END)
                self.msg_fields["Zeit (UTC)"].insert(0, now)
        
        # Die Funktion ruft sich nach 1000ms (1 Sekunde) selbst wieder auf
        self.root.after(1000, self.update_iaru_time)

    # ---------- Über NoFuS-TX ----------
    def show_about_window(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("Über NoFuS-TX")
        about_win.geometry("400x300")

        tk.Label(about_win, text="NoFuS-TX - Einsatzleitsoftware v1.9.15b").pack(pady=10)
        tk.Label(about_win, text="© 2026 NoFuS-TX DO2ITH").pack(pady=5)
        tk.Label(about_win, text="Alle Rechte vorbehalten.").pack(pady=10)
        tk.Label(about_win, text="E-Mail: info@ithnet.de").pack(pady=10)
        tk.Label(about_win, text="Land: Deutschland").pack(pady=10)
        tk.Label(about_win, text="Webseite: https://www.ithnet.de").pack(pady=10)
        tk.Label(about_win, text="GitHub: https://github.com/jochenkurzschluss/NoFuSTX").pack(pady=10)

    # ---------- KONFIGURATION ----------
    def show_config_window(self):
        # Hardware- & Modi-Konfiguration inkl. Drucker und SSTV-Spezialfeldern
        win = tk.Toplevel(self.root)
        win.title("Hardware Konfiguration")
        win.geometry("800x700")
        try:
            # Erstmal das Wetter Icon
            conf_icon = tk.PhotoImage(file="icons/settings.png") 
            win.iconphoto(False, conf_icon)
            # Referenz speichern, damit das Icon im Speicher bleibt
            win._icon_ref = conf_icon # type: ignore
        except Exception as e:
            print(f"Fehler beim Laden des Konfigurations-Icons: {e}")

        nb = ttk.Notebook(win)
        nb.pack(expand=1, fill="both", padx=5, pady=5)

        self.temp_entries = {}  # Initialisiere temp_entries

        # JS8Call
        js8_f = ttk.Frame(nb)
        nb.add(js8_f, text="JS8Call")
        params = self.config["MODES"]["JS8CALL"]
        self.temp_entries["JS8CALL"] = {}

        v = tk.BooleanVar(value=params.get("active", False))
        tk.Checkbutton(js8_f, text="JS8Call Aktiv", variable=v).pack(pady=10)
        self.temp_entries["JS8CALL"]["active"] = v

        tk.Label(js8_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(js8_f)
        freq_ent.insert(0, str(params.get("frequency", "7.078 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["JS8CALL"]["frequency"] = freq_ent

        tk.Label(js8_f, text="CALLSIGN:").pack()
        call_ent = ttk.Entry(js8_f)
        call_ent.insert(0, str(params.get("callsign", "NOCALL")))
        call_ent.pack(pady=2)
        self.temp_entries["JS8CALL"]["callsign"] = call_ent

        tk.Label(js8_f, text="SOUNDCARD:").pack()
        sc_cb = ttk.Combobox(js8_f, values=["System", "USB Codec", "Virtual"])
        sc_cb.set(params.get("soundcard", "System"))
        sc_cb.pack(pady=2)
        self.temp_entries["JS8CALL"]["soundcard"] = sc_cb

        # VARA (ähnlich)
        vara_f = ttk.Frame(nb)
        nb.add(vara_f, text="VARA")
        params = self.config["MODES"]["VARA"]
        self.temp_entries["VARA"] = {}

        v = tk.BooleanVar(value=params.get("active", False))
        tk.Checkbutton(vara_f, text="VARA Aktiv", variable=v).pack(pady=10)
        self.temp_entries["VARA"]["active"] = v

        tk.Label(vara_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(vara_f)
        freq_ent.insert(0, str(params.get("frequency", "14.105 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["VARA"]["frequency"] = freq_ent

        tk.Label(vara_f, text="CALLSIGN:").pack()
        call_ent = ttk.Entry(vara_f)
        call_ent.insert(0, str(params.get("callsign", "NOCALL")))
        call_ent.pack(pady=2)
        self.temp_entries["VARA"]["callsign"] = call_ent

        tk.Label(vara_f, text="SOUNDCARD:").pack()
        sc_cb = ttk.Combobox(vara_f, values=["System", "USB Codec", "Virtual"])
        sc_cb.set(params.get("soundcard", "System"))
        sc_cb.pack(pady=2)
        self.temp_entries["VARA"]["soundcard"] = sc_cb

        # MT63 (ähnlich, mit bandwidth)
        mt63_f = ttk.Frame(nb)
        nb.add(mt63_f, text="MT63")
        params = self.config["MODES"]["MT63"]
        self.temp_entries["MT63"] = {}

        v = tk.BooleanVar(value=params.get("active", False))
        tk.Checkbutton(mt63_f, text="MT63 Aktiv", variable=v).pack(pady=10)
        self.temp_entries["MT63"]["active"] = v

        tk.Label(mt63_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(mt63_f)
        freq_ent.insert(0, str(params.get("frequency", "7.040 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["MT63"]["frequency"] = freq_ent

        tk.Label(mt63_f, text="BANDWIDTH:").pack()
        bw_cb = ttk.Combobox(mt63_f, values=["500Hz", "1k", "2k"])
        bw_cb.set(params.get("bandwidth", "1k"))
        bw_cb.pack(pady=2)
        self.temp_entries["MT63"]["bandwidth"] = bw_cb

        tk.Label(mt63_f, text="SOUNDCARD:").pack()
        sc_cb = ttk.Combobox(mt63_f, values=["System", "USB Codec", "Virtual"])
        sc_cb.set(params.get("soundcard", "System"))
        sc_cb.pack(pady=2)
        self.temp_entries["MT63"]["soundcard"] = sc_cb

        # AX.25 Ports
        ax_f = ttk.Frame(nb)
        nb.add(ax_f, text="AX.25 Ports")

        self.ax_scroll_f = ttk.Frame(ax_f)
        self.ax_scroll_f.pack(fill="both", expand=True)
        self.ax_temp_list = []

        def render_ax_ports():
            for w in self.ax_scroll_f.winfo_children():
                w.destroy()
            self.ax_temp_list = []

            
            for i, port in enumerate(self.config["MODES"]["AX25_PORTS"]):
                p_frame = ttk.LabelFrame(self.ax_scroll_f, text=f"AX.25 Port #{i}")
                p_frame.pack(fill="x", padx=10, pady=2)

                v = tk.BooleanVar(value=port.get("active", False))
                tk.Checkbutton(p_frame, text="Aktiv", variable=v).grid(row=0, column=0)

                dev = ttk.Combobox(p_frame, values=self.options["AX25_DEVICES"], width=8)
                dev.set(port.get("device", "ax0"))
                dev.grid(row=0, column=1, padx=5)

                nick = ttk.Entry(p_frame, width=15)
                nick.insert(0, port.get("nickname", ""))
                nick.grid(row=0, column=2, padx=5)

                call = ttk.Entry(p_frame, width=10)
                call.insert(0, port.get("call", "NOCALL"))
                call.grid(row=0, column=3, padx=5)

                btn_del = ttk.Button(p_frame, text="X", width=3, 
                                     command=lambda idx=i: dummy(idx))
                btn_del.grid(row=0, column=4, padx=5)

                self.ax_temp_list.append(
                    {"active": v, "device": dev, "nickname": nick, "call": call}
                )
        render_ax_ports()

        # --- Button zum Hinzufügen eines neuen Ports
        def add_ax_port():
            dialog_ax_add = tk.Toplevel(self.root)
            dialog_ax_add.title("Neuen AX.25 Port hinzufügen")
            dialog_ax_add.geometry("300x150")
            ttk.Label(dialog_ax_add, text="Gerät (z.B. ax0):").pack(pady=5)
            ttk.Label(dialog_ax_add, text="Nickname:").pack(pady=5)
            ttk.Label(dialog_ax_add, text="call").pack(pady=5)

            # self.config["MODES"]["AX25_PORTS"].append(
            #     {"active": False, "device": "ax0", "nickname": "", "call": "NOCALL"}
            # )
            render_ax_ports()

        def dummy(idx):
            if messagebox.askyesno("Löschen", f"AX.25 Port #{idx} entfernen?"):
                # del self.config["MODES"]["AX25_PORTS"][idx]
                render_ax_ports()
        # Drucker
        pr_f = ttk.Frame(nb)
        nb.add(pr_f, text="Drucker")

        ttk.Label(pr_f, text="Drucker:").pack(pady=5)
        printers = self.get_system_printers()

        self.prn_name = ttk.Combobox(pr_f, values=printers)
        current_printer = self.config.get("PRINTER", {}).get("name", "")
        if current_printer and current_printer in printers:
            self.prn_name.set(current_printer)
        elif printers:
            self.prn_name.set(printers[0])
        self.prn_name.pack(pady=5, padx=10, fill="x")

        self.prn_auto = tk.BooleanVar(
            value=self.config.get("PRINTER", {}).get("auto_print", False)
        )
        tk.Checkbutton(pr_f, text="Auto-Print", variable=self.prn_auto).pack(pady=10)

        # Weitere Modi (inkl. SSTV-Spezialfall), aber nur für Modi ohne eigene Tabs
        for mode, params in self.config["MODES"].items():
            if mode in ("AX25_PORTS", "JS8CALL", "VARA", "MT63"):  # Diese haben eigene Tabs
                continue

            f = ttk.Frame(nb)
            nb.add(f, text=mode)
            # self.temp_entries[mode] wird bereits oben gesetzt, also nicht neu initialisieren
            if mode not in self.temp_entries:
                self.temp_entries[mode] = {}

            v = tk.BooleanVar(value=params.get("active", False))
            tk.Checkbutton(f, text=f"{mode} Aktiv", variable=v).pack(pady=10)
            self.temp_entries[mode]["active"] = v

            if mode == "SSTV":
                tk.Label(f, text="SSTV MODUS:").pack()
                ms = ttk.Combobox(f, values=self.options["SSTV_MODES"])
                ms.set(params.get("mode", "Martin 1"))
                ms.pack()
                self.temp_entries[mode]["mode"] = ms

                tk.Label(f, text="SOUNDKARTE:").pack()
                ss = ttk.Combobox(f, values=["System", "USB Codec", "Virtual"])
                ss.set(params.get("soundcard", "System"))
                ss.pack()
                self.temp_entries[mode]["soundcard"] = ss
            elif mode == "RTTY":
                # Spezielle RTTY-Konfiguration inkl. Soundkarte
                tk.Label(f, text="BPS:").pack()
                bps_cb = ttk.Combobox(f, values=self.options["RTTY_BPS"], width=10)
                bps_cb.set(str(params.get("bps", "45.45")))
                bps_cb.pack(pady=2)
                self.temp_entries[mode]["bps"] = bps_cb

                tk.Label(f, text="SHIFT (Hz):").pack()
                shift_ent = ttk.Entry(f)
                shift_ent.insert(0, str(params.get("shift", "170")))
                shift_ent.pack(pady=2)
                self.temp_entries[mode]["shift"] = shift_ent

                tk.Label(f, text="SOUNDKARTE:").pack()
                rtty_sc = ttk.Combobox(f, values=["System", "USB Codec", "Virtual"])
                rtty_sc.set(params.get("soundcard", "System"))
                rtty_sc.pack(pady=2)
                self.temp_entries[mode]["soundcard"] = rtty_sc
            else:
                for k, val in params.items():
                    if k == "active":
                        continue
                    tk.Label(f, text=k.upper()).pack()
                    if k == "passcode":
                        ent = ttk.Entry(f, show="*")
                    else:
                        ent = ttk.Entry(f)
                    ent.insert(0, str(val))
                    ent.pack(pady=2)
                    self.temp_entries[mode][k] = ent

        ttk.Button(
            win, text="Konfiguration speichern", command=lambda: self.apply_config(win)
        ).pack(pady=20)

    # --- Konfiguration übernehmen und Fenster schließen ---
    def apply_config(self, win):
        # AX.25 Ports übernehmen
        self.config["MODES"]["AX25_PORTS"] = [
            {
                "active": p["active"].get(),
                "device": p["device"].get(),
                "nickname": p["nickname"].get(),
                "call": p["call"].get(),
            }
            for p in self.ax_temp_list
        ]

        # Drucker übernehmen
        self.config["PRINTER"] = {
            "name": self.prn_name.get(),
            "auto_print": self.prn_auto.get(),
        }

        # Modi übernehmen
        for m, entries in self.temp_entries.items():
            self.config["MODES"][m]["active"] = entries["active"].get()
            for k, widget in entries.items():
                if k == "active":
                    continue
                self.config["MODES"][m][k] = widget.get()

        self.save_settings()
        self.setup_digimode_terminals()
        self.setup_fundus_tab()
        win.destroy()

    # ---------- DIGIMODES ----------
    def setup_digimode_terminals(self):
        for w in self.tab_digi.winfo_children():
            w.destroy()

        # Referenzen auf die Terminal-Fenster für spätere Nutzung (z.B. Senden)
        self.digi_terminals = {}

        nb = ttk.Notebook(self.tab_digi)
        nb.pack(expand=1, fill="both")

        # AX.25 Ports als eigene Tabs
        for port in self.config["MODES"]["AX25_PORTS"]:
            if port.get("active"):
                f = ttk.Frame(nb)
                nb.add(f, text=f"AX: {port.get('nickname', '')}")
                t = tk.Text(
                    f, bg="#001100", fg="#00FF00", font=("Courier", 11)
                )
                t.pack(expand=1, fill="both")
                key = f"AX:{port.get('nickname', '')}"
                self.digi_terminals[key] = t

        # Weitere Modi als einfache Terminals
        for mode, data in self.config["MODES"].items():
            if mode not in ("AX25_PORTS", "APRS_IS") and data.get("active"):
                f = ttk.Frame(nb)
                nb.add(f, text=mode)
                t = tk.Text(f, bg="#001100", fg="#00FF00", font=("Courier", 11))
                t.pack(expand=1, fill="both")
                self.digi_terminals[mode] = t

    # ---------- LOG ----------
    def log_iaru_msg(self):
        nr = self.msg_fields["Nummer"].get()
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        log_line = f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : MSG #{nr} archiviert."
        self.log_list.insert(0, log_line)
        # Auch in die Einsatz-Session-Datei schreiben
        self.write_session_log(f"[{ts}] {log_line}")
        self.clear_iaru_form()
        messagebox.showinfo("NoFuS-TX", "Meldung gespeichert.")

    # --- Meldung senden (in Terminal und/oder nur Loggen) ---
    def send_iaru_msg(self):
        # IARU-Meldung als Text zusammensetzen
        header_keys = ["Nummer", "Quelle / Station", "Wort-Zähler", "Herkunft", "Zeit (UTC)", "Datum"]
        header_lines = []
        for key in header_keys:
            val = self.msg_fields.get(key)
            header_lines.append(f"{key}: {val.get().strip() if val else ''}")

        prio = self.prio_var.get() if hasattr(self, "prio_var") else ""
        body = self.msg_text.get("1.0", "end").strip()

        text_trenner = "####################### Meldungstext #######################\n \n \n"

        full_text = text_trenner + "--- IARU-Meldung ---\n" + "\n".join(header_lines) + f"\nWICHTIGKEIT: {prio}\n\n{body}\n"

        # Gewählten Digimode ermitteln
        mode = self.send_mode_var.get() if hasattr(self, "send_mode_var") else "Nur Log"

        if mode and mode != "Nur Log":
            term = getattr(self, "digi_terminals", {}).get(mode)
            if term:
                term.insert("end", "\n--- IARU-Meldung ---\n")
                term.insert("end", full_text + "\n")
                term.see("end")
            else:
                messagebox.showwarning(
                    "Digimode",
                    f"Kein Terminal für Modus '{mode}' gefunden.\nDie Meldung wird nur geloggt.",
                )

        # Immer ins Einsatz-Log und in die Einsatz-Session-Datei übernehmen
        nr = self.msg_fields["Nummer"].get()
        time_str = datetime.datetime.utcnow().strftime("%H:%M:%S")
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if mode and mode != "Nur Log":
            log_text = f"{time_str} : MSG #{nr} gesendet über {mode}."
        else:
            log_text = f"{time_str} : MSG #{nr} ins Log übernommen."
        self.log_list.insert(0, log_text)

        # Vollständige Meldung zusätzlich in die Einsatz-Session-Datei schreiben
        session_entry = [
            f"[{ts}] IARU-Meldung protokolliert:",
            *header_lines,
            f"WICHTIGKEIT: {prio}",
            "",
            body,
            "",
        ]
        self.write_session_log("\n".join(session_entry))

        # Optional drucken
        if hasattr(self, "print_on_send") and self.print_on_send.get():
            self.print_message(full_text)

        self.clear_iaru_form()
        messagebox.showinfo("NoFuS-TX", "Meldung gesendet und protokolliert.")

    # --- Log-Tab einrichten ---
    def setup_log_tab(self):
        self.log_list = tk.Listbox(self.tab_log, font=("Courier", 10))
        self.log_list.pack(expand=1, fill="both", padx=10, pady=10)

    # ---------- UHR ----------
    def update_clock(self):
        now_utc = datetime.datetime.utcnow()
        self.time_label.config(text=now_utc.strftime("%d.%m.%Y - %H:%M:%S UTC"))
        self.root.after(1000, self.update_clock)

# ---------- MAIN ----------
# Startet die Anwendung, indem die Hauptklasse instanziiert und die Tkinter-Hauptschleife gestartet wird.
if __name__ == "__main__":
    root = tk.Tk()
    app = NoFuSTX(root)
    root.mainloop()
