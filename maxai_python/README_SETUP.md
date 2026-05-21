# MAX-AI — Setup-Anleitung (Deutsch)

> **Wichtig:** Dieses Tool ist ausschließlich für isolierte CTF-/Security-Lab-Umgebungen
> und eigene Trainings-Setups bestimmt. Kein Einsatz gegen fremde Systeme oder in
> Live-Spielen anderer Anbieter.

---

## Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    MAX-AI  (Python 3.11+)                   │
│                                                             │
│  ┌──────────┐   BGRA    ┌──────────────┐   Detections      │
│  │  DXGI    │ ─────────▶│  YOLO ONNX   │ ─────────────┐    │
│  │ Capture  │           │  Detector    │              │    │
│  └──────────┘           └──────────────┘              ▼    │
│                                                ┌───────────┐│
│  ┌──────────────────┐   dx,dy           ┌─────│  Aligner  ││
│  │  Input Backend   │◀──────────────────│     └───────────┘│
│  │  relative_mouse  │                   │  ┌────────────┐  │
│  │  virtual_gamepad │◀──fire────────────┘  │ Auto-Fire  │  │
│  │  kernel_driver   │                      └────────────┘  │
│  └──────────────────┘                                      │
│                                                             │
│  ┌────────────────┐   REST API   ┌──────────────────────┐  │
│  │  FastAPI       │◀────────────▶│  Web-UI (Browser)    │  │
│  │  :17384        │              └──────────────────────┘  │
│  └────────────────┘                                        │
│        │                                                   │
│        ├── Cloudflare Tunnel (optional)                     │
│        └── Discord RPC (optional)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Systemanforderungen

| Anforderung | Details |
|-------------|---------|
| **Betriebssystem** | Windows 10 / 11 x64 |
| **Python** | 3.11 oder neuer, „Add to PATH" beim Installieren aktivieren |
| **GPU (empfohlen)** | NVIDIA mit CUDA **oder** DirectX 12 (DirectML) |
| **GPU (optional)** | AMD / Intel — nur DirectML |
| **Admin-Rechte** | Empfohlen für DXGI Desktop Duplication |
| **Spielmodus** | Fenstermodus oder Borderless Window (Fullscreen Exclusive kann Capture blockieren) |
| **ViGEmBus** | Nur wenn Backend „Virtual Gamepad" gewählt wird |
| **Eigener Treiber** | Nur wenn Backend „Kernel Driver" gewählt wird |

---

## 2. Installation — Schritt für Schritt

### 2.1  Python installieren

