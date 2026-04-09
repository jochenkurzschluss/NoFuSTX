README: NoFuSTX – Installation & Abhängigkeiten

Kurzbeschreibung
NoFuSTX ist eine Einsatzleitsoftware (GUI) mit Unterstützung für APRS, JS8Call, VARA, Winlink, MT63, RTTY, SSTV, FAX, AX.25 u.v.m.
Es ist die Digitale Lösung nach dem NoFuSatz nach DO2ITH, wie im gleichnamigen PDF.
Projektseite
https://ithnet.de/h16/view.html
Das PDF
https://ithnet.de/h16/NoFuSatz_v1-9-3_offiziell.pdf

Das Projekt läuft unter Windows, Linux und macOS.

Python-Abhängigkeiten (Required / Optional)

+   Kern-Abhängigkeiten (erforderlich für die meisten Funktionen)
-   tkintermapview (Kartenanzeige)
-   Pillow (PIL)
-   requests
+   Funk-/Modem-Module (optional, werden ggf. deaktiviert wenn nicht installiert)
-   aprslib (APRS)
-   pyjs8call (JS8Call API)
-   pyfldigi (Steuerung von fldigi)
-   pyserial (PTT/CAT über seriell)
-   pyaudio + numpy (Sound/Audiostream für MT63/SSTV)
-   pysstv (SSTV-Generierung)

System-Abhängigkeiten (nicht per pip)

    - Linux/macOS
        - axlisten (AX.25 Empfang, oft aus Paket ax25-apps)
        - lpstat / lp (Druck über CUPS)
        - ggf. portaudio (für pyaudio)
    -Windows
        - wmic / powershell (Drucker-Erkennung)
        - notepad (Drucken im Windows-Modus)

Installation (empfohlen)

1) Virtuelle Umgebung anlegen (empfohlen)

python3 -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

2) Python-Abhängigkeiten installieren

Option A: requirements.txt (wenn du erstellst)

        tkintermapview
        Pillow
        aprslib
        pyjs8call
        pyfldigi
        pyserial
        pyaudio
        numpy
        pysstv
        requests
        pyvara

python -m pip install -r requirements.txt

Option B: manuell (alle Pakete)

    python -m pip install --upgrade pip
    python -m pip install requests tkintermapview pillow aprslib pyjs8call pyfldigi pyserial numpy pyaudio pysstv

Optional: Installationsskripte

    install_deps.sh (Linux/macOS)
    install_deps.bat (Windows)

Diese prüfen python, pip und installieren die Pakete automatisch.

Programm starten

    python NoFuSTX_1-9-14.py

Troubleshooting (häufige Situationen)

    - tkinter fehlt (ImportError) → Python wurde ohne Tk-Unterstützung kompiliert / du
      brauchst das OS-Paket (z.B. sudo apt install python3-tk).
      
    - pyaudio Probleme (Build/portaudio) → installiere systemweit portaudio (apt 
      install 
      
    - portaudio19-dev) oder nutze eine vorgefertigte Wheel-Datei.
    
    - axlisten nicht gefunden → installiere Paket ax25-apps (Linux) oder deaktiviere
    AX.25 im Programm.

