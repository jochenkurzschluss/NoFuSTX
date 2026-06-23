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
# NoFuS-TX - IMPORT SEKTION (v1.9.16d)
# Unterstützt: APRS, JS8Call, VARA, Winlink, MT63, RTTY, SSTV, FAX, AX.25
# Plattformen: Windows, Linux, macOS
# =============================================================================
#
# --- 1. Python Standard-Bibliotheken (Immer vorhanden) ---
import sys
import os
import signal
# Ermittle den Pfad, wo dieses Script liegt
base_path = os.path.dirname(os.path.abspath(__file__))
libs_path = os.path.join(base_path, 'libs')
# Existiert der libs Ordner ? Wenn ja, schieben wir ihn an den Anfang der sys.path, damit unsere lokalen Versionen der Module Vorrang haben
if os.path.exists(libs_path):
    # Wir schieben unseren libs-Ordner an Position 0 der Suchliste
    sys.path.insert(0, libs_path)
    # Debug-Ausgabe in der Konsole
    INFOECHO = f"[Lib] NoFuS-TX Portable-Modus: Nutze lokale Libs aus {libs_path}"

# Jetzt können wir die Module importieren, die in libs liegen (z.B. pyjs8call, pyvara, etc.)
import datetime
import copy
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
import http.server
import socketserver
from typing import Any, cast
# --- 2. Grafische Benutzeroberfläche & Karten (GUI) ---
import tkinter as tk
from tkinter import ttk, messagebox
try:
    import tkintermapview   # Die Karten-Engine
    from tkintermapview.offline_loading import OfflineLoader
    from tkintermapview import OfflineLoader
except ImportError:
    tkintermapview = None
try:
    import psutil
except ImportError:
    psutil = None
try:
    from PIL import Image, ImageTk  # Bildverarbeitung für Icons und Karten
except ImportError:
    Image = None
    ImageTk = None
# --- Die Terminals im OS nutzen
try:
    import tkterminal
except ImportError:
    tkterminal = None

from tkterminal import Terminal # type: ignore
# --- 3. Funk- & Modem-Schnittstellen (Externe Module) ---
# Hinweis: Diese müssen über den check_dependencies() geprüft werden
try:
    import aprslib      # APRS-Protokoll Dekodierung
    import aprslib.parsing
    import aprslib.exceptions
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
    import serial.tools.list_ports
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
try: # --- AX.25 Bibliotheken ---
    import ax25
    import ax25.netrom
    import ax25.ports
    import ax25.socket
    # Optional: Falls du das veraltete Modul auch direkt abfangen willst
    # import ax25old # Falls jemand die alte Version installiert hat, um Konflikte zu vermeiden
except ImportError:
    ax25 = None
    ax25old = None
try:
    import meshtastic # --- Meshtastic für LoRa Mesh Netzwerke ---
    import meshtastic.serial_interface as meshtastic_serial_interface
    import meshtastic.mesh_interface as meshtastic_mesh_interface
    import pubsub
    from pubsub import pub  # Für die Kommunikation mit Meshtastic-Threads
except ImportError:
    meshtastic = None
    meshtastic_serial_interface = None
    meshtastic_mesh_interface = None
    pubsub = None
    pub = None
try:
    import urllib.request # --- Für den Download von Karten-Updates über LAN-Sync ---
    import shutil
except ImportError:
    urllib = None
    shutil = None
from lang.default_lang import DEFAULT_LANG_DICT