1. Lade Python 3.11+ von [python.org](https://www.python.org/downloads/) herunter.
2. Beim Installer: **„Add Python to PATH"** anhaken.
3. Prüfe in einer neuen CMD:
   ```cmd
   python --version
   ```
   Erwartet: `Python 3.11.x` oder höher.

---

### 2.2  Projektordner vorbereiten

```cmd
cd C:\maxai_python
```
*(oder wo auch immer du den Ordner abgelegt hast)*

---

### 2.3  Virtuelle Umgebung anlegen und aktivieren

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Du siehst jetzt `(.venv)` am Anfang der Eingabeaufforderung.

---

### 2.4  Abhängigkeiten installieren

**Option A — NVIDIA CUDA (empfohlen für beste Performance):**
```cmd
pip install -r requirements.txt
```

**Option B — Ohne CUDA (DirectML / CPU):**
```cmd
pip install fastapi "uvicorn[standard]" onnxruntime-directml numpy toml pydantic pypresence dxcam Pillow
```

> **Hinweis:** `onnxruntime-gpu` und `onnxruntime-directml` können nicht gleichzeitig
> installiert sein. Wähle je nach Hardware eine der beiden Optionen.

---

### 2.5  ONNX-Modell einfügen

1. Lege deine `.onnx`-Modelldatei neben `main.py`, z.B.:
   ```
   maxai_python/
   ├── main.py
   └── model_320.onnx   ← hier ablegen
   ```
2. Wenn der Dateiname das Muster `_<size>.onnx` enthält (z.B. `model_320.onnx`),
   wird `capture_size` automatisch erkannt — kein manuelles Setzen nötig.
3. Oder trage den Pfad manuell in `config.toml` ein:
   ```toml
   [detection]
   model_path = "C:/pfad/zum/model.onnx"
   ```

---

### 2.6  ONNX Runtime DLLs (CUDA-Setup)

Nur notwendig wenn `onnxruntime-gpu` genutzt wird:

1. Installiere [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) (11.x oder 12.x).
2. Installiere [cuDNN](https://developer.nvidia.com/cudnn) passend zur CUDA-Version.
3. Füge `CUDA_PATH\bin` zur Systemvariable `PATH` hinzu.
4. **Optional:** Lege `onnxruntime_gpu.dll` neben `main.py` für explizite DLL-Auswahl.

MAX-AI erkennt CUDA automatisch anhand von `CUDA_PATH` und sucht nach `cudnn*.dll`.

---

### 2.7  Konfigurationsdatei anlegen (optional)

```cmd
copy config.toml.example config.toml
```

Passe anschließend `config.toml` nach Bedarf an. Alle Werte können auch über
die Web-UI zur Laufzeit geändert werden.

---

### 2.8  ViGEmBus installieren (nur für Backend 2 — Virtual Gamepad)

1. Lade den ViGEmBus-Installer von
   [github.com/nefarius/ViGEmBus/releases](https://github.com/nefarius/ViGEmBus/releases)
2. Installiere als Administrator.
3. Nach der Installation erscheint ViGEmBus in den Windows-Diensten.
4. Starte MAX-AI und wähle beim Startmenü **[2] Virtual Gamepad**.

---

### 2.9  Kernel-Treiber einrichten (nur für Backend 3 — fortgeschritten)

> Nur für Nutzer die einen kompatiblen Kernel-Mode-Treiber selbst bereitstellen.

1. Der Treiber muss am Device-Pfad `\\.\MaxAIDriver` erreichbar sein.
2. Unterstützte IOCTLs (Device Type 0x8000):
   - `0x800` — MOVE: `struct { i32 dx; i32 dy; }` (8 Bytes)
   - `0x801` — FIRE: `u8` (0 = aus, 1 = an)
   - `0x802` — ADS:  `u8` (0 = aus, 1 = an)
3. Starte MAX-AI und wähle **[3] Kernel Driver**.
4. Bei Fehler erscheint eine klare Fehlermeldung mit dem Device-Pfad.

---

## 3. Start

### Standard-Start (interaktives Menü)

```cmd
python main.py
```

Ausgabe:
```
====================================================
  MAX-AI  —  Input Backend Auswahl
====================================================
  [1] Relative Mouse (SendInput — kein Treiber nötig)
  [2] Virtual Gamepad (ViGEmBus Xbox360)
  [3] Kernel Driver (IOCTL — eigener Treiber erforderlich)
====================================================
Auswahl [1]:
```

Drücke `Enter` für den Standard (Relative Mouse) oder wähle 1–3.

---

### Start mit Kommandozeilenargument (kein Menü)

```cmd
python main.py --input relative_mouse
python main.py --input virtual_gamepad
python main.py --input kernel_driver
```

Weitere Optionen:
```cmd
python main.py --port 8080          # Anderen Port nutzen
python main.py --no-browser         # Browser nicht automatisch öffnen
python main.py --no-tunnel          # Kein Cloudflare Tunnel
python main.py --no-discord         # Kein Discord RPC
```

---

## 4. Web-UI bedienen

Nach dem Start öffnet sich automatisch der Browser mit `http://127.0.0.1:17384`.

### Tabs im Überblick

| Tab | Inhalt |
|-----|--------|
| **Status** | FPS, Targets, Loop-Control (Start/Stop/Kill), Model-Status |
| **Capture** | Monitor, Crop-Größe, FPS-Limit |
| **Detection** | Model-Pfad, Confidence, NMS, CUDA/TRT |
| **Assist** | FOV, Smoothness, Aim-Key, Prediction |
| **Mouse / Pad** | Sensitivity, Smoothing, ADS-Verhalten |
| **Crosshair** | Offset, Parallax |
| **Trigger** | Auto-Fire Konfiguration |
| **Debug** | FPS anzeigen, Verbose Logging |
| **Info** | Discord RPC, Tunnel-URL |

### Workflow

1. Tab **Status** → **Start** klicken (startet Assist Loop in Hintergrund-Thread).
2. FPS-Wert erscheint, `model_found: true` bestätigt Modellerkennung.
3. Im Spiel: Assist-Taste (Standard: `mouse5`) gedrückt halten → Tracking aktiv.
4. `F6` = Assist ein/aus schalten, `F12` = Loop beenden.
5. Einstellungen in beliebigen Tabs anpassen → **Apply** → sofort aktiv.
6. **Save Config** speichert alles nach `config.toml`.

---

## 5. Cloudflare Tunnel (Remote-Zugriff)

MAX-AI sucht automatisch nach `cloudflared.exe`:
1. Im selben Ordner wie `main.py`
2. Im System-`PATH`
3. Falls nicht gefunden: **automatischer Download** von GitHub Releases

Nach Start erscheint die Tunnel-URL im Info-Tab:
```
https://xxxxxx-xxxx.trycloudflare.com
```

Über diese URL ist die Web-UI von überall erreichbar.

**Tunnel deaktivieren:**
```cmd
python main.py --no-tunnel
```

---

## 6. Discord Rich Presence

Wird automatisch aktiviert wenn:
- `info.discord_rpc = true` in config.toml (Standard)
- Discord Desktop läuft
- `pypresence` installiert ist

Zeigt: **„Spielt MAX-AI"** im Discord-Profil.

**Deaktivieren:**
```cmd
python main.py --no-discord
```
oder in `config.toml`:
```toml
[info]
discord_rpc = false
```

---

## 7. Erster-Start-Checkliste

Prüfe nach dem ersten Start folgende Punkte in der Web-UI:

- [ ] **model_found: true** (Status-Tab → Model-Karte)
- [ ] **Provider**: zeigt `CUDAExecutionProvider`, `DmlExecutionProvider` oder `CPUExecutionProvider`
- [ ] **FPS > 0** nach Klick auf „Start"
- [ ] **detection_count** steigt wenn Zielobjekte im Bild sichtbar sind
- [ ] Assist-Taste gedrückt halten → **aim_active: true** im Status
- [ ] Bewegung des Fadenkreuzes / Controllers erkennbar
- [ ] **F12** beendet den Loop sauber

---

## 8. Häufige Fehler und Lösungen

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `DuplicateOutput failed` | Kein Admin, falscher GPU-Treiber | Als Administrator starten; GPU-Treiber aktualisieren |
| `Model not found` | `.onnx`-Datei fehlt | `.onnx` neben `main.py` legen oder Pfad in config.toml setzen |
| `CUDA failed, running on CPU` | CUDA/cuDNN nicht installiert | DirectML nutzen: `pip install onnxruntime-directml` |
| Sehr langsam (< 10 FPS) | CPU-Inference oder großes Modell | `capture_size = 320` oder kleiner; CUDA/DirectML aktivieren |
| Maus bewegt sich nicht | Spiel nutzt Raw Input | Borderless-Window-Modus; `aim_smoothness` verringern |
| `ViGEm connect failed` | ViGEmBus nicht installiert | ViGEmBus-Installer ausführen (als Admin) |
| Kein Tunnel-URL sichtbar | Firewall blockiert cloudflared | Firewall-Ausnahme für cloudflared.exe hinzufügen |
| Discord RPC fehlt | pypresence nicht installiert | `pip install pypresence`; Discord Desktop starten |
| Port bereits belegt | Anderer Prozess auf 17384 | `python main.py --port 9090` (anderen Port wählen) |
| `import onnxruntime` schlägt fehl | Paket nicht installiert | `.venv` aktivieren; `pip install onnxruntime-gpu` oder `-directml` |

---

## 9. Log-Datei

Die Datei `maxai.log` (neben `main.py`) enthält alle Log-Einträge.

Für mehr Detail:
```toml
[debug]
verbose = true
```

---

## 10. Projektstruktur

```
maxai_python/
├── main.py                  # Einstiegspunkt, Startmenü, Server
├── assist_loop.py           # Haupt-Frame-Loop (Thread)
├── capture_dxgi.py          # DXGI Screen Capture
├── detector_yolo.py         # ONNX YOLO Inferenz
├── aligner.py               # Crosshair Aligner + Predictor
├── auto_fire.py             # Auto-Fire State Machine
├── hotkeys.py               # GetAsyncKeyState Wrapper
├── config.py                # TOML Config + Live-Reload
├── web_server.py            # FastAPI REST Server
├── tunnel.py                # Cloudflare Tunnel Manager
├── discord_rpc.py           # Discord Rich Presence
├── math_utils.py            # distance, IoU, clamp, lerp
├── input_backends/
│   ├── __init__.py          # Backend Registry
│   ├── base.py              # AbstractInputBackend
│   ├── relative_mouse.py    # SendInput (Standard)
│   ├── virtual_gamepad.py   # ViGEmBus Xbox360
│   └── kernel_driver.py     # IOCTL Kernel Adapter
├── static/
│   └── web_ui.html          # Web-Interface (Single Page)
├── requirements.txt
├── config.toml.example
├── README_SETUP.md          # Diese Datei
└── maxai.log                # Laufzeit-Log (wird erstellt)
```

---

## 11. API-Referenz (REST)

| Method | Pfad | Funktion |
|--------|------|----------|
| `GET`  | `/`      | Web-UI HTML |
| `GET`  | `/x/s`   | Status JSON |
| `GET`  | `/x/c`   | Komplette Config als JSON |
| `POST` | `/x/c`   | Partielle Config-Änderung (JSON body) |
| `POST` | `/x/r`   | Assist Loop starten |
| `POST` | `/x/p`   | Assist Loop stoppen |
| `POST` | `/x/t`   | Assist ein/aus schalten |
| `POST` | `/x/v`   | Config als TOML speichern |
| `POST` | `/x/k`   | App + Tunnel beenden |

**Beispiel — Config per curl ändern:**
```bash
curl -X POST http://127.0.0.1:17384/x/c \
  -H "Content-Type: application/json" \
  -d '{"aim": {"fov_radius": 150.0}}'
```

---

## 12. CTF-Hinweis

Dieses Tool ist für den Einsatz in **isolierten VM-Umgebungen** und **eigenen
Trainings-Setups** entwickelt worden. Die Verwendung gegen Systeme oder
Anwendungen Dritter ohne explizite Genehmigung ist untersagt und kann
rechtliche Konsequenzen haben.
