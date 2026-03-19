# =============================================================================
# NoFuSTX - Emergency Communication Suite
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
# NoFuSTX - IMPORT SEKTION (v1.9.14c)
# Unterstützt: APRS, JS8Call, VARA, Winlink, MT63, RTTY, SSTV, FAX, AX.25
# Plattformen: Windows, Linux, macOS
# =============================================================================

# --- 1. Python Standard-Bibliotheken (Immer vorhanden) ---
import sys
import os
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

# --- 2. Grafische Benutzeroberfläche & Karten (GUI) ---
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import tkintermapview   # Die Karten-Engine
except ImportError:
    tkintermapview = None

try:
    from PIL import Image, ImageTk  # Bildverarbeitung für Icons und Karten
except ImportError:
    Image = None
    ImageTk = None

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
    import pyvara  # Für VARA-Modem
except ImportError:
    pyvara = None

# MT63 ist bereits über pyfldigi abgedeckt (falls du das so willst), oder füge eine separate Lib hinzu:
# try:
#     import pymt63  # Falls eine spezifische MT63-Bibliothek existiert
# except ImportError:
#     pymt63 = None
# =============================================================================

def check_dependencies():
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
    # if pymt63 is None:  # Falls du MT63 separat prüfst
    #     missing.append("pymt63")

    # ... (Rest der Funktion bleibt gleich)

    if missing:
        install_cmd = "python -m pip install " + " ".join(
            m.replace(" + ", " ").split()[0] for m in missing
        )
        msg = (
            "Einige optionale Abhängigkeiten fehlen:\n\n"
            + "\n".join(f"• {m}" for m in missing)
            + "\n\nInstallieren mit:\n\n"
            + install_cmd
            + "\n\n(Die App kann auch ohne diese Pakete starten, aber bestimmte Funktionen sind dann deaktiviert.)"
        )
        try:
            # Anstatt Messagebox ein kopierbares Textfeld öffnen
            win = tk.Toplevel()
            win.title("NoFuSTX: fehlende Abhängigkeiten")
            win.geometry("500x300")

            text = tk.Text(win, wrap="word", height=12, padx=10, pady=10, bg="lightgray", fg="black", font=("Arial", 10))
            text.insert("1.0", msg)
            text.pack(expand=True, fill="both")
            
            button = tk.Button(win, text="Schließen", command=win.destroy, bg="lightgray", fg="black", font=("Arial", 10))
            button.pack()
        except Exception:
            print(msg)



