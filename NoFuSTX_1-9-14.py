import tkinter as tk
from tkinter import ttk, messagebox
import tkintermapview
import datetime
import json
import os
import subprocess
import platform
import tempfile


class NoFuSTX:
    def __init__(self, root):
        self.root = root
        self.root.title("NoFuSTX - Einsatzleitsoftware v1.9.14")
        self.root.geometry("1250x950")
        self.config_file = "nofustx_config.json"

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
                    "port": "14480",
                    "call": "NOCALL",
                    "passcode": "00000",
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
            },
            "PRINTER": {"name": "Standard-Thermo", "auto_print": False},
            "UNITS": [
                {"name": "Zentrale (NoFuS-E)", "type": "NoFuS-E", "status": True},
                {"name": "Mobil 1", "type": "NoFuS-M", "status": True},
                {"name": "Trupp A", "type": "NoFuS-P", "status": False},
            ],
            # Standard-Lagekarte: ca. 10 km Radius um 51.9621817 / 9.6509120
            "MAP": {
                "center_lat": 51.9621817,
                "center_lon": 9.6509120,
                "zoom": 13,
            },
        }

        self.load_settings()
        self.setup_ui()

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

    def setup_map_view(self):
        # Karte mit APRS-Integration
        self.map_widget = tkintermapview.TkinterMapView(self.tab_map)
        self.map_widget.pack(expand=1, fill="both")

        # Startposition aus Config (MAP) – Standard ca. 10 km Radius um 51.9621817 / 9.6509120
        map_conf = self.config.get("MAP", {})
        lat = float(map_conf.get("center_lat", 51.9621817))
        lon = float(map_conf.get("center_lon", 9.6509120))
        zoom = int(map_conf.get("zoom", 13))

        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(zoom)

        btn_refresh = ttk.Button(
            self.tab_map,
            text="APRS-Lage auf Karte markieren",
            command=self.update_aprs_on_map,
        )
        btn_refresh.pack(pady=5)

    def update_aprs_on_map(self):
        call = self.config["MODES"]["APRS_IS"]["call"]
        if call != "NOCALL":
            self.map_widget.set_marker(51.1657, 10.4515, text=f"Station: {call}")
            self.log_list.insert(
                0,
                f"{datetime.datetime.utcnow().strftime('%H:%M')} : APRS Position markiert.",
            )
        else:
            messagebox.showwarning("APRS", "Bitte Rufzeichen konfigurieren.")

    def update_aprs_on_map_initial(self):
        """
        Startet – falls konfiguriert – mit einem APRS-Marker, ohne den Nutzer
        mit Warnmeldungen zu stören. Wird einmalig beim Programmstart aufgerufen.
        """
        call = self.config["MODES"]["APRS_IS"]["call"]
        if call == "NOCALL":
            return

        # Marker nahe der aktuellen Kartenmitte setzen
        try:
            current_pos = self.map_widget.get_position()
            lat, lon = current_pos[0], current_pos[1]
        except Exception:
            # Fallback: zentrale Deutschland-Position
            lat, lon = 51.1657, 10.4515

        self.map_widget.set_marker(lat, lon, text=f"Station: {call}")
        # Eintrag im Log, aber keine Messagebox
        self.log_list.insert(
            0,
            f"{datetime.datetime.utcnow().strftime('%H:%M')} : APRS Position (Auto-Start) markiert.",
        )

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
            command=lambda: messagebox.showinfo("Info", "Funktion in v1.9.14 geplant."),
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Status ändern", command=self.toggle_unit_status
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_f, text="Einheit löschen", command=self.delete_unit
        ).pack(side="left", padx=5)

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
            ent = ttk.Entry(header_f)
            ent.grid(row=1, column=i, padx=5, pady=5, sticky="ew")
            self.msg_fields[title] = ent

        # Zeit & Datum vorbelegen (UTC)
        self.msg_fields["Zeit (UTC)"].insert(
            0, datetime.datetime.utcnow().strftime("%H:%M")
        )
        self.msg_fields["Datum"].insert(
            0, datetime.datetime.utcnow().strftime("%d.%m.%Y")
        )

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
            # Nur typische Übertragungsmodi für Text anbieten
            if mode in ("RTTY", "WINLINK") and data.get("active"):
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

    # ---------- KONFIGURATION ----------
    def show_config_window(self):
        # Hardware- & Modi-Konfiguration inkl. Drucker und SSTV-Spezialfeldern
        win = tk.Toplevel(self.root)
        win.title("Hardware Konfiguration")
        win.geometry("800x700")

        nb = ttk.Notebook(win)
        nb.pack(expand=1, fill="both", padx=5, pady=5)

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

                self.ax_temp_list.append(
                    {"active": v, "device": dev, "nickname": nick, "call": call}
                )

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

        # Weitere Modi (inkl. SSTV-Spezialfall)
        self.temp_entries = {}
        for mode, params in self.config["MODES"].items():
            if mode == "AX25_PORTS":
                continue

            f = ttk.Frame(nb)
            nb.add(f, text=mode)
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
            if mode != "AX25_PORTS" and data.get("active"):
                f = ttk.Frame(nb)
                nb.add(f, text=mode)
                t = tk.Text(
                    f, bg="black", fg="lightgreen", font=("Courier", 10)
                )
                t.pack(expand=1, fill="both")
                # Modus-Namen als Schlüssel (z.B. "RTTY", "WINLINK")
                self.digi_terminals[mode] = t

    # ---------- LOG ----------
    def log_iaru_msg(self):
        nr = self.msg_fields["Nummer"].get()
        self.log_list.insert(
            0,
            f"{datetime.datetime.utcnow().strftime('%H:%M')} : MSG #{nr} archiviert.",
        )
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

        full_text = "IARU-Meldung\n" + "\n".join(header_lines) + f"\nWICHTIGKEIT: {prio}\n\n{body}\n"

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

        # Immer ins Einsatz-Log übernehmen
        nr = self.msg_fields["Nummer"].get()
        if mode and mode != "Nur Log":
            log_text = (
                f"{datetime.datetime.utcnow().strftime('%H:%M')} : MSG #{nr} gesendet über {mode}."
            )
        else:
            log_text = (
                f"{datetime.datetime.utcnow().strftime('%H:%M')} : MSG #{nr} ins Log übernommen."
            )
        self.log_list.insert(0, log_text)

        # Optional drucken
        if hasattr(self, "print_on_send") and self.print_on_send.get():
            self.print_message(full_text)

        messagebox.showinfo("NoFuSTX", "Meldung gesendet und protokolliert.")

    def setup_log_tab(self):
        self.log_list = tk.Listbox(self.tab_log, font=("Courier", 10))
        self.log_list.pack(expand=1, fill="both", padx=10, pady=10)

    # ---------- UHR ----------
    def update_clock(self):
        self.time_label.config(
            text=datetime.datetime.utcnow().strftime("%H:%M:%S UTC")
        )
        self.root.after(1000, self.update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = NoFuSTX(root)
    root.mainloop()
