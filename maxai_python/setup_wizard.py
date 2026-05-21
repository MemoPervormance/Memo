"""
CroixAI — Driver Installation Wizard.
Detects installed drivers/packages and downloads/installs missing ones.
Supports: ViGEmBus, CH340 (Arduino), CP2102 (MAKCU/RP2040), dxcam, pyserial, opencv-python.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("croixai.setup")

# ---------------------------------------------------------------------------
# Driver / package registry
# ---------------------------------------------------------------------------

DRIVERS: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------ #
    #  System / Runtime                                                    #
    # ------------------------------------------------------------------ #

    "vcredist": {
        "label":       "VC++ 2015–2022 Runtime (x64)",
        "description": "Pflicht für onnxruntime, dxcam und fast alle nativen Python-Module.",
        "url":         "https://aka.ms/vs/17/release/vc_redist.x64.exe",
        "filename":    "vc_redist.x64.exe",
        "install_args": ["/quiet", "/norestart"],
        "registry_keys": [
            r"HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
            r"HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
        ],
        "type":        "exe",
        "category":    "system",
    },

    # ------------------------------------------------------------------ #
    #  Input hardware drivers                                              #
    # ------------------------------------------------------------------ #

    "vigem": {
        "label":       "ViGEmBus (Virtual Controller)",
        "description": "Pflicht für virtual_gamepad Backend — emuliert Xbox 360 Controller.",
        "url":         "https://github.com/nefarius/ViGEmBus/releases/latest/download/ViGEmBus_Setup_1.22.0.exe",
        "filename":    "ViGEmBus_Setup.exe",
        "install_args": ["/quiet", "/norestart"],
        "registry_keys": [
            r"HKLM\SOFTWARE\Nefarius Software Solutions e.U.\ViGEm Bus Driver",
        ],
        "type":        "exe",
        "category":    "input",
    },

    "interception": {
        "label":       "Interception (Kernel-Maus)",
        "description": (
            "Kernel-Level Maus/Tastatur-Treiber. Sendet Inputs auf niedrigstem "
            "Level — robustester Input-Modus. Benötigt einmaligen Neustart."
        ),
        "url":         "https://github.com/oblitum/Interception/releases/download/v1.0.1/Interception.zip",
        "filename":    "Interception.zip",
        "install_args": [],
        "registry_keys": [
            r"HKLM\SYSTEM\CurrentControlSet\Services\keyboard_filter",
            r"HKLM\SYSTEM\CurrentControlSet\Services\mouse_filter",
        ],
        "type":        "interception",
        "category":    "input",
        "manual_note": "Benötigt Admin + Neustart nach Installation.",
    },

    "ch340": {
        "label":       "CH340 / CH341 Treiber (Arduino)",
        "description": "Pflicht für Arduino Leonardo / Pro Micro mit CH340-Chip (USB-Serial).",
        "registry_keys": [
            r"HKLM\SYSTEM\CurrentControlSet\Services\CH341SER",
            r"HKLM\SYSTEM\CurrentControlSet\Services\CH341",
        ],
        "type":        "manual",
        "category":    "input",
        "manual_note": "Download: https://www.wch-ic.com/downloads/CH341SER_EXE.html  →  CH341SER.EXE herunterladen und installieren.",
    },

    "cp2102": {
        "label":       "CP2102 / CP210x Treiber (MAKCU / RP2040)",
        "description": "Pflicht für MAKCU ESP32-S3, RP2040 / RP2350 und viele ESP32-Boards.",
        "url":         "https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip",
        "filename":    "CP210x_Driver.zip",
        "install_args": [],
        "registry_keys": [
            r"HKLM\SYSTEM\CurrentControlSet\Services\silabser",
        ],
        "type":        "zip_inf",
        "inf_file":    "silabser.inf",
        "category":    "input",
    },

    "titan_two": {
        "label":       "ConsoleTuner (Titan Two)",
        "description": "Pflicht für das Titan Two Backend — Gtuner IV Software.",
        "url":         "https://www.consoletuner.com/download/",
        "filename":    "GtunerIV_Setup.exe",
        "install_args": [],
        "registry_keys": [
            r"HKLM\SOFTWARE\ConsoleTuner\Gtuner IV",
            r"HKCU\SOFTWARE\ConsoleTuner",
        ],
        "type":        "manual",
        "category":    "input",
        "manual_note": "Download: https://www.consoletuner.com/download/ → Gtuner IV installieren.",
    },

    # ------------------------------------------------------------------ #
    #  Mouse software (für G-Hub Backend)                                  #
    # ------------------------------------------------------------------ #

    "ghub": {
        "label":       "Logitech G-Hub",
        "description": "Pflicht für Logitech-Mäuse mit G-Hub Backend (G502, G Pro X usw.).",
        "url":         "https://download01.logi.com/web/ftp/pub/techsupport/gaming/lghub_installer.exe",
        "filename":    "lghub_installer.exe",
        "install_args": ["--silent"],
        "registry_keys": [
            r"HKLM\SOFTWARE\LGHUB",
            r"HKCU\SOFTWARE\LGHUB",
        ],
        "type":        "exe",
        "category":    "mouse",
    },

    # ------------------------------------------------------------------ #
    #  Python packages                                                     #
    # ------------------------------------------------------------------ #

    "pyserial": {
        "label":       "pyserial",
        "description": "Pflicht für Arduino, MAKCU, RP2040, Titan Two Serial-Backends.",
        "pip_package": "pyserial>=3.5",
        "type":        "pip",
        "category":    "python",
    },

    "dxcam": {
        "label":       "dxcam (DXGI Capture)",
        "description": "Schnellste DXGI Desktop-Aufnahme — empfohlen für alle Spiele.",
        "pip_package": "dxcam",
        "type":        "pip",
        "category":    "python",
    },

    "opencv": {
        "label":       "opencv-python (Capture Card)",
        "description": "Pflicht für Capture-Card Backend (Elgato HD60, Fifine A3).",
        "pip_package": "opencv-python>=4.9",
        "type":        "pip",
        "category":    "python",
    },

    "pywin32": {
        "label":       "pywin32 (Overlay / GDI)",
        "description": "Pflicht für transparentes Overlay-Fenster und GDI-Fallback-Capture.",
        "pip_package": "pywin32>=306",
        "type":        "pip",
        "category":    "python",
    },

    "pillow": {
        "label":       "Pillow (Screenshots)",
        "description": "Pflicht für Screenshot-Funktion und Bild-Resize.",
        "pip_package": "Pillow>=10.0",
        "type":        "pip",
        "category":    "python",
    },

    "windows_capture": {
        "label":       "windows-capture (WinRT)",
        "description": "Optional: Windows.Graphics.Capture API — gut für HDR / Exclusive-Fullscreen.",
        "pip_package": "windows-capture>=1.2",
        "type":        "pip",
        "category":    "python",
    },

    "ndi_python": {
        "label":       "ndi-python (NDI Backend)",
        "description": "Optional: NDI Netzwerk-Video-Capture für 2-PC Setups via OBS NDI.",
        "pip_package": "ndi-python>=0.1",
        "type":        "pip",
        "category":    "python",
    },

    "interception_py": {
        "label":       "interception-python",
        "description": "Python-Wrapper für den Interception Kernel-Treiber.",
        "pip_package": "interception-python>=0.1",
        "type":        "pip",
        "category":    "python",
    },
}


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _check_registry(keys: List[str]) -> bool:
    """Return True if any registry key exists (Windows only)."""
    if sys.platform != "win32":
        return False
    import winreg  # type: ignore[import]
    for key in keys:
        hive_str, _, subkey = key.partition("\\")
        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }
        hive = hive_map.get(hive_str)
        if hive is None:
            continue
        try:
            with winreg.OpenKey(hive, subkey):
                return True
        except FileNotFoundError:
            pass
    return False


def _check_pip(package_spec: str) -> bool:
    """Return True if the pip package (bare name) is importable."""
    name = package_spec.split(">=")[0].split("==")[0].replace("-", "_").lower()
    alias = {
        "opencv_python":      "cv2",
        "pywin32":            "win32api",
        "windows_capture":    "windows_capture",
        "ndi_python":         "ndi",
        "interception_python":"interception",
        "pillow":             "PIL",
    }
    import_name = alias.get(name, name)
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def check_driver(driver_id: str) -> Dict[str, Any]:
    """Return status dict for a single driver."""
    info = DRIVERS.get(driver_id)
    if info is None:
        return {"id": driver_id, "installed": False, "error": "Unknown driver"}

    installed = False
    if info["type"] == "pip":
        installed = _check_pip(info["pip_package"])
    elif info["type"] in ("exe", "zip_inf", "interception"):
        installed = _check_registry(info.get("registry_keys", []))
    elif info["type"] == "manual":
        installed = _check_registry(info.get("registry_keys", []))

    return {
        "id":          driver_id,
        "label":       info["label"],
        "description": info["description"],
        "installed":   installed,
        "type":        info["type"],
        "category":    info.get("category", "other"),
        "manual_note": info.get("manual_note"),
    }


def check_all() -> List[Dict[str, Any]]:
    return [check_driver(did) for did in DRIVERS]


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

_install_progress: Dict[str, str] = {}
_install_lock = threading.Lock()


def get_install_progress(driver_id: str) -> str:
    with _install_lock:
        return _install_progress.get(driver_id, "idle")


def _set_progress(driver_id: str, msg: str) -> None:
    with _install_lock:
        _install_progress[driver_id] = msg
    logger.info("[%s] %s", driver_id, msg)


def install_driver(driver_id: str) -> None:
    """Start driver install in background thread."""
    t = threading.Thread(target=_install_worker, args=(driver_id,), daemon=True)
    t.start()


def _install_worker(driver_id: str) -> None:
    info = DRIVERS.get(driver_id)
    if info is None:
        _set_progress(driver_id, "error:Unknown driver")
        return

    _set_progress(driver_id, "starting")

    try:
        if info["type"] == "pip":
            _install_pip(driver_id, info["pip_package"])
        elif info["type"] == "exe":
            _install_exe(driver_id, info)
        elif info["type"] == "zip_inf":
            _install_zip_inf(driver_id, info)
        elif info["type"] == "interception":
            _install_interception(driver_id, info)
        elif info["type"] == "manual":
            _set_progress(driver_id, f"manual:{info.get('manual_note', info.get('url', ''))}")
        else:
            _set_progress(driver_id, "error:Unsupported install type")
    except Exception as exc:
        _set_progress(driver_id, f"error:{exc}")


def _install_pip(driver_id: str, package: str) -> None:
    _set_progress(driver_id, f"Installing {package} via pip…")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package, "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _set_progress(driver_id, "done")
    else:
        _set_progress(driver_id, f"error:{result.stderr.strip()[:200]}")


def _install_exe(driver_id: str, info: Dict[str, Any]) -> None:
    _set_progress(driver_id, "Downloading installer…")
    url = info["url"]
    fname = info["filename"]
    tmp = Path(tempfile.mkdtemp()) / fname
    urllib.request.urlretrieve(url, tmp)
    _set_progress(driver_id, "Running installer (may require UAC)…")
    cmd = [str(tmp)] + info.get("install_args", [])
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode in (0, 3010):  # 3010 = reboot required
        _set_progress(driver_id, "done")
    else:
        _set_progress(driver_id, f"error:Installer exited {result.returncode}")


def _install_interception(driver_id: str, info: Dict[str, Any]) -> None:
    """Install Interception kernel driver (requires admin + reboot)."""
    import zipfile
    _set_progress(driver_id, "Downloading Interception…")
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / "Interception.zip"
    try:
        urllib.request.urlretrieve(info["url"], zip_path)
    except Exception as exc:
        _set_progress(driver_id, f"error:Download fehlgeschlagen: {exc}")
        return
    _set_progress(driver_id, "Extracting…")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)
    installer_candidates = list(tmp_dir.rglob("install-interception.exe"))
    if not installer_candidates:
        installer_candidates = list(tmp_dir.rglob("*.exe"))
    if not installer_candidates:
        _set_progress(driver_id, "error:Installer nicht gefunden im Archiv.")
        return
    installer = installer_candidates[0]
    _set_progress(driver_id, "Installiere Kernel-Treiber (UAC-Fenster erscheint)…")
    # Must use ShellExecute runas — subprocess alone cannot write to system32\drivers
    # PowerShell Start-Process -Verb RunAs forces UAC elevation even from non-admin shell
    ps_cmd = (
        f"$p = Start-Process -FilePath '{installer}' "
        f"-ArgumentList '/install' -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True,
    )
    if result.returncode in (0, 3010):
        _set_progress(driver_id, "done:Neustart erforderlich!")
    else:
        stderr = (result.stderr or result.stdout or "").strip()[:300]
        _set_progress(driver_id, f"error:{stderr or f'Exit code {result.returncode}'}")


def _install_zip_inf(driver_id: str, info: Dict[str, Any]) -> None:
    import zipfile
    _set_progress(driver_id, "Downloading driver archive…")
    url = info["url"]
    fname = info["filename"]
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / fname
    urllib.request.urlretrieve(url, zip_path)
    _set_progress(driver_id, "Extracting…")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)
    inf_name = info.get("inf_file", "")
    inf_paths = list(tmp_dir.rglob(inf_name))
    if not inf_paths:
        _set_progress(driver_id, "error:.inf not found in archive")
        return
    inf_path = inf_paths[0]
    _set_progress(driver_id, "Installing driver via pnputil…")
    result = subprocess.run(
        ["pnputil", "/add-driver", str(inf_path), "/install"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _set_progress(driver_id, "done")
    else:
        _set_progress(driver_id, f"error:{result.stderr.strip()[:200]}")


# ---------------------------------------------------------------------------
# Tutorial / Setup Guide
# ---------------------------------------------------------------------------

SETUP_GUIDE: List[Dict[str, str]] = [
    {
        "step": "1",
        "title": "VC++ Runtime & System",
        "body": (
            "Installiere zuerst <b>VC++ 2015–2022 Runtime (x64)</b> — das ist Pflicht für "
            "onnxruntime, dxcam und alle nativen Python-Module. "
            "Klick auf <b>Installieren</b> im Setup-Tab, Kategorie System."
        ),
    },
    {
        "step": "2",
        "title": "Input-Backend wählen & Treiber installieren",
        "body": (
            "<b>Für Valorant / CS2 FaceIt:</b> Nutze Hardware-Backend "
            "(Arduino → CH340, MAKCU → CP2102, KMBOX Net → kein Treiber, "
            "Titan Two → ConsoleTuner, Logitech → G-Hub). "
            "<b>Für Apex / Fortnite / COD / R6 / Rust</b> im Fenstermodus: "
            "<b>relative_mouse</b> (kein Treiber nötig) funktioniert. "
            "Für maximale Zuverlässigkeit: <b>Interception</b> Kernel-Treiber installieren."
        ),
    },
    {
        "step": "3",
        "title": "Maus-Software (optional)",
        "body": (
            "Nutzt du eine <b>Logitech-Maus</b> (G502, G Pro X, G303 usw.)? "
            "Installiere <b>G-Hub</b> und wähle im Input-Tab das <b>ghub</b>-Backend — "
            "das sendet Mausbewegungen über die G-Hub-API direkt. "
            "Razer, SteelSeries, Corsair-Mäuse funktionieren mit <b>relative_mouse</b> "
            "oder <b>Interception</b> ohne extra Software."
        ),
    },
    {
        "step": "4",
        "title": "Capture-Backend wählen",
        "body": (
            "<b>DXGI</b> (dxcam) — schnellstes Backend, für alle Spiele im Fenstermodus. "
            "<b>WinRT</b> — für HDR-Monitore oder Exclusive-Fullscreen. "
            "<b>Capture Card</b> (Elgato HD60/Fifine A3) — für 2-PC Setup per HDMI. "
            "<b>NDI</b> — für 2-PC via Netzwerk (OBS NDI Plugin)."
        ),
    },
    {
        "step": "5",
        "title": "Game-Preset laden",
        "body": (
            "Gehe zu <b>Game Presets</b> und wähle dein Spiel. "
            "Das konfiguriert automatisch FOV, Speed, Konfidenz, Blob-Größe "
            "und empfohlenes AI-Modell. "
            "Feinjustierung in den Tabs Assist / AI / Capture / Input."
        ),
    },
    {
        "step": "6",
        "title": "AI-Modell laden",
        "body": (
            "Lege deine <code>.onnx</code> oder <code>.engine</code> Datei "
            "in den CroixAI-Ordner. "
            "Pfad einstellen unter <b>AI → Model Path</b>. "
            "320 oder 640 Blob-Größe für beste Genauigkeit. "
            "TRT <code>.engine</code> läuft über TensorRT — maximale FPS."
        ),
    },
    {
        "step": "7",
        "title": "Loop starten",
        "body": (
            "Drücke <b>Start</b> im Status-Tab. "
            "Standard Aim-Key: <kbd>Maus2 (RMB)</kbd>. "
            "Pause: <kbd>Pause/Break</kbd>. "
            "Overlay: <kbd>Insert</kbd>. "
            "Beenden: <kbd>F12</kbd>."
        ),
    },
]


# ---------------------------------------------------------------------------
# Category helper for UI grouping
# ---------------------------------------------------------------------------

DRIVER_CATEGORIES: Dict[str, str] = {
    "system": "System / Runtime",
    "input":  "Input-Treiber (Hardware)",
    "mouse":  "Maus-Software",
    "python": "Python-Pakete",
    "other":  "Sonstiges",
}


def check_all_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Return drivers grouped by category for the UI."""
    result: Dict[str, List[Dict[str, Any]]] = {k: [] for k in DRIVER_CATEGORIES}
    for did in DRIVERS:
        status = check_driver(did)
        cat = status.get("category", "other")
        result.setdefault(cat, []).append(status)
    return result
