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
    "vigem": {
        "label":       "ViGEmBus (Virtual Gamepad)",
        "description": "Required for virtual_gamepad input backend (Xbox 360 emulation).",
        "url":         "https://github.com/nefarius/ViGEmBus/releases/latest/download/ViGEmBus_Setup_1.22.0.exe",
        "filename":    "ViGEmBus_Setup.exe",
        "install_args": ["/quiet", "/norestart"],
        "registry_keys": [
            r"HKLM\SOFTWARE\Nefarius Software Solutions e.U.\ViGEm Bus Driver",
        ],
        "type":        "exe",
    },
    "ch340": {
        "label":       "CH340 Driver (Arduino)",
        "description": "Required for Arduino Leonardo / Pro Micro USB serial (CH340 chip).",
        "url":         "https://www.wch-ic.com/downloads/file/65.html",
        "filename":    "CH340_Setup.exe",
        "install_args": [],
        "registry_keys": [
            r"HKLM\SYSTEM\CurrentControlSet\Services\CH341SER",
            r"HKLM\SYSTEM\CurrentControlSet\Services\CH341",
        ],
        "type":        "exe",
        "manual_note": "Download from https://www.wch-ic.com/downloads/CH341SER_EXE.html",
    },
    "cp2102": {
        "label":       "CP2102 / CP210x Driver (MAKCU / RP2040)",
        "description": "Required for MAKCU ESP32-S3, RP2040 / RP2350 USB serial.",
        "url":         "https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip",
        "filename":    "CP210x_Driver.zip",
        "install_args": [],
        "registry_keys": [
            r"HKLM\SYSTEM\CurrentControlSet\Services\silabser",
        ],
        "type":        "zip_inf",
        "inf_file":    "silabser.inf",
    },
    "pyserial": {
        "label":       "pyserial (Python package)",
        "description": "Required for Arduino, MAKCU, RP2040, Titan Two serial backends.",
        "pip_package": "pyserial>=3.5",
        "type":        "pip",
    },
    "dxcam": {
        "label":       "dxcam (DXGI capture)",
        "description": "Fast DXGI Desktop Duplication capture — recommended for DXGI backend.",
        "pip_package": "dxcam",
        "type":        "pip",
    },
    "opencv": {
        "label":       "opencv-python (Capture Card)",
        "description": "Required for capture_card (Elgato / Fifine DirectShow) backend.",
        "pip_package": "opencv-python>=4.9",
        "type":        "pip",
    },
    "pywin32": {
        "label":       "pywin32 (Overlay / GDI)",
        "description": "Required for the transparent overlay window and GDI capture fallback.",
        "pip_package": "pywin32>=306",
        "type":        "pip",
    },
    "windows_capture": {
        "label":       "windows-capture (WinRT backend)",
        "description": "Optional: Windows.Graphics.Capture API (WinRT capture backend).",
        "pip_package": "windows-capture>=1.2",
        "type":        "pip",
    },
    "ndi_python": {
        "label":       "ndi-python (NDI backend)",
        "description": "Optional: NDI low-latency network video capture backend.",
        "pip_package": "ndi-python>=0.1",
        "type":        "pip",
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
    # Special mapping
    alias = {
        "opencv_python": "cv2",
        "pywin32":       "win32api",
        "windows_capture": "windows_capture",
        "ndi_python":    "ndi",
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
    elif info["type"] in ("exe", "zip_inf"):
        installed = _check_registry(info.get("registry_keys", []))

    return {
        "id":          driver_id,
        "label":       info["label"],
        "description": info["description"],
        "installed":   installed,
        "type":        info["type"],
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
        "title": "Choose your input backend",
        "body": (
            "For Valorant (Vanguard anti-cheat) or CS2 FaceIt, you MUST use a hardware input backend "
            "(Arduino, KMBOX Net, MAKCU, RP2040, Titan Two, or G-Hub). "
            "For other games (Apex, Fortnite, COD, R6, Rust) in borderless-window mode, "
            "<b>relative_mouse</b> (Windows SendInput) works fine."
        ),
    },
    {
        "step": "2",
        "title": "Install required drivers",
        "body": (
            "Use the <b>Setup → Drivers</b> tab to install drivers for your chosen backend. "
            "ViGEmBus is needed for virtual_gamepad. "
            "CH340 or CP2102 for USB serial devices. "
            "pyserial is always needed for serial backends."
        ),
    },
    {
        "step": "3",
        "title": "Choose your capture backend",
        "body": (
            "For borderless-window games: use <b>DXGI</b> (fastest, uses dxcam). "
            "For HDR monitors or exclusive-fullscreen: use <b>WinRT</b>. "
            "For 2-PC setups: <b>Capture Card</b> (Elgato HD60/Fifine A3) or <b>UDP</b>. "
            "NDI is available via OBS NDI plugin."
        ),
    },
    {
        "step": "4",
        "title": "Load a game preset",
        "body": (
            "Go to <b>Game Presets</b> and click your game. "
            "This auto-configures FOV, speed, confidence, blob size, and recommended backend. "
            "Fine-tune in the Assist / AI / Capture / Input tabs."
        ),
    },
    {
        "step": "5",
        "title": "Load your model",
        "body": (
            "Place your <code>.onnx</code> or <code>.engine</code> model file in the CroixAI folder. "
            "Set the path in <b>AI → Model Path</b>. "
            "Use 320 or 640 blob size for best accuracy. "
            "TRT .engine files load via TensorRT for maximum FPS."
        ),
    },
    {
        "step": "6",
        "title": "Start the loop",
        "body": (
            "Press <b>Start</b> on the Status tab. "
            "Default aim key: <kbd>Mouse5</kbd>. "
            "Pause: <kbd>Pause/Break</kbd>. "
            "Overlay toggle: <kbd>Insert</kbd>. "
            "Exit: <kbd>F12</kbd>."
        ),
    },
]