class NoFuSTX:
    def __init__(self, root):
        self.root = root
        self.root.title("NoFuSTX - Einsatzleitsoftware v1.9.14c")
        try:
            # Wir laden das PNG als PhotoImage
            icon_img = tk.PhotoImage(file="icons/NoFuSTX.png")
            self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Programm-Icon Fehler: {e}")
        self.root.geometry("1250x950")
        self.config_file = "nofustx_config.json"
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

        # Vollständige Default-Config inkl. neuer Felder
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
        }

        self.load_settings()
        check_dependencies()
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
            # pass_coords=True sorgt dafür, dass wir (lat, lon) erhalten
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

        # Empfangs-Threads starten (listen-only)
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
        # Falls symbol_table kein / oder \ ist, nehmen wir / als Standard.
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

        # Log-Schreiben (hilft uns beim Debuggen)
        # try:
            # with open(icon_log, "a", encoding="utf-8") as f:
                # f.write(f"{datetime.datetime.utcnow().isoformat()} - Suche: {candidates} (Original war: {symbol_table})\n")
        # except Exception:
            # pass

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

        # 1) Default-Shape ausblenden
        try:
            # if hasattr(marker, "canvas_icon"):
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
            # Ohne gültiges Rufzeichen verbinden wir uns nicht mit APRS-IS
            self.aprs_update_queue.put(
                {
                    "type": "log",
                    "message": f"{datetime.datetime.utcnow().strftime('%H:%M:%S')} : APRS-IS nicht aktiv (Rufzeichen NOCALL).",
                }
            )
            return

        def _callback(packet):
            self.aprs_update_queue.put(packet)
            try:
                data = packet
                pos = self.extract_aprs_position(data)
                if not pos:
                    return
                pos["source_type"] = "APRS-IS"
                self.aprs_update_queue.put(
                    {
                        "type": "position",
                        **pos,
                    }
                )
            except Exception:
                # Parsing-Fehler still ignorieren, um den Worker nicht zu beenden
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
                # range_km = 20  # Empfangsbereich in Kilometern um die HOME-Position
                # home_lat = self.config.get("HOME_LAT", 51.9621817)
                # home_lon = self.config.get("HOME_LON", 9.650912)
                map_conf = self.config.get("MAP", {})
                home_lat = map_conf.get("home_lat", 51.9621817)
                home_lon = map_conf.get("home_lon", 9.650912)
                # filter_str = f"t/po m/{range_km}/{home_lat:.4f}/{home_lon:.4f}" # Falsches Format, korrigiert zu:
                filter_str = f"r/{home_lat:.4f}/{home_lon:.4f}/{range_km}"
                # print(f"APRS-IS Filter: {filter_str}") # Debug-Ausgabe
                # is_conn.set_filter("t/po m/10/51.9622/9.6509")  # Beispiel: Filter auf 10 km um 51.9622N, 9.6509E
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
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # Typische Form: SRCCALL>DEST,PATH1,PATH2:PAYLOAD
            if ">" not in line or ":" not in line:
                continue

            try:
                # Direkt an aprslib.parse übergeben – es versteht das APRS-Frameformat.
                pkt = aprslib.parse(line)
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

                if etype == "position":
                    self.handle_aprs_position_event(event)
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
        self.tab_digi = ttk.Frame(self.tabs)
        self.tab_log = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_map, text="Lagekarte")
        self.tabs.add(self.tab_fundus, text="Fundus / Personal")
        self.tabs.add(self.tab_msg, text="Not-Mitteilung (IARU)")
        self.tabs.add(self.tab_digi, text="Digimodes Terminal")
        self.tabs.add(self.tab_log, text="Einsatz-Log")

        self.setup_map_view()
        self.setup_fundus_tab()
        self.setup_message_tab()
        self.setup_digimode_terminals()
        self.setup_log_tab()

        # Wenn APRS-IS konfiguriert ist, beim Start automatisch Marker setzen
        self.update_aprs_on_map_initial()

    def setup_menu(self):
        m = tk.Menu(self.root)
        self.root.config(menu=m)

        # DATEI
        datei_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Datei", menu=datei_m)
        datei_m.add_command(label="Beenden", command=self.root.quit)

        # EINSTELLUNGEN
        settings_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Einstellungen", menu=settings_m)
        settings_m.add_command(label="Hardware & Modi", command=self.show_config_window)

        # Hilfe-Menü
        help_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Hilfe", menu=help_m)
        help_m.add_command(label="Über NoFuSTX", command=self.show_about_window)

    def setup_map_view(self):
        # Karte mit APRS-Integration
        if tkintermapview is None:
            tk.Label(self.tab_map, text="Karte nicht verfügbar (tkintermapview nicht installiert)").pack(expand=1)
            return
        self.map_widget = tkintermapview.TkinterMapView(self.tab_map)
        self.map_widget.pack(expand=1, fill="both")

        # Startposition aus Config (MAP) – Standard ca. 10 km Radius um 51.9621817 / 9.6509120
        map_conf = self.config.get("MAP", {})
        home_lat = map_conf.get("home_lat", 51.9621817)
        home_lon = map_conf.get("home_lon", 9.650912)
        zoom = int(map_conf.get("zoom", 13))

        self.map_widget.set_position(home_lat, home_lon)
        self.map_widget.set_zoom(zoom)

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
        
        # Hier definieren wir die Liste der Fahrzeugtypen
        # Du kannst diese Liste beliebig erweitern!
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

    def refresh_unit_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in self.config.get("UNITS", []):
            stat_text = "EINSATZBEREIT" if u.get("status") else "NICHT AKTIV"
            self.tree.insert("", "end", values=(u["name"], u["type"], stat_text))

    def toggle_unit_status(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self.config["UNITS"][idx]["status"] = not self.config["UNITS"][idx]["status"]
            self.save_settings()
            self.refresh_unit_tree()

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

    # ---------- Über NoFuSTX ----------
    def show_about_window(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("Über NoFuSTX")
        about_win.geometry("400x300")

        tk.Label(about_win, text="NoFuSTX - Einsatzleitsoftware v1.9.14c").pack(pady=10)
        tk.Label(about_win, text="© 2026 NoFuSTX DO2ITH").pack(pady=5)
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
            # Wir nehmen ein technisches Icon, z.B. das Zahnrad/Wetterstation-Symbol
            conf_icon = tk.PhotoImage(file="icons/settings.png") 
            win.iconphoto(False, conf_icon)
            # Referenz speichern, damit das Icon im Speicher bleibt
            win._icon_ref = conf_icon 
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
        messagebox.showinfo("NoFuSTX", "Meldung gespeichert.")

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
        messagebox.showinfo("NoFuSTX", "Meldung gesendet und protokolliert.")

    def setup_log_tab(self):
        self.log_list = tk.Listbox(self.tab_log, font=("Courier", 10))
        self.log_list.pack(expand=1, fill="both", padx=10, pady=10)

    # ---------- UHR ----------
    def update_clock(self):
        now_utc = datetime.datetime.utcnow()
        self.time_label.config(text=now_utc.strftime("%d.%m.%Y - %H:%M:%S UTC"))
        self.root.after(1000, self.update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = NoFuSTX(root)
    root.mainloop()