# Hauptklasse der Anwendung
class NoFuSTX:
    def __init__(self, root):
        self.root = root
        self.root.title("NoFuS-TX - Notfunk-Software")
        try:
            # Wir laden das PNG als PhotoImage
            icon_img = tk.PhotoImage(file="icons/NoFuSTX.png")
            self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Programm-Icon Fehler: {e}")
        self.root.geometry("1250x950")
        # --- Datei- und Ordnerstruktur sicherstellen ---
        self.config_folder = os.path.join(base_path, "config")
        os.makedirs(self.config_folder, exist_ok=True)
        self.config_file = os.path.join(self.config_folder, "nofustx_config.json")
        self.frequency_file = os.path.join(self.config_folder, "notfunk_freqs.json")
        self.band_plan_file = os.path.join(self.config_folder, "band_plan.json")
        self.msg_folder = os.path.join(base_path, "msg")
        os.makedirs(self.msg_folder, exist_ok=True)
        self.msg_history_entries = {}
        self.counter_number_msg = 1 # --- IARU Mitteilungszähler ---
        self.version_nummer = f"1.9.16d (Alpha)"
        # Voltmeter-Gerät
        self.BAUD_RATE = 9600  # Standard-Baudrate für die serielle Kommunikation mit dem Voltmeter (kann in der Konfiguration angepasst werden)

        # Einsatz-Session-Log (pro Programmstart eine Datei)
        self.session_log_file = None
        self.session_log_start_utc = None
        self.session_log_path = None

        # APRS-Lage: Marker- und Update-Verwaltung
        self.aprs_update_queue = queue.Queue()
        self.aprs_markers = {}
        self.aprs_icon_cache = {}
        self.home_marker = None
        self.wx_history = []
        self.wx_metric_history = {
            "temp": [],
            "hum": [],
            "press": [],
            "wind": [],
            "rain": []
        }
        # fldigi-Variablen
        self.fldigi_client = None
        self.fldigi_app = None
        self.fldigi_polling_active = False  # Flag gegen doppelte Polling-Timer
        self.fldigi_after_id = None  # ID des laufenden after()-Timers
        # Puffer zum Filtern des RX und zur Erkennung von IARU-Mitteilungen
        self.recive_buffer = ""
        
        self.user_say_no = False  # Flag, um zu verhindern, dass der Nutzer mehrfach gefragt wird, wenn er einmal "Nein" gesagt hat - im LAN Sync
        self.rx_mesh_ch_tab = 0
        
        # --- Für Konfig und andere Standards
        self.options = {
            "RTTY_BPS": ["45.45", "50", "75", "100", "200"],  # <--- RTTY-Übertragungsraten in Baud (bps)
            "SSTV_MODES": ["Martin 1", "Martin 2", "Scottie 1", "Scottie 2", "Robot 36", "Robot 72"],  # <--- Standard-SSTV-Modelle
            "AX25_DEVICES": ["ax0", "ax1", "ax2", "kiss0", "udp0"],  # <--- Mögliche AX.25-Kernel-Devices oder KISS-Worker, je nachdem, was du nutzt.
            "LORA_MODEMS": ["LongFast", "LongSlow", "ShortFast"],  # <-- Standard-LoRa-Modemprofile, können aber je nach Hardware variieren.
            "BAUD_RATES": ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"],  # <--- Gängige Baudraten
            "HARDWARE": ["ax", "kiss", "ip", "soft"]  # <--- "ax" spricht Linux-AX.25 an, "kiss" den neuen KISS-Worker, "ip" für netzwerkgebundene Betriebsarten wie Hamnet und "soft" für Meshtastic und ähnliche Lösungen.
        }

        # Vollständige Default-Config inkl. neuer Felder für Modi oder Ergänungen
        self.default_config = {
            "MODES": {
                "AX25_PORTS": [
                    {
                    "active": False,
                    "device": "/dev/ttyUSB0",  # <--- Ändert sich zu /dev/ttyUSB0-9 oder COM0-9; zuvor war es ax0
                    "hardware": "ax",  # <--- Hier wird definiert, wie der AFSK/Packet-Port angesprochen wird
                    "BAUD_RATE": 9600,  # <--- Übertragungsrate, wenn es ein TNC bzw. ein Gerät ist, das über /dev/ttyUSB oder COM1 angesprochen wird
                    "aprs": False,  # <-- Kommen über dieses Gerät APRS-Frames?
                    "nickname": "CB-APRS",  # <--- Kurzname, damit die einzelnen Geräte unterschieden werden
                    "call": "NOCALL"  # <--- Das Rufzeichen, das genutzt wird (später sollte dies aus der globalen Konfiguration kommen)
                    },
                    {
                    "active": False,
                    "device": "/dev/ttyUSB0",  # <--- Ändert sich zu /dev/ttyUSB0-9 oder COM0-9; zuvor war es ax0
                    "hardware": "kiss",  # <--- Hier wird definiert, wie der AFSK/Packet-Port angesprochen wird
                    "BAUD_RATE": 9600,  # <--- Übertragungsrate, wenn es ein TNC bzw. ein Gerät ist, das über /dev/ttyUSB oder COM1 angesprochen wird
                    "aprs": False,  # <-- Kommen über dieses Gerät APRS-Frames?
                    "nickname": "CB-APRS",  # <--- Kurzname, damit die einzelnen Geräte unterschieden werden
                    "call": "NOCALL"  # <--- Das Rufzeichen, das genutzt wird (später sollte dies aus der globalen Konfiguration kommen)
                    },
                    {
                    "active": False,
                    "device": "/dev/ttyUSB0",  # <--- Ändert sich zu /dev/ttyUSB0-9 oder COM0-9; zuvor war es ax0
                    "hardware": "ip",  # <--- Hier wird definiert, wie der AFSK/Packet-Port angesprochen wird
                    "BAUD_RATE": 9600,  # <--- Übertragungsrate, wenn es ein TNC bzw. ein Gerät ist, das über /dev/ttyUSB oder COM1 angesprochen wird
                    "aprs": False,  # <-- Kommen über dieses Gerät APRS-Frames?
                    "nickname": "CB-APRS",  # <--- Kurzname, damit die einzelnen Geräte unterschieden werden
                    "call": "NOCALL"  # <--- Das Rufzeichen, das genutzt wird (später sollte dies aus der globalen Konfiguration kommen)
                    },
                    {
                    "active": False,
                    "device": "/dev/ttyUSB0",  # <--- Ändert sich zu /dev/ttyUSB0-9 oder COM0-9; zuvor war es ax0
                    "hardware": "soft",  # <--- Hier wird definiert, wie der AFSK/Packet-Port angesprochen wird
                    "BAUD_RATE": 9600,  # <--- Übertragungsrate, wenn es ein TNC bzw. ein Gerät ist, das über /dev/ttyUSB oder COM1 angesprochen wird
                    "aprs": False,  # <-- Kommen über dieses Gerät APRS-Frames?
                    "nickname": "CB-APRS",  # <--- Kurzname, damit die einzelnen Geräte unterschieden werden
                    "call": "NOCALL"  # <--- Das Rufzeichen, das genutzt wird (später sollte dies aus der globalen Konfiguration kommen)
                    }
                ],
                "APRS_IS": {
                    "active": False,
                    "server": "euro.aprs2.net", # <--- APRS-IS Server kann auch ithnet.de oder CBaprs.de sein
                    "port": "14580", # <--- Port zur kommunikation
                    "call": "NOCALL", # <--- Rufzeichen kommt später auch aus der Config Usercall
                    "passcode": "00000", # <--- Passcode zum rufzeichen, ist nötig um APRS-IS TX zu ermöglichen aber auch nützlich für RX
                    "range_km": "20", # <--- Filter angabe 
                    "view_range": "13", # <--- Anzeige Radius
                },
                "LORA_APRS": {
                    "active": False,
                    "port": "/dev/ttyUSB0", # <--- Port zur Kommunikation mit dem LoRa-Modem (kann je nach Hardware variieren, z.B. /dev/ttyUSB0-9 oder COM0-9)
                    "baud": 115200 # <--- Baudrate für die serielle Kommunikation mit dem LoRa-Modem (muss mit der Einstellung im Modem übereinstimmen)
                },
                "LORA_MESH": {
                    "active": False,
                    "Device": "MeshID", # <--- Hier wird die Device-ID oder der Mesh-Name eingetragen, damit die App weiß, mit welchem Gerät sie kommunizieren soll. Je nach Hardware kann das z.B. "ttyUSB0" oder "COM3" sein, oder bei Netzwerkgebundenen Modems eine IP-Adresse oder ein eindeutiger Mesh-Name.
                    "modem": "LongFast", # <--- Hier wird das Modemprofil eingetragen, z.B. "LongFast", "LongSlow" oder "ShortFast". Je nach Hardware und Anwendungsfall kann das variieren. Einfach mal in der Dokumentation des Modems schauen, welche Profile es unterstützt und die Liste hier anpassen!
                    "ConnectionMode": "/dev/ttyACM0", # <--- Hier wird die Art der Verbindung zum Modem eingetragen. Das kann z.B. ein serieller Port wie "/dev/ttyACM0" oder "COM3" sein, oder bei Netzwerkgebundenen Modems eine IP-Adresse mit Port wie "192.168.1.100:8080"
                    "ADMIN": "1234", # <--- AdminPasswort Neue sicherheitsregel bei Meshtastic
                    },
                "WINLINK": {
                    "active": False,
                    "rms_server": "cms.winlink.org",
                    "port": "8772",
                    "call": "NOCALL",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "PSK500",
                },
                "RTTY": {
                    "active": False,
                    "bps": "45.45",
                    "shift": "170",
                    "soundcard": "System",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "RTTY",
                },
                "SSTV": {
                    "active": False,
                    "mode": "Martin 1",
                    "soundcard": "System Standard",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "SSB",
                },
                "FAX": {
                    "active": False,
                    "lpm": "120",
                    "ioc": "576",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "WEFAX576",
                },
                "JS8CALL": {
                    "active": False,
                    "frequency": "7.078 MHz",  # Typische JS8Call-Frequenz
                    "callsign": "NOCALL",
                    "soundcard": "System",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "BPSK31",
                },
                "VARA": {
                    "active": False,
                    "frequency": "14.105 MHz",  # Typische VARA-Frequenz
                    "callsign": "NOCALL",
                    "soundcard": "System",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "SSB",
                },
                "MT63": {
                    "active": False,
                    "frequency": "7.040 MHz",  # Typische MT63-Frequenz
                    "bandwidth": "1k",  # z. B. 500Hz, 1k, 2k
                    "soundcard": "System",
                    "device": "/dev/ttyUSB0",
                    "hardware": "TNC",
                    "BAUD_RATE": 9600,
                    "use_fldigi": True,
                    "fldigi_modem": "MT63-1KS",
                },
            },
            # --- Drucker --- 
            "PRINTER": {"name": "Standard-Thermo", "auto_print": False},
            "UNITS": [
                {"name": "Zentrale (NoFuS-E)", "type": "NoFuS-E", "status": True},
                {"name": "Mobil 1", "type": "NoFuS-M", "status": True},
                {"name": "Trupp A", "type": "NoFuS-P", "status": False},
                {"name": "Trupp B", "type": "NoFuS-P", "status": False},
            ],
            #GUI Einstellungen
            "GUI": {
                "debug": False,
                "equip_check": False,
                "if_mesh_gps": False,
                "voltmeter": False,
                "SPRACHE": "DE",          # <--- Hier definieren wir den Standard für den Erststart!
                },
            # Standard-Lagekarte: ca. 10 km Radius um 51.9621817 / 9.6509120
            "MAP": {
                "center_lat": 51.9621817,
                "center_lon": 9.6509120,
                "zoom": 10,
            },
            # Abhängigkeiten: Hier kann später den Status der optionalen Module speichern, damit die App nicht jedes Mal neu prüfen muss (z.B. nach einem fehlgeschlagenen Start)
            "DEPENDENCIES": {
                "is_read": 0,
            },
            # --- IARU Mitteilungszähler ---
            "IARU": {
                "next_message_number": 1
            },
            # --- Rufzeichen z.B. DO2ITH ---
            "USERCALL": {
                "CALLSINGEN": "NOCALL"
            },
            # --- Software-Defined-Radio-Optionen
            "SDR":{
                "active": False,
                "sdr_mode": "none",  # z.B. "rtl_sdr", "gqrx", "sdrplay" wie wird SDR betrieben
                "sdr_rate": "2400k",
                "audio_rate_sdr": "48k",
                "audio_rate_aplay": "48000"
            }
        }
        # Vollständige Standardfrequenzen mit Beschreibungen in JSON, die für jede Gruppe angepasst werden können!
        self.default_frequencies = {
            "FREQUENCIES": [
                ["FM", "145.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","144.800 MHz", "APRS zur Positionsermittlung"],
                ["FM","149.050 MHz", "Freenet in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","446.03125 MHz", "PMR in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","430.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","433.500 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","28.325 MHz", "in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","27.065 MHz", "CB in Fonie zur Kommunikation der Einheiten untereinander"],
                ["FM","27.235 MHz", "CB AFSK/APRS zur Positionsermittlung und Datenübertragung"],
                ["USB","14.300 MHz", "in Fonie zur Kommunikation über sehr große Entfernungen (Grenzübergreifend)"],
                ["LSB","7.110 kHz", "LSB in Fonie zur Kommunikation über sehr große Entfernungen (Deutschland weit)"],
                ["LSB","3.760 kHz", "LSB in Fonie zur Kommunikation über sehr große Entfernungen (Deutschland weit)"],
                ]
        }
        # Einstellungen und Frequenzen laden und dabei die Struktur reparieren, falls neue Felder oder Bereiche in der Standardkonfiguration hinzugekommen sind, damit die App nach Updates mit alten Konfigurationen weiterhin läuft, ohne wichtige Einstellungen zu verlieren.
        self.default_lang_dict = DEFAULT_LANG_DICT
        self.lang_folder = os.path.join(base_path, "lang")
        os.makedirs(self.lang_folder, exist_ok=True)
        self.default_lang = "DE" # Standart Sprache
        self.load_settings()
        self.load_frequencies()
        self.load_language()
        
        # Wenn in deiner Config eingestellt ist, dass Debug AUS sein soll:
        if not self.config.get("GUI", {}).get("debug", False):
            # Wir leiten alle Standard-Ausgaben (sys.stdout) in das Null-Gerät des Betriebssystems um
            sys.stdout = open(os.devnull, 'w')
            
            # Optional: Wenn du auch Fehlermeldungen unterdrücken willst (Vorsicht im Beta-Test!)
            sys.stderr = open(os.devnull, 'w')
        print(INFOECHO)  # Diese Zeile wird nur angezeigt, wenn Debug in der Config aktiviert ist
        self.counter_number_msg = self.load_message_counter()
        self.init_session_log() # <--- Starten des Einsatzlog
        if not self.config.get("DEPENDENCIES", {}).get("is_read", 0): # <--- Ist es ein Erststart des Progrmms ?
            self.check_dependencies()
            self.config["DEPENDENCIES"]["is_read"] = 1
            self.set_USERCALL()
            self.show_config_window()
            self.save_settings()
        
        self.setup_ui()# <--- Grafikoberfläche Starten
        self.mesh_connected = False # <--- Status, ob wir mit einem LoRa-Mesh verbunden sind
        self.interface: Any = None # <--- Schnittstellen-Objekt für LoRa Mesh (z.B. SerialInterface oder NetworkInterface, je nach ConnectionMode)
        self.mesh_kanal_name = None
        self.mesh_channels_dict = {}
        self.mesh_dm_history = {} # <--- Mesh Direktnachrichten Speicher
        self.mesh_home_auto_updated = False # <--- Flag, um zu verhindern, dass die Home-Position mehrfach automatisch aktualisiert wird, wenn das GPS-Signal schwankt
        self.dm_window = None        # Speichert das Toplevel-Fenster, wenn es offen ist
        self.dm_tabs = {}            # Speichert die Text-Widgets der Absender: { "sender_id": text_widget }
        self.dm_notebook = None      # Speichert das Notebook innerhalb des Fensters

        # Prüfen, ob LORA_MESH in deiner Config aktiv geschaltet ist
        if self.config["MODES"].get("LORA_MESH", {}).get("active"):
            print("[Mesh] Konfiguration aktiv. Starte Hardware-Suche...")
            self.init_meshtastic_hardware()
            self.mesh_gps_pos()
        self.init_aprs_system() # <--- APRS System starten (APRS-IS Verbindung, TNC-Listener, etc.)
        if self.config.get("GUI", {}).get("equip_check", True): # <--- Wenn in der Config eingestellt ist, dass die Ausrüstungsprüfung aktiviert sein soll, dann starten wir sie direkt beim Programmstart
            self.check_equip()
        if self.config.get("GUI", {}).get("voltmeter", True): # <--- Wenn in der Config eingestellt ist, dass das Voltmeter aktiviert sein soll, dann starten wir es direkt beim Programmstart
            self.voltmeter_thread()
        self.squelch_var = 0
        self.play_beep()
    # --------- KONFIGURATIONSLADUNG & -SPEICHERUNG ----------
    def _repair_config_structure(self, config: Any, defaults: Any) -> bool: # <--- Funtion die eine Prüfung der Konfigiration durchführt und ggf. Reperiert!
        """
        Aktualisiert eine geladene Config dynamisch mit den aktuellen Default-Werten.
        Erhält bestehende Nutzerdaten, ergänzt aber fehlende oder kaputte Bereiche.
        """
        changed = False

        if not isinstance(config, dict) or not isinstance(defaults, dict):
            return True

        for key, default_value in defaults.items():
            if key not in config or config[key] is None:
                config[key] = copy.deepcopy(default_value)
                changed = True
                continue

            current_value = config[key]

            if isinstance(default_value, dict):
                if not isinstance(current_value, dict):
                    config[key] = copy.deepcopy(default_value)
                    changed = True
                    continue
                changed = self._repair_config_structure(current_value, default_value) or changed
                continue

            if isinstance(default_value, list):
                if not isinstance(current_value, list):
                    config[key] = copy.deepcopy(default_value)
                    changed = True
                    continue

                if default_value and isinstance(default_value[0], dict) and isinstance(current_value, list):
                    merged_list = []
                    for item in current_value:
                        if isinstance(item, dict):
                            template = copy.deepcopy(default_value[0])
                            template.update(item)
                            merged_list.append(template)
                        else:
                            merged_list.append(copy.deepcopy(default_value[0]))

                    if len(merged_list) < len(default_value):
                        merged_list.extend(copy.deepcopy(default_value[len(merged_list):]))

                    if merged_list != current_value:
                        config[key] = merged_list
                        changed = True
                continue

            if type(current_value) is not type(default_value):
                config[key] = copy.deepcopy(default_value)
                changed = True

        return changed

    def load_settings(self): # <--- Laden der Konfiguration aus der JSON-Datei, mit Reparatur der Struktur bei fehlenden oder neuen Feldern
        if not os.path.exists(self.config_file):
            legacy_config = os.path.join(base_path, "nofustx_config.json")
            if os.path.exists(legacy_config):
                try:
                    with open(legacy_config, "r") as f:
                        self.config = json.load(f)
                except Exception:
                    self.config = copy.deepcopy(self.default_config)
            else:
                self.config = copy.deepcopy(self.default_config)

            self._repair_config_structure(self.config, self.default_config)
            self.save_settings()
            return

        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)

            if self._repair_config_structure(self.config, self.default_config):
                self.save_settings()
        except Exception:
            self.config = copy.deepcopy(self.default_config)
            self.save_settings()

    def load_language(self): # <--- Lädt die Sprachdatei und repariert fehlende Keys anhand des Standard-Fallbacks
        # 1. Sprache aus der Config holen (Fallbback auf dein self.default_lang "DE")
        lang_code = self.config.get("GUI", {}).get("SPRACHE", self.default_lang)
        
        # Pfad dynamisch mit deinem self.lang_folder zusammenbauen
        file_path = os.path.join(self.lang_folder, f"{lang_code}.json")

        # Fall A: Die gewünschte Datei existiert gar nicht auf der Festplatte
        if not os.path.exists(file_path):
            print(f"[i18n] ⚠️ {lang_code}.json nicht gefunden! Nutze kompletten Default-Fallback.")
            # Falls die DE.json (dein Standard) nicht da ist, müssen wir self.tr 
            # zumindest als leeres Dict anlegen, damit die Reparatur greift.
            self.tr = {}
            # Hier versuchen wir die originale DE.json als Basis zu laden, falls verfügbar
            default_path = os.path.join(self.lang_folder, f"{self.default_lang}.json")
            if os.path.exists(default_path):
                try:
                    with open(default_path, "r", encoding="utf-8") as f:
                        self.tr = json.load(f)
                except Exception:
                    pass
            return

        # Fall B: Datei ist da -> Laden und mit der internen default_lang-Struktur abgleichen
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.tr = json.load(f)

            # Struktur prüfen und reparieren (falls z.B. eine ältere EN.json geladen wurde)
            # Hinweis: 'self.default_lang_dict' wäre das im Code fest hinterlegte vollständige Wörterbuch
            if hasattr(self, 'default_lang_dict'):
                self._repair_lang_structure(self.tr, self.default_lang_dict)

            print(f"[i18n] 👍 Sprache erfolgreich geladen und geprüft: {lang_code}")

        except Exception as e:
            print(f"[i18n] ❌ Fehler beim Laden von {lang_code}.json: {e}. Nutze leeres Standard-Wörterbuch.")
            self.tr = {}

    def _repair_lang_structure(self, current, default):
        """Durchläuft das Wörterbuch und ergänzt fehlende Keys aus dem Default."""
        repaired = False
        for key, value in default.items():
            if key not in current:
                # Key fehlt komplett -> Aus dem Standard-Wörterbuch nachziehen
                current[key] = copy.deepcopy(value)
                repaired = True
                print(f"[i18n] 🔧 Fehlenden Key repariert: {key}")
            elif isinstance(value, dict):
                # Wenn es ein Unterordner (dict) ist, gehen wir eine Ebene tiefer
                if not isinstance(current[key], dict):
                    current[key] = {}
                if self._repair_lang_structure(current[key], value):
                    repaired = True
        return repaired
        
    def check_dependencies(self): # <--- Abhängigkeiten Prüfen und den Nutzer informieren, welche optionalen Module fehlen, damit er sie installieren kann, um alle Funktionen nutzen zu können!
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
        if psutil is None:
            missing.append("psutil")
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
                # Statt einer Messagebox ein kopierbares Textfeld öffnen.
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
    # =============================================================================
    # NoFuS-TX - LAN SYNC SEKTION (P2P Map Sharing)
    # =============================================================================

    def init_lan_sync(self, statusbar_parent): # <--- Initialisiert das LAN-Sync System, das die offline_tiles.db über das lokale Netzwerk mit anderen NoFuS-Stationen teilt, damit alle Teilnehmer schnellere Kartenupdates erhalten können, ohne dass jeder die Daten einzeln aus dem Internet laden muss. Es besteht aus einem Broadcast-Sender, der regelmäßig die Verfügbarkeit von Updates ankündigt, einem Broadcast-Listener, der auf Ankündigungen anderer Stationen hört und bei Bedarf die Daten von ihnen anfordert, und einem HTTP-Server, der die offline_tiles.db für andere Stationen bereitstellt, wenn sie es anfordern.
        """Initialisiert das UI-Widget und startet die Hintergrund-Dienste"""
        # 1. UI Widget in der Mitte der Statusleiste
        self.sync_frame = tk.Frame(statusbar_parent, bd=1, relief="sunken", bg="black")
        self.sync_frame.pack(side="left", expand=True, padx=10) # expand=True schiebt es in die Mitte

        self.sync_icon = tk.Label(self.sync_frame, text="🔵", bg="black")
        self.sync_icon.pack(side="left", padx=2)

        self.sync_label = tk.Label(self.sync_frame, text="LAN-Sync: Idle", font=("Arial", 8), bg="black")
        self.sync_label.pack(side="left", padx=5)

        # 2. Threads starten
        threading.Thread(target=self._run_broadcast_sender, daemon=True).start()
        threading.Thread(target=self._run_broadcast_listener, daemon=True).start()
        threading.Thread(target=self._run_http_server, daemon=True).start()
        self.write_session_log(f"[{self.utc_iso_timestamp()}] LAN-Sync initialisiert. Hintergrunddienste gestartet.")
        print("[LAN-Sync] Initialisiert: Broadcast-Sender, Broadcast-Listener und HTTP-Server laufen im Hintergrund.")

    def _get_local_tile_count(self): # <--- Zählt die Anzahl der lokalen Kartenkacheln, um sie in den Ankündigungen zu teilen und mit anderen Stationen zu vergleichen. Je mehr Kacheln, desto aktueller ist die Karte, aber es braucht auch mehr Speicherplatz. So können Stationen mit weniger Kacheln erkennen, dass es ein Update gibt, und die Daten von Stationen mit mehr Kacheln anfordern, um ihre Karten zu aktualisieren.
        """Zählt, wie viele Kartenkacheln wir aktuell haben"""
        db_path = os.path.join(base_path, "off_Maps", "offline_tiles.db")
        # print(f"[LAN-Sync] Überprüfe lokale Tiles in {db_path}")
        if not os.path.exists(db_path): return 0
        try:
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT count(*) FROM tiles").fetchone()[0]
            conn.close()
            return count
        except Exception: return 0

    def _run_http_server(self): # <--- Startet einen einfachen HTTP-Server, der die offline_tiles.db für andere Stationen bereitstellt, wenn sie es anfordern. Er lauscht auf Port 27245 und liefert die Datei aus dem off_Maps-Ordner aus. Andere Stationen können dann die URL http://IP_DES_PARTNERS:27245/off_Maps/offline_tiles.db verwenden, um die Daten herunterzuladen und ihre Karten zu aktualisieren.
        """Stellt die offline_tiles.db via HTTP bereit"""
        port = 27245
        # Es braucht einen Handler, der nur die tiles.db ausliefert
        os.chdir(base_path) 
        handler = http.server.SimpleHTTPRequestHandler
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                httpd.serve_forever()
        except Exception as e:
            print(f"[*] LAN-Server Port belegt: {e}")

    def _run_broadcast_sender(self): # <--- Sendet alle 15 Sekunden eine Ankündigung im lokalen Netzwerk, dass diese Station verfügbar ist und wie viele Kartenkacheln sie hat. Andere Stationen können diese Ankündigungen empfangen und entscheiden, ob sie die Daten von dieser Station anfordern wollen, um ihre Karten zu aktualisieren. Die Ankündigung enthält auch die IP-Adresse und den Port des HTTP-Servers, damit andere Stationen wissen, wo sie die Daten herunterladen können.
        """Kündigt alle 15 Sekunden im Netzwerk an"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        def test_my_ip():
            try:
                # Erstellt einen UDP-Socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Verbindet sich mit einem beliebigen externen Server (muss nicht erreichbar sein)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except Exception:
                ip_address = "0.0.0.0"
            return ip_address
        
        while True:
            try:
                my_call = self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")
                info = {
                    "app": "NoFuS-TX",
                    "call": my_call,
                    "tiles": self._get_local_tile_count(),
                    #"ip": socket.gethostbyname(socket.gethostname()),
                    "ip": test_my_ip(),
                    "port": 27245
                }
                msg = json.dumps(info).encode('utf-8')
                sock.sendto(msg, ('<broadcast>', 5005))
            except Exception: pass
            time.sleep(15)
    

    def _run_broadcast_listener(self): # <--- Lauscht auf Ankündigungen anderer NoFuS-Stationen im lokalen Netzwerk. Wenn eine Ankündigung empfangen wird, prüft sie, ob die Partner-Station mehr Kartenkacheln hat als die lokale Station. Wenn ja, zeigt sie dem Nutzer an, dass ein Update verfügbar ist, und bietet die Möglichkeit, die Daten von der Partner-Station herunterzuladen und zu integrieren. Wenn der Nutzer zustimmt, startet sie den Download und den Abgleich der Kartenkacheln. Wenn der Nutzer ablehnt oder wenn die Partner-Station nicht mehr Kacheln hat als die lokale Station, zeigt sie den entsprechenden Status an.
        """Lauscht auf andere NoFuS-Stationen"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 5005))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                info = json.loads(data.decode('utf-8'))
                
                if info.get("app") == "NoFuS-TX":
                    remote_call = info.get("call", "Unbekannt")
                    remote_tiles = info.get("tiles", 0)
                    local_tiles = self._get_local_tile_count()

                    # Wenn der Partner mehr Tiles hat als wir...
                    if remote_tiles > local_tiles:
                        # Bereite die vollständige HTTP-URL des Partners vor
                        partner_url = f"http://{info.get('ip')}:{info.get('port')}/off_Maps/offline_tiles.db"
                        
                        if not self.user_say_no:
                            # 1. UI auf Grün setzen: Update steht bereit!
                            self.sync_icon.config(text="🟢", fg="green")
                            self.sync_label.config(text=f"Update von {remote_call} verfügbar!")
                            
                            # 2. Direkt die Funktion merge_tiles aufrufen.
                            # Sie prüft den Speicher und fragt den Operator mit exakten MB-Angaben!
                            self.merge_tiles(partner_url)
                        else:
                            # Der Nutzer hat für diese Session bereits einmal "Nein" gesagt
                            self.sync_icon.config(text="🔴", fg="red")
                            self.sync_label.config(text=f"Update von {remote_call} blockiert")
                            
                    elif remote_tiles <= local_tiles:
                        # Wir sind aktuell oder haben sogar mehr Daten als der Partner
                        self.sync_icon.config(text="🔵", fg="blue")
                        self.sync_label.config(text=f"Partner: {remote_call} (OK)")
                        
            except Exception: 
                pass

    def merge_tiles(self, other_db_url): # <--- Führt die Kartenkacheln aus der Partner-Station in die lokale offline_tiles.db ein, nachdem geprüft wurde, dass genügend Speicherplatz vorhanden ist und der Nutzer dem Download zugestimmt hat. Sie lädt die Partner-DB herunter, öffnet sie zusammen mit der lokalen DB, führt die Kacheln zusammen (ohne Duplikate) und speichert das Ergebnis in der lokalen DB. Nach dem Abgleich zeigt sie den Erfolg an und aktualisiert die UI entsprechend.
        """Prüft den Speicherplatz, fragt den User und führt fremde Tiles ein."""
          # Für die Speicherplatz-Prüfung
        
        local_db = os.path.join(base_path, "off_Maps", "offline_tiles.db")
        temp_remote_db = os.path.join(base_path, "off_Maps", "remote_temp.db")
        
        print(f"[LAN-Sync] Frage Metadaten von {other_db_url} ab...")
        self.sync_label.config(text="Prüfe Remote-DB...")
        self.root.update_idletasks()

        try:
            # 1. Dateigröße der Partner-DB über das Netzwerk ermitteln (HTTP HEAD Request)
            req = urllib.request.Request(other_db_url, method='HEAD') # type: ignore
            with urllib.request.urlopen(req, timeout=5) as response: # type: ignore
                # Holt die Größe in Bytes (Standardwert 0 falls nicht lesbar)
                remote_size_bytes = int(response.headers.get('Content-Length', 0))
            
            remote_size_mb = remote_size_bytes / (1024 * 1024)
            
            # 2. Freien Speicherplatz auf der lokalen Festplatte ermitteln
            # shutil.disk_usage gibt (total, used, free) in Bytes zurück
            _, _, free_space_bytes = shutil.disk_usage(base_path) # type: ignore
            free_space_mb = free_space_bytes / (1024 * 1024)

            print(f"[LAN-Sync] Partner-DB: {remote_size_mb:.2f} MB | Freier Speicher: {free_space_mb:.2f} MB")

            # 3. Sicherheitsnetz: Reicht der Platz überhaupt?
            # Wir fordern zur Sicherheit das Doppelte der Dateigröße (für Download + SQLite-Merge)
            if free_space_mb < (remote_size_mb * 2):
                messagebox.showerror(
                    "Speicherplatz-Warnung", 
                    f"Abgleich abgebrochen!\n\n"
                    f"Die Partner-Datenbank ist {remote_size_mb:.1f} MB groß.\n"
                    f"Du hast nur noch {free_space_mb:.1f} MB freien Speicherplatz.\n"
                    f"Das ist zu riskant für das System."
                )
                self.sync_icon.config(text="🔴", fg="red")
                self.sync_label.config(text="Mangelnder Speicher!")
                return

            # 4. Der gewünschte Dialog: Operator explizit mit Größenangabe fragen
            frage_text = (
                f"Die Karten-Datenbank des Partners ist {remote_size_mb:.1f} MB groß.\n"
                f"Dein freier Speicherplatz: {free_space_mb:.1f} MB.\n\n"
                f"Möchtest du den Download und den Abgleich jetzt starten?"
            )
            
            if not messagebox.askyesno("LAN-Sync Bestätigung", frage_text):
                print("[LAN-Sync] Download vom Benutzer aufgrund der Dateigröße abgelehnt.")
                self.user_say_no = True
                self.sync_icon.config(text="🔴", fg="red")
                self.sync_label.config(text="Sync abgelehnt")
                return

            # 5. AB HIER STARTET DER ECHTE DOWNLOAD (Sichergestellt: Genug Platz & User will es)
            print(f"[LAN-Sync] Starte Download von {remote_size_mb:.2f} MB...")
            self.sync_label.config(text=f"Lade {remote_size_mb:.1f}MB herunter...")
            self.root.update_idletasks()

            urllib.request.urlretrieve(other_db_url, temp_remote_db) # type: ignore
            
            print(f"[LAN-Sync] Download abgeschlossen. Starte SQLite-Merge...")
            self.sync_label.config(text="Führe Karten zusammen...")
            self.root.update_idletasks()

            # Verbindung herstellen und zusammenführen
            try:
                conn = sqlite3.connect(local_db)
                print(f"[KARTEN-MERGE] Öffne DB {local_db}")
                conn.execute(f"ATTACH DATABASE '{temp_remote_db}' AS remote")
                print(f"[KARTEN-MERGE] ATTACH DB REmote {temp_remote_db}")
                conn.execute("INSERT OR IGNORE INTO tiles SELECT * FROM remote.tiles")
                print(f"[KARTEN-MERGE] INSERT DB")
                conn.commit()
                print(f"[KARTEN-MERGE] COMMIT DB")
                conn.execute("DETACH DATABASE remote")
                print(f"[KARTEN-MERGE] DETACH DB")
                conn.close()
                print(f"[KARTEN-MERGE] Schließe DB")
            except Exception as fail:
                print(f"[KARTEN-MERGE] Fehler beim merge: {fail}")
            
            print("[LAN-Sync] Kartenabgleich erfolgreich abgeschlossen!")
            messagebox.showinfo("Sync", "Karten erfolgreich abgeglichen!")
            self.write_session_log(f"[{self.utc_iso_timestamp()}] Karten von {other_db_url} ({remote_size_mb:.1f} MB) erfolgreich abgeglichen.")
            
            self.sync_icon.config(text="🔵", fg="blue")
            self.sync_label.config(text="LAN-Sync: Idle")

        except Exception as e:
            messagebox.showerror("Sync Fehler", f"Fehler beim Kartenabgleich:\n{e}")
            print(f"[LAN-Sync] Fehler beim Kartenabgleich: \n{e}\n")
            self.sync_icon.config(text="🔴", fg="red")
            self.sync_label.config(text="Sync Fehler!")
            
        finally:
            # Sauber aufräumen
            if os.path.exists(temp_remote_db):
                try:
                    os.remove(temp_remote_db)
                    print("[LAN-Sync] Temporäre DB-Datei erfolgreich gelöscht.")
                except Exception as e:
                    print(f"[LAN-Sync] Warnung: Temp-Datei konnte nicht gelöscht werden: {e}")

    # --------- USERCALL SETZEN ----------
    def set_USERCALL(self, callsign="NOCALL"): # <--- Setzt Das Globale Rufzeichen in der Software.
        try:
            callsign = self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")
        except Exception:
            callsign = "NOCALL"
        usercall_win = tk.Toplevel(self.root)
        usercall_win.title("Rufzeichen setzen - NoFuS-TX")
        usercall_win.geometry("400x300")

        tk.Label(usercall_win, text="Setzen Sie Ihr Rufzeichen").pack(pady=10)
        entry = tk.Entry(usercall_win, font=("Arial", 14), justify="center")
        entry.insert(0, callsign)
        entry.pack(pady=10)
        # --- Speichern-Funktion, die die neue Einstellung in der Config speichert und das Fenster schließt ---
        def save_callsign():
            new_callsign = entry.get()
            usercall_config = self.config.setdefault("USERCALL", {})
            usercall_config["CALLSINGEN"] = new_callsign
            self.save_settings()
            usercall_win.destroy()
            self.write_session_log(f"[{self.utc_iso_timestamp()}] Rufzeichen gesetzt: {new_callsign}")

        tk.Button(usercall_win, text="Speichern", command=save_callsign).pack(pady=10)
    # --------- FREQUENZENLADUNG & -SPEICHERUNG ----------
    def load_frequencies(self): # <--- Laden der Frequenzen aus der JSON-Datei, mit Übernahme von alten Frequenzen aus einer Legacy-Datei, falls die neue Datei noch nicht existiert, damit Nutzer ihre benutzerdefinierten Frequenzen behalten können, wenn sie von einer älteren Version aktualisieren.
        if not os.path.exists(self.frequency_file):
            legacy_frequencies = os.path.join(base_path, "notfunk_freqs.json")
            if os.path.exists(legacy_frequencies):
                try:
                    with open(legacy_frequencies, "r") as f:
                        self.frequencies = json.load(f)
                except Exception:
                    self.frequencies = self.default_frequencies
            else:
                self.frequencies = self.default_frequencies
            os.makedirs(self.config_folder, exist_ok=True)
            with open(self.frequency_file, "w") as f:
                json.dump(self.frequencies, f, indent=4)
        else:
            try:
                with open(self.frequency_file, "r") as f:
                    self.frequencies = json.load(f)
            except Exception:
                self.frequencies = self.default_frequencies

    def save_settings(self): # <--- Speichern der aktuellen Konfiguration in der JSON-Datei, damit die Einstellungen auch nach einem Neustart erhalten bleiben. Es wird die gesamte Config-Struktur in die Datei geschrieben, damit alle Änderungen und Anpassungen dauerhaft gespeichert werden.
        os.makedirs(self.config_folder, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    # ---------- EINSATZ-SESSION-LOG ----------
    def init_session_log(self): # <--- Initialisiert die Einsatz-Session-Logdatei, die alle wichtigen Ereignisse und Aktionen während einer Einsatz-Session aufzeichnet. Beim Start der App wird eine neue Logdatei mit der Startzeit im Namen erstellt, und beim Beenden der App wird die Datei mit der Stop-Zeit umbenannt
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

        #self.session_log_start_utc = datetime.datetime.utcnow()
        try:
            self.session_log_start_utc = datetime.datetime.now(datetime.timezone.utc)
        except AttributeError:
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

    def write_session_log(self, text): # <--- Schreibt eine Zeile in die aktuelle Einsatz-Session-Logdatei, damit alle wichtigen Ereignisse und Aktionen während der Session dokumentiert werden. Es wird geprüft, ob die Logdatei geöffnet ist, bevor der Text geschrieben wird, um Fehler zu vermeiden.
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

    def finalize_session_log(self): # <--- Ergänzt die Stop-Zeit in der Einsatz-Session-Logdatei und benennt die Datei von "RUNNING" auf ein endgültiges Format mit Start- und Stop-Zeit um, damit die Logdatei nach dem Einsatz korrekt benannt und abgeschlossen ist. Es wird geprüft, ob die Logdatei geöffnet ist, bevor die Stop-Zeit eingetragen und die Datei umbenannt wird, um Fehler zu vermeiden.
        """
        Ergänzt beim Programmende die Stop-Zeit und benennt die Datei auf
        'einsatz-STARTUTC_STOPUTC.txt' um.
        """
        if not self.session_log_path or not self.session_log_start_utc:
            return

        #stop_utc = datetime.datetime.utcnow()
        stop_utc = self.get_utc_now() 
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

    def on_close(self): # <--- Close Handler für das Schließen des Hauptfensters, der sicherstellt, dass alle laufenden Prozesse sauber beendet werden, der Einsatz-Session-Log korrekt abgeschlossen wird und die Verbindung zum Meshtastic-Gerät geschlossen wird, damit keine Ressourcen offen bleiben und die Logdatei mit einem Stop-Zeitstempel versehen wird.
        """
        Wird beim Schließen des Hauptfensters aufgerufen.
        Sorgt dafür, dass das Einsatz-Session-Log sauber abgeschlossen wird.
        """
        self.on_closing()  # Alle laufenden Prozesse beenden
        self.stop_direct_sdr() # Falls der direkte SDR-Modus aktiv ist, beendet den Prozess
        self.finalize_session_log()
        self.root.destroy()
        if self.interface and self.mesh_connected:
            self.interface.close() # Schließt die Verbindung zum Meshtastic-Gerät

    # ---------- APRS GRUND-INITIALISIERUNG ----------
    def init_aprs_system(self): # <--- Initialisiert das APRS-System, indem es die Empfangsthreads für APRS-IS und AX.25 startet, die Update-Queue im GUI-Thread periodisch verarbeitet und einen optional gespeicherten HOME-Marker auf der Karte lädt und setzt, damit die App bereit ist, APRS-Daten zu empfangen und anzuzeigen.
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
                    f"{self.utc_time_str()} : APRS deaktiviert (aprslib nicht installiert).",
                )
                self.write_session_log(f"[{self.utc_iso_timestamp()}] APRS deaktiviert (aprslib nicht installiert).")
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
                    marker_kwargs["icon"] = home_image
                self.home_marker = self.map_widget.set_marker(
                    lat, lon, text="HOME", **marker_kwargs
                )
                self._apply_icon_to_marker(self.home_marker, home_image)
            except Exception:
                self.home_marker = None

        # Empfangs-Threads starten (nur zuhören; keine Lizenzprüfung) – die Threads stellen Pakete in die aprs_update_queue, die im GUI-Thread verarbeitet wird.
        # Empfangs-Threads starten (nur zuhören; keine Lizenzprüfung)
        modes = self.config.get("MODES", {})  # Hinweis: Vorher stand hier modes = self.config.get("MODES", []) – falls es ein Dictionary ist, nutzen wir {} als Fallback

        # 1. APRS-IS Internet Stream
        aprs_is_conf = modes.get("APRS_IS", {})
        if aprs_is_conf.get("active"):
            t_is = threading.Thread(target=self.aprs_is_worker, daemon=True)
            t_is.start()

        # 2. Klassische Linux AX.25 Ports
        for port in modes.get("AX25_PORTS", []):
            if port.get("active") and port.get("hardware") == "ax" and port.get("aprs") != False:
                device = port.get("device") or "ax0"
                t_ax = threading.Thread(
                    target=self.ax25_worker, args=(device,), daemon=True
                )
                t_ax.start()
            elif port.get("hardware","") == "kiss" and port.get("aprs") != False:
                self.init_nofus_v2_hardware()
            

        # 3. NEU: Direkter LoRa-APRS Empfänger via T-Beam (KISS)
        lora_conf = modes.get("LORA_APRS", {})
        if lora_conf.get("active"):
            t_lora = threading.Thread(target=self.lora_aprs_worker, daemon=True)
            t_lora.start()

        # Queue im GUI-Thread regelmäßig abarbeiten
        self.root.after(500, self.process_aprs_queue)
        

    # ---------- APRS HILFSFUNKTIONEN ----------
    def get_home_image(self): # <--- Liefert (und cached) ein spezielles HOME-Icon, falls vorhanden. Erwarteter Dateiname im Unterordner ./icons: - home.png oder home.gif. Wenn die Datei gefunden und geladen werden kann, wird sie im Cache gespeichert und zurückgegeben. Wenn die Datei nicht gefunden wird oder ein Fehler beim Laden auftritt, wird None zurückgegeben und im Cache vermerkt, damit zukünftige Aufrufe schneller reagieren können.
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

    def get_symbol_image(self, symbol_table, symbol_code): # <--- Verbesserte Suche: Erzwingt gültige APRS-Tabellen (Hex 2f oder 5c).
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

    def _apply_icon_to_marker(self, marker, image): # <--- Versteckt den Standard-Kartenmarker (Kreis/Dreieck) und justiert das Icon (unten-mittig), damit benutzerdefinierte APRS-Symbole korrekt angezeigt werden können, ohne dass die Standardmarker die Sichtbarkeit stören. Es wird geprüft, ob der Marker existiert, bevor versucht wird, die Standardformen auszublenden und das Icon zu platzieren, um Fehler zu vermeiden.
        """
        Versteckt den Standard-Kartenmarker (Kreis/Dreieck) und
        justiert das Icon (unten-mittig).
        """
        if not marker:
            return

        # 1) Standardformen ausblenden, aber das eigentliche Icon sichtbar lassen.
        try:
            if hasattr(marker, "canvas_icon"):
                self.map_widget.canvas.itemconfig(marker.canvas_icon, state="normal")
            if hasattr(marker, "polygon"):
                self.map_widget.canvas.itemconfig(marker.polygon, state="hidden")
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
                marker.image = None
                marker.icon = image
                marker.icon_anchor = "center"  # punktgenau in der Mitte
                marker.calculate_text_y_offset()  # damit die interne Offset-Berechnung passt

                # Draw + danach Text neu platzieren
                def draw_and_place(event=None):
                    # Original zeichnen
                    orig_draw(event)

                    # Text nach unten verschieben (unter das Icon) und Icon garantieren sichtbar.
                    if getattr(marker, "canvas_icon", None):
                        self.map_widget.canvas.itemconfig(marker.canvas_icon, state="normal")
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

    def extract_aprs_position(self, packet): # <--- Extrahiert aus einem von aprslib gelieferten Packet-Dict die für die Lagedarstellung relevanten Daten.
        """
        Extrahiert aus einem von aprslib gelieferten Packet-Dict die für die Lagedarstellung relevanten Daten.
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
    
    def extract_aprs_weather(self, packet): # <--- Verbesserte Extraktion, die auch Unter-Dicts von aprslib prüft.
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
            # Sonderfall: Wenn nichts gefunden wurde, wird kurz im Kommentar nachgesehen.
            # Manche Stationen senden Wetter nur als Text im Kommentar.
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


    def handle_weather_event(self, event): # <--- Verarbeitet ein Wetter-Event, das von den APRS-Empfangs-Threads in die aprs_update_queue gestellt wird, aktualisiert die entsprechenden Labels im Wetter-Tab und fügt einen Eintrag in die Listbox auf der rechten Seite hinzu, damit die neuesten Wetterdaten sichtbar und nachvollziehbar sind.
        """
        Nimmt die Wetterdaten aus der Queue entgegen und aktualisiert die 
        Labels im Wetter-Tab (tab_wx).
        """
        wx = event.get("wx_data", {})
        callsign = event.get("callsign", "Unbekannt")

        try:
            # 1. Die UI-Variablen (tk.StringVar) aktualisieren
            # Prüfen mit .get(), ob der Wert existiert, sonst nutzen wir "--"
            
            def parse_value(value):
                if value is None:
                    return None
                try:
                    return float(value)
                except Exception:
                    try:
                        return float(str(value).replace(",", "."))
                    except Exception:
                        return None

            temp = parse_value(wx.get("temp"))
            if temp is not None:
                self.wx_vars["temp"].set(f"{temp:.1f} °C")
            
            hum = parse_value(wx.get("hum"))
            if hum is not None:
                self.wx_vars["hum"].set(f"{hum:.1f} %")
                
            press = parse_value(wx.get("press"))
            if press is not None:
                self.wx_vars["press"].set(f"{press:.1f} hPa")

            wind_s = parse_value(wx.get("wind_speed"))
            if wind_s is not None:
                self.wx_vars["wind"].set(f"{wind_s * 3.6:.1f} km/h")

            rain = parse_value(wx.get("rain_24h"))
            if rain is not None:
                self.wx_vars["rain"].set(f"{rain:.1f} mm")

            self.wx_vars["station"].set(callsign)

            # Speichere die letzten 8 empfangenen Werte pro Kennzahl
            if temp is not None:
                self.wx_metric_history["temp"].append(temp)
                self.wx_metric_history["temp"] = self.wx_metric_history["temp"][-8:]
            if hum is not None:
                self.wx_metric_history["hum"].append(hum)
                self.wx_metric_history["hum"] = self.wx_metric_history["hum"][-8:]
            if press is not None:
                self.wx_metric_history["press"].append(press)
                self.wx_metric_history["press"] = self.wx_metric_history["press"][-8:]
            if wind_s is not None:
                self.wx_metric_history["wind"].append(wind_s * 3.6)
                self.wx_metric_history["wind"] = self.wx_metric_history["wind"][-8:]
            if rain is not None:
                self.wx_metric_history["rain"].append(rain)
                self.wx_metric_history["rain"] = self.wx_metric_history["rain"][-8:]

            record = {}
            if temp is not None:
                record["temp"] = temp
            if hum is not None:
                record["hum"] = hum
            if press is not None:
                record["press"] = press
            if wind_s is not None:
                record["wind"] = wind_s * 3.6
            if rain is not None:
                record["rain"] = rain
    
            if record:
                self.wx_history.append(record)
                if len(self.wx_history) > 8:
                    self.wx_history.pop(0)
                self.update_weather_average()

            # 2. Eintrag in die Listbox auf der rechten Seite
            timestamp = self.get_utc_now().strftime("%H:%M")
            entry_text = f"{timestamp} | {callsign} | {self.wx_vars['temp'].get()}"
            self.wx_listbox.insert(0, entry_text)

            # Liste auf 50 Einträge begrenzen 
            if self.wx_listbox.size() > 50:
                self.wx_listbox.delete(tk.END)

        except Exception as e:
            print(f"Fehler bei der Wetter-Anzeige: {e}")

    def update_weather_average(self): # <--- Berechnet den Durchschnitt der letzten 8 Werte für jede Wetter-Kennzahl und aktualisiert die entsprechenden Labels im Durchschnittsbereich, damit die Nutzer einen Überblick über die jüngsten Wettertrends erhalten.
        def avg(key):
            values = self.wx_metric_history.get(key, [])
            if not values:
                return None
            return sum(values) / len(values)

        averages = {
            "temp": avg("temp"),
            "hum": avg("hum"),
            "press": avg("press"),
            "wind": avg("wind"),
            "rain": avg("rain"),
        }

        if averages["temp"] is not None:
            self.wx_avg_vars["temp"].set(f"{averages['temp']:.1f} °C")
        else:
            self.wx_avg_vars["temp"].set("-- °C")

        if averages["hum"] is not None:
            self.wx_avg_vars["hum"].set(f"{averages['hum']:.1f} %")
        else:
            self.wx_avg_vars["hum"].set("-- %")

        if averages["press"] is not None:
            self.wx_avg_vars["press"].set(f"{averages['press']:.1f} hPa")
        else:
            self.wx_avg_vars["press"].set("---- hPa")

        if averages["wind"] is not None:
            self.wx_avg_vars["wind"].set(f"{averages['wind']:.1f} km/h")
        else:
            self.wx_avg_vars["wind"].set("-- km/h")

        if averages["rain"] is not None:
            self.wx_avg_vars["rain"].set(f"{averages['rain']:.1f} mm")
        else:
            self.wx_avg_vars["rain"].set("-- mm")

    # ---------- APRS HINTERGRUND-THREADS ----------
    def aprs_is_worker(self): # <--- Empfängt APRS-IS Daten über das Internet, analysiert die Pakete auf Positions- und Wetterinformationen und stellt die relevanten Daten in die aprs_update_queue, damit sie im GUI-Thread verarbeitet und angezeigt werden können. Es wird eine Verbindung zum APRS-IS Server hergestellt, ein Filter für die Empfangsreichweite um die HOME-Position gesetzt und eingehende Pakete werden kontinuierlich ausgewertet. Bei Verbindungsfehlern wird ein erneuter Verbindungsversuch nach 30 Sekunden unternommen.
        """
        Empfang von APRS-IS über aprslib.IS (listen-only).
        Keine Beacon- oder Sende-Funktion – reine Auswertung eingehender Pakete.
        """
        if aprslib is None:
            return

        modes = self.config.get("MODES", {})
        conf = modes.get("APRS_IS", {})
        call = self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")
        server = conf.get("server", "euro.aprs2.net")
        port = int(conf.get("port", "14580"))
        passwd = conf.get("passcode", "-1")
        range_km = conf.get("range_km", 20)  # Empfangsbereich in Kilometern um die HOME-Position

        if not call or call == "NOCALL":
            # Ohne gültiges Rufzeichen wird keine Verbindung zu APRS-IS aufgebaut.
            self.aprs_update_queue.put(
                {
                    "type": "log",
                    "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : APRS-IS nicht aktiv (Rufzeichen NOCALL).",
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
                try:
                    is_conn.connect()
                except Exception as err:
                    print(f"[APRS-IS] Fehler {err}")
                    
                self.aprs_update_queue.put(
                    {
                        "type": "log",
                        "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : APRS-IS verbunden ({server}:{port}).",
                    }
                )
                # consumer() blockiert in dieser Thread-Funktion, liefert Pakete an _callback
                is_conn.consumer(callback=_callback, raw=False)
                
            except Exception as e:
                self.aprs_update_queue.put(
                    {
                        "type": "log",
                        "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : APRS-IS Verbindung fehlgeschlagen – neuer Versuch in 30 s.",
                    }
                )
                time.sleep(30)
                print(f"[APRS-IS] Fehler {e}")

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
                    "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : AX.25-Listener für {device} konnte nicht gestartet werden.",
                }
            )
            return

        self.aprs_update_queue.put(
            {
                "type": "log",
                "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : AX.25-Listener aktiv auf {device}.",
            }
        )

        # Zeilenweise Ausgabe von axlisten auswerten (könnte obsolet werden, sobald der KISS-Worker vollständig eingebaut ist und keine Kernelmodule mehr benötigt werden).
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
                            self.write_session_log(f"[{self.utc_iso_timestamp()}] {msg}")
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
                f"{self.get_utc_now().strftime('%H:%M:%S')} : "
                f"APRS {src} ({source_type}) -> {symbol_table}{symbol_code} "
                f"@ {lat:.5f},{lon:.5f}"
            )
            try:
                self.log_list.insert(0, log_text)
                self.write_session_log(f"[{self.utc_iso_timestamp()}] {log_text}")
            except Exception:
                pass

    def lora_aprs_worker(self): # <--- Ist für die 433 MHz LoraAPRS Boards (T-Beam, KISS-TNC) gedacht, die ihre empfangenen Pakete über eine serielle Schnittstelle (USB oder TCP) im KISS-Format bereitstellen. Der Worker liest kontinuierlich die seriellen Datenströme, erkennt die KISS-Frames, extrahiert die AX.25-Payloads, dekodiert die Rufzeichen und füttert den internen APRS-Parser, damit auch diese LoRa-APRS Pakete in der App angezeigt werden können.
        """
        Direkter Empfang von LoRa-APRS Daten von einem T-Beam oder KISS-TNC via USB/KISS-TCP.
        Entpackt die seriellen KISS-Datenströme, rekonstruiert die AX.25-Rufzeichen
        und füttert den internen APRS-Parser für Lagedarstellung und Wetter.
        """
        if aprslib is None:
            return

        # Konfiguration laden (Pfade und Parameter dynamisch halten)
        modes = self.config.get("MODES", {})
        conf = modes.get("LORA_APRS", {})
        port_name = conf.get("port", "/dev/ttyUSB0")  # 'COM11' unter Windows
        baud_rate = int(conf.get("baud", "115200"))   # Standard für CA2RXU Firmware

        # Logge den Startversuch in der GUI
        self.aprs_update_queue.put({
            "type": "log",
            "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : Starte LoRa-APRS auf {port_name} ({baud_rate} Baud)...",
        })

        try:
            import serial
            ser = serial.Serial(port=port_name, baudrate=baud_rate, timeout=0.1)
        except Exception as e:
            self.aprs_update_queue.put({
                "type": "log",
                "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : LoRa-Fehler: Schnittstelle {port_name} nicht erreichbar ({e}).",
            })
            return

        self.aprs_update_queue.put({
            "type": "log",
            "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : LoRa-APRS Empfänger aktiv auf {port_name}.",
        })

        buffer = b""
        FEND = b'\xc0'

        # Helfer für den AX.25-Rufzeichendecoder
        def _decode_callsign(byte_chunk):
            call = ""
            for b in byte_chunk[:6]:
                char = chr(b >> 1)
                if char.isalnum() or char == ' ':
                    call += char
            if len(byte_chunk) >= 7:
                ssid = (byte_chunk[6] >> 1) & 0x0F
            else:
                ssid = 0
            call = call.strip()
            return f"{call}-{ssid}" if ssid > 0 else call

        while True:
            try:
                chunk = ser.read(256)
                if not chunk:
                    continue
                
                buffer += chunk
                
                # Pakete umschlossen von FEND-Bytes aus dem persistenten Puffer schneiden
                while buffer.count(FEND) >= 2:
                    start_idx = buffer.find(FEND)
                    end_idx = buffer.find(FEND, start_idx + 1)
                    
                    if end_idx != -1:
                        kiss_frame = buffer[start_idx : end_idx + 1]
                        buffer = buffer[end_idx + 1 :]
                        
                        if len(kiss_frame) <= 3:
                            continue

                        raw_ax25 = kiss_frame[2:-1]  # FENDs und KISS-Cmd entfernen
                        
                        if len(raw_ax25) < 14:
                            continue

                        # Ziel und Absender extrahieren (je exakt 7 Bytes)
                        target_call = _decode_callsign(raw_ax25[0:7])
                        source_call = _decode_callsign(raw_ax25[7:14])
                        
                        # Dynamische Payload-Trennung via AX.25 PID-Byte (0xF0)
                        if b'\xf0' in raw_ax25:
                            pid_idx = raw_ax25.find(b'\xf0')
                            payload_bytes = raw_ax25[pid_idx + 1:]
                        else:
                            payload_bytes = raw_ax25[14:]
                            while len(payload_bytes) > 0 and payload_bytes[0] < 0x20:
                                payload_bytes = payload_bytes[1:]

                        payload_string = payload_bytes.decode('latin-1', errors='ignore')
                        
                        # Synthetisiere den APRS-IS Klartext-String für deine aprslib.parse()
                        aprs_is_string = f"{source_call}>{target_call}:{payload_string}"
                        
                        try:
                            # Parse das Paket über deine Hauptfunktion
                            pkt = aprslib.parse(aprs_is_string)
                            
                            # 1. Wetter extrahieren und in Queue werfen
                            wx = self.extract_aprs_weather(pkt)
                            if wx:
                                self.aprs_update_queue.put({
                                    "type": "weather",
                                    "callsign": wx["src"],
                                    "wx_data": wx
                                })
                            
                            # 2. Position extrahieren und in Queue werfen
                            pos = self.extract_aprs_position(pkt)
                            if pos:
                                pos["source_type"] = f"LoRa:{port_name}"
                                self.aprs_update_queue.put({
                                    "type": "position", 
                                    **pos
                                })
                                
                        except aprslib.exceptions.ParseError:
                            # Defekte oder unvollständige Funk-Pakete ignorieren
                            continue
                    else:
                        break
            except Exception as e:
                # Bei Verbindungsabrissen (z.B. USB-Kabel gezogen) Thread sauber loggen und beenden
                self.aprs_update_queue.put({
                    "type": "log",
                    "message": f"{self.get_utc_now().strftime('%H:%M:%S')} : LoRa-APRS Thread wegen Fehler beendet ({e}).",
                })
                break

    # ---------- HOME-POSITION ----------
    def set_home_position_from_click(self, coords): # <--- Position Per Mausklick (Rechts) setzen!
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
                f"{self.get_utc_now().strftime('%H:%M:%S')} : "
                f"HOME-Position gesetzt @ {lat:.5f},{lon:.5f}"
            )
            try:
                self.log_list.insert(0, msg)
                self.write_session_log(f"[{self.utc_iso_timestamp()}] {msg}")
            except Exception:
                pass

    def _remove_marker(self, marker): # <--- Marker entfernen, wenn er nicht mehr benötigt wird (z.B. bei Positionsänderung eines APRS-Objekts oder beim Aktualisieren der HOME-Position). Es wird geprüft, ob der Marker existiert, bevor versucht wird, ihn von der Karte zu entfernen, um Fehler zu vermeiden.
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

    def get_system_printers(self): # <--- Drucker Erkennen
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

    def print_message(self, text): # <--- Druckt eine Mitteilung
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
    def setup_ui(self): # <--- Baut die gesamte Benutzeroberfläche auf, inklusive Menü, Statusleiste, Telemetrie-Balken und Notebook-Reiter. Es wird eine klare Struktur verfolgt, um die verschiedenen UI-Komponenten übersichtlich zu organisieren und die spätere Wartung zu erleichtern.
        # 1. Menü initialisieren
        self.setup_menu()
        
        # 2. Statusleiste unten aufbauen
        self.status_bar = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.grid_columnconfigure(2, weight=1)
        
        # Aktueller Reiter und ZoomLevel
        self.zoom_label = tk.Label(self.status_bar, text="Zoom: 100%", font=("Courier", 10))
        self.zoom_label.grid(row=0, column=0, padx=10, sticky="w")
        
        # RX bereich
        self.rx_label = tk.Label(self.status_bar, text="RX Modus:", font=("Courier", 10))
        self.rx_label.grid(row=0, column=1, padx=10, sticky="w")
        
        # RX Auswahl aus der Config laden
        rx_modes = ["Kein RX"]
        for rx_mode, data in self.config["MODES"].items():
            if rx_mode in ("RTTY", "WINLINK", "JS8CALL", "VARA", "MT63") and data.get("active"):
                rx_modes.append(rx_mode)
                
        self.rx_combo = ttk.Combobox(self.status_bar, values=rx_modes, state="readonly", width=12, font=("Courier", 10))
        self.rx_combo.current(0)
        self.rx_combo.grid(row=0, column=2, padx=(0, 10), sticky="w")
        self.rx_combo.bind("<<ComboboxSelected>>", self.simple_rx)
        
        # Sync-Status der Tiles
        self.sync_container = tk.Frame(self.status_bar)
        self.sync_container.grid(row=0, column=3, padx=10, sticky="ew")
        
        # Zeitanzeige unten Rechts
        self.time_label = tk.Label(self.status_bar, text="12:00:00", font=("Courier", 10, "bold"))
        self.time_label.grid(row=0, column=4, padx=10, sticky="e")
        
        self.init_lan_sync(self.sync_container)
        self.update_clock()

        # =====================================================================
        # 3. HIER NEU: DER TELEMETRIE-BALKEN (ZENTRIERTE MESSWERTE)
        # Ssitzt direkt unter dem Menü und über den Tabs
        # =====================================================================
        self.telemetry_bar = tk.Frame(self.root, bg="#000A00", height=24, relief=tk.RIDGE, bd=1)
        self.telemetry_bar.pack(side=tk.TOP, fill=tk.X)

        # Spalten-Gewichtung für perfekte Zentrierung im Fenster
        self.telemetry_bar.grid_columnconfigure(0, weight=1)
        self.telemetry_bar.grid_columnconfigure(2, weight=1)

        # Zentraler innerer Container für die Labels
        self.sys_monitor_container = tk.Frame(self.telemetry_bar, bg="#000A00")
        self.sys_monitor_container.grid(row=0, column=1, pady=2)

        # Die Telemetrie-Labels (U1 bis U4 + CPU) nebeneinander packen
        self.lbl_u1 = tk.Label(self.sys_monitor_container, text="Batterie: ???", fg="#00FF00", bg="#000A00", font=("Courier", 10, "bold"))
        self.lbl_u1.pack(side=tk.LEFT, padx=8)

        self.lbl_u2 = tk.Label(self.sys_monitor_container, text="Solarenergie: ???", fg="#00FF00", bg="#000A00", font=("Courier", 10, "bold"))
        self.lbl_u2.pack(side=tk.LEFT, padx=8)

        self.lbl_u3 = tk.Label(self.sys_monitor_container, text="Ausgabe U1: ???", fg="#00FF00", bg="#000A00", font=("Courier", 10, "bold"))
        self.lbl_u3.pack(side=tk.LEFT, padx=8)

        self.lbl_u4 = tk.Label(self.sys_monitor_container, text="Ausgabe U2: ???", fg="#00FF00", bg="#000A00", font=("Courier", 10, "bold"))
        self.lbl_u4.pack(side=tk.LEFT, padx=8)

        # Optischer Trenner vor der CPU
        lbl_sep = tk.Label(self.sys_monitor_container, text="|", fg="#00FF00", bg="#000A00", font=("Courier", 10))
        lbl_sep.pack(side=tk.LEFT, padx=4)

        self.lbl_cpu = tk.Label(self.sys_monitor_container, text="CPU: na.", fg="#00FF00", bg="#000A00", font=("Courier", 10, "bold"))
        self.lbl_cpu.pack(side=tk.LEFT, padx=8)
        # =====================================================================

        # 4. Ab hier folgen wie gewohnt die Notebook-Reiter
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
        
        # UI-Inhalte initialisieren
        self.setup_map_view()
        self.setup_fundus_tab()
        self.setup_message_tab()
        self.setup_weather_tab()
        self.setup_digimode_terminals()
        self.setup_help_and_info_tabs()
        
        if self.chk_sdr() == False:
            self.setup_sdr_tab()
        else:
            self.no_sdr_found()

        self.setup_os_terminal_tab()
        self.setup_log_tab()

        # Karten-Initialisierung
        self.update_aprs_on_map_initial()
        self.get_current_map_zoom()
    
    def no_sdr_found(self): # <--- Kein SDR Gefunden dann Anzeige im SDR Tab
        label = ttk.Label(self.tab_sdr, text="Kein SDR gefunden. Bitte überprüfen Sie die Verbindung und die Treiber.\nNach Anschluss oder geladenem Treiber Starten Sie das Programm erneut!", font=("Arial", 12), foreground="red")
        label.pack(pady=20)
    def setup_weather_tab(self):
        # Einfacher Platzhalter-Text, damit der Tab nicht leer ist
        label = tk.Label(self.tab_wx, text="Wetterinformationen werden hier angezeigt.", font=("Arial", 12))
        label.pack(pady=20)
        
        for widget in self.tab_wx.winfo_children():
            widget.destroy()

        # Haupt-Container
        self.wx_main_frame = ttk.Frame(self.tab_wx)
        self.wx_main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # LINKER BEREICH: Wird horizontal geteilt in aktuelle Werte und Durchschnitt
        self.wx_left_frame = ttk.Frame(self.wx_main_frame)
        self.wx_left_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=5)

        self.wx_display_frame = ttk.LabelFrame(self.wx_left_frame, text=" Aktuelle Wetterdaten (APRS-WX) ")
        self.wx_display_frame.pack(side=tk.TOP, expand=True, fill="both", pady=(0, 5))

        self.wx_avg_frame = ttk.LabelFrame(
            self.wx_left_frame,
            text="Durchschnitt der letzten 8 empfangenen Messwerte"
        )
        self.wx_avg_frame.pack(side=tk.BOTTOM, fill="x")

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
            tk.Label(self.wx_display_frame, text=txt, font=("Arial", 14, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=10)
            tk.Label(self.wx_display_frame, textvariable=var, font=("Arial", 14)).grid(row=i, column=1, sticky="w", padx=10, pady=10)

        self.wx_avg_vars = {
            "temp": tk.StringVar(value="-- °C"),
            "hum": tk.StringVar(value="-- %"),
            "press": tk.StringVar(value="---- hPa"),
            "wind": tk.StringVar(value="-- km/h"),
            "rain": tk.StringVar(value="-- mm"),
        }

        avg_labels = [
            ("Temp. 8-Mittel:", self.wx_avg_vars["temp"]),
            ("Luftfeuchte 8-Mittel:", self.wx_avg_vars["hum"]),
            ("Luftdruck 8-Mittel:", self.wx_avg_vars["press"]),
            ("Windgeschw. 8-Mittel:", self.wx_avg_vars["wind"]),
            ("Niederschlag 8-Mittel:", self.wx_avg_vars["rain"]),
        ]

        for i, (txt, var) in enumerate(avg_labels):
            tk.Label(self.wx_avg_frame, text=txt, font=("Arial", 14, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            tk.Label(self.wx_avg_frame, textvariable=var, font=("Arial", 14)).grid(row=i, column=1, sticky="w", padx=10, pady=5)

        # RECHTER BEREICH: Liste der WX-Stationen in der Nähe
        self.wx_list_frame = ttk.LabelFrame(self.wx_main_frame, text=" Empfangene Stationen ")
        self.wx_list_frame.pack(side=tk.RIGHT, fill="y", padx=5)

        self.wx_listbox = tk.Listbox(self.wx_list_frame, width=30, font=("Courier", 14), bg="#F0F0F0", fg="#000000")
        self.wx_listbox.pack(expand=True, fill="both", padx=5, pady=5)
        


    # --- SDR ---
    def chk_sdr(self): # <--- Prüft die anwesenheit eines Unterstüzten SDRs (RTL-SDR, Airspy, HackRF, etc.) durch systemabhängige Befehle. Es wird die Ausgabe auf bekannte SDR-Hersteller gefiltert. Das Ergebnis wird geloggt und ggf. eine Warnung ausgegeben, wenn kein SDR gefunden wurde.
        No_sdr = False
        print("[SDR]Prüfe Anwesenheit von SDRs...")
        self.write_session_log(f"[{self.utc_iso_timestamp()}] Prüfe Anwesenheit von SDRs...")

        if sys.platform == "linux":
            cmd = "lsusb | grep -i rtl"
        elif sys.platform == "win32":
            cmd = 'powershell "Get-PnpDevice | Where-Object {$_.FriendlyName -like \'*RTL*\'}"'
        elif sys.platform == "darwin":  # Mac
            cmd = "system_profiler SPUSBDataType | grep -A 5 -B 5 RTL"
        else:
            print("Unbekannte Plattform")
            sys.exit(1)

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                print("[SDR] SDR gefunden:\n" + result.stdout)
                self.write_session_log(f"[{self.utc_iso_timestamp()}] SDR gefunden: {result.stdout.strip()}")
                No_sdr = False
            else:
                print("[SDR] Kein SDR gefunden")
                self.write_session_log(f"[{self.utc_iso_timestamp()}] Kein SDR gefunden.")
                if self.config.get("SDR", {}).get("active", True):
                    messagebox.showwarning("SDR Check", "Kein SDR gefunden. Bitte überprüfen Sie die Verbindung und die Treiber.")  
                No_sdr = True
        except Exception as e:
            print(f"[SDR] Fehler: {e}")
            self.write_session_log(f"[{self.utc_iso_timestamp()}] Fehler beim Prüfen der SDR-Anwesenheit: {e}")
            No_sdr = False
        return No_sdr

    def parse_to_hz(self, freq_str): # <--- Wandelt eine Frequenzangabe mit Einheiten (MHz, kHz) in eine reine Hertz-Angabe als Integer um. Es wird versucht, die Zahl zu extrahieren und entsprechend der Einheit umzurechnen. Fehlerhafte Eingaben führen zu einem Rückgabewert von 0 und werden geloggt.
        """Wandelt '145.500 MHz' oder '3.760 kHz' in Hertz (int) um."""
        try:
            # Leerzeichen säubern und splitten (z.B. ["145.500", "MHz"])
            parts = freq_str.replace(",", ".").split()
            if len(parts) < 2: return 0
            
            value = float(parts[0])
            unit = parts[1].upper()

            if "MHZ" in unit:
                return int(value * 1_000_000)
            elif "KHZ" in unit:
                return int(value * 1_000)
            else:
                return int(value)
        except Exception as e:
            print(f"Fehler beim Parsen der Frequenz {freq_str}: {e}")
            return 0

    def sdr_remote_cmd(self, command): # <--- Fernsteuerung von Gqrx über das TCP-Protokoll. Es wird ein separater Thread gestartet, um die Verbindung herzustellen und den Befehl zu senden, damit die Haupt-UI nicht blockiert wird. Fehler bei der Verbindung oder beim Senden werden geloggt.
        """Sendet Befehle an Gqrx via TCP (Port 7356)"""
        def _socket_task():
            host = "127.0.0.1"
            port = 7356
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect((host, port))
                    s.sendall(f"{command}\n".encode())
            except Exception as e:
                print(f"SDR-Verbindungsfehler: {e}")

        threading.Thread(target=_socket_task, daemon=True).start()

    def apply_sdr_settings(self, freq, mode): # <--- Sendet die ausgewählte Frequenz und den Modus entweder an Gqrx über das TCP-Protokoll oder startet einen direkten RTL-SDR Prozess, abhängig von der Konfiguration. Es werden auch die UI-Felder im SDR-Tab aktualisiert, damit sie den aktuellen Einstellungen entsprechen.
        """Sendet Frequenz und Modus an Gqrx und aktualisiert die UI-Felder"""
        sdr_backend = self.config.get("SDR", {}).get("sdr_mode", "")
        # print(f"SDR Backend: {sdr_backend}") #Debug ausgabe
        # Befehle an Gqrx senden
        if sdr_backend == "gqrx":
            # Der Weg über das Netzwerk-Protokoll
            self.sdr_remote_cmd(f"F {freq}")
            self.sdr_remote_cmd(f"M {mode}")
    
        elif sdr_backend == "rtl_sdr":
            # Der Weg direkt über die Kommandozeile
            self.start_direct_sdr(freq, mode)
        
        
        # UI-Elemente im SDR-Tab synchronisieren (falls vorhanden)
        if hasattr(self, 'sdr_freq_var'):
            self.sdr_freq_var.set(str(freq))
        if hasattr(self, 'sdr_mode_var'):
            self.sdr_mode_var.set(mode)
    
    def start_direct_sdr(self, freq, mode):
        self.stop_direct_sdr()

        # Hardware-Parameter aus der Config laden
        sdr_rate = self.config.get("SDR", {}).get("sdr_rate", "2400k")
        audio_rate_sdr = self.config.get("SDR", {}).get("audio_rate_sdr", "24k") # Standard für rtl_fm ist 24k
        
        # Standard-Audio-Ausgabe für ffplay
        audio_rate_aplay = "24000" 

        # Mapping der Modi für rtl_fm
        mode_map = {"FM": "fm", "WFM": "wbfm", "AM": "am", "LSB": "lsb", "USB": "usb"}
        m = mode_map.get(mode, "fm")

        # SPEZIALFALL WBFM: Laut Help-Text gibt WBFM standardmäßig 32k Audio aus!
        if mode == "WFM":
            audio_rate_aplay = "32000"
        else:
            # Für FM, AM, SSB nutzen wir die Standard-24k von rtl_fm
            audio_rate_aplay = "24000"

        # Squelch sicher auslesen (deine funktionierende Reparatur!)
        try:
            sq_val = int(self.squelch_spinbox.get()) if hasattr(self, 'squelch_spinbox') else 0
        except:
            sq_val = 0

        # Standardmäßig verpassen wir dem Signal z.B. einen festen 6dB Boost.
        # Du kannst statt "6dB" auch "12dB" nehmen, wenn es noch zu leise ist, 
        # oder den Wert dynamisch aus der Config/GUI holen.
        gain_val = "6dB" 

        # Der Befehl mit dem neuen Audio-Filter (-af volume=...)
        if self.deemp_var.get() == True:
            print(f"[SDR] Rauschsperre: {sq_val} | Modus: {m} | Gain: {gain_val}")
            cmd = (f"rtl_fm -M {m} -f {freq} -g 49 -E dc -E deemp -l {sq_val} |"
               f"ffplay -nodisp -autoexit -loglevel quiet -f s16le -ar {audio_rate_aplay} -ac 1 -af volume={gain_val} -i pipe:0")
        else:
            print(f"[SDR] Rauschsperre: {sq_val} | Modus: {m} | Gain: {gain_val} (ohne deemp)")
            cmd = (f"rtl_fm -M {m} -f {freq} -g 49 -E dc -l {sq_val} |"
               f"ffplay -nodisp -autoexit -loglevel quiet -f s16le -ar {audio_rate_aplay} -ac 1 -af volume={gain_val} -i pipe:0")
            
        def _run():
            self.sdr_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"SDR DIREKT AKTIV: {freq} Hz | Mode: {m} | Squelch: {sq_val}")

        threading.Thread(target=_run, daemon=True).start()

    def stop_direct_sdr(self): # <--- Stoppt den Direkten SDR
        if hasattr(self, 'sdr_process') and self.sdr_process:
            # Beendet die ganze Prozess-Gruppe (rtl_fm UND aplay)
            os.killpg(os.getpgid(self.sdr_process.pid), signal.SIGTERM)
            self.sdr_process = None

    def setup_sdr_tab(self): # <--- Den SDR-Tab Einrichten (UI Zusatz)
        # 1. Daten laden (Nutzt deine existierende Funktion)
        #self.chk_sdr()
        self.load_frequencies()
        
        # Variable für das Eingabefeld
        self.sdr_freq_var = tk.StringVar(value="145500000")

        # Haupt-Container im Tab
        sdr_container = ttk.Frame(self.tab_sdr, padding=10)
        sdr_container.pack(fill="both", expand=True)

        # --- SEKTION 1: DYNAMISCHE BUTTONS (Presets) ---
        preset_frame = ttk.LabelFrame(sdr_container, text=" Notfunk-Presets (Default-Liste) ", padding=10)
        preset_frame.pack(fill="x", pady=(0, 10))

        # Scrollbar für die Buttons (falls es viele sind)
        canvas = tk.Canvas(preset_frame, height=80)
        scrollbar = ttk.Scrollbar(preset_frame, orient="horizontal", command=canvas.xview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)

        canvas.pack(side="top", fill="x", expand=True)
        scrollbar.pack(side="bottom", fill="x")

        # Buttons aus deiner Liste erstellen
        freq_list = self.frequencies.get("FREQUENCIES", [])
        for item in freq_list:
            mode_raw = item[0]  # "FM"
            freq_raw = item[1]  # "145.500 MHz"
            desc = item[2]      # "Anrufkanal..."
            
            hz_val = self.parse_to_hz(freq_raw)
            if hz_val > 0:
                btn = ttk.Button(scroll_frame, text=f"{freq_raw}\n{mode_raw}", 
                                command=lambda f=hz_val, m=mode_raw: self.apply_sdr_settings(f, m))
                btn.pack(side="left", padx=5, pady=5)

        # --- SEKTION 2: MANUELLE STEUERUNG MIT MODI ---
        manual_frame = ttk.LabelFrame(sdr_container, text=" Manuelle Frequenz- & Moduswahl ", padding=10)
        manual_frame.pack(fill="x")

        # Zeile für Eingabe und Dropdown
        ctrl_row = ttk.Frame(manual_frame)
        ctrl_row.pack(fill="x", pady=5)

        # Frequenz-Eingabe (bleibt in Hz für die Technik)
        ttk.Label(ctrl_row, text="Hz:").pack(side="left", padx=2)
        entry = ttk.Entry(ctrl_row, textvariable=self.sdr_freq_var, width=15)
        entry.pack(side="left", padx=5)

        # Das "Schönlese"-Label für MHz
        self.mhz_label = ttk.Label(ctrl_row, text="0.000 MHz", font=("Arial", 10, "bold"), foreground="blue")
        self.mhz_label.pack(side="left", padx=10)

        # "Beobachter"-Funktion an die Variable
        self.sdr_freq_var.trace_add("write", self.update_mhz_display)

        # Modus-Dropdown
        ttk.Label(ctrl_row, text="Modus:").pack(side="left", padx=(10, 2))
        self.sdr_mode_var = tk.StringVar(value="FM")
        mode_combo = ttk.Combobox(ctrl_row, textvariable=self.sdr_mode_var, width=7, state="readonly")
        mode_combo['values'] = ("USB", "LSB", "AM", "FM", "WFM", "CW")
        mode_combo.pack(side="left", padx=5)

        # Setzen Button (überträgt Frequenz UND Modus)
        ttk.Button(ctrl_row, text="Anwenden", 
                   command=lambda: self.apply_sdr_settings(self.sdr_freq_var.get(), self.sdr_mode_var.get())).pack(side="left", padx=10)
        # print(f"SDR Backend in Config: {self.config.get('SDR', {}).get('sdr_mode', 'Nicht gesetzt')}") # Debug-Ausgabe
        if self.config.get("SDR", {}).get("sdr_mode") == "rtl_sdr":
            ttk.Button(ctrl_row, text="SDR stoppen", command=self.stop_direct_sdr).pack(side="left", padx=5)
            ttk.Label(ctrl_row, text="deemp Ein / Aus").pack(side="left", padx=(20, 2))
            self.deemp_var = tk.BooleanVar(value=True)
            deemp_check = ttk.Checkbutton(ctrl_row, variable=self.deemp_var, command=lambda: print(f"De-Emphasis {'AN' if self.deemp_var.get() else 'AUS'} (funktioniert nur bei direktem SDR-Modus)"))
            deemp_check.pack(side="left", padx=5)

        # Enter-Taste binden (nimmt den aktuell gewählten Modus)
        entry.bind("<Return>", lambda e: self.apply_sdr_settings(self.sdr_freq_var.get(), self.sdr_mode_var.get()))

        # Grob-Tuning Slider (2m Band als Beispiel)
        ttk.Label(manual_frame, text="Grob-Tuning (1.5 - 899 MHz):").pack(anchor="w", pady=(10, 0))
        slider = ttk.Scale(manual_frame, from_=1500000, to=899000000, orient="horizontal",
                           command=lambda v: self.sdr_freq_var.set(str(int(float(v)))))
        slider.set(145500000)
        slider.pack(fill="x", pady=5)

        self.squelch_var = tk.IntVar(value=0)

        # 2. Das Label für die Anzeige
        squelch_label = tk.Label(ctrl_row, text="Rauschsperre:")
        squelch_label.pack(side="left", padx=5)

        # 3. Die Spinbox erstellen
        self.squelch_spinbox = tk.Spinbox(
            ctrl_row, 
            from_=0,             # Minimaler Wert (Unterstrich bei from_ ist wichtig in Python!)
            to=100,              # Maximaler Wert
            increment=1,         # Schrittweite pro Klick
            textvariable=self.squelch_var, # Verknüpfung mit deiner Variable
            width=6              # Breite des Feldes (reicht dicke für Zahlen bis 100)
        )
        
        self.squelch_spinbox.pack(side="left", padx=5)

        # Status-Hinweis
        info_lbl = ttk.Label(sdr_container, text="ACHTUNG! Nicht jeder SDR-Stick kann den ganzen angebotenen Frequenzbereich!\nGqrx Remote (7356) muss aktiv sein.", font=("Arial", 8, "italic"))
        info_lbl.pack(side="bottom", pady=5)

    def update_mhz_display(self, *args): # <--- Aktualisiert die Anzeige der Frequenz in MHz, wenn sich die Hz-Eingabe ändert. Es wird versucht, die aktuelle Hz-Zahl zu parsen und in MHz umzurechnen, um sie benutzerfreundlich anzuzeigen. Fehlerhafte Eingaben führen zu einer Platzhalteranzeige von "--- MHz".
        """Rechnet Hz live in MHz um für bessere Lesbarkeit"""
        try:
            hz_val = float(self.sdr_freq_var.get())
            mhz_val = hz_val / 1_000_000
            # Zeigt es mit 3 Nachkommastellen an (z.B. 145.500)
            self.mhz_label.config(text=f"{mhz_val:07.3f} MHz".replace(".", ","))
        except:
            self.mhz_label.config(text="--- MHz")
    # --------- UI-GRUNDSTRUKTUR & -ELEMENTE & Menü ----------
    def setup_menu(self): # <--- Menü einrichten mit den Hauptkategorien "Datei", "Einstellungen" und "Hilfe". Unter "Datei" gibt es Optionen zum Beenden, Drucken des Einsatz-Logs, Setzen des Rufzeichens und erneuten Prüfen der Abhängigkeiten. Unter "Einstellungen" können die Hardware & Modi konfiguriert und eine externe Konsole geöffnet werden. Das "Hilfe"-Menü bietet Zugriff auf das Handbuch und Informationen über NoFuS-TX. Alle Menüaktionen sind mit entsprechenden Funktionen verknüpft, um die gewünschten Aktionen auszuführen.
        m = tk.Menu(self.root)
        self.root.config(menu=m)

        # DATEI
        datei_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Datei", menu=datei_m)
        datei_m.add_command(label="Beenden", command=self.root.quit)
        datei_m.add_command(label="Einsatz-Log drucken", command=lambda: self.print_message("\n".join(self.log_list.get(0, tk.END))))
        datei_m.add_command(label="Rufzeichen setzen", command=self.set_USERCALL)
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


    def show_manual_window(self): # <--- Den Hilfe-Tab aufrufen, der das Handbuch und weitere Informationen enthält. Es wird versucht, den entsprechenden Tab im Unter-Notebook auszuwählen und den Haupt-Hilfe-Tab zu aktivieren. Fehler bei der Anzeige führen zu einer Messagebox, die den Benutzer informiert, dass der Hilfebereich derzeit nicht verfügbar ist.
        try:
            self.help_notebook.select(self.sub_tab_manual)
            self.tabs.select(self.tab_help_main)
        except Exception:       
            messagebox.showinfo("Hilfe", "Der Hilfebereich ist derzeit nicht verfügbar.")

    def show_external_terminal_window(self): # <--- Die externe Konsole öffnen
        
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
    
    def setup_os_terminal_tab(self): # <--- Den OS-Terminal Tab einrichten. Zuerst wird ein Haupt-Container erstellt, in dem entweder eine Warnung oder das eigentliche Terminal angezeigt wird. Beim ersten Aufruf wird eine Warnung angezeigt, die den Benutzer über die Einschränkungen des integrierten Terminals informiert und ihn auffordert, die externe Konsole für volle Funktionalität zu nutzen. Sobald der Benutzer bestätigt, wird die Warnung entfernt und das Terminal geladen.
        # Haupt-Container für den Tab
        self.term_container = ttk.Frame(self.tab_os_terminal)
        self.term_container.pack(fill=tk.BOTH, expand=True)

        # Zuerst nur den Disclaimer zeigen
        self.show_terminal_disclaimer()

    def show_terminal_disclaimer(self): # <--- Zeigt eine Warnung im OS-Terminal Tab an, die den Benutzer über die Einschränkungen des integrierten Terminals informiert. Es wird ein zentral platzierter Frame erstellt, der eine mehrzeilige Nachricht enthält, die erklärt, dass das Terminal nur für einfache Systemabfragen gedacht ist und keine interaktiven Programme unterstützt. Ein Button ermöglicht es dem Benutzer, die Warnung zu entfernen und das Terminal zu aktivieren.
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

    def activate_terminal(self): # <--- Entfernt die Warnung und aktiviert das Terminal im OS-Terminal Tab. Es wird überprüft, ob die Warnung bereits existiert, und falls ja, wird sie entfernt. Anschließend wird das Terminal geladen und konfiguriert, damit der Benutzer sofort mit der Eingabe beginnen kann.
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
    def setup_help_and_info_tabs(self): # <--- Den Hilfe-Tab einrichten, der ein Unter-Notebook mit drei Tabs enthält: Checkliste, Bandpläne/Frequenzen und Handbuch/Hilfe. Jeder Tab wird mit einer entsprechenden Funktion gefüllt, die die Inhalte bereitstellt. Es wird versucht, die Inhalte korrekt anzuzeigen, und Fehler führen zu einer Messagebox, die den Benutzer informiert.
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

    def setup_manual_tab_content(self, parent_frame): # <--- Den Inhalt des "Hilfe"-Tabs einrichten, der eine PDF-Auswahl auf der rechten Seite und eine Vorschau mit Seitensteuerung auf der linken Seite enthält. Es wird ein Haupt-Frame erstellt, der horizontal in zwei Bereiche geteilt ist. Der linke Bereich enthält die PDF-Vorschau mit einer Seitensteuerung, während der rechte Bereich die Buttons für die verfügbaren PDFs und einen Button zum externen Öffnen des aktuell ausgewählten Dokuments enthält. Alle Funktionen sind so verknüpft, dass sie die Anzeige aktualisieren und die Navigation ermöglichen.
        
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

    def refresh_pdf_buttons(self): # <--- Aktualisiert die Liste der PDF-Buttons im "Hilfe"-Tab, indem sie den Inhalt des "assets/"-Ordners überprüft und für jede gefundene PDF-Datei einen Button erstellt. Es wird sichergestellt, dass der "assets/"-Ordner existiert, und falls er leer ist, wird eine entsprechende Nachricht angezeigt. Alle Buttons sind so konfiguriert, dass sie die ausgewählte PDF anzeigen und den externen Öffnen-Button aktivieren.
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

    
    def select_pdf(self, path, name): # <--- PDF auswählen und im Tool anzeigen. Es wird die aktuell ausgewählte PDF gespeichert, der Button zum externen Öffnen aktiviert und die Vorschau der PDF im linken Bereich aktualisiert. Alle Funktionen sind so verknüpft, dass sie die Anzeige korrekt aktualisieren und die Navigation ermöglichen.
        self.current_selected_pdf = path
        self.btn_open_extern.config(state="normal")
        
        # PDF im Tool anzeigen
        self.display_pdf_preview(path)

    def display_pdf_preview(self, path, page_num=0): # <--- Vorschau der PDF anzeigen. Es wird versucht, die PDF mit fitz zu öffnen, die angegebene Seite zu rendern und als Bild im linken Bereich anzuzeigen. Die Seitensteuerung wird entsprechend aktualisiert, damit der Benutzer durch die Seiten navigieren kann. Fehler bei der Anzeige führen zu einer Messagebox, die den Benutzer informiert.
        try:
            doc = fitz.open(path) # type: ignore
            self.total_pages = len(doc)
            self.current_page = page_num
            
            page = doc[self.current_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)) # Zoom 1.2 # type: ignore
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

    def change_page(self, delta): # <--- In der PDF Blättern 
        if hasattr(self, 'current_selected_pdf') and self.current_selected_pdf:
            new_page = self.current_page + delta
            if 0 <= new_page < self.total_pages:
                self.display_pdf_preview(self.current_selected_pdf, new_page)

    def open_current_pdf(self): # <--- PDF Öffnen
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
    def build_checklist_content(self, parent): # <-- Die Checkliste für Equip-Check
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
    def build_frequency_tables(self,parent): # <--- Die Frequenzübersichtstabelle erstellen. Es wird eine Treeview mit den Spalten "Mode", "Frequenz" und "Beschreibung" erstellt, die die Informationen aus der geladenen Frequenzliste anzeigt. Die Spaltenbreiten und Ausrichtungen werden so eingestellt, dass sie gut lesbar sind, und die Daten werden Zeile für Zeile in die Tabelle eingefügt.
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
    def load_and_build_bandplans(self, parent_notebook): # <--- Die Bandpläne aus der JSON Laden.
        # Datei laden (Fehlerbehandlung mit try/except wäre gut)
        band_plan_path = self.band_plan_file
        if not os.path.exists(band_plan_path):
            legacy_band_plan = os.path.join(base_path, "band_plan.json")
            if os.path.exists(legacy_band_plan):
                band_plan_path = legacy_band_plan

        with open(band_plan_path, "r", encoding="utf-8") as f:
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

    
    def draw_band_diagram(self, parent, segments): # <--- Bandplan grafik zeichnen ---
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

    def on_closing(self): # <--- Aufräumen beim Schließen der Anwendung. Es wird überprüft, ob der Direkte SDR-Modus aktiv ist, und falls ja, wird er gestoppt. Anschließend wird versucht, die Datenbankverbindung der Karte zu schließen, um sicherzustellen, dass alle Ressourcen freigegeben werden. Schließlich wird eine Nachricht ausgegeben, die den Benutzer darüber informiert, dass NoFuSTX beendet wird.
        
        if hasattr(self, 'map_widget'):
            
            try:
                self.map_widget.database_path = None # type: ignore
                print("[Map] Datenbank sauber synchronisiert.")
            except:
                pass
        print("[System] Beende NoFuSTX...")

    def is_online(self): # <--- Internet-Test Hat das Programm Internet?
        """Prüft robust, ob eine Internetverbindung besteht."""
        try:
            # Test um zu sehen, ob eine Verbindung zum Internet besteht, via Google
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except (socket.timeout, socket.error, OSError):
            return False

    def setup_map_view(self): # <--- Lagekarte einrichten
        """Initialisiert die Karte stabil ohne fehlerhaftes Pre-Caching."""
        
        if tkintermapview is None:
            tk.Label(self.tab_map, text="Karte nicht verfügbar").pack(expand=1)
            return

        # 1. Pfade
        map_folder = os.path.join(base_path, "off_Maps")
        os.makedirs(map_folder, exist_ok=True)
        db_path = os.path.join(map_folder, "offline_tiles.db")

        # === HIER DIE DATENBANK STRUKTUR VORBEREITEN ===
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Server-Tabelle anlegen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server (
                    url VARCHAR(300) PRIMARY KEY NOT NULL,
                    max_zoom INTEGER NOT NULL
                )
            ''')
            
            # Sections-Tabelle anlegen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sections (
                    position_a VARCHAR(100) NOT NULL,
                    position_b VARCHAR(100) NOT NULL,
                    zoom_a INTEGER NOT NULL,
                    zoom_b INTEGER NOT NULL,
                    server VARCHAR(300) NOT NULL,
                    CONSTRAINT fk_server FOREIGN KEY (server) REFERENCES server (url),
                    CONSTRAINT pk_tiles PRIMARY KEY (position_a, position_b, zoom_a, zoom_b, server)
                )
            ''')
            
            # Tiles-Tabelle anlegen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tiles (
                    zoom INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    server VARCHAR(300) NOT NULL,
                    tile_image BLOB NOT NULL,
                    CONSTRAINT fk_server FOREIGN KEY (server) REFERENCES server (url),
                    CONSTRAINT pk_tiles PRIMARY KEY (zoom, x, y, server)
                )
            ''')
            
            # Standard-Server eintragen, damit der Fremdschlüssel passt
            cursor.execute('''
                INSERT OR IGNORE INTO server (url, max_zoom)
                VALUES ('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', 19)
            ''')
            
            conn.commit()
            conn.close()
            # print("[DB-Setup] SQLite-Schema erfolgreich überprüft/erstellt.") # Optional für dein Log
        except Exception as e:
            print(f"⚠️ [DB-Setup] Fehler beim Erstellen der Tabellen: {e}")

        # 2. Online-Check
        online_status = False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1.0)
            online_status = True
        except: online_status = False
        
        print(f"[Map] {'🌐 ONLINE' if online_status else '🔌 OFFLINE'} aktiv.")
        self.write_session_log(f"Kartenmodus: {'Online' if online_status else 'Offline'}")
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
        self.btn_home_map = tk.Button(
            self.map_widget, 
            text="Karte Zentrieren", 
            command=lambda: self.center_to_coordinates(
                float(self.config.get("MAP", {}).get("home_lat", 51.9621)),
                float(self.config.get("MAP", {}).get("home_lon", 9.6509)),
                int(self.config.get("MAP", {}).get("zoom", 13))
            ),
            bg="#f0f0f0",
            fg="black",
            font=("Arial", 9, "bold"),
            relief="raised"
        )
        # Positionierung: 10 Pixel vom rechten und oberen Rand entfernt
        self.btn_home_map.place(relx=1.0, rely=0.0, x=-10, y=10, anchor="ne")

    def center_to_coordinates(self, lat, lon, zoom): # <--- Karte nach Koordinaten Zentrieren
        """Hilfsfunktion zum Zentrieren der Karte auf bestimmte Koordinaten."""
        try:
            self.map_widget.set_position(lat, lon)
            self.map_widget.set_zoom(zoom)
            print(f"[Map] Karte auf Home zentriert: {lat}, {lon} (Zoom: {zoom})")
        except Exception as e:
            print(f"[Map] Fehler beim Zentrieren: {e}")
        
    def manual_tile_save(self): # <--- Manueles speichern der Karten tiles in der offline_tiles.db
        """Startet den Offline-Download in einem Hintergrund-Thread."""
        db_path = os.path.join(base_path, "off_Maps", "offline_tiles.db")
        current_pos = self.map_widget.get_position()
        zoom = int(self.map_widget.zoom)

        def download_thread(): # <--- Kartendownload im Hintergrund damit die UI nicht einfriert.
            
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
#-------------- Diese Funktionen sind aus Entwicklungsgründen obsolet und werden aus Gründen der Historie beibehalten, bis sicher ist, dass sie nicht mehr benötigt werden. ------------
    def update_aprs_on_map(self):
        # Dieser Button ist obsolet; APRS-Marker werden stattdessen aus den eingehenden Positionsdaten erzeugt.
        pass

    def update_aprs_on_map_initial(self):
        """
        Startet – falls konfiguriert – mit einem APRS-Marker, ohne den Nutzer
        mit Warnmeldungen zu stören. Wird einmalig beim Programmstart aufgerufen.
        """
        # Kein automatischer "Station: ..." Marker mehr
        return
#------------------------------------------ Ende der Historie funktionen ------------------------------------------------------------------------------------------#
    # ---------- FUNDUS / UNITS ----------
    def setup_fundus_tab(self):# <--- Vollständiger Fundus mit Status-Umschaltung und Löschen erstellen
        
        for w in self.tab_fundus.winfo_children():
            w.destroy()

        lbl = ttk.Label(
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
            command=self.add_unit
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Status ändern", command=self.toggle_unit_status
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Einheit löschen", command=self.delete_unit
        ).pack(side="left", padx=5)

    # --- Neue Einheit hinzufügen ---
    def add_unit(self): # <--- Einheit hinzufügen und speichern
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

        
        def save(): # <--- 3. Speichern-Button mit Funktionalität
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
    def refresh_unit_tree(self): # <--- Einheitstabelle aktualisieren
        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in self.config.get("UNITS", []):
            stat_text = "EINSATZBEREIT" if u.get("status") else "NICHT AKTIV"
            self.tree.insert("", "end", values=(u["name"], u["type"], stat_text))

    # --- Status wechseln ---
    def toggle_unit_status(self): # <--- Status einer Einheit wechseln
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self.config["UNITS"][idx]["status"] = not self.config["UNITS"][idx]["status"]
            self.save_settings()
            self.refresh_unit_tree()

    # --- Einheit löschen ---
    def delete_unit(self): # <--- Ausgewählte Einheit löschen
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Löschen", "Einheit entfernen?"):
            idx = self.tree.index(sel[0])
            del self.config["UNITS"][idx]
            self.save_settings()
            self.refresh_unit_tree()

    # ---------- IARU MELDUNG ----------
    def setup_message_tab(self): # <--- IARU Meldungstab erstellen
        # IARU-Formular, das sich dynamisch mit dem Hauptfenster mitskaliert
        for w in self.tab_msg.winfo_children():
            w.destroy()

        # Grid-Layout für den ganzen Tab aktivieren
        self.tab_msg.rowconfigure(0, weight=0)   # Kopfzeile
        self.tab_msg.rowconfigure(1, weight=0)   # Wichtigkeit
        self.tab_msg.rowconfigure(2, weight=2)   # Meldungstext (soll wachsen)
        self.tab_msg.rowconfigure(3, weight=1)   # Verlauf
        self.tab_msg.rowconfigure(4, weight=0)   # Buttonzeile
        self.tab_msg.columnconfigure(0, weight=1)
        
        # Kopfdaten
        header_f = ttk.LabelFrame(self.tab_msg, text="Kopfdaten (IARU Standard)")
        header_f.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        titles = ["Nummer", "Quelle / Station", "Wort-Zaehler", "Herkunft", "Zeit (UTC)", "Datum"]
        self.msg_fields = {}

        for i, title in enumerate(titles):
            header_f.columnconfigure(i, weight=1)
            ttk.Label(header_f, text=title).grid(row=0, column=i, padx=5, sticky="w")
            
            if title == "Zeit (UTC)":
                # Container für Feld + Checkbox
                time_container = ttk.Frame(header_f)
                time_container.grid(row=1, column=i, sticky="ew")
                time_container.columnconfigure(0, weight=1) # Entry soll wachsen

                ent = ttk.Entry(time_container)
                ent.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="ew")
                self.msg_fields[title] = ent

                self.auto_time_var = tk.BooleanVar(value=True)
                cb = ttk.Checkbutton(time_container, text="Auto", variable=self.auto_time_var)
                cb.grid(row=0, column=1, padx=(0, 5))
            else:
                ent = ttk.Entry(header_f)
                ent.grid(row=1, column=i, padx=5, pady=5, sticky="ew")
                self.msg_fields[title] = ent

        # Zeit & Datum vorbelegen (UTC)
        self.msg_fields["Zeit (UTC)"].insert(
            0, self.utc_time_str()
        )
        self.msg_fields["Datum"].insert(
            0, self.utc_date_str()
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

        self.msg_text = tk.Text(body_f, font=("Arial", 12), wrap="word", bg="#FFFFFF", fg="#000000")
        self.msg_text.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)

        text_scroll = ttk.Scrollbar(
            body_f, orient="vertical", command=self.msg_text.yview
        )
        text_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        self.msg_text.configure(yscrollcommand=text_scroll.set)

        # Meldungsverlauf (scrollbar) oberhalb der Digimode-Buttons
        history_f = ttk.LabelFrame(self.tab_msg, text="Meldungsverlauf")
        history_f.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        history_f.rowconfigure(0, weight=1)
        history_f.columnconfigure(0, weight=1)

        self.msg_history_tree = ttk.Treeview(
            history_f,
            columns=("time", "nr", "prio", "direction", "summary"),
            show="headings",
            selectmode="browse",
        )
        self.msg_history_tree.heading("time", text="Zeit")
        self.msg_history_tree.heading("nr", text="Nr.")
        self.msg_history_tree.heading("prio", text="Wichtigkeit")
        self.msg_history_tree.heading("direction", text="Richtung")
        self.msg_history_tree.heading("summary", text="Kurzer Text")
        self.msg_history_tree.column("time", width=120, anchor="w")
        self.msg_history_tree.column("nr", width=60, anchor="center")
        self.msg_history_tree.column("prio", width=120, anchor="w")
        self.msg_history_tree.column("direction", width=100, anchor="w")
        self.msg_history_tree.column("summary", width=420, anchor="w")
        self.msg_history_tree.grid(row=0, column=0, sticky="nsew")

        history_scroll = ttk.Scrollbar(
            history_f, orient="vertical", command=self.msg_history_tree.yview
        )
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.msg_history_tree.configure(yscrollcommand=history_scroll.set)
        self.msg_history_tree.bind("<Double-1>", self.on_msg_history_double_click)

        self.msg_history_entries.clear()
        self.load_message_history()

        # Untere Steuerleiste: Digimode-Auswahl, Druck-Option, Buttons
        control_f = ttk.Frame(self.tab_msg)
        control_f.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        for i in range(5):
            control_f.columnconfigure(i, weight=0)
        control_f.columnconfigure(2, weight=1)

        ttk.Label(control_f, text="Digimode:").grid(row=0, column=0, padx=5, sticky="w")

        modes = ["Nur Log"]
        for mode, data in self.config["MODES"].items():
            # Alle aktiven Modi für Text-Übertragung anbieten
            if mode in ("RTTY", "WINLINK", "JS8CALL", "VARA", "MT63", "LORA_MESH") and data.get("active"):
                modes.append(mode)

        self.send_mode_var = tk.StringVar(value=modes[0])
        self.send_mode_combo = ttk.Combobox(
            control_f, values=modes, textvariable=self.send_mode_var, state="readonly", width=12
        )
        self.send_mode_combo.grid(row=0, column=1, padx=5, sticky="w")

        self.print_on_send = tk.BooleanVar(
            value=self.config.get("PRINTER", {}).get("auto_print", False)
        )
        ttk.Checkbutton(
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

    
    def clear_iaru_form(self): # <--- Meldungstext leeren und Formular für neue Meldung vorbereiten ---
        """Leert alle Felder des IARU-Formulars für eine neue Meldung."""

        # Alle Entry-Felder in der Kopfzeile leeren
        for title, field in self.msg_fields.items():
            field.delete(0, tk.END)
        
        # Das große Textfeld leeren
        self.msg_text.delete("1.0", tk.END)
        
        # Wichtigkeit auf Standard zurücksetzen
        self.prio_var.set("Routine")
        
        # Datum und Zeit sofort wieder neu belegen
        self.msg_fields["Datum"].insert(0, self.utc_date_str())
        # Die Zeit wird durch update_iaru_time automatisch befüllt, wenn Auto aktiv ist
        
        # Wort-Zähler auf 0 setzen
        self.update_word_count()
        
        self.msg_fields["Nummer"].insert(0, str(self.counter_number_msg))  # Neue Nummer eintragen
        # print("IARU-Formular wurde geleert.")

    # --- Wort-Zähler aktualisieren ---
    def update_word_count(self, event=None):
        """Zählt die Wörter im Textfeld und schreibt sie in das Feld 'Wort-Zaehler'."""
        content = self.msg_text.get("1.0", tk.END).strip()
        if not content:
            count = 0
        else:
            # Zählt alles, was durch Leerzeichen getrennt ist
            count = len(content.split())
        field = self.msg_fields["Wort-Zaehler"]
        field.delete(0, tk.END)
        field.insert(0, str(count))
    # --- Automatische UTC-Zeitaktualisierung ---
    def update_iaru_time(self):
        """Aktualisiert die UTC-Zeit im Formular, wenn Auto-Zeit aktiv ist."""
        # Prüfen, ob das Tab/Feld überhaupt noch existiert (vermeidet Fehler beim Schließen)
        if "Zeit (UTC)" in self.msg_fields and self.msg_fields["Zeit (UTC)"].winfo_exists():
            if self.auto_time_var.get():
                now = self.utc_time_str()
                # Feld leeren und neue Zeit rein
                self.msg_fields["Zeit (UTC)"].delete(0, tk.END)
                self.msg_fields["Zeit (UTC)"].insert(0, now)
        # Die Funktion ruft sich nach 1000ms (1 Sekunde) selbst wieder auf
        self.root.after(1000, self.update_iaru_time)
    
    def show_about_window(self): # <--- Über NoFuS-TX Fenster erstellen
        about_win = tk.Toplevel(self.root)
        about_win.title("Über NoFuS-TX")
        about_win.geometry("400x450")
        tk.Label(about_win, text="NoFuS-TX - Notfunk-Software").pack(pady=10)
        tk.Label(about_win, text=f"Version: {self.version_nummer}").pack(pady=10)
        tk.Label(about_win, text="© 2026 NoFuS-TX DO2ITH").pack(pady=5)
        tk.Label(about_win, text="Alle Rechte vorbehalten.").pack(pady=10)
        tk.Label(about_win, text="E-Mail: info@ithnet.de").pack(pady=10)
        tk.Label(about_win, text="Land: Deutschland").pack(pady=10)
        tk.Label(about_win, text="Webseite: https://www.ithnet.de").pack(pady=10)
        tk.Label(about_win, text="GitHub: https://github.com/jochenkurzschluss/NoFuSTX").pack(pady=10)
    
    def show_config_window(self): # <--- KONFIGURATION FENSTER MIT UNTERSCHIEDLICHEN REITERN FÜR JEDE FUNKTIONALITÄT (MODI, HARDWARE, SPEZIALFELDER, ETC.) ---
        # Hardware- & Modi-Konfiguration inkl. Drucker und SSTV-Spezialfeldern
        win = tk.Toplevel(self.root)
        win.title("Hardware Konfiguration")
        win.geometry("850x550")
        try:
            # Erstmal das Icon
            conf_icon = tk.PhotoImage(file="icons/settings.png") 
            win.iconphoto(False, conf_icon)
            # Referenz speichern, damit das Icon im Speicher bleibt
            win._icon_ref = conf_icon # type: ignore
        except Exception as e:
            print(f"Fehler beim Laden des Konfigurations-Icons: {e}")
        nb = ttk.Notebook(win)
        nb.pack(expand=1, fill="both", padx=5, pady=5)
        self.temp_entries = {}  # Initialisiere temp_entries
        #GUI
        gui_f = ttk.Frame(nb)
        nb.add(gui_f, text="GUI")
        params = self.config["GUI"]
        self.temp_entries["GUI"] = {}

        ttk.Label(gui_f, text="Oberfläche und Hintergrundfunktionen").pack()
        
        d_gui = tk.BooleanVar(value=params.get("debug", False))
        ttk.Checkbutton(gui_f, text="Debugausgaben Anzeigen", variable=d_gui).pack(pady=10)
        self.temp_entries["GUI"]["debug"] = d_gui

        e_gui = tk.BooleanVar(value=params.get("equip_check", False))
        ttk.Checkbutton(gui_f, text="Equipmentprüfung Beim Start", variable=e_gui).pack(pady=10)
        self.temp_entries["GUI"]["equip_check"] = e_gui

        i_gui = tk.BooleanVar(value=params.get("if_mesh_gps", False))
        ttk.Checkbutton(gui_f, text="Wenn MeshGPS Home-Automatisieren", variable=i_gui).pack(pady=10)
        self.temp_entries["GUI"]["if_mesh_gps"] = i_gui

        c_gui = ttk.Button(gui_f, text="Rufzeichen Neu Setzen", command=self.set_USERCALL)
        c_gui.pack(pady=10)

        v_gui = tk.BooleanVar(value=params.get("voltmeter", False))
        ttk.Checkbutton(gui_f, text="Voltmeter des Koffers", variable=v_gui).pack(pady=10)
        self.temp_entries["GUI"]["voltmeter"] = v_gui
        #GUI-MAP
        self.temp_entries["MAP"] = {}
        ttk.Label(gui_f, text="Karten Eigenschaften").pack()
        # --- zoom ---
        ttk.Label(gui_f, text="- Karten Zoom -").pack()
        map_gui = tk.Entry(gui_f)
        map_gui.insert(0, str(self.config.get("MAP", {}).get("zoom","11")))
        map_gui.pack(pady=2)
        self.temp_entries["MAP"]["zoom"] = map_gui
        # --- LAT ---
        ttk.Label(gui_f, text="- Karten Position LAT -").pack()
        map_gui = tk.Entry(gui_f)
        map_gui.insert(0, str(self.config.get("MAP", {}).get("center_lat")))
        map_gui.pack(pady=2)
        self.temp_entries["MAP"]["center_lat"] = map_gui
        # --- LON ---
        ttk.Label(gui_f, text="- Karten Position LON -").pack()
        map_gui = tk.Entry(gui_f)
        map_gui.insert(0, str(self.config.get("MAP", {}).get("center_lon")))
        map_gui.pack(pady=2)
        self.temp_entries["MAP"]["center_lon"] = map_gui


        # JS8Call
        js8_f = ttk.Frame(nb)
        nb.add(js8_f, text="JS8Call")
        params = self.config["MODES"]["JS8CALL"]
        self.temp_entries["JS8CALL"] = {}
        v = tk.BooleanVar(value=params.get("active", False))
        ttk.Checkbutton(js8_f, text="JS8Call Aktiv", variable=v).pack(pady=10)
        self.temp_entries["JS8CALL"]["active"] = v
        ttk.Label(js8_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(js8_f)
        freq_ent.insert(0, str(params.get("frequency", "7.078 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["JS8CALL"]["frequency"] = freq_ent
        f_use = tk.BooleanVar(value=params.get("use_fldigi", True))
        ttk.Checkbutton(js8_f, text="FLDIGI-Sendepfad aktiv", variable=f_use).pack(pady=5)
        self.temp_entries["JS8CALL"]["use_fldigi"] = f_use
        fldigi_modem = ttk.Entry(js8_f)
        fldigi_modem.insert(0, str(params.get("fldigi_modem", "BPSK31")))
        ttk.Label(js8_f, text="FLDIGI-Modem:").pack(pady=2)
        fldigi_modem.pack(pady=2)
        self.temp_entries["JS8CALL"]["fldigi_modem"] = fldigi_modem
        ttk.Label(js8_f, text="CALLSIGN:").pack()
        call_ent = ttk.Entry(js8_f)
        call_ent.insert(0, str(self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")))
        call_ent.pack(pady=2)
        self.temp_entries["JS8CALL"]["callsign"] = call_ent
        ttk.Label(js8_f, text="SOUNDCARD:").pack()
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
        ttk.Checkbutton(vara_f, text="VARA Aktiv", variable=v).pack(pady=10)
        self.temp_entries["VARA"]["active"] = v
        ttk.Label(vara_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(vara_f)
        freq_ent.insert(0, str(params.get("frequency", "14.105 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["VARA"]["frequency"] = freq_ent
        f_use = tk.BooleanVar(value=params.get("use_fldigi", True))
        ttk.Checkbutton(vara_f, text="FLDIGI-Sendepfad aktiv", variable=f_use).pack(pady=5)
        self.temp_entries["VARA"]["use_fldigi"] = f_use
        fldigi_modem = ttk.Entry(vara_f)
        fldigi_modem.insert(0, str(params.get("fldigi_modem", "SSB")))
        ttk.Label(vara_f, text="FLDIGI-Modem:").pack(pady=2)
        fldigi_modem.pack(pady=2)
        self.temp_entries["VARA"]["fldigi_modem"] = fldigi_modem
        ttk.Label(vara_f, text="CALLSIGN:").pack()
        call_ent = ttk.Entry(vara_f)
        call_ent.insert(0, str(self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")))
        call_ent.pack(pady=2)
        self.temp_entries["VARA"]["callsign"] = call_ent
        ttk.Label(vara_f, text="SOUNDCARD:").pack()
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
        ttk.Checkbutton(mt63_f, text="MT63 Aktiv", variable=v).pack(pady=10)
        self.temp_entries["MT63"]["active"] = v
        ttk.Label(mt63_f, text="FREQUENCY:").pack()
        freq_ent = ttk.Entry(mt63_f)
        freq_ent.insert(0, str(params.get("frequency", "7.040 MHz")))
        freq_ent.pack(pady=2)
        self.temp_entries["MT63"]["frequency"] = freq_ent
        f_use = tk.BooleanVar(value=params.get("use_fldigi", True))
        ttk.Checkbutton(mt63_f, text="FLDIGI-Sendepfad aktiv", variable=f_use).pack(pady=5)
        self.temp_entries["MT63"]["use_fldigi"] = f_use
        fldigi_modem = ttk.Entry(mt63_f)
        fldigi_modem.insert(0, str(params.get("fldigi_modem", "MT63-1KS")))
        ttk.Label(mt63_f, text="FLDIGI-Modem:").pack(pady=2)
        fldigi_modem.pack(pady=2)
        self.temp_entries["MT63"]["fldigi_modem"] = fldigi_modem
        ttk.Label(mt63_f, text="BANDWIDTH:").pack()
        bw_cb = ttk.Combobox(mt63_f, values=["500Hz", "1k", "2k"])
        bw_cb.set(params.get("bandwidth", "1k"))
        bw_cb.pack(pady=2)
        self.temp_entries["MT63"]["bandwidth"] = bw_cb
        ttk.Label(mt63_f, text="SOUNDCARD:").pack()
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
        self.ax_port_data = [dict(port) for port in self.config.get("MODES", {}).get("AX25_PORTS", [])]
        def render_ax_ports(): # <--- Dynamische Darstellung der AX.25 Ports mit Bearbeitungs- und Löschfunktion
            for w in self.ax_scroll_f.winfo_children():
                w.destroy()
            self.ax_temp_list = []
            
            # Hilfsfunktion, die beim Umschalten der Combobox anspringt
            def on_hardware_change(event, index, combobox):
                new_hardware = combobox.get()
                # Den neuen Typ im originalen Daten-Array speichern
                self.ax_port_data[index]["hardware"] = new_hardware
                # Wichtig: Die Liste einmal komplett neu zeichnen, damit das passende 'case' greift!
                render_ax_ports()

            for i, port in enumerate(self.ax_port_data):
                # Jeder Port hat auch einen Namen
                p_frame = ttk.LabelFrame(self.ax_scroll_f, text=f"AX.25 Port #{i+1}")
                p_frame.pack(fill="x", padx=10, pady=2)
                
                # Ist der Port An/Aus?!
                v = tk.BooleanVar(value=port.get("active", False))
                ttk.Checkbutton(p_frame, text="Aktiv", variable=v).grid(row=0, column=0)
                
                # Werden über dieses gerät auch APRS Frames empfangen ?
                aprs = tk.BooleanVar(value=port.get("aprs", False)) # Kleiner Fix: port.get("aprs") statt "active"
                ttk.Checkbutton(p_frame, text="APRS", variable=aprs).grid(row=1, column=0, padx=5, pady=5)
                
                # Hardwaretyp Festlegen
                ttk.Label(p_frame, text="Hardwaretyp:").grid(row=0, column=1, padx=5)
                dm = ttk.Combobox(p_frame, values=self.options.get("HARDWARE", []), width=9, state="readonly")
                dm.set(port.get("hardware", "ax"))
                dm.grid(row=1, column=1, padx=5)
                
                # --- HIER IST DIE MAGIE: Das Event an die Combobox binden ---
                # Wir übergeben den aktuellen Index (i) und die Combobox selbst an die Funktion
                dm.bind("<<ComboboxSelected>>", lambda event, idx=i, cb=dm: on_hardware_change(event, idx, cb))
                
                # --- Abfragen welcher Hardware Typ je port genutzt wird!
                match port.get("hardware", "ax"):
                    case "kiss": # <--- Kiss Typ 
                        # Baud Rate festlegen, geschwindigkeit der Übertragung
                        ttk.Label(p_frame, text="Baudrate:").grid(row=0, column=2, padx=5)
                        dev_baud = ttk.Combobox(p_frame, values=self.options.get("BAUD_RATES", []), width=8, state="normal")
                        dev_baud.set(port.get("BAUD_RATE", "9600"))
                        dev_baud.grid(row=1, column=2, padx=5)
                        # Wie ist die Hardware Adresse des Geräts
                        ttk.Label(p_frame, text="tty/Com Port:").grid(row=0, column=3, padx=5)
                        dev = ttk.Entry(p_frame, width=10)
                        dev.insert(0, port.get("device", "/dev/ttyUSB0"))
                        dev.grid(row=1, column=3, padx=5)
                        # Alias des Geräts zur Identifikation
                        ttk.Label(p_frame, text="Alias des Geräts:").grid(row=0, column=4, padx=5)
                        nick = ttk.Entry(p_frame, width=15)
                        nick.insert(0, port.get("nickname", ""))
                        nick.grid(row=1, column=4, padx=5)
                        # Rufzeichen mögliche abweichung (Trennung CB / AFU)
                        ttk.Label(p_frame, text="Verwendeter Call:").grid(row=0, column=5, padx=5)
                        call = ttk.Entry(p_frame, width=10)
                        if port.get("call", "") == self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL") or port.get("call", "") == "NOCALL":
                            call.insert(0, self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL"))
                        else:
                            call.insert(0, port.get("call", "NOCALL"))
                        call.grid(row=1, column=5, padx=5)
                                                
                        # Löschen funktion des Ports. Bedeuted durch drücken auf den X Button wird der Ganze Port aus der Konfiguration gelöscht
                        ttk.Label(p_frame, text="Port Löschen:").grid(row=0, column=6, padx=5)
                        btn_del = ttk.Button(
                            p_frame,
                            text="X",
                            width=3,
                            command=lambda idx=i: remove_ax_port(idx),
                        )
                        btn_del.grid(row=1, column=6, padx=5)
                        self.ax_temp_list.append(
                            {"active": v, "aprs": aprs, "hardware": dm, "BAUD_RATE": dev_baud, "device": dev, "nickname": nick, "call": call}
                        )
                        
                    case "ax": # <--- der Klassische AX.25 Kernel weg (es wird mit axlisten gearbeitet)
                        ttk.Label(p_frame, text="AX Port bei Unix:").grid(row=0, column=2, padx=5)
                        dev = ttk.Combobox(p_frame, values=self.options.get("AX25_DEVICES", []), width=8, state="normal")
                        dev.set(port.get("device", "ax0"))
                        dev.grid(row=1, column=2, padx=5)
                        ttk.Label(p_frame, text="Alias des Geräts:").grid(row=0, column=3, padx=5)
                        nick = ttk.Entry(p_frame, width=15)
                        nick.insert(0, port.get("nickname", ""))
                        nick.grid(row=1, column=3, padx=5)
                        ttk.Label(p_frame, text="Verwendeter Call:").grid(row=0, column=4, padx=5)
                        call = ttk.Entry(p_frame, width=10)
                        if port.get("call", "") == self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL") or port.get("call", "") == "NOCALL":
                            call.insert(0, self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL"))
                        else:
                            call.insert(0, port.get("call", "NOCALL"))
                        call.grid(row=1, column=4, padx=5)
                        ttk.Label(p_frame, text="Port Löschen:").grid(row=0, column=5, padx=5)
                        btn_del = ttk.Button(
                            p_frame,
                            text="X",
                            width=3,
                            command=lambda idx=i: remove_ax_port(idx),
                        )
                        btn_del.grid(row=1, column=5, padx=5)
                        dev_baud = port.get("BAUD_RATE", "9600")
                        self.ax_temp_list.append(
                            {"active": v, "aprs": aprs, "hardware": dm, "BAUD_RATE": dev_baud, "device": dev, "nickname": nick, "call": call}
                        )
                        
                    case "ip": # <--- IP Basierte verbindungen ähnlich wie axip oder ähnliche
                        # Baud Rate festlegen, geschwindigkeit der Übertragung
                        ttk.Label(p_frame, text="Baudrate:").grid(row=0, column=2, padx=5)
                        dev_baud = ttk.Combobox(p_frame, values=self.options.get("BAUD_RATES", []), width=8, state="normal")
                        dev_baud.set(port.get("BAUD_RATE", "9600"))
                        dev_baud.grid(row=1, column=2, padx=5)
                        # Wie ist die Hardware Adresse des Geräts
                        ttk.Label(p_frame, text="Adresse:").grid(row=0, column=3, padx=5)
                        dev = ttk.Entry(p_frame, width=10)
                        dev.insert(0, port.get("device", "192.168.2.1:8081"))
                        dev.grid(row=1, column=3, padx=5)
                        # Alias des Geräts zur Identifikation
                        ttk.Label(p_frame, text="Alias des Geräts:").grid(row=0, column=4, padx=5)
                        nick = ttk.Entry(p_frame, width=15)
                        nick.insert(0, port.get("nickname", ""))
                        nick.grid(row=1, column=4, padx=5)
                        # Rufzeichen mögliche abweichung (Trennung CB / AFU)
                        ttk.Label(p_frame, text="Verwendeter Call:").grid(row=0, column=5, padx=5)
                        call = ttk.Entry(p_frame, width=10)
                        if port.get("call", "") == self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL") or port.get("call", "") == "NOCALL":
                            call.insert(0, self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL"))
                        else:
                            call.insert(0, port.get("call", "NOCALL"))
                        call.grid(row=1, column=5, padx=5)
                                                
                        # Löschen funktion des Ports. Bedeuted durch drücken auf den X Button wird der Ganze Port aus der Konfiguration gelöscht
                        ttk.Label(p_frame, text="Port Löschen:").grid(row=0, column=6, padx=5)
                        btn_del = ttk.Button(
                            p_frame,
                            text="X",
                            width=3,
                            command=lambda idx=i: remove_ax_port(idx),
                        )
                        btn_del.grid(row=1, column=6, padx=5)
                        self.ax_temp_list.append(
                            {"active": v, "aprs": aprs, "hardware": dm, "BAUD_RATE": dev_baud, "device": dev, "nickname": nick, "call": call}
                        )
                        
                    case "soft":
                        # Baud Rate festlegen, geschwindigkeit der Übertragung
                        ttk.Label(p_frame, text="Baudrate:").grid(row=0, column=2, padx=5)
                        dev_baud = ttk.Combobox(p_frame, values=self.options.get("BAUD_RATES", []), width=8, state="normal")
                        dev_baud.set(port.get("BAUD_RATE", "9600"))
                        dev_baud.grid(row=1, column=2, padx=5)
                        # Wie ist die Hardware Adresse des Geräts
                        ttk.Label(p_frame, text="Software:").grid(row=0, column=3, padx=5)
                        dev = ttk.Entry(p_frame, width=10)
                        dev.insert(0, port.get("device", "fldigi"))
                        dev.grid(row=1, column=3, padx=5)
                        # Alias des Geräts zur Identifikation
                        ttk.Label(p_frame, text="Alias des Geräts:").grid(row=0, column=4, padx=5)
                        nick = ttk.Entry(p_frame, width=15)
                        nick.insert(0, port.get("nickname", ""))
                        nick.grid(row=1, column=4, padx=5)
                        # Rufzeichen mögliche abweichung (Trennung CB / AFU)
                        ttk.Label(p_frame, text="Verwendeter Call:").grid(row=0, column=5, padx=5)
                        call = ttk.Entry(p_frame, width=10)
                        if port.get("call", "") == self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL") or port.get("call", "") == "NOCALL":
                            call.insert(0, self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL"))
                        else:
                            call.insert(0, port.get("call", "NOCALL"))
                        call.grid(row=1, column=5, padx=5)
                                                
                        # Löschen funktion des Ports. Bedeuted durch drücken auf den X Button wird der Ganze Port aus der Konfiguration gelöscht
                        ttk.Label(p_frame, text="Port Löschen:").grid(row=0, column=6, padx=5)
                        btn_del = ttk.Button(
                            p_frame,
                            text="X",
                            width=3,
                            command=lambda idx=i: remove_ax_port(idx),
                        )
                        btn_del.grid(row=1, column=6, padx=5)
                        self.ax_temp_list.append(
                            {"active": v, "aprs": aprs, "hardware": dm, "BAUD_RATE": dev_baud, "device": dev, "nickname": nick, "call": call}
                        )
                    
        def add_ax_port(): # <--- AX port hinzufügen (Ergänzt mit allen Standardwerten)
            # Holen des Standard-Rufzeichens aus der Konfiguration, falls vorhanden
            default_call = self.config.get("USERCALL", {}).get("CALLSINGEN", "NOCALL")
            self.ax_port_data.append({
                "active": False,
                "aprs": False,
                "hardware": "ax",                       # Startet standardmäßig als klassischer Unix-AX-Port
                "device": "ax0",                        # Standard-Device (wird bei Umschalten auf KISS/IP/Soft überschrieben)
                "BAUD_RATE": "9600",                    # Standard-Geschwindigkeit für KISS, IP und Soft
                "nickname": "",                         # Leeres Alias Feld
                "call": default_call                    # Setzt direkt dein Haupt-Rufzeichen als Standard ein
            })
            # UI neu zeichnen, damit der neue Port sofort unten auftaucht
            render_ax_ports()
        def remove_ax_port(idx): # <--- AX port entfernen
            if messagebox.askyesno("Löschen", f"AX.25 Port #{idx+1} entfernen?"):
                if 0 <= idx < len(self.ax_port_data):
                    del self.ax_port_data[idx]
                render_ax_ports()
        render_ax_ports() # <--- AUSGEBEN DER AKTUELLEN AX.25 PORTS
        add_button_frame = ttk.Frame(ax_f)
        add_button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(add_button_frame, text="Neuen AX.25 Port hinzufügen", command=add_ax_port).pack(side="left")
        
        # --- SDR einrichten --- 
        sdr_f = ttk.Frame(nb)
        nb.add(sdr_f, text="SDR")
        self.temp_entries["SDR"] = {}
        ttk.Label(sdr_f, text="SDR System:").pack(pady=5)
        v_sdr_active = tk.BooleanVar(value=self.config.get("SDR", {}).get("active", False))
        ttk.Checkbutton(sdr_f, text="SDR aktivieren", variable=v_sdr_active).pack(pady=10)
        self.temp_entries["SDR"]["active"] = v_sdr_active
        sdr_options = ["rtl_sdr", "gqrx", "none"]
        self.sdr_system = ttk.Combobox(sdr_f, values=sdr_options)
        ttk.Label(sdr_f, text="SDR Sample Rate (Hz):").pack(pady=5)
        sdr_rate_f = ttk.Frame(sdr_f)
        sdr_rate_f.pack(pady=5, padx=10, fill="x")
        sdr_rate = ttk.Entry(sdr_rate_f)
        sdr_rate.pack(fill="x")
        current_sdr_rate = self.config.get("SDR", {}).get("sdr_rate", "")
        sdr_rate.insert(0, current_sdr_rate)
        self.temp_entries["SDR"]["sdr_rate"] = sdr_rate
        ttk.Label(sdr_f, text="SDR Audio Rate (Hz):").pack(pady=5)
        sdr_audio_rate_f = ttk.Frame(sdr_f)
        sdr_audio_rate_f.pack(pady=5, padx=10, fill="x")
        sdr_audio_rate = ttk.Entry(sdr_audio_rate_f)
        sdr_audio_rate.pack(fill="x")
        current_sdr_audio_rate = self.config.get("SDR", {}).get("audio_rate_sdr", "")
        sdr_audio_rate.insert(0, current_sdr_audio_rate)
        self.temp_entries["SDR"]["sdr_audio_rate"] = sdr_audio_rate
        ttk.Label(sdr_f, text="APLAY Audio Rate (Hz):").pack(pady=5)
        aplay_audio_f = ttk.Frame(sdr_f)
        aplay_audio_f.pack(pady=5, padx=10, fill="x")
        aplay_audio_rate = ttk.Entry(aplay_audio_f)
        aplay_audio_rate.pack(fill="x")
        current_aplay_audio_rate = self.config.get("SDR", {}).get("audio_rate_aplay", "")
        aplay_audio_rate.insert(0, current_aplay_audio_rate)
        self.temp_entries["SDR"]["audio_rate_aplay"] = aplay_audio_rate
        current_sdr = self.config.get("SDR", {}).get("sdr_mode", "")
        if current_sdr and current_sdr in sdr_options:
            self.sdr_system.set(current_sdr)
        elif sdr_options:
            self.sdr_system.set(sdr_options[0])
        self.sdr_system.pack(pady=5, padx=10, fill="x")
        self.temp_entries["SDR"]["sdr_mode"] = self.sdr_system
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
        ttk.Checkbutton(pr_f, text="Auto-Print", variable=self.prn_auto).pack(pady=10)
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
            ttk.Checkbutton(f, text=f"{mode} Aktiv", variable=v).pack(pady=10)
            self.temp_entries[mode]["active"] = v
            if mode == "SSTV":
                ttk.Label(f, text="SSTV MODUS:").pack()
                ms = ttk.Combobox(f, values=self.options["SSTV_MODES"])
                ms.set(params.get("mode", "Martin 1"))
                ms.pack()
                self.temp_entries[mode]["mode"] = ms
                ttk.Label(f, text="SOUNDKARTE:").pack()
                ss = ttk.Combobox(f, values=["System", "USB Codec", "Virtual"])
                ss.set(params.get("soundcard", "System"))
                ss.pack()
                self.temp_entries[mode]["soundcard"] = ss
                f_use = tk.BooleanVar(value=params.get("use_fldigi", True))
                ttk.Checkbutton(f, text="FLDIGI-Sendepfad aktiv", variable=f_use).pack(pady=5)
                self.temp_entries[mode]["use_fldigi"] = f_use
                fldigi_modem = ttk.Entry(f)
                fldigi_modem.insert(0, str(params.get("fldigi_modem", "SSB")))
                ttk.Label(f, text="FLDIGI-Modem:").pack(pady=2)
                fldigi_modem.pack(pady=2)
                self.temp_entries[mode]["fldigi_modem"] = fldigi_modem
            elif mode == "RTTY":
                # Spezielle RTTY-Konfiguration inkl. Soundkarte
                ttk.Label(f, text="BPS:").pack()
                bps_cb = ttk.Combobox(f, values=self.options["RTTY_BPS"], width=10)
                bps_cb.set(str(params.get("bps", "45.45")))
                bps_cb.pack(pady=2)
                self.temp_entries[mode]["bps"] = bps_cb
                ttk.Label(f, text="SHIFT (Hz):").pack()
                shift_ent = ttk.Entry(f)
                shift_ent.insert(0, str(params.get("shift", "170")))
                shift_ent.pack(pady=2)
                self.temp_entries[mode]["shift"] = shift_ent
                ttk.Label(f, text="SOUNDKARTE:").pack()
                rtty_sc = ttk.Combobox(f, values=["System", "USB Codec", "Virtual"])
                rtty_sc.set(params.get("soundcard", "System"))
                rtty_sc.pack(pady=2)
                self.temp_entries[mode]["soundcard"] = rtty_sc
                f_use = tk.BooleanVar(value=params.get("use_fldigi", True))
                ttk.Checkbutton(f, text="FLDIGI-Sendepfad aktiv", variable=f_use).pack(pady=5)
                self.temp_entries[mode]["use_fldigi"] = f_use
                fldigi_modem = ttk.Entry(f)
                fldigi_modem.insert(0, str(params.get("fldigi_modem", "RTTY")))
                ttk.Label(f, text="FLDIGI-Modem:").pack(pady=2)
                fldigi_modem.pack(pady=2)
                self.temp_entries[mode]["fldigi_modem"] = fldigi_modem
            else:
                for k, val in params.items():
                    if k == "active":
                        continue
                    ttk.Label(f, text=k.upper()).pack()
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
    def apply_config(self, win): # <--- Alle Einstellungen aus dem Konfigurationsfenster übernehmen, speichern und Fenster schließen
        # --- AX.25 Ports sicher übernehmen ---
        ax25_ports_saved = []
        for p in self.ax_temp_list:
            
            # Erstmal prüfen, ob die Baudrate ein Widget (.get()) oder ein fester Wert ist
            baud_value = p["BAUD_RATE"]
            if hasattr(baud_value, "get"):
                baud_value = baud_value.get()  # Es ist eine Combobox (kiss, ip, soft)
            else:
                baud_value = str(baud_value)   # Es ist der feste Wert aus dem "ax"-Case

            # Die Basis-Daten, die JEDER Hardware-Typ hat
            port_dict = {
                "active": p["active"].get(),
                "aprs": p["aprs"].get(),
                "hardware": p["hardware"].get(),
                "BAUD_RATE": baud_value,       # Der sauber ermittelte Wert
                "device": p["device"].get(),
                "nickname": p["nickname"].get(),
                "call": p["call"].get(),
            }
                
            ax25_ports_saved.append(port_dict)

        # In die Konfiguration schreiben
        self.config["MODES"]["AX25_PORTS"] = ax25_ports_saved

        # Drucker übernehmen
        self.config["PRINTER"] = {
            "name": self.prn_name.get(),
            "auto_print": self.prn_auto.get(),
        }
        # SDR übernehmen
        self.config["SDR"] = {
            "active": self.temp_entries["SDR"]["active"].get(),
            "sdr_mode": self.temp_entries["SDR"]["sdr_mode"].get(),
            "sdr_rate": self.temp_entries["SDR"]["sdr_rate"].get(),
            "audio_rate_sdr": self.temp_entries["SDR"]["sdr_audio_rate"].get(),
            "audio_rate_aplay": self.temp_entries["SDR"]["audio_rate_aplay"].get(),
        }
        # GUI übernehmen
        self.config["GUI"] = {
            "debug": self.temp_entries["GUI"]["debug"].get(),
            "equip_check": self.temp_entries["GUI"]["equip_check"].get(),
            "if_mesh_gps": self.temp_entries["GUI"]["if_mesh_gps"].get(),
            "voltmeter": self.temp_entries["GUI"]["voltmeter"].get(),
        }
        self.config["MAP"] = {
            "center_lat": self.temp_entries["MAP"]["center_lat"].get(),
            "center_lon": self.temp_entries["MAP"]["center_lon"].get(),
            "zoom": self.temp_entries["MAP"]["zoom"].get(),
        }
        # Modi übernehmen
        for m, entries in self.temp_entries.items():
            if m in self.config["MODES"]:
                self.config["MODES"][m]["active"] = entries["active"].get()
                for k, widget in entries.items():
                    if k == "active":
                        continue
                    self.config["MODES"][m][k] = widget.get()
                    
        self.save_settings() # <--- Speichernfunktion
        self.setup_digimode_terminals() # <--- Terminal-Fenster neu aufbauen, da sich die aktiven Modi geändert haben könnten
        self.setup_fundus_tab() # <--- Fundus-Tab neu aufbauen, da sich die Modi und damit die verfügbaren Meldungen geändert haben könnten
        win.destroy() # <--- Schließen des Kofig Fensters
    # ---------- DIGIMODES ----------
    def setup_digimode_terminals(self): # <--- Terminal-Fenster für die aktiven Digimodes aufbauen (AX.25 Ports, LoRa Mesh, etc.)
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
                t_rx = tk.LabelFrame(f, text=" Funkverkehr (RX Text) ", fg="#00FF00", bg="#001100")
                t_rx.pack(expand=1, fill="both", padx=5, pady=2)
                t = tk.Text(t_rx, bg="#001100", fg="#00FF00", font=("Arial", 14))
                t.pack(expand=1, fill="both")
                t_tx = tk.LabelFrame(f, text=" Funkverkehr (TX Text) ", fg="#00FF00", bg="#001100")
                t_tx.pack(expand=1, fill="both", padx=5, pady=2)
                t_tx = tk.Entry(t_tx, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                t_tx.pack(expand=1, fill="both")
                key = f"AX:{port.get('nickname', '')}"
                self.digi_terminals[key] = t
                
        for mode, data in self.config["MODES"].items():
            if mode == "LORA_MESH" and data.get("active"):
                f = ttk.Frame(nb)
                nb.add(f, text=f"{mode}")
                self.digi_terminals[mode] = {}
                
                # --- RECHTE SEITE: Die Liste zuerst ---
                lf_list = tk.LabelFrame(f, text=" Aktive Nodes ", fg="#00FF00", bg="#001100")
                lf_list.pack(side="right", fill="both", padx=5, pady=2)
                
                scrollbar = tk.Scrollbar(lf_list, orient="vertical", bg="#001100")
                scrollbar.pack(side="right", fill="y")
                scrollbarR = tk.Scrollbar(lf_list, orient="horizontal", bg="#001100")
                scrollbarR.pack(side="bottom", fill="x")
                
                node_list = tk.Listbox(
                    lf_list, 
                    bg="#001100", 
                    fg="#00FF00", 
                    font=("Courier", 14), 
                    borderwidth=0, 
                    width=35,
                    yscrollcommand=scrollbar.set,
                    xscrollcommand=scrollbarR.set
                )
                node_list.pack(side="left", expand=1, fill="both", padx=5, pady=5)
                scrollbar.config(command=node_list.yview)
                scrollbarR.config(command=node_list.xview)
                
                self.digi_terminals[mode]["node_list"] = node_list
                self.digi_terminals["LORA_MESH"]["node_list"].bind("<Motion>", self.show_node_tooltip)
                self.digi_terminals["LORA_MESH"]["node_list"].bind("<Leave>", self.hide_node_tooltip)
                self.digi_terminals["LORA_MESH"]["node_list"].bind("<Double-1>", self.on_mheard_double_click)
                
                # --- LINKE SEITE ---
                left_container = tk.Frame(f, bg="#001100")
                left_container.pack(side="left", expand=1, fill="both")
                
                # MONITOR BEREICH
                lf_mon = tk.LabelFrame(left_container, text=" System-Status / Monitor ", fg="#00FF00", bg="#001100")
                lf_mon.pack(fill="x", padx=5, pady=2)
                mon = tk.Text(lf_mon, height=8, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                mon.pack(fill="x", padx=5, pady=5)
                self.digi_terminals[mode]["monitor"] = mon
                
                # Unterstrukturen für Kanäle anlegen
                self.digi_terminals[mode]["receive_channels"] = {}
                self.digi_terminals[mode]["sender_channels"] = {}  # <--- NEU: Platz für die Kanal-Sender
                
                # RECEIVE & SENDER BEREICH
                if getattr(self, 'rx_mesh_ch_tab', 0) == 0 or not hasattr(self, 'mesh_channels_dict') or not self.mesh_channels_dict:
                    # Fallback: Alles wie gehabt in einem einzigen Block, wenn keine Tabs aktiv sind
                    lf_recv = tk.LabelFrame(left_container, text=" Funkverkehr (RX Text) ", fg="#00FF00", bg="#001100")
                    lf_recv.pack(expand=1, fill="both", padx=5, pady=2)
                    recv = tk.Text(lf_recv, height=10, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                    recv.pack(expand=1, fill="both", padx=5, pady=5)
                    
                    lf_send = tk.LabelFrame(left_container, text=" Senden (TX Text) ", fg="#00FF00", bg="#001100")
                    lf_send.pack(fill="x", padx=5, pady=2)
                    send = tk.Entry(lf_send, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                    send.pack(fill="x", padx=5, pady=5)
                    send.bind("<Return>", self.on_mesh_send_enter)
                    
                    self.digi_terminals[mode]["receive"] = recv
                    self.digi_terminals[mode]["sender"] = send
                    self.digi_terminals[mode]["receive_channels"][0] = recv
                    self.digi_terminals[mode]["sender_channels"][0] = send
                else:
                    # ECHTE REITER (TABS) FÜR RX UND TX PRO KANAL
                    print(f"[MESH-UI] Erstelle Kanäle (RX+TX) als TABS hintereinander:\n{self.mesh_channels_dict}")
                    
                    channel_nb = ttk.Notebook(left_container)
                    channel_nb.pack(expand=1, fill="both", padx=5, pady=2)
                    
                    for ch_index, ch_name in self.mesh_channels_dict.items():
                        # Frame für den Kanal-Tab
                        ch_frame = tk.Frame(channel_nb, bg="#001100")
                        channel_nb.add(ch_frame, text=f" CH {ch_index}: {ch_name} ")
                        
                        # 1. Empfangsfeld im Tab
                        lf_recv = tk.LabelFrame(ch_frame, text=f" Funkverkehr ({ch_name}) ", fg="#00FF00", bg="#001100")
                        lf_recv.pack(expand=1, fill="both", padx=2, pady=2)
                        recv = tk.Text(lf_recv, height=10, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                        recv.pack(expand=1, fill="both", padx=5, pady=5)
                        
                        # 2. Sendefeld IM SELBEN TAB direkt darunter packen
                        lf_send = tk.LabelFrame(ch_frame, text=f" Senden ({ch_name}) ", fg="#00FF00", bg="#001100")
                        lf_send.pack(fill="x", padx=2, pady=2)
                        send = tk.Entry(lf_send, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                        send.pack(fill="x", padx=5, pady=5)
                        
                        # Event-Binding bleibt gleich, wir hängen aber Infos ans Widget (siehe Tipp unten)
                        send.bind("<Return>", self.on_mesh_send_enter)
                        send._mesh_channel_id = ch_index  # <--- Trick: Kanal-ID direkt ans Widget tackern! # type: ignore
                        
                        # Im Dictionary einsortieren
                        self.digi_terminals[mode]["receive_channels"][ch_index] = recv
                        self.digi_terminals[mode]["sender_channels"][ch_index] = send
                    
                    # Abwärtskompatibilität für alte Funktionen
                    if 0 in self.digi_terminals[mode]["receive_channels"]:
                        self.digi_terminals[mode]["receive"] = self.digi_terminals[mode]["receive_channels"][0]
                    if 0 in self.digi_terminals[mode]["sender_channels"]:
                        self.digi_terminals[mode]["sender"] = self.digi_terminals[mode]["sender_channels"][0]
                
        # Weitere Modi als einfache Terminals
        for mode, data in self.config["MODES"].items():
            if mode not in ("AX25_PORTS", "APRS_IS", "LORA_MESH", "LORA_APRS") and data.get("active"):
                f = ttk.Frame(nb)
                nb.add(f, text=mode)
                t_container = tk.Frame(f, bg="#001100")
                t_container.pack(expand=1, fill="both")
                
                t_recive = tk.LabelFrame(t_container, text=" Funkverkehr (RX Text) ", fg="#00FF00", bg="#001100")
                t_recive.pack(expand=1, fill="both", padx=5, pady=2)
                t = tk.Text(t_recive, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                t.pack(expand=1, fill="both", padx=5, pady=5)
                
                t_send = tk.LabelFrame(t_container, text=" Senden (TX Text) ", fg="#00FF00", bg="#001100")
                t_send.pack(fill="x", padx=5, pady=2)
                t_send_entry = tk.Entry(t_send, bg="#001100", fg="#00FF00", font=("Arial", 14), borderwidth=0)
                t_send_entry.pack(fill="x", padx=5, pady=5)
                t_send_entry.bind("<Return>", self.on_digimode_send_enter)
                t_send_entry._digimode_mode = mode # type: ignore
                self.digi_terminals[mode] = {"receive": t, "sender": t_send_entry}
    # ---------- LOG ----------
    def get_utc_now(self): # <--- Hole den UTC Timestamp
        """Gibt die aktuelle UTC-Zeit zurück, kompatibel für ältere und neuere Python-Versionen."""
        try:
            return datetime.datetime.now(datetime.timezone.utc)
        except AttributeError:
            return datetime.datetime.utcnow()
    def utc_iso_timestamp(self, dt=None): # <--- Formatiere einen UTC Timestamp im ISO-Format (z.B. für IARU-Meldungen)
        dt = dt or self.get_utc_now()
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    def utc_time_str(self, dt=None): # <--- Formatiere einen UTC Timestamp als Zeitstring (z.B. für die Anzeige in der Historie)
        dt = dt or self.get_utc_now()
        return dt.strftime("%H:%M:%S")
    def utc_date_str(self, dt=None): # <--- Formatiere einen UTC Timestamp als Datumstring (z.B. für die Anzeige in der Historie)
        dt = dt or self.get_utc_now()
        return dt.strftime("%d.%m.%Y")
    def formatted_utc_timestamp(self, timestamp=None): # <--- Formatiere einen UTC Timestamp als Zeitstring, mit Fehlerbehandlung (z.B. für die Anzeige in der Historie)
        dt=None
        try:
            if timestamp is not None:
                dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                #print(f"[DEBUG] die Variable sieht so aus: {dt}")
            return dt.strftime("%H:%M:%S") # type: ignore
        except Exception:
            return None
    def ago_rx(self, timestamp): # <--- Berechnet die vergangenen Minuten seit dem letzten RX unter Nutzung von get_utc_now
        if not timestamp:
            return "Nie"
        try:
            # 1. Deine vorhandene Funktion nutzen und direkt in Sekunden (Unix-Timestamp) umwandeln
            jetzt_ts = time.time()
            # 2. Differenz berechnen
            diff_sekunden = float(jetzt_ts) - float(timestamp)
            
            # Sicherheitsnetz für minimale Zeitabweichungen
            if diff_sekunden < 0:
                diff_sekunden = 0
                
            # 3. In Minuten umrechnen
            diff_minuten = diff_sekunden // 60
            
            # 4. Text-Ausgabe generieren
            if diff_minuten < 1:
                return "Jetzt"
            elif diff_minuten < 60:
                return f"{diff_minuten}Min."
            else:
                diff_stunden = diff_minuten // 60
                rest_minuten = diff_minuten % 60
                if diff_stunden < 24:
                    return f"{diff_stunden}Std. {rest_minuten}Min."
                else:
                    return f"{diff_stunden // 24} Tagen"
                    
        except Exception as e:
            print(f"[ago_rx Fehler]: {e}")
            return "Fehler"
    def ensure_msg_folder(self): # <--- Stelle sicher, dass der Ordner für die IARU-Meldungen existiert
        os.makedirs(self.msg_folder, exist_ok=True)
    def load_message_counter(self): # <--- Lade den Zähler für die IARU-Meldungen, basierend auf der Konfiguration und den vorhandenen Meldungsdateien
        self.ensure_msg_folder()
        counter = 1
        config_counter = self.config.get("IARU", {}).get("next_message_number")
        if isinstance(config_counter, int) and config_counter > 0:
            counter = config_counter
        for path in glob.glob(os.path.join(self.msg_folder, "*.txt")):
            m = re.search(r"MSG#?(\d+)", os.path.basename(path))
            if m:
                counter = max(counter, int(m.group(1)) + 1)
        if "IARU" not in self.config:
            self.config["IARU"] = {"next_message_number": counter}
        else:
            self.config["IARU"]["next_message_number"] = counter
        return counter
    def compose_iaru_text(self, header_lines, prio, body): # <--- Erstelle den Text für die IARU-Meldung basierend auf den Header-Informationen, der Wichtigkeit und dem Meldungstext
        text_trenner = "\n\n#NOFUSTX#Meldungstext#\n\n\n"
        return (
            text_trenner
            + "-IARU-Meldung-\n"
            + "\n".join(header_lines)
            + f"\nWICHTIGKEIT: {prio}\n\n{body}\n"
            + f"\n---Ende der Meldung---\n\n"
        )
    def sanitize_filename_part(self, part): # <--- Bereinige einen Teil des Dateinamens, um ungültige Zeichen zu entfernen (z.B. für die Priorität oder Richtung in der IARU-Meldungsdatei)
        return re.sub(r"[^A-Za-z0-9_-]", "_", str(part).strip().replace(" ", "_"))
    def get_message_filename(self, nr, prio, direction, timestamp): # <--- Erstelle den Dateinamen für eine IARU-Meldung
        prio_key = self.sanitize_filename_part(prio)
        direction_key = self.sanitize_filename_part(direction)
        filename = f"{timestamp}_MSG{nr}_prio-{prio_key}_{direction_key}.txt"
        path = os.path.join(self.msg_folder, filename)
        suffix = 1
        while os.path.exists(path):
            filename = f"{timestamp}_MSG{nr}_prio-{prio_key}_{direction_key}_{suffix}.txt"
            path = os.path.join(self.msg_folder, filename)
            suffix += 1
        return path
    def make_message_summary(self, body): # <--- Erstelle eine kurze Zusammenfassung des Meldungstextes für die Anzeige in der Historie (z.B. die ersten 120 Zeichen, bereinigt von Zeilenumbrüchen und überflüssigen Leerzeichen)
        summary = " ".join(str(body).split())
        return summary[:120]
    def add_message_history_entry(self, direction, nr, prio, summary, file_path): # <--- Füge einen Eintrag zur Historie der IARU-Meldungen hinzu, basierend auf den Informationen der Meldung und dem Dateipfad
        try:
            #time_str = datetime.datetime.utcfromtimestamp(os.path.getmtime(file_path)).strftime("%H:%M:%S")
            time_str = self.formatted_utc_timestamp(os.path.getmtime(file_path))
            #print(f"[DEBUG] {os.path.getmtime(file_path)}")
            #print(f"[DEBUG] Parsed time: {self.formatted_utc_timestamp(os.path.getmtime(file_path))}")
        except Exception:
            time_str = self.utc_time_str()
        if hasattr(self, "msg_history_tree"):
            item = self.msg_history_tree.insert(
                "",
                0,
                values=(time_str, nr, prio, direction, summary),
            )
            self.msg_history_entries[item] = file_path
    def parse_iaru_message_file(self, file_path): # <--- Lese eine IARU-Meldungsdatei ein und extrahiere die Informationen für die Anzeige und Bearbeitung (z.B. Header, Meldungstext, Richtung, Zusammenfassung)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            return None
        data = {"header": {}, "body": "", "direction": "Lokal", "summary": ""}
        lines = text.splitlines()
        in_body = False
        body_lines = []
        for line in lines:
            if line.startswith("#NOFUSTX#Meldungstext#"):
                in_body = True
                continue
            if in_body:
                body_lines.append(line)
                continue
            if line.startswith("-IARU-Meldung-"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                data["header"][key.strip()] = val.strip()
        data["body"] = "\n".join(body_lines).strip()
        data["summary"] = self.make_message_summary(data["body"])
        basename = os.path.basename(file_path).lower()
        if "recv" in basename or "empfangen" in basename:
            data["direction"] = "Empfangen"
        elif "sent" in basename or "gesendet" in basename or "log" in basename:
            data["direction"] = "Gesendet"
        else:
            data["direction"] = "Lokal"
        return data
    def load_message_history(self): # <--- Lade die Historie der IARU-Meldungen aus den gespeicherten Dateien und zeige sie in der Historie an (z.B. mit Zeit, Nummer, Wichtigkeit, Richtung und Zusammenfassung)
        if not hasattr(self, "msg_history_tree"):
            return
        self.msg_history_tree.delete(*self.msg_history_tree.get_children())
        self.msg_history_entries.clear()
        self.ensure_msg_folder()
        for file_path in sorted(glob.glob(os.path.join(self.msg_folder, "*.txt")), reverse=True):
            parsed = self.parse_iaru_message_file(file_path)
            if not parsed:
                continue
            nr = parsed["header"].get("Nummer", "")
            prio = parsed["header"].get("WICHTIGKEIT", "")
            self.add_message_history_entry(
                parsed["direction"], nr, prio, parsed["summary"], file_path
            )
    def load_iaru_message_from_file(self, file_path): # <--- Lade eine IARU-Meldung aus einer Datei und fülle die entsprechenden Felder im Formular für die Anzeige und Bearbeitung (z.B. Header-Felder, Meldungstext, Wichtigkeit)
        parsed = self.parse_iaru_message_file(file_path)
        if not parsed:
            return
        for key, value in parsed["header"].items():
            if key in self.msg_fields:
                try:
                    self.msg_fields[key].delete(0, tk.END)
                    self.msg_fields[key].insert(0, value)
                except Exception:
                    pass
        if "WICHTIGKEIT" in parsed["header"] and hasattr(self, "prio_var"):
            self.prio_var.set(parsed["header"]["WICHTIGKEIT"])
        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", parsed["body"])
        self.update_word_count()
    def on_msg_history_double_click(self, event): # <--- Event-Handler für Doppelklick auf einen Eintrag in der Historie, um die entsprechende IARU-Meldung zu laden und anzuzeigen
        selection = self.msg_history_tree.selection()
        if not selection:
            return
        file_path = self.msg_history_entries.get(selection[0])
        if file_path:
            self.load_iaru_message_from_file(file_path)
    def increment_message_counter(self): # <--- Erhöhe den Zähler für IARU-Meldungen
        self.counter_number_msg += 1
        if "IARU" not in self.config:
            self.config["IARU"] = {"next_message_number": self.counter_number_msg}
        else:
            self.config["IARU"]["next_message_number"] = self.counter_number_msg
        self.save_settings()
    def save_iaru_message_file(self, nr, prio, direction, full_text, summary): # <--- Speichere den Text einer IARU-Meldung in einer Datei, basierend auf der Nummer, Wichtigkeit, Richtung und einem Zeitstempel, und füge einen Eintrag zur Historie hinzu
        self.ensure_msg_folder()
        ts = self.get_utc_now().strftime("%Y%m%d_%H%M%S")
        file_path = self.get_message_filename(nr, prio, direction, ts)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            os.chmod(file_path, 0o644)
        except Exception:
            pass
        self.add_message_history_entry(direction, nr, prio, summary, file_path)
        return file_path
    def process_iaru_message(self, direction, header_lines, prio, body, nr=None): # <--- Verarbeite eine IARU-Meldung, indem der vollständige Text erstellt, eine Datei gespeichert und die Historie aktualisiert wird (z.B. für empfangene oder lokal geloggte Meldungen)
        full_text = self.compose_iaru_text(header_lines, prio, body)
        if nr is None:
            nr = self.msg_fields["Nummer"].get() if "Nummer" in self.msg_fields else str(self.counter_number_msg)
        summary = self.make_message_summary(body)
        file_path = self.save_iaru_message_file(nr, prio, direction, full_text, summary)
        self.increment_message_counter()
        return full_text, file_path
    def receive_iaru_msg(self, source, header_lines, prio, body, nr=None): # <--- Verarbeite eine empfangene IARU-Meldung, indem der vollständige Text erstellt, eine Datei gespeichert und die Historie aktualisiert wird, und zusätzlich einen Eintrag im Einsatz-Log erstellt wird
        full_text, file_path = self.process_iaru_message("Empfangen", header_lines, prio, body, nr=nr)
        time_str = self.utc_time_str()
        nr_display = nr if nr is not None else "?"
        if nr_display == "?" and "Nummer" in self.msg_fields:
            nr_display = self.msg_fields["Nummer"].get()
        log_line = f"{time_str} : MSG #{nr_display} empfangen von {source}."
        self.log_list.insert(0, log_line)
        self.write_session_log(f"[{self.utc_iso_timestamp()}] {log_line}")
        return full_text, file_path
    def log_iaru_msg(self): # <--- Verarbeite eine lokal geloggte IARU-Meldung, indem der vollständige Text erstellt, eine Datei gespeichert und die Historie aktualisiert wird, und zusätzlich einen Eintrag im Einsatz-Log erstellt wird
        header_keys = ["Nummer", "Quelle / Station", "Wort-Zaehler", "Herkunft", "Zeit (UTC)", "Datum"]
        header_lines = []
        for key in header_keys:
            val = self.msg_fields.get(key)
            header_lines.append(f"{key}: {val.get().strip() if val else ''}")
        prio = self.prio_var.get() if hasattr(self, "prio_var") else ""
        body = self.msg_text.get("1.0", "end").strip()
        full_text, file_path = self.process_iaru_message("Lokal", header_lines, prio, body)
        nr = self.msg_fields["Nummer"].get()
        ts = self.utc_iso_timestamp()
        log_line = f"{self.utc_time_str()} : MSG #{nr} archiviert."
        self.log_list.insert(0, log_line)
        self.write_session_log(f"[{ts}] {log_line}")
        self.clear_iaru_form()
        messagebox.showinfo("NoFuS-TX", "Meldung gespeichert.")
    # --- Meldung senden (in Terminal und/oder nur Loggen) ---
    def send_iaru_msg(self): # <--- Verarbeite eine zu sendende IARU-Meldung, indem der vollständige Text erstellt, eine Datei gespeichert und die Historie aktualisiert wird, zusätzlich ein Eintrag im Einsatz-Log erstellt wird, und optional die Meldung über einen Digimode gesendet und/oder gedruckt wird
        # IARU-Meldung als Text zusammensetzen
        header_keys = ["Nummer", "Quelle / Station", "Wort-Zaehler", "Herkunft", "Zeit (UTC)", "Datum"]
        header_lines = []
        for key in header_keys:
            val = self.msg_fields.get(key)
            header_lines.append(f"{key}: {val.get().strip() if val else ''}")
        prio = self.prio_var.get() if hasattr(self, "prio_var") else ""
        body = self.msg_text.get("1.0", "end").strip()
        # Gewählten Digimode ermitteln
        mode = self.send_mode_var.get() if hasattr(self, "send_mode_var") else "Nur Log"
        direction = mode if mode and mode != "Nur Log" else "Lokal"
        full_text, file_path = self.process_iaru_message(direction, header_lines, prio, body)
        '''MESH-TX'''
        if mode == "LORA_MESH" and self.mesh_connected:
            self.iaru_mesh_send_msg(full_text) # <--- Hier wird die Funktion aufgerufen, die die Meldung über das LoRa Mesh sendet (wenn dieser Modus gewählt ist und die Hardware verbunden ist)
        if mode and mode != "Nur Log" and mode != "LORA_MESH":
            self.transmit_digimode_text(mode, full_text) # <--- Hier wird die Funktion aufgerufen, die die Meldung über den gewählten Digimode sendet (wenn dieser Modus gewählt ist und nicht "Nur Log" oder "LORA_MESH" ist)
            term = getattr(self, "digi_terminals", {}).get(mode)
            if isinstance(term, dict):
                monitor = term.get("monitor")
                receive = term.get("receive")
                target = monitor if monitor is not None else receive
                if target is not None:
                    target.insert("end", f"\n[{self.utc_time_str()}] {self.config.get('USERCALL',{}).get('CALLSINGEN', 'N0CALL')} via {mode}\n")
                    target.insert("end", full_text + "\n")
                    target.see("end")
                else:
                    messagebox.showwarning(
                        "Digimode",
                        f"Kein Terminal für Modus '{mode}' gefunden.\nDie Meldung wird nur geloggt.",
                    )
            elif term:
                term.insert("end", "\n-IARU-Meldung-\n")
                term.insert("end", full_text + "\n")
                term.see("end")
            else:
                messagebox.showwarning(
                    "Digimode",
                    f"Kein Terminal für Modus '{mode}' gefunden.\nDie Meldung wird nur geloggt.",
                )
        # Immer ins Einsatz-Log und in die Einsatz-Session-Datei übernehmen
        nr = self.msg_fields["Nummer"].get()
        time_str = self.utc_time_str()
        ts = self.utc_iso_timestamp()
        if mode and mode != "Nur Log":
            log_text = f"{time_str} : MSG #{nr} gesendet über {mode}."
        else:
            log_text = f"{time_str} : MSG #{nr} ins Log übernommen."
        self.log_list.insert(0, log_text)
        self.write_session_log(f"[{self.utc_iso_timestamp()}] {log_text}")
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
    def setup_log_tab(self): # <--- Das Einsatzlog-Tab einrichten
        self.log_list = tk.Listbox(self.tab_log, font=("Courier", 10), bg="#FFFFFF", fg="#000000")
        self.log_list.pack(expand=1, fill="both", padx=10, pady=10)
    # ---------- UHR ----------
    def update_clock(self): # <--- Aktualisiere die Uhrzeit-Anzeige im Hauptfenster, basierend auf der aktuellen UTC-Zeit, und plane die nächste Aktualisierung in 1 Sekunde
        now_utc = self.get_utc_now()
        self.time_label.config(text=now_utc.strftime("%d.%m.%Y - %H:%M:%S UTC"))
        self.root.after(1000, self.update_clock)
    # ---------- Aktueller Map Zoom ----------
    def get_current_map_zoom(self): # <--- Holt die aktuelle Zoomstufe und zeigt den Aktuellen Tab an, damit man sofort sieht, ob die Lagekarte aktiv ist und welchen Zoom sie hat (wenn sie aktiv ist), oder welcher andere Tab aktiv ist (wenn nicht)
        current_tab_text = self.tabs.tab(self.tabs.select(), "text") # type: ignore
        if current_tab_text == "Lagekarte":
            if hasattr(self, "map_widget") and self.map_widget:
                now_zoom = int(self.map_widget.zoom)
                self.zoom_label.config(text=f"lagekarte Aktueller Map Zoom: {now_zoom}x")
            pass
        else:
            self.zoom_label.config(text=f"{current_tab_text}")
        self.cpu_usage()
        self.root.after(2000, self.get_current_map_zoom)  # Alle 2 Sekunden aktualisieren
    def cpu_usage(self): # <--- Aktualisiert die Anzeige der CPU- und RAM-Auslastung, wenn psutil verfügbar ist, und plant die nächste Aktualisierung in 2 Sekunden
        mem = psutil.virtual_memory() # type: ignore
        if psutil is not None:
            usage = psutil.cpu_percent(interval=1)
            self.lbl_cpu.config(text=f"CPU: {usage}% | RAM: {mem.percent}%")
        else:
            self.lbl_cpu.config(text="CPU: N/A")
    # --- Meshtastic integration --- #
    def init_meshtastic_hardware(self): # <--- Initialisiert das Meshtastic-Hardware-Interface mit echtem PIN-Support
        try:
            # Konfigurations-Werte laden
            mesh_conf = self.config.get("MODES", {}).get("LORA_MESH", {})
            dev = mesh_conf.get("ConnectionMode", "")
            config_pin = mesh_conf.get("ADMIN", "") # Deine "1234" aus der Config
            
            print(f"[Mesh] Gerätepfad {dev}")
            
            if meshtastic_serial_interface is None:
                raise ImportError("Meshtastic-Serial-Interface nicht verfügbar")

            # 1. Ganz normal das serielle Interface öffnen (ohne falsche Parameter!)
            self.interface = meshtastic_serial_interface.SerialInterface(devPath=dev)
            mesh_iface = cast(Any, self.interface)

            # 2. Wenn eine PIN in der Config hinterlegt ist, authentifizieren wir uns jetzt
            if config_pin:
                print(f"[Mesh] 🔐 Sende Admin-Authentifizierung aus Config...")
                try:
                    # Der direkte, sichere Weg in der Python API ohne den Umweg über die 'set_admin_pin' Methode:
                    if hasattr(mesh_iface, "localNode") and mesh_iface.localNode:
                        mesh_iface.localNode.localConfig.security.admin_pin_code = int(config_pin) # Als Zahl übergeben!
                        print(f"[Mesh] 🔐 Admin-PIN im API-Interface gesetzt.")
                    
                except Exception as pin_err:
                    print(f"[Mesh] ⚠️ Konnte Admin-PIN nicht setzen: {pin_err}")

            # 3. Jetzt holen wir die Node-Infos (das schlägt ohne PIN bei neuer Firmware fehl)
            d = mesh_iface.getMyNodeInfo()
            
            # Wenn erfolgreich: Flags setzen und Funktionen anstoßen
            self.mesh_connected = True
            print(f"[Mesh] ✅ Gerät erfolgreich initialisiert.")
            
            # Deine Start-Kette für den Mesh-Betrieb
            if pub is not None:
                pub.subscribe(self.on_mesh_receive, "meshtastic.receive")
            # Hier Holen wir die Bestehenden Kanäle im Node
            try:
                self.mesh_kanal_name = self.interface.localNode.channels
                print(f"[Mesh] Kanäle erfolgreich gelesen.")
                
                # --- NEU: Wir bauen ein lesbares Wörterbuch für die App ---
                self.mesh_channels_dict = {}
                
                for ch in self.mesh_kanal_name:
                    # Prüfen, ob der Kanal überhaupt konfiguriert ist (Rolle ist nicht DISABLED)
                    if ch.role != 0:  # 0 steht in Protobuf oft für DISABLED / UNSET
                        ch_index = ch.index
                        
                        # Den Namen herausholen. Wenn es der PRIMARY ist und kein Name 
                        # gesetzt wurde, heißt er standardmäßig "PRIMARY"
                        ch_name = ch.settings.name
                        if not ch_name:
                            ch_name = "PRIMARY" if ch.role == 1 else f"Ch {ch_index}"
                        
                        # In unserem Wörterbuch speichern (z.B. {1: "NoFuS"})
                        self.mesh_channels_dict[ch_index] = ch_name
                        self.rx_mesh_ch_tab = self.rx_mesh_ch_tab +1

                
                print(f"[Mesh] 🗺️ Erkannte Kanal-Zuweisung: {self.mesh_channels_dict}")
                
                
            except Exception as f:
                print(f"[Mesh] Fehler beim Kanal Holen\n {f} \n")
                self.mesh_channels_dict = {0: "PRIMARY"} # Fallback, damit es nicht kracht
            
            self.setup_digimode_terminals()
            self.meshtastic_test()
            self.start_mesh_monitor_thread()            
            
        except Exception as e:
            self.mesh_connected = False
            self.interface = None
            print(f"[Mesh] ❌ Hardware nicht gefunden, blockiert oder Authentifizierung fehlgeschlagen!")
            
            # Direktes Feedback in deinen Monitor
            if "LORA_MESH" in self.digi_terminals:
                self.digi_terminals["LORA_MESH"]["monitor"].insert(
                    "end", 
                    f"[{self.utc_time_str()}] ⚠️ SYSTEM-WARNUNG:\n"
                    f"Hardware konnte nicht initialisiert werden!\n"
                    f"Mesh-Modus läuft im OFFLINE-Modus.\n"
                    f"Fehler: {e}\n\n"
                )
                self.digi_terminals["LORA_MESH"]["monitor"].see("end")
    def _start_fldigi_client(self): # <--- Interne Funktion, um den FLDIGI/pyfldigi-Client zu starten, falls die Bibliothek verfügbar ist, und eine Referenz darauf zurückzugeben, oder None, wenn es nicht funktioniert
        """Initialisiert FLDIGI/pyfldigi bei Bedarf und liefert einen Client zurück."""
        if pyfldigi is None:
            return None
        try:
            if self.fldigi_client is None:
                if self.fldigi_app is None:
                    try:
                        self.fldigi_app = pyfldigi.ApplicationMonitor()
                        self.fldigi_app.start()
                    except Exception:
                        self.fldigi_app = None
                self.fldigi_client = pyfldigi.Client()
            return self.fldigi_client
        except Exception as exc:
            print(f"[FLDIGI] Initialisierung fehlgeschlagen: {exc}")
            return None
    def transmit_digimode_text(self, mode, text): # <--- Sendet den gegebenen Text über FLDIGI, wenn der Modus aktiviert ist und die FLDIGI-Integration funktioniert, und gibt True zurück, wenn es gesendet wurde, oder False, wenn es nicht gesendet werden konnte (z.B. weil der Modus nicht aktiviert ist oder FLDIGI nicht verfügbar ist)
        """Sendet IARU-Text über FLDIGI, sofern im Modus aktiviert."""
        if not text:
            return False
        mode = (mode or "").strip().upper()
        params = self.config.get("MODES", {}).get(mode, {})
        if not params.get("use_fldigi", True):
            return False
        client = self._start_fldigi_client()
        if client is None:
            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] {mode}: FLDIGI nicht verfügbar, TX nur protokolliert.")
            return False
        try:
            modem_name = params.get("fldigi_modem") or {
                "RTTY": "RTTY",
                "MT63": "MT63-1KS",
                "FAX": "WEFAX576",
                "SSTV": "SSB",
                "JS8CALL": "BPSK31",
                "VARA": "SSB",
                "WINLINK": "PSK500",
            }.get(mode, mode)
            if hasattr(client, "modem") and hasattr(client.modem, "name"):
                try:
                    client.modem.name = modem_name
                except Exception:
                    pass
            if hasattr(client, "main") and hasattr(client.main, "send"):
                client.main.send(text, block=False)
                self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] {mode}: TX an FLDIGI gesendet.")
                return True
        except Exception as exc:
            print(f"[DIGI] {mode} TX fehlgeschlagen: {exc}")
        return False
    def insert_with_limit(self, widget, text_to_insert, max_lines=100): # <--- Limitiert die Anzahl der Zeilen in einem Text-Widget, indem neue Zeilen unten eingefügt und alte Zeilen oben gelöscht werden, wenn das Limit überschritten wird
        """Fügt Text ein und wirft oben Zeilen raus, wenn es zu voll wird."""
        # 1. Text ganz normal unten rein und scrollen
        widget.insert("end", text_to_insert)
        widget.see("end")
        # 2. Aktuelle Zeilenanzahl ermitteln
        total_lines = int(widget.index('end-1c').split('.')[0])
        # 3. Wenn das Limit gesprengt wird, oben abschneiden
        if total_lines > max_lines:
            lines_to_delete = total_lines - max_lines
            widget.delete("1.0", f"{lines_to_delete + 1}.0")
    def meshtastic_test(self): # <--- Testet Mesh und holt wenn vorhanden Informationen aus dem und über das device
        try:
            mesh_iface = cast(Any, self.interface)
            data = mesh_iface.getMyNodeInfo()
            # Daten sicher extrahieren
            # .get() verhindert Abstürze, falls ein Feld (wie position) fehlt
            user_info = data.get('user', {})
            long_name = user_info.get('longName', 'Unbekannt')
            hw_model = user_info.get('hwModel', 'T-Beam?')
            pos = data.get('position', {})
            # Umrechnung der Meshtastic-Koordinaten in normales Format
            lat = pos.get('latitude')
            lon = pos.get('longitude')
            high = pos.get('altitude')
            # print(f"lat: {lat}")
            self.log_list.insert(0, f"[{self.utc_time_str()}]---Meshtastic--- Gerät gefunden")
            self.write_session_log(f"[{self.utc_time_str()}] ---Meshtastic--- Gerät gefunden\nMesh Node: {long_name} | Hardware: {hw_model}")
            self.log_list.insert(0, f"{self.utc_time_str()} : Mesh {long_name} | Hardware: {hw_model}")
            self.digi_terminals["LORA_MESH"]["monitor"].insert("end", f"Mesh Node: {long_name} | Hardware: {hw_model}\n")
            if lat and lon:
                # Meshtastic nutzt 10^7 Format (7 Nachkommastellen)
                self.log_list.insert(0, f"[{self.utc_time_str()}] Position: LAT {lat}, LON {lon}, Höhe: {high}m")
            else:
                self.log_list.insert(0, f"[{self.utc_time_str()}] Position: Keine GPS-Daten verfügbar.")
            self.mesh_my_heard()
            return data
        except Exception as e:
            print(f"Fehler bei Hardware Zugriff: {e}")
            return None
        
    def show_node_tooltip(self, event): # <--- Zeigt ein schwebendes Info-Fenster (Tooltip) über dem aktuellen Listbox-Eintrag
        # 1. Welches Element ist unter der Maus?
        listbox = event.widget
        index = listbox.nearest(event.y)
        
        # Den Header (Zeile 0) überspringen wir
        if index == 0:
            self.hide_node_tooltip(None)
            return
            
        try:
            # Den Text des Eintrags holen, um den LongName zu extrahieren
            entry_text = listbox.get(index)
            # Da wir mit festen Breiten formatieren ({long_name:<20}), splitte am Trenner
            long_name = entry_text.split("|")[0].strip()
            
            # 2. Die passenden Daten aus der Mesh-Datenbank fischen
            mesh_iface = cast(Any, self.interface)
            nodes = getattr(mesh_iface, "nodes", None) or {}
            
            node_details = "Keine weiteren Infos"
            for n_id, n_data in nodes.items():
                user = n_data.get('user', {})
                
                if user.get('longName') == long_name:
                    # --- HIER KORRIGIERT: Aus n_data holen, nicht aus user! ---
                    last_heard_raw = n_data.get('lastHeard')
                    
                    if last_heard_raw:
                        last_heard = self.formatted_utc_timestamp(timestamp=last_heard_raw)
                    else:
                        last_heard = "Nie"
                        
                    lname = user.get('longName')
                    sname = user.get('shortName')
                    hex_id = user.get('id', 'Unbekannt')
                    mac_addr = user.get('macaddr', 'Unbekannt')
                    snr = n_data.get('snr', 'N/A')
                    
                    # Hier deine super ausgerichtete Monospace-Anzeige:
                    node_details = f"LongName: {lname}\nKurzName: {sname}\nLast-RX:  {last_heard}\nID      : {hex_id}\nMAC     : {mac_addr}\nSNR     : {snr} dB"
                    break
            
            # 3. Altes Fenster zerstören, falls vorhanden
            if hasattr(self, 'mesh_tooltip_win') and self.mesh_tooltip_win:
                self.mesh_tooltip_win.destroy()
                
            # 4. Neues schwebendes Fenster (Toplevel) erstellen
            self.mesh_tooltip_win = tk.Toplevel(self.root)
            self.mesh_tooltip_win.wm_overrideredirect(True) # Rahmen und Schließen-Button ausblenden
            
            # Position direkt neben dem Mauszeiger berechnen
            x = event.x_root + 15
            y = event.y_root + 10
            self.mesh_tooltip_win.wm_geometry(f"+{x}+{y}")
            
            # Der Inhalt des Info-Fensters
            lbl = tk.Label(
                self.mesh_tooltip_win, 
                text=node_details, 
                justify="left", 
                background="#ffffcc", # Schönes, klassisches Notizgelb
                foreground="#000000",
                relief="solid", 
                borderwidth=1, 
                font=("Courier", 12, "normal")
            )
            lbl.pack()
            
        except Exception as e:
            print(f"[Tooltip-Fehler]: {e}")

    def hide_node_tooltip(self, event): # <--- Schließt das schwebende Info-Fenster, wenn die Maus das Widget verlässt
        if hasattr(self, 'mesh_tooltip_win') and self.mesh_tooltip_win:
            self.mesh_tooltip_win.destroy()
            self.mesh_tooltip_win = None

    def mesh_my_heard(self): # <--- Holt die Liste der zuletzt gehörten Mesh-Teilnehmer (Schlanke Version für Tooltip-Nutzung)
        try:
            mesh_iface = cast(Any, self.interface)
            nodes = getattr(mesh_iface, "nodes", None) or {}
            
            self.digi_terminals["LORA_MESH"]["node_list"].delete(0, "end")
            
            # Hier werfen wir das SNR aus dem Header, weil die Liste jetzt schmal ist!
            self.digi_terminals["LORA_MESH"]["node_list"].insert("end", f"Name                 | Letztes RX")
            
            if nodes:
                for node_id, node_data in nodes.items():
                    user = node_data.get('user', {})
                    long_name = user.get('longName', 'Unbekannt')
                    hex_id = user.get('id', 'Unbekannt')
                    
                    last_heard_raw = node_data.get('lastHeard')
                    
                    if last_heard_raw:
                        last_heard = self.formatted_utc_timestamp(timestamp=last_heard_raw)
                        ago = self.ago_rx(last_heard_raw)
                    else:
                        last_heard = "Nie"
                        ago = self.ago_rx(last_heard_raw)
                        
                    snr = node_data.get('snr', 'N/A')
                    
                    # Das Session-Log im Hintergrund behält natürlich alle Infos!
                    self.log_list.insert(0, f"{self.utc_time_str()} : Mesh {long_name} (ID: {hex_id}), Last Heard: {last_heard}")
                    
                    # --- HIER DIE SCHLANKE ANZEIGE ---
                    # Nur noch Name und Zeitstempel in der Listbox anzeigen
                    self.digi_terminals["LORA_MESH"]["node_list"].insert("end", f"{long_name:<20} | {ago} | ID: {hex_id}")
                    #print(f"[Mesh-MyHeard] Gelesen um {self.utc_time_str()}")
                    
            self.root.after(180000, self.mesh_my_heard) # Alle 3 Minuten aktualisieren
        except Exception as e:
            print(f"Fehler bei mesh_my_heard: {e}")

    def on_mheard_double_click(self, event): # <--- Wird aufgerufen bei Doppelklick auf einen Eintrag in der Node-Liste
        try:
            widget = event.widget
            selection = widget.curselection() # Holt den Index der ausgewählten Zeile (z.B. 0, 1, 2...)
            
            if not selection:
                return
                
            index = selection[0]
            selected_text = widget.get(index) # Holt den echten Text aus der Zeile
            
            print(f"[Node-Klick] Doppelklick auf Eintrag: '{selected_text}'")
            
            # --- ID AUS DEM TEXT EXTRAHIEREN ---
            # Je nachdem, wie du die Zeilen in die Liste schreibst, müssen wir die ID isolieren.
            # Fall 1: Wenn du nur die rohe ID oder das Rufzeichen reinschreibst, das direkt in der Node-DB existiert:
            node_id = selected_text.strip()
            
            # Fall 2 (Sicherheitsnetz): Falls in der Liste "Name (ID: 12345)" steht, 
            # filtern wir die Zahl heraus. Wenn deine Liste nur aus IDs/Namen besteht, kannst du das anpassen:
            if "ID:" in selected_text:
                # Schneidet alles zwischen "ID: " und ")" aus
                node_id = selected_text.split("ID:")[-1].replace(")", "").strip()

            # Jetzt rufen wir deine universelle DM-Fenster-Funktion auf!
            # packet bleibt None, weil wir ja aktiv den Chat öffnen wollen!
            self.rx_mesh_direct(packet=None, direct_node_id=node_id)
            
        except Exception as e:
            print(f"[Node-Klick] Fehler beim Verarbeiten des Doppelklicks: {e}")

    def on_mesh_receive(self, packet, interface): # <--- MESH Wird aufgerufen, wenn ein neues Paket im Mesh ankommt, und verarbeitet es je nach Inhalt (Textnachricht, Position, Telemetrie), zeigt es im Monitor an, übersetzt die Sender-ID in einen Namen, wenn möglich, und aktualisiert die APRS-Position, wenn es eine Positionsmeldung ist
        sender_id = packet.get('fromId')
        user_info = {}
        # --- SENDER-ID IN NAME ÜBERSETZEN ---
        sender_name = "Unbekannt"
        # Wir schauen in der Node-DB nach, ob wir diese ID kennen
        mesh_iface = cast(Any, self.interface)
        nodes = getattr(mesh_iface, "nodes", None) or {}
        if nodes and sender_id in nodes:
            node_info = nodes[sender_id]
            user_info = node_info.get('user', {})
            # Versuche den LongName zu bekommen, sonst ShortName, sonst bleibt es die ID
            sender_name = user_info.get('longName', user_info.get('shortName', sender_id))
        else:
            # Falls der Node brandneu ist und noch nicht in der Liste war
            sender_name = f"ID: {sender_id}"
            
        decoded = packet.get('decoded', {})
        portnum = decoded.get('portnum') # Was für eine Art von Daten?
        my_node_id = self.interface.getMyNodeInfo().get("num") if self.interface else None
        to_id = packet.get('toId', "Unknown")
        self.digi_terminals["LORA_MESH"]["monitor"].insert("end", f"Empfangenes Paket: {packet}\n")
        self.digi_terminals["LORA_MESH"]["monitor"].see("end")
        #self.write_session_log(f"[{self.utc_iso_timestamp()}] Empfangenes Paket: {packet}")
        self.insert_with_limit(self.digi_terminals["LORA_MESH"]["monitor"], packet, max_lines=150)
        
        if portnum == "TEXT_MESSAGE_APP":
            # --- DEBUG PRINTS FÜR DICH IM TERMINAL ---
            print(f"[Mesh-Weiche] Meine Node-ID (Typ: {type(my_node_id)}): {my_node_id}")
            print(f"[Mesh-Weiche] Empfänger toId (Typ: {type(to_id)}): {to_id}")
            print(f"[Mesh-Weiche] Paket-Empfänger 'to' (Typ: {type(packet.get('to'))}): {packet.get('to')}")

            # Wir wandeln alles in Strings um, um "int vs string" Fehler komplett zu eliminieren!
            my_id_str = str(my_node_id) if my_node_id is not None else ""
            to_id_str = str(to_id)
            packet_to_str = str(packet.get('to', ''))

            # --- DIE ROBUSTE DM-PRÜFUNG ---
            # Eine DM liegt vor, wenn die Empfänger-ID mit unserer ID übereinstimmt 
            # UND es kein Broadcast (4294967295) ist!
            is_broadcast = (to_id_str == "4294967295" or to_id_str.upper() == "0XFFFFFFFF")
            
            if not is_broadcast and (to_id_str == my_id_str or packet_to_str == my_id_str):
                print("[Mesh-Weiche] 🎯 TREFFER: Das ist eine Direktnachricht! Rufe rx_mesh_direct auf.")
                self.rx_mesh_direct(packet)
            else:
                print(f"[Mesh-Weiche] 📡 Kanal-Nachricht. Geht an Kanal-Index: {packet.get('channel', 0)}")
                # 1. Die Kanalnummer direkt aus dem empfangenen Paket holen
                kanal_nummer = packet.get("channel", 0)
                kanal_name = self.mesh_channels_dict.get(kanal_nummer, f"Kanal {kanal_nummer}")
                
                msg = decoded.get('text')
                
                # 2. Das RICHTIGE Text-Widget für diesen spezifischen Kanal ermitteln
                if "receive_channels" in self.digi_terminals["LORA_MESH"]:
                    target_recv = self.digi_terminals["LORA_MESH"]["receive_channels"].get(kanal_nummer)
                else:
                    target_recv = self.digi_terminals["LORA_MESH"].get("receive")
                    
                if not target_recv:
                    target_recv = self.digi_terminals["LORA_MESH"].get("receive")
                    
                # 3. Den Text in den Kanal-Tab einfügen
                if target_recv:
                    target_recv.insert(
                        "end", 
                        f"[{self.utc_time_str()}] {sender_name}:\n{msg}\n"
                    )
                    target_recv.see("end")
                
        # Wenn es eine Position ist:
        elif portnum == "POSITION_APP":
            pos = decoded.get('position', {})
            lat = pos.get('latitude')
            lon = pos.get('longitude')
            if lat is not None and lon is not None:
                short_name = user_info.get('shortName')
                display_src = short_name or sender_name
                self.digi_terminals["LORA_MESH"]["monitor"].insert(
                    "end",
                    f"[{self.utc_time_str()}] POSITION von {display_src}: {lat:.7f}, {lon:.7f}\n"
                )
                self.digi_terminals["LORA_MESH"]["monitor"].see("end")
                self.aprs_update_queue.put({
                    "type": "position",
                    "lat": lat,
                    "lon": lon,
                    "src": display_src,
                    #"id": sender_id,
                    "symbol_table": "/",
                    "symbol_code": "{",
                    "source_type": "Mesh POSITION_APP",
                })
            else:
                print(f"POSITION_APP ohne Koordinaten: {pos}")
                
        # Wenn es Telemetrie ist (Batterie etc.):
        elif portnum == "TELEMETRY_APP":
            tele = decoded.get('telemetry', {})
    def rx_mesh_direct(self, packet=None, direct_node_id=None): # <--- Öffnet oder aktualisiert das DM-Fenster für eingehende DMs ODER Doppelklick
        # Thread-Sicherheit für Tkinter garantieren (Wechsel in den Haupt-Thread)
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, lambda: self.rx_mesh_direct(packet, direct_node_id))
            return

        try:
            # --- 1. ABSENDER & TEXT ERMITTELN ---
            if packet is not None:
                sender_id = str(packet.get('fromId'))
                decoded = packet.get('decoded', {})
                msg = decoded.get('text', '[Kein Text]')
            elif direct_node_id is not None:
                sender_id = str(direct_node_id)
                msg = None # Nur Tab öffnen, kein neuer Text
            else:
                return

            # Namen aus deiner Node-DB holen
            sender_name = "Unbekannt"
            mesh_iface = cast(Any, self.interface)
            nodes = getattr(mesh_iface, "nodes", None) or {}
            if nodes and sender_id in nodes:
                user_info = nodes[sender_id].get('user', {})
                sender_name = user_info.get('longName', user_info.get('shortName', sender_id))
            else:
                sender_name = f"ID: {sender_id}"

            # --- 2. PRÜFEN OB FENSTER EXISTIERT (WASSERDICHT) ---
            window_needs_init = False
            if self.dm_window is None:
                window_needs_init = True
            else:
                try:
                    if not self.dm_window.winfo_exists():
                        window_needs_init = True
                except Exception:
                    window_needs_init = True

            # Wenn das Fenster nicht existiert oder geschlossen war, komplett neu aufbauen
            if window_needs_init:
                self.dm_window = tk.Toplevel(self.root)
                self.dm_window.title("🔐 NoFuSTX — Direktnachrichten (Privat)")
                self.dm_window.configure(bg="#001100")
                self.dm_window.geometry("500x400") # Platz für Eingabefelder
                
                try:
                    dm_icon = tk.PhotoImage(file="icons/settings.png") 
                    self.dm_window.iconphoto(False, dm_icon)
                    self.dm_window._icon_ref = dm_icon # type: ignore
                except Exception:
                    pass

                # Beim Schließen alles sauber zurücksetzen
                def on_close_dm():
                    self.dm_tabs.clear()
                    self.dm_notebook = None
                    if self.dm_window:
                        self.dm_window.destroy()
                    self.dm_window = None
                
                self.dm_window.protocol("WM_DELETE_WINDOW", on_close_dm)

                # Notebook ERST HIER erstellen, wenn das Fenster frisch gebaut wird!
                self.dm_notebook = ttk.Notebook(self.dm_window)
                self.dm_notebook.pack(fill="both", expand=True, padx=5, pady=5)

            # Bring das Fenster nach vorne
            if self.dm_window:
                self.dm_window.attributes("-topmost", True)
                self.dm_window.attributes("-topmost", False)

            # --- 3. NEUEN TAB ERSTELLEN, FALLS NOCH NICHT VORHANDEN ---
            if sender_id not in self.dm_tabs and self.dm_notebook is not None:
                tab_frame = tk.Frame(self.dm_notebook, bg="#001100")
                
                # Das große Textfeld für den Verlauf
                txt_area = tk.Text(
                    tab_frame, bg="#001a00", fg="#00FF00", height=12,
                    insertbackground="#00FF00", font=("Courier", 10), bd=2, relief="sunken", wrap="word"
                )
                txt_area.pack(fill="both", expand=True, padx=5, pady=5)
                
                # === NEU: ALTEN VERLAUF AUS DEM SPEICHER LADEN ===
                if sender_id in self.mesh_dm_history:
                    txt_area.insert("1.0", self.mesh_dm_history[sender_id])
                
                txt_area.config(state="disabled") # Erst nach dem Laden sperren!
                
                # =============================================================
                # VORBEREITUNG ZUM ANTWORTEN
                # =============================================================
                reply_frame = tk.Frame(tab_frame, bg="#001100")
                reply_frame.pack(fill="x", padx=5, pady=5)
                
                entry_reply = ttk.Entry(reply_frame)
                entry_reply.pack(side="left", fill="x", expand=True, padx=(0, 5))
                
                btn_send = ttk.Button(
                    reply_frame, 
                    text="Senden", 
                    command=lambda s_id=sender_id, ent=entry_reply: self.send_mesh_direct(s_id, ent)
                )
                btn_send.pack(side="right")
                
                # Enter-Taste bind
                entry_reply.bind("<Return>", lambda event, s_id=sender_id, ent=entry_reply: self.send_mesh_direct(s_id, ent))
                # =============================================================

                self.dm_tabs[sender_id] = txt_area
                self.dm_notebook.add(tab_frame, text=f" {sender_name} ")

            # --- 4. TEXT NUR EINFÜGEN, WENN EINE NACHRICHT MITKAM ---
            if msg is not None:
                formatted_msg = f"[{self.utc_time_str()}] 📥 {sender_name}:\n{msg}\n\n"
                
                # 1. In der globalen History speichern (fürs nächste Mal)
                if sender_id not in self.mesh_dm_history:
                    self.mesh_dm_history[sender_id] = ""
                self.mesh_dm_history[sender_id] += formatted_msg
                
                # 2. Im aktuell offenen Widget anzeigen (falls das Fenster offen ist)
                if sender_id in self.dm_tabs:
                    target_text_widget = self.dm_tabs[sender_id]
                    target_text_widget.config(state="normal")
                    target_text_widget.insert("end", formatted_msg)
                    target_text_widget.config(state="disabled")
                    target_text_widget.see("end")

            # --- 5. FOKUS AUF DEN GEWÄHLTEN TAB LENKEN ---
            if self.dm_notebook and sender_id in self.dm_tabs:
                tab_frame_to_select = self.dm_tabs[sender_id].master
                self.dm_notebook.select(tab_frame_to_select)

        except Exception as e:
            print(f"[Mesh-DM] Fehler im DM-Tab-Manager: {e}")

    def mesh_receive_loop(self): # <--- Mesch empfangs schleife die in einem eigenen Thread läuft, um kontinuierlich Pakete zu empfangen und die on_mesh_receive-Funktion aufzurufen, ohne die GUI zu blockieren, und Fehler im Empfangsprozess abzufangen und im Monitor anzuzeigen
        mesh_iface = cast(Any, self.interface)
        if not mesh_iface or not hasattr(mesh_iface, "stream_packets"):
            return
        try:
            for packet in mesh_iface.stream_packets():
                self.on_mesh_receive(packet, self.interface)
        except Exception as e:
            print(f"[Mesh] Fehler im Empfangs-Loop: {e}")
    def start_mesh_monitor_thread(self): # <--- Startet den Monitorthread für Mesh
        if not self.mesh_connected or not self.interface:
            return
        if not hasattr(self.interface, "stream_packets"):
            # Einige meshtastic-Versionen liefern empfangene Pakete über pubsub statt über stream_packets
            return
        t = threading.Thread(target=self.mesh_receive_loop, daemon=True)
        t.start()
    def on_digimode_send_enter(self, event): # <--- Wenn Enter gedrückt wird in einem Digimode Sende den Text
        """Sendet Text direkt aus einem Digimode-Entry-Feld."""
        widget = event.widget
        mode = getattr(widget, "_digimode_mode", None) or ""
        msg_text = widget.get().strip()
        if not mode or not msg_text:
            return
        if not self.transmit_digimode_text(mode, msg_text):
            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] {mode}: TX nicht gesendet (kein FLDIGI/Client verfügbar).")
        term = self.digi_terminals.get(mode)
        if isinstance(term, dict):
            receive = term.get("receive")
            if receive is not None:
                receive.insert("end", f"[{self.utc_time_str()}] {self.config.get('USERCALL',{}).get('CALLSINGEN', 'N0CALL')} via {mode}:\n{msg_text}\n")
                receive.see("end")
        widget.delete(0, "end")
    def send_mesh_direct(self, s_id, ent): # <--- Sendet die getippte DM ins Mesh raus
        # 1. Den geschriebenen Text aus dem Eingabefeld (ent) holen und Leerzeichen abschneiden
        text_to_send = ent.get().strip()
        if not text_to_send:
            return # Leere Nachrichten senden wir erst gar nicht
            
        try:
            print(f"[Mesh-TX] Sende Privatnachricht an {s_id}: {text_to_send}")
            
            if self.interface:
                self.interface.sendText(text_to_send, destinationId=s_id)
            else:
                raise Exception("Meshtastic-Interface ist nicht initialisiert!")
            
            # Text für die History formatieren
            formatted_tx = f"[{self.utc_time_str()}] 📤 Du:\n{text_to_send}\n\n"
            
            # 1. In der globalen History speichern
            if s_id not in self.mesh_dm_history:
                self.mesh_dm_history[s_id] = ""
            self.mesh_dm_history[s_id] += formatted_tx
            
            # 2. Im offenen Chatfenster anzeigen
            if s_id in self.dm_tabs:
                target_text_widget = self.dm_tabs[s_id]
                target_text_widget.config(state="normal")
                target_text_widget.insert("end", formatted_tx)
                target_text_widget.config(state="disabled")
                target_text_widget.see("end")
            
            ent.delete(0, "end")
            
        except Exception as e:
            print(f"[Mesh-TX] ❌ Fehler beim Senden der DM: {e}")
            # Kleines visuelles Feedback im Chatfenster bei Fehlern (z.B. Node außer Reichweite/Interface weg)
            if s_id in self.dm_tabs:
                target_text_widget = self.dm_tabs[s_id]
                target_text_widget.config(state="normal")
                target_text_widget.insert("end", f"[SYSTEM] ⚠️ Senden fehlgeschlagen!\nFehler: {e}\n\n")
                target_text_widget.config(state="disabled")
    def on_mesh_send_enter(self, event): # <--- Wird aufgerufen, wenn im Entry-Feld ENTER gedrückt wird
        """Wird aufgerufen, wenn im Entry-Feld ENTER gedrückt wird."""
        if not self.mesh_connected or not self.interface:
            print("[Mesh] Senden nicht möglich: Keine Hardware verbunden.")
            return
            
        widget = event.widget
        # Bei tk.Entry holt ein einfaches .get() den kompletten Text!
        msg_text = widget.get().strip()
        ch_id = 0
        if msg_text:
            try:
                # 1. Die Kanal-ID aus dem Widget auslesen, in dem ENTER gedrückt wurde (Fallback 0)
                ch_id = getattr(widget, "_mesh_channel_id", 0)
                
                # Text per Meshtastic senden – JETZT MIT DEM RICHTIGEN KANAL!
                mesh_iface = cast(Any, self.interface)
                mesh_iface.sendText(msg_text, channelIndex=ch_id) # <--- WICHTIG für Kanaltrennung auf HF!
                
                # 2. Das RICHTIGE Text-Widget für diesen spezifischen Kanal aus dem Dictionary holen
                # Falls wir im Monomodus sind (rx_mesh_ch_tab == 0), fallen wir auf "receive" zurück
                if "receive_channels" in self.digi_terminals["LORA_MESH"]:
                    target_recv = self.digi_terminals["LORA_MESH"]["receive_channels"].get(ch_id)
                else:
                    target_recv = self.digi_terminals["LORA_MESH"].get("receive")
                
                # Falls das Widget existiert, genau DORT hineinschreiben
                if target_recv:
                    target_recv.insert(
                        "end", 
                        f"[{self.utc_time_str()}] - {self.config.get('USERCALL',{}).get('CALLSINGEN', 'N0CALL')}\n{msg_text}\n"
                    )
                    target_recv.see("end")
                    
                # Im globalen Monitor wird natürlich trotzdem alles zentral mitgeloggt
                self.digi_terminals["LORA_MESH"]["monitor"].insert(
                    "end", 
                    f"[{self.utc_time_str()}] TX (CH {ch_id}): {msg_text}\n"
                )
                self.digi_terminals["LORA_MESH"]["monitor"].see("end")
                
                # Bei tk.Entry löscht man von Index 0 bis zum bitteren Ende ("end")
                widget.delete(0, "end")
                
            except Exception as e:
                print(f"[Mesh] Fehler beim Senden auf Kanal {ch_id}: {e}")
                self.digi_terminals["LORA_MESH"]["monitor"].insert(
                    "end", 
                    f"[{self.utc_time_str()}] ❌ Sende-Fehler (CH {ch_id}): {e}\n"
                )
                self.digi_terminals["LORA_MESH"]["monitor"].see("end")
    def iaru_mesh_send_msg(self, msg): # <--- wird aufgerufen wenn via Mesh eine IARU mitteilung gesendet werden soll
        if not self.mesh_connected or not self.interface:
            print("[Mesh] Senden nicht möglich: Keine Hardware verbunden.")
            return
            
        # --- SCHLANKE KANALAUSWAHL DIREKT AM ANFANG ---
        channel_id = 0 # Standard-Kanal (PRIMARY)
        channels = getattr(self, "mesh_channels_dict", {})
        
        # Nur wenn wir wirklich MEHR als einen Kanal haben, fragen wir nach
        if len(channels) > 1:
            # Eine kleine Variable, die wir im Fenster verändern können
            choice_var = tk.IntVar(value=0)
            
            # Mini-Fenster aufbauen
            dialog = tk.Toplevel(self.root)
            dialog.title("Kanal?")
            dialog.configure(bg="#001100")
            dialog.geometry("250x180")
            dialog.transient(self.root)
            dialog.grab_set()
            
            tk.Label(dialog, text="Kanal auswählen:", fg="#00FF00", bg="#001100", font=("Arial", 11, "bold")).pack(pady=10)
            
            # Radiobuttons für jeden Kanal zeichnen
            for ch_index, ch_name in channels.items():
                tk.Radiobutton(
                    dialog, text=f"CH {ch_index}: {ch_name}", variable=choice_var, value=ch_index,
                    bg="#001100", fg="#00FF00", selectcolor="#002200", activebackground="#001100", activeforeground="#00FF00"
                ).pack(anchor="w", padx=30, pady=2)
                
            # OK-Button schließt nur das Fenster, die Variable bleibt im Speicher!
            tk.Button(
                dialog, text=" OK ", bg="#003300", fg="#00FF00", font=("Arial", 10, "bold"),
                command=dialog.destroy
            ).pack(pady=15)
            
            # WICHTIG: Hier warten wir, bis das Fenster geschlossen wurde, bevor der Code weitergeht!
            self.root.wait_window(dialog)
            channel_id = choice_var.get() # Die getroffene Auswahl übernehmen
        # ----------------------------------------------

        try:
            # 1. Text bereinigen (Damit Zeilenumbrüche die Chunks nicht verfälschen)
            clean_msg = msg.replace("\n", " ").replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
            clean_msg = clean_msg.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
            clean_msg = " ".join(clean_msg.split())
            # 2. Chunks schneiden (140 Zeichen)
            max_chunk_size = 140
            chunks = [clean_msg[i:i+max_chunk_size] for i in range(0, len(clean_msg), max_chunk_size)]
            total_chunks = len(chunks)
            # Ein einfaches Flag, das signalisiert, ob das Board bereit für das nächste Paket ist
            self.mesh_ready_for_next = False
            # Lokale Hilfsfunktion für das ACK-Event 
            def on_ack_received(packet, interface): # <--- prüfe ob das erste Paket gesendet ist
                routing = packet.get("decoded", {}).get("routing", {})
                error_reason = routing.get("errorReason", "NONE")
                if error_reason == "NONE":
                    print("[Mesh] 👍 Mesh hat ein Paket erfolgreich auf die Antenne gelegt.")
                    self.mesh_ready_for_next = True
            # Temporär auf das Routing-Signal von Meshtastic lauschen
            if pub is not None:
                pub.subscribe(on_ack_received, "meshtastic.receive.routing")
                
            # --- HIER DEN INSERTS-PFAD ANPASSEN ---
            # Wir holen das passende Textfeld aus deinen neuen Kanaltabs.
            # Falls es das Dictionary nicht gibt, fallen wir sauber auf das alte "receive" zurück.
            if "receive_channels" in self.digi_terminals["LORA_MESH"]:
                target_recv = self.digi_terminals["LORA_MESH"]["receive_channels"].get(channel_id)
            else:
                target_recv = self.digi_terminals["LORA_MESH"].get("receive")
                
            if not target_recv:
                target_recv = self.digi_terminals["LORA_MESH"].get("receive")
            # --------------------------------------

            for index, chunk in enumerate(chunks):
                formatted_chunk = chunk
                if total_chunks > 1:
                    formatted_chunk = f"({index+1}/{total_chunks}) {chunk}"
                # Sende-Flag für diesen Durchlauf zurücksetzen
                self.mesh_ready_for_next = False
                print(f"[Mesh] Übergebe Teil {index+1}/{total_chunks} an Mesh...")
                
                # Nachricht absenden – JETZT MIT DEM DYNAMISCH GEWÄHLTEN KANAL!
                mesh_iface = cast(Any, self.interface)
                mesh_iface.sendText(formatted_chunk, channelIndex=channel_id) # <--- Kanal-Index übergeben
                
                # Lokale GUI-Einträge befüllen
                self.digi_terminals["LORA_MESH"]["monitor"].insert(
                    "end", f"[{self.utc_time_str()}] TX ({index+1}/{total_chunks}) [CH {channel_id}]: {chunk}\n"
                )
                
                # Schreibt es exakt in den richtigen Tab!
                if target_recv:
                    target_recv.insert(
                        "end", f"[{self.utc_time_str()}] - {self.config.get('USERCALL',{}).get('CALLSINGEN', 'N0CALL')}\n{formatted_chunk}\n"
                    )
                self.digi_terminals["LORA_MESH"]["monitor"].see("end")
                if target_recv:
                    target_recv.see("end")
                    
                # --- WARTEN AUF HARDWARE-BEREITSCHAFT ---
                if total_chunks > 1:
                    start_wait = time.time()
                    while not self.mesh_ready_for_next:
                        self.root.update()  # GUI flüssig halten
                        time.sleep(0.1)     # CPU schonen
                        # Sicherheits-Timeout (Erhöht auf 12 Sekunden, da End-to-End-ACKs im Mesh dauern)
                        if time.time() - start_wait > 12:
                            print(f"[Mesh] ⚠️ Kein ACK erhalten für Teil {index+1}, fahre aus Sicherheitsgründen fort...")
                            break
                # --- DAS GEHEIMNIS GEGEN DEN PAKETVERLUST ---
                if total_chunks > 1:
                    for _ in range(6):
                        self.root.update()
                        time.sleep(0.5)
            # Nach der Schleife den temporären Listener wieder sauber abmelden
            if pub is not None:
                pub.unsubscribe(on_ack_received, "meshtastic.receive.routing")
            print("[Mesh] IARU-Meldung vollständig verarbeitet.")
        except Exception as e:
            print(f"[Mesh] Fehler beim Senden: {e}")
            self.digi_terminals["LORA_MESH"]["monitor"].insert(
                "end", f"[{self.utc_time_str()}] ❌ Sende-Fehler: {e}\n"
            )
            self.digi_terminals["LORA_MESH"]["monitor"].see("end")
    def check_equip(self): # <--- Zeigt eine Checkliste mit der wichtigsten Ausrüstung an
        equip_check_quest = messagebox.askyesno(
            title = "Ablageplatz und Equipment",
            message="Soll die Checkliste angezeigt werden?\nSie können Diese dann abarbeiten"
        )
        if equip_check_quest:
            try:
                self.help_notebook.select(self.sub_tab_check)
                self.tabs.select(self.tab_help_main)
            except Exception as e:
                messagebox.showinfo("Hilfe", "Der Hilfebereich ist derzeit nicht verfügbar.")
        else:
            pass
    def mesh_gps_pos(self): # <--- Aktualisiert beim Programmstart einmalig die HOME-Position aus Mesh-GPS, sofern die Konfiguration das erlaubt und ein gültiger GPS-Stand verfügbar ist
        """
        Aktualisiert beim Programmstart einmalig die HOME-Position aus Mesh-GPS,
        sofern die Konfiguration das erlaubt und ein gültiger GPS-Stand verfügbar ist.
        """
        if not self.config.get("GUI", {}).get("if_mesh_gps", True):
            return
        if getattr(self, "mesh_home_auto_updated", False):
            return
        try:
            if not self.mesh_connected or not self.interface:
                return
            mesh_iface = cast(Any, self.interface)
            data = mesh_iface.getMyNodeInfo()
            pos = data.get("position", {}) if isinstance(data, dict) else {}
            lat_raw = pos.get("latitude")
            lon_raw = pos.get("longitude")
            if lat_raw is None or lon_raw is None:
                return
            # Meshtastic liefert Positionswerte oft in 10^7-Format.
            lat = float(lat_raw) / 1e7 if abs(float(lat_raw)) > 180 else float(lat_raw)
            lon = float(lon_raw) / 1e7 if abs(float(lon_raw)) > 180 else float(lon_raw)
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return
            self.mesh_home_auto_updated = True
            self.set_home_position_from_click((lat, lon))
            # Auch in der Konfig ablegen
            map_conf = self.config.setdefault("MAP", {})
            map_conf["center_lat"] = float(lat)
            map_conf["center_lon"] = float(lon)
            self.save_settings()
            if hasattr(self, "log_list"):
                try:
                    self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] Mesh-GPS Home-Update: {lat:.6f}, {lon:.6f}")
                    self.write_session_log(f"[{self.utc_iso_timestamp()}] Mesh-GPS Home-Update: {lat:.6f}, {lon:.6f}")

                except Exception:
                    pass
        except Exception:
            self.mesh_home_auto_updated = True
            return
    def simple_rx(self, event): # <--- Wird aufgerufen, wenn der RX-Modus gewechselt wird, und startet die entsprechende RX-Funktion oder stoppt sie, je nach Auswahl
        mode = self.rx_combo.get()
        def is_fldigi_aktive(m): # <--- Hillfsfunktion, um zu prüfen, ob der ausgewählte Modus die FLDIGI-Integration aktiviert hat, basierend auf der Konfiguration
            cfg_raw = self.config.get("MODES", {}).get(m, {})
            cfg = cfg_raw.get("use_fldigi", False)
            return cfg
        # Auswahl der RX Modi-Funktion
        match mode:
            case "MT63" if is_fldigi_aktive("MT63"):
                print("[RX-Mode] MT63-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "RTTY" if is_fldigi_aktive("RTTY"):
                print("[RX-Mode] RTTY-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "WINLINK" if is_fldigi_aktive("WINLINK"):
                print("[RX-Mode] WINLINK-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "JS8CALL" if is_fldigi_aktive("JS8CALL"):
                print("[RX-Mode] JS8CALL-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "VARA" if is_fldigi_aktive("VARA"):
                print("[RX-Mode] VARA-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "FAX" if is_fldigi_aktive("FAX"):
                print("[RX-Mode] FAX-Modus ausgewählt.")
                self.start_fldigi_rx_loop()
            case "Kein RX":
                print("[RX-Mode] Kein RX-Modus ausgewählt.")
                self.clear_vars_fldigi()
            case _:
                print("[RX-Mode] Kein RX-Modus. Wechsle zum Default")
                messagebox.showwarning(
                    "Modus nicht verfügbar", 
                    f"Der Modus '{mode}' ist in der Konfiguration derzeit deaktiviert "
                    "oder nutzt nicht die fldigi-Schnittstelle."
                )
                try:
                    werte = self.rx_combo['values']
                    if "Kein RX" in werte:
                        self.rx_combo.current(werte.index("Kein RX"))
                    else:
                        self.rx_combo.set("Kein RX")
                except Exception:
                    self.rx_combo.set("")
    def clear_vars_fldigi(self): # <--- Setzt alle Variablen zurück, die mit fldigi zu tun haben.
        """Setzt alle Variablen zurück, die mit fldigi zu tun haben."""
        # Polling-Timer abbrechen wenn aktiv
        if self.fldigi_after_id is not None:
            try:
                self.root.after_cancel(self.fldigi_after_id)
            except:
                pass
            self.fldigi_after_id = None
        self.fldigi_polling_active = False
    def start_fldigi_rx_loop(self): # <--- Startet die regelmäßige Abfrage von fldigi.
        """Startet die regelmäßige Abfrage von fldigi.
        Wird einmalig am Ende von setup_ui() aufgerufen."""
        if pyfldigi is None:  # Prüfen, ob die Library überhaupt geladen ist
            return
        # Guard: Wenn Polling bereits aktiv, nicht nochmal starten
        if self.fldigi_polling_active:
            print("[fldigi] Polling läuft bereits, kein neuer Start.")
            return
        # Markiere Polling als aktiv
        self.fldigi_polling_active = True
        try:
            # Einmalig beim Start: ApplicationMonitor initialisieren (falls noch nicht geschehen)
            # und den Client vorbereiten
            client = self._start_fldigi_client()
            if client is None:
                self.fldigi_polling_active = False
                print("[fldigi] Client-Initialisierung fehlgeschlagen.")
                return
            # Alten Text-Müll bei fldigi löschen
            client.text.get_rx_data()
            print("[fldigi] RX-Abfrage-Loop gestartet...")
        except Exception as e:
            self.fldigi_polling_active = False
            print(f"[fldigi] Start-Verbindungsfehler: {e}")
            return
        # Den ersten automatischen Durchlauf anstoßen
        self.poll_fldigi_rx()
    def poll_fldigi_rx(self): # <--- Prüft die fldigi-Schnittstelle und plant sich selbst nach 60 Sek. neu ein.
        """Prüft die fldigi-Schnittstelle und plant sich selbst nach 60 Sek. neu ein"""
        mode = self.rx_combo.get()
        # Wenn zu "Kein RX" gewechselt wurde, Polling stoppen
        if mode == "Kein RX" or not self.fldigi_polling_active:
            self.fldigi_polling_active = False
            self.fldigi_after_id = None
            return
        # Hilfsprüfung: Mode muss fldigi aktivieren
        mode_cfg = self.config.get("MODES", {}).get(mode, {})
        if mode_cfg.get("use_fldigi", False):
            try:
                client = self._start_fldigi_client()
                if client is not None:
                    neue_daten = client.text.get_rx_data()
                    if neue_daten:
                        # Sicher decodieren
                        text = neue_daten.decode('utf-8', errors='ignore') if isinstance(neue_daten, bytes) else str(neue_daten)
                        if mode in self.digi_terminals and "receive" in self.digi_terminals[mode]:
                            text_widget = self.digi_terminals[mode]["receive"]
                            text_widget.insert("end", text)
                            text_widget.see("end")
                            # WICHTIG: Zuerst in den Buffer schreiben, DAMIT check_rx_iaru() es sehen kann!
                            self.recive_buffer += text
                            print(f"Inhalt des Buffers aktuell:\n{self.recive_buffer}")
                            if "#NOFUSTX#Meldungstext#" in text :
                                print(f"Startmaker gefunden\n")
                            if "#NOFUSTX#Meldungstext#" in self.recive_buffer and "---Ende der Meldung---" in self.recive_buffer:
                                print("[fldigi] Verdächtiger Textblock erkannt, prüfe auf IARU-Meldung...")
                            # Jetzt erst prüfen
                            self.check_rx_iaru(text)
                            print(f"inhalt des Buffer:\n{self.recive_buffer}")
            except Exception as e:
                # Im Hintergrund unauffällig loggen, falls fldigi mal nicht läuft
                print(f"[fldigi] Loop-Abfrage fehlgeschlagen (fldigi geschlossen?): {e}")
        # In 60.000 Millisekunden (60 Sek.) diese Funktion wieder aufrufen
        # Es gibt nur EINEN laufenden Timer, nicht mehrere
        if not mode == "Kein RX" and self.fldigi_polling_active:
            self.fldigi_after_id = self.root.after(60000, self.poll_fldigi_rx)
    def check_rx_iaru(self, rx_text): # <--- Sammelt empfangene FLDIGI-Textblöcke und verarbeitet vollständige IARU-Meldungen. (Hier nochmal prüfen ob diese Funktion so arbeitet wie gedacht)
        """Sammelt empfangene FLDIGI-Textblöcke und verarbeitet vollständige IARU-Meldungen."""
        start_marker = "#NOFUSTX#Meldungstext#"
        end_marker = "---Ende der Meldung---"
        # Debug-Meldungen krisensicher im echten Buffer prüfen
        if start_marker in self.recive_buffer:
            print("[IARU-Scanner] Start-Marker im Buffer erkannt!")
        if end_marker in self.recive_buffer:
            print("[IARU-Scanner] End-Marker im Buffer erkannt! Verarbeite Block...")
        # Endlosschleife, falls mehrere komplette Meldungen im Buffer stecken
        while True:
            start = self.recive_buffer.find(start_marker)
            if start == -1:
                break # Kein Startmarker da? Abbrechen und auf mehr Text warten.
            end = self.recive_buffer.find(end_marker, start)
            if end == -1:
                break # Startmarker da, aber Endmarker fehlt noch? Abbrechen und auf Rest warten!
            # Wenn wir hier landen, haben wir einen VOLLSTÄNDIGEN Block!
            end += len(end_marker)
            # Block ausschneiden
            block = self.recive_buffer[start:end]
            # WICHTIG: Nur den verarbeiteten Teil aus dem Buffer löschen, 
            # falls danach schon die nächste Nachricht anfängt!
            self.recive_buffer = self.recive_buffer[end:]
            try:
                self._process_rx_iaru_block(block)
            except Exception as e:
                print(f"[IARU] Fehler bei der Verarbeitung empfangener Meldung: {e}")
    def _process_rx_iaru_block(self, block): # <--- Extrahiert Header und Text aus einem kompletten IARU-Block und protokolliert ihn.
        """Extrahiert Header und Text aus einem kompletten IARU-Block und protokolliert ihn."""
        # Der Block beginnt mit dem Marker, kann aber auch noch zusätzliche Zeilen enthalten.
        payload = block
        if "-IARU-Meldung-" in payload:
            payload = payload.split("-IARU-Meldung-", 1)[1]
        lines = [line.rstrip() for line in payload.splitlines()]
        header_lines = []
        body_lines = []
        end_marker = "---Ende der Meldung---"
        seen_body = False
        for line in lines:
            if not seen_body:
                if not line.strip() and header_lines:
                    seen_body = True
                    continue
                if not line.strip():
                    continue
                if ":" in line:
                    header_lines.append(line.strip())
                    continue
                seen_body = True
            if seen_body:
                if line.strip() == end_marker:
                    break
                body_lines.append(line)
        body_text = "\n".join(body_lines).strip()
        prio = ""
        for header in header_lines:
            if header.upper().startswith("WICHTIGKEIT:"):
                prio = header.split(":", 1)[1].strip()
                break
        if not body_text:
            print("[IARU] Keine Nutzdaten im empfangenen IARU-Block gefunden.")
            return
        source = "FLDIGI"
        self.receive_iaru_msg(source, header_lines, prio, body_text)
# ---------- Voltmeter ----------
    def finde_nofus_arduino(self): # <--- Sucht nach einem Arduino mit dem Voltmeter, Erkennung nach NoFuS-TAG
        """
        Scannt alle verfügbaren Ports und sucht nach dem NoFuS-Erkennungs-Tag.
        """
        print("🔍 NoFuS-TX: Scanne USB-Ports nach Spannungsmonitor...")
        verfuegbare_ports = serial.tools.list_ports.comports() # type: ignore
        for port in verfuegbare_ports:
            print(f"   Prüfe Schnittstelle: {port.device} ({port.description})...")
            try:
                # Port kurz öffnen mit 3 Sekunden Lese-Timeout
                test_ser = serial.Serial(port.device, self.BAUD_RATE, timeout=3) # type: ignore
                time.sleep(2)  # Arduino Zeit zum Booten geben
                # Versuchen, bis zu 2 Zeilen zu lesen (falls die erste unvollständig war)
                for _ in range(2):
                    if test_ser.in_waiting > 0:
                        line = test_ser.readline().decode('utf-8', errors='ignore').strip()
                        # Prüfen, ob unser Erkennungs-Tag im String existiert
                        if '"dev": "nofus-vmon"' in line:
                            print(f"   🎯 Treffer! NoFuS-Hardware auf {port.device} erkannt.\n")
                            test_ser.close() # Test-Port schließen, um ihn gleich richtig zu nutzen
                            return port.device
                test_ser.close()
            except (serial.SerialException, UnicodeDecodeError): # type: ignore
                # Port blockiert oder keine Rechte (z.B. Dialout-Gruppe unter Linux)
                continue
        return None
    def formatiere_spannung(self, wert): # <--- Verarbeite die Spannung vom Voltmeter
        if wert is None or wert < 0.5:
            return "N/A"
        return f"{wert:.2f} V"
    def voltmeter_thread(self): # <--- Voltmeter Thread (Überwachung der Spannung im Notfall-Koffer)
        # Erstellt den Hintergrund-Prozess
        monitor_thread = threading.Thread(target=self.starte_spannungs_monitor, daemon=True)
        # Startet ihn parallel zur Hauptsoftware
        monitor_thread.start()
    def starte_spannungs_monitor(self): # <--- Starte Spannungs und Systemmonitor und schreibe ins Log
        # Automatische Suche starten
        automatischer_port = self.finde_nofus_arduino()
        if not automatischer_port:
            print("❌ Keine NoFuS-Hardware gefunden. Bitte Kabel prüfen oder manuell starten.")
            return
        try:
            # Mit dem automatisch gefundenen Port dauerhaft verbinden
            ser = serial.Serial(automatischer_port, self.BAUD_RATE, timeout=1) # type: ignore
            print(f"✅ Dauerhafte Überwachung gestartet auf {automatischer_port}.\n")
            log_counter = 0
            while True:
                if ser.in_waiting > 0:
                    raw_line = ser.readline().decode('utf-8').strip()
                    try:
                        daten = json.loads(raw_line)
                        # Werte auslesen
                        u1 = daten.get("ch1", 0.0)
                        u2 = daten.get("ch2", 0.0)
                        u3 = daten.get("ch3", 0.0)
                        u4 = daten.get("ch4", 0.0)
                        self.lbl_u1.config(text=f"Batterie: {self.formatiere_spannung(u1)}")
                        self.lbl_u2.config(text=f"Solar: {self.formatiere_spannung(u2)}")
                        self.lbl_u3.config(text=f"Ausgabe U1: {self.formatiere_spannung(u3)}")
                        self.lbl_u4.config(text=f"Ausgabe U2: {self.formatiere_spannung(u4)}")
                        if log_counter == 30 or log_counter == 0: # Alle 5 Minuten einmal in die Logdatei schreiben
                            log_counter = 0
                            volt_log = (f"[Voltmeter]--- AKKU STATUS {time.strftime('%H:%M:%S')} ---\n"
                                "[Voltmeter] Messpunkt 1 (Batterie): {self.formatiere_spannung(u1)}\n"
                                "[Voltmeter] Messpunkt 2 (Solarspannung):  {self.formatiere_spannung(u2)}\n"
                                "[Voltmeter] Messpunkt 3 (Reglerausgabespannung): {self.formatiere_spannung(u3)}\n"
                                "[Voltmeter] Messpunkt 4 (Verteilerleiste Spannung): {self.formatiere_spannung(u4)}\n"
                            )
                            self.write_session_log(volt_log)
                            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] --- AKKU STATUS ---")
                            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] Messpunkt 1 (Batterie): {self.formatiere_spannung(u1)}")
                            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] Messpunkt 2 (Solarspannung):  {self.formatiere_spannung(u2)}")
                            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] Messpunkt 3 (Reglerausgabespannung): {self.formatiere_spannung(u3)}")
                            self.log_list.insert(0, f"[{self.utc_iso_timestamp()}] Messpunkt 4 (Verteilerleiste Spannung): {self.formatiere_spannung(u4)}")
                            print(f"--- 🔋 AKKU STATUS {time.strftime('%H:%M:%S')} ---")
                            print(f" Messpunkt 1 (Batterie): {self.formatiere_spannung(u1):>7}")
                            print(f" Messpunkt 2 (Solarspannung):  {self.formatiere_spannung(u2):>7}")
                            print(f" Messpunkt 3 (Reglerausgabespannung): {self.formatiere_spannung(u3):>7}")
                            print(f" Messpunkt 4 (Verteilerleiste Spannung): {self.formatiere_spannung(u4):>7}")
                            print("-" * 33)
                        log_counter += 1
                    except json.JSONDecodeError:
                        pass
                time.sleep(60) # Alle 10 Sekunden prüfen cpu schonen
        except serial.SerialException as e:  # type: ignore
            print(f"❌ Verbindung im laufenden Betrieb verloren: {e}")
            messagebox.showerror("Verbindungsfehler", f"Die Verbindung zum NoFuS-Spannungsmonitor wurde unterbrochen:\n{e}")
        
    # =============================================================================
    # NoFuS-TX v2.0 - MULTI-TREIBER HARDWARE STARTER
    # =============================================================================
    def init_nofus_v2_hardware(self): # <--- Neue Schnittstellen funktion Für alle extern angeschlossenen Geräte wie TNC, Arduino, oder Ähnliche die Kiss Sprechen
        """
        Der neue v2.0 Core-Starter. Geht deine AX25_PORTS durch und 
        entscheidet anhand der Kategorie (ax, kiss, ip, soft), welcher
        Hintergrund-Dienst gestartet wird.
        """
        modes = self.config.get("MODES", {})
        ports_list = modes.get("AX25_PORTS", [])
        
        # Speicher für aktive serielle Verbindungen (für die spätere TX-Senderichtung)
        self.active_hardware_connections = {}

        for port_cfg in ports_list:
            # Nur starten, wenn active auf True steht
            if not port_cfg.get("active", False):
                continue

            # Wir holen deine exakten v2.0 Variablenbezeichnungen aus der Config
            port = port_cfg.get("device")          # /dev/ttyUSB0-9, COM0-9, oder ax0/ax1
            baud = int(port_cfg.get("BAUD_RATE", 9600))
            hw_mode = port_cfg.get("hardware", "kiss") # Standardmäßig "kiss" falls leer
            nickname = port_cfg.get("nickname", "Unbekannt")
            port_call = port_cfg.get("call", "NOCALL")

            if not port:
                continue

            # -----------------------------------------------------------------
            # WEICHE 1: "ax" -> Der klassische Linux-Kernel-Stack
            # -----------------------------------------------------------------
            if hw_mode == "ax":
                self.aprs_update_queue.put({
                    "type": "log",
                    "message": f"🐧 [{nickname}] Nutze Linux-AX.25 Stack auf Device: {port}"
                })
                # Hier klinken wir später deine neue socket.py ein!
                # t_ax = threading.Thread(target=self.linux_ax25_worker, args=(port, port_call), daemon=True)
                # t_ax.start()

            # -----------------------------------------------------------------
            # WEICHE 2: "kiss" -> Der neue universelle USB/Seriell-Worker
            # -----------------------------------------------------------------
            elif hw_mode == "kiss":
                t_kiss = threading.Thread(
                    target=self.universal_kiss_worker,
                    args=(port, baud, nickname, port_call),
                    daemon=True,
                    name=f"NoFuS_KISS_{nickname}"
                )
                t_kiss.start()

            # -----------------------------------------------------------------
            # WEICHE 3: "ip" -> Netzwerk-basierte Verbindung (Hamnet / TCP-KISS)
            # -----------------------------------------------------------------
            elif hw_mode == "ip":
                self.aprs_update_queue.put({
                    "type": "log",
                    "message": f"🌐 [{nickname}] Vorbereitung für IP/Hamnet-Port auf {port}..."
                })
                # Hier kommt später der TCP-Socket-Worker hin

            # -----------------------------------------------------------------
            # WEICHE 4: "soft" -> API-basierte Hardware (Meshtastic, Voltmeter etc.)
            # -----------------------------------------------------------------
            elif hw_mode == "soft":
                self.aprs_update_queue.put({
                    "type": "log",
                    "message": f"🤖 [{nickname}] Starte Software-API/Treiber für {port} ({nickname})..."
                })
                # Hier wird z.B. der native Meshtastic-Python-Treiber eingeklinkt
            
    def universal_kiss_worker(self, port, baudrate, nickname, port_call): # <--- Der universelle KISS-Worker für serielle USB-Geräte
        """
        Der CPU-schonende KISS-Arbeiter für das USB-Kabel.
        Lauscht auf dem Port, filtert KISS-Frames und schont die CPU im Leerlauf.
        """

        self.aprs_update_queue.put({
            "type": "log",
            "message": f"🔌 [{nickname}] Öffne KISS-Port {port} ({baudrate} Baud)..."
        })

        try:
            # timeout=0.5 zwingt den Thread zum Schlafen, wenn keine Daten da sind (0% CPU!)
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5) # type: ignore
            self.active_hardware_connections[port] = ser
        except Exception as e:
            self.aprs_update_queue.put({
                "type": "log",
                "message": f"❌ [{nickname}] Serieller Fehler auf {port}: {e}"
            })
            return

        # --- RETRO-TNC INITIALISIERUNG (TNC2S & Co.) ---
        # Da wir im KISS-Modus sind, schicken wir den Aufwachbefehl
        try:
            ser.write(b"\r\n\r\n\r\n")
            time.sleep(0.1)
            ser.write(b"KISS ON\r")
            time.sleep(0.1)
            ser.write(b"RESTART\r")
            time.sleep(0.3)
            self.aprs_update_queue.put({
                "type": "log",
                "message": f"✅ [{nickname}] TNC-Initialisierung an {port} gesendet."
            })
        except Exception as e:
            self.aprs_update_queue.put({
                "type": "log",
                "message": f"⚠️ [{nickname}] Initialisierungsfehler: {e}"
            })

        buffer = b""
        FEND = b'\xc0'

        # --- REINER EMPFANGS-LOOP ---
        while True:
            try:
                chunk = ser.read(256)
                if not chunk:
                    continue

                buffer += chunk

                while buffer.count(FEND) >= 2:
                    start_idx = buffer.find(FEND)
                    end_idx = buffer.find(FEND, start_idx + 1)
                    
                    if end_idx != -1:
                        kiss_frame = buffer[start_idx : end_idx + 1]
                        buffer = buffer[end_idx + 1 :]
                        
                        if len(kiss_frame) <= 3:
                            continue

                        # Ein sauberes Datenpaket ist da! Wir übergeben es der Hauptschleife.
                        self.aprs_update_queue.put({
                            "type": "raw_kiss_frame",
                            "hardware": "kiss",
                            "port": port,
                            "nickname": nickname,
                            "port_call": port_call,
                            "frame": kiss_frame
                        })
                    else:
                        break

            except Exception as e:
                self.aprs_update_queue.put({
                    "type": "log",
                    "message": f"⚠️ [{nickname}] Verbindung unterbrochen: {e}"
                })
                if port in self.active_hardware_connections:
                    del self.active_hardware_connections[port]
                break

    def play_beep(self, frequenz=1100, dauer_ms=200): # <--- Erzeugt einen präzisen Systemton via ffplay (QBASIC-Style)
        """Erzeugt einen Sinuston mit definierter Frequenz und Dauer."""
        def _task():
            # wandelt Millisekunden in Sekunden um
            dauer_sek = dauer_ms / 1000.0
            # Ein genialer ffmpeg-Befehl, der einen reinen Sinuston generiert
            cmd = f"ffplay -f lavfi -i \"sine=frequency={frequenz}:duration={dauer_sek}\" -nodisp -autoexit -loglevel quiet"
            try:
                subprocess.run(cmd, shell=True)
            except Exception as e:
                print(f"[Beep-Fehler] ffplay konnte nicht piepen: {e}")

        # Wir starten das in einem Thread, damit die UI während des Piep-Tons nicht einfriert!
        threading.Thread(target=_task, daemon=True).start()        
# ---------- MAIN ----------
# Startet die Anwendung, indem die Hauptklasse instanziiert und die Tkinter-Hauptschleife gestartet wird.
if __name__ == "__main__":
    root = tk.Tk()
    app = NoFuSTX(root)
    root.mainloop()
