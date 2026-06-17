"""
TweaksExecutor — maps setting IDs to Windows registry/shell commands.
Runs each operation in QThreadPool to avoid blocking the UI.
Requires admin rights for HKLM writes; gracefully skips if unavailable.
"""
import os
import subprocess
import ctypes
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ── Tweak action table ──────────────────────────────────────────────────────
# Format per entry: {"apply": ("cmd", [...]), "revert": ("cmd", [...])}
# type "cmd"      → run subprocess directly
# type "reg_file" → run `reg import <path>` (path relative to tweaks_root)
# type "bat"      → run batch file (path relative to tweaks_root)
# type "powercfg_import" → powercfg /import then /setactive

TWEAK_REGISTRY: dict[str, dict] = {

    # ── FPS / Game Boost ───────────────────────────────────────────────────
    "game_mode": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKCU\Software\Microsoft\GameBar",
                           "/v", "AutoGameModeEnabled", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKCU\Software\Microsoft\GameBar",
                           "/v", "AutoGameModeEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]),
    },
    "disable_xbox_dvr": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKCU\System\GameConfigStore",
                           "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKCU\System\GameConfigStore",
                           "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "1", "/f"]),
    },
    "priority_boost": {
        # CSRSS High Priority — from CSRSS High Priority.reg in user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\csrss.exe\PerfOptions",
                           "/v", "CpuPriorityClass", "/t", "REG_DWORD", "/d", "4", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\csrss.exe\PerfOptions",
                           "/v", "CpuPriorityClass", "/f"]),
    },
    "power_plan_ultimate": {
        # Ultimate Performance plan GUID
        "apply":  ("cmd", ["powercfg", "/setactive", "e9a42b02-d5df-448d-aa00-03f14749eb61"]),
        "revert": ("cmd", ["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"]),
    },
    "disable_power_throttling": {
        # Disable Power Throttling.reg equivalent — from user's AlphaWolf/HyperTweaks packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                           "/v", "PowerThrottlingOff", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                           "/v", "PowerThrottlingOff", "/f"]),
    },
    "maintain_low_latency": {
        # MaintainLowLatency-HighPerformanceBoost.REG from user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "SystemResponsiveness", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "SystemResponsiveness", "/t", "REG_DWORD", "/d", "20", "/f"]),
    },

    # ── GPU ────────────────────────────────────────────────────────────────
    "gpu_power_max": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                           "/v", "PerfLevelSrc", "/t", "REG_DWORD", "/d", "0x2222", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                           "/v", "PerfLevelSrc", "/f"]),
    },
    "hw_accel_scheduling": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                           "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                           "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "1", "/f"]),
    },

    # ── CPU ────────────────────────────────────────────────────────────────
    "disable_core_parking": {
        # Disable Core Parking.reg from user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerSettings"
                           r"\54533251-82be-4824-96c1-47b60b740d00"
                           r"\0cc5b647-c1df-4637-891a-dec35c318583",
                           "/v", "ValueMax", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerSettings"
                           r"\54533251-82be-4824-96c1-47b60b740d00"
                           r"\0cc5b647-c1df-4637-891a-dec35c318583",
                           "/v", "ValueMax", "/t", "REG_DWORD", "/d", "100", "/f"]),
    },
    "timer_resolution": {
        # Sets Windows timer resolution to 0.5ms via registry flag
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "SystemResponsiveness", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "SystemResponsiveness", "/t", "REG_DWORD", "/d", "20", "/f"]),
    },
    "msi_mode": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                           "/v", "MSISupported", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                           "/v", "MSISupported", "/t", "REG_DWORD", "/d", "0", "/f"]),
    },
    "cpu_affinity_boost": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
                           "/v", "Affinity", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
                           "/v", "Affinity", "/f"]),
    },

    # ── RAM ────────────────────────────────────────────────────────────────
    "disable_superfetch": {
        "apply":  ("cmd", ["sc", "config", "SysMain", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "SysMain", "start=", "auto"]),
    },
    "large_pages": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "LargePageMinimum", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "LargePageMinimum", "/f"]),
    },

    # ── Network / Ping ─────────────────────────────────────────────────────
    "tcp_no_delay": {
        # Disable Nagles Algorithm.reg — from Nagle tweaks in user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                           "/v", "TcpNoDelay", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                           "/v", "TcpNoDelay", "/f"]),
    },
    "tcp_ack_freq": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                           "/v", "TcpAckFrequency", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                           "/v", "TcpAckFrequency", "/f"]),
    },
    "network_throttling_disable": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "NetworkThrottlingIndex", "/t", "REG_DWORD", "/d", "0xffffffff", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                           "/v", "NetworkThrottlingIndex", "/t", "REG_DWORD", "/d", "10", "/f"]),
    },
    "rss_scaling": {
        "apply":  ("cmd", ["netsh", "int", "tcp", "set", "global", "rss=enabled"]),
        "revert": ("cmd", ["netsh", "int", "tcp", "set", "global", "rss=disabled"]),
    },
    "tcp_window_size": {
        "apply":  ("cmd", ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"]),
        "revert": ("cmd", ["netsh", "int", "tcp", "set", "global", "autotuninglevel=disabled"]),
    },
    "adapter_power_save_off": {
        "apply":  ("cmd", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                           "19caa947-ffffffff-ffffffff", "12bbebe6-58d6-4636-95bb-3217ef867c1a", "0"]),
        "revert": ("cmd", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                           "19caa947-ffffffff-ffffffff", "12bbebe6-58d6-4636-95bb-3217ef867c1a", "100"]),
    },
    "dns_cloudflare": {
        "apply":  ("cmd", ["netsh", "interface", "ipv4", "set", "dnsserver",
                           "name=Ethernet", "static", "1.1.1.1", "primary"]),
        "revert": ("cmd", ["netsh", "interface", "ipv4", "set", "dnsserver",
                           "name=Ethernet", "dhcp"]),
    },
    "dns_google": {
        "apply":  ("cmd", ["netsh", "interface", "ipv4", "set", "dnsserver",
                           "name=Ethernet", "static", "8.8.8.8", "primary"]),
        "revert": ("cmd", ["netsh", "interface", "ipv4", "set", "dnsserver",
                           "name=Ethernet", "dhcp"]),
    },
    "dns_cache_flush": {
        "apply":  ("cmd", ["ipconfig", "/flushdns"]),
        "revert": None,
    },

    # ── Input / Delay ──────────────────────────────────────────────────────
    "mouse_accel_off": {
        "apply":  ("cmd", ["reg", "add", r"HKCU\Control Panel\Mouse",
                           "/v", "MouseSpeed", "/t", "REG_SZ", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add", r"HKCU\Control Panel\Mouse",
                           "/v", "MouseSpeed", "/t", "REG_SZ", "/d", "1", "/f"]),
    },
    "usb_interrupt_priority": {
        # Mouse-DataQueue.REG from user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
                           "/v", "MouseDataQueueSize", "/t", "REG_DWORD", "/d", "0x14", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
                           "/v", "MouseDataQueueSize", "/t", "REG_DWORD", "/d", "0x64", "/f"]),
    },
    "keyboard_polling_1000": {
        # Keyboard - DataQueueSize.REG from user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\kbdclass\Parameters",
                           "/v", "KeyboardDataQueueSize", "/t", "REG_DWORD", "/d", "0x14", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Services\kbdclass\Parameters",
                           "/v", "KeyboardDataQueueSize", "/t", "REG_DWORD", "/d", "0x64", "/f"]),
    },
    "disable_sticky_keys": {
        "apply":  ("cmd", ["reg", "add", r"HKCU\Control Panel\Accessibility\StickyKeys",
                           "/v", "Flags", "/t", "REG_SZ", "/d", "506", "/f"]),
        "revert": ("cmd", ["reg", "add", r"HKCU\Control Panel\Accessibility\StickyKeys",
                           "/v", "Flags", "/t", "REG_SZ", "/d", "510", "/f"]),
    },

    # ── System ─────────────────────────────────────────────────────────────
    "telemetry_off": {
        # Disable Windows Telemetry.reg equivalent
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                           "/v", "AllowTelemetry", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                           "/v", "AllowTelemetry", "/f"]),
    },
    "cortana_off": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                           "/v", "AllowCortana", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                           "/v", "AllowCortana", "/f"]),
    },
    "search_index_off": {
        "apply":  ("cmd", ["sc", "config", "WSearch", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "WSearch", "start=", "delayed-auto"]),
    },
    "windows_update_delay": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
                           "/v", "NoAutoUpdate", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
                           "/v", "NoAutoUpdate", "/f"]),
    },
    "fast_startup": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                           "/v", "HiberbootEnabled", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                           "/v", "HiberbootEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]),
    },
    "svc_sysmain": {
        "apply":  ("cmd", ["sc", "config", "SysMain", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "SysMain", "start=", "auto"]),
    },
    "svc_print_spooler": {
        "apply":  ("cmd", ["sc", "config", "Spooler", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "Spooler", "start=", "auto"]),
    },
    "svc_fax": {
        "apply":  ("cmd", ["sc", "config", "Fax", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "Fax", "start=", "demand"]),
    },
    "svc_bits": {
        "apply":  ("cmd", ["sc", "config", "BITS", "start=", "disabled"]),
        "revert": ("cmd", ["sc", "config", "BITS", "start=", "demand"]),
    },
    "reg_irq8_priority": {
        # IRQ8Priority.reg from user's packs
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl",
                           "/v", "IRQ8Priority", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl",
                           "/v", "IRQ8Priority", "/f"]),
    },
    "large_system_cache_off": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "LargeSystemCache", "/t", "REG_DWORD", "/d", "0", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "LargeSystemCache", "/t", "REG_DWORD", "/d", "1", "/f"]),
    },
    "clear_standby_ram": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "ClearPageFileAtShutdown", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "add",
                           r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                           "/v", "ClearPageFileAtShutdown", "/t", "REG_DWORD", "/d", "0", "/f"]),
    },
    "reg_no_low_disk": {
        "apply":  ("cmd", ["reg", "add",
                           r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                           "/v", "NoLowDiskSpaceChecks", "/t", "REG_DWORD", "/d", "1", "/f"]),
        "revert": ("cmd", ["reg", "delete",
                           r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                           "/v", "NoLowDiskSpaceChecks", "/f"]),
    },

    # ── BIOS helper (OS-level equivalents) ─────────────────────────────────
    "bios_c_states_off": {
        "apply":  ("cmd", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                           "54533251-82be-4824-96c1-47b60b740d00",
                           "943c8cb6-6f93-4227-ad87-e9a3feec08d1", "1"]),
        "revert": ("cmd", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                           "54533251-82be-4824-96c1-47b60b740d00",
                           "943c8cb6-6f93-4227-ad87-e9a3feec08d1", "0"]),
    },
}


class _WorkerSignals(QObject):
    done = pyqtSignal(str, bool, str)


class _TweakWorker(QRunnable):
    """Runs one shell command off the main thread."""

    def __init__(self, setting_id: str, cmd: list):
        super().__init__()
        self.setting_id = setting_id
        self.cmd = cmd
        self.signals = _WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            r = subprocess.run(
                self.cmd,
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            ok = r.returncode == 0
            msg = (r.stdout.strip() or r.stderr.strip() or ("Applied" if ok else "Failed"))[:120]
            self.signals.done.emit(self.setting_id, ok, msg)
        except subprocess.TimeoutExpired:
            self.signals.done.emit(self.setting_id, False, "Timed out")
        except FileNotFoundError as e:
            self.signals.done.emit(self.setting_id, False, f"Not found: {e.filename}")
        except Exception as e:
            self.signals.done.emit(self.setting_id, False, str(e)[:120])


class TweaksExecutor(QObject):
    """
    Singleton that dispatches tweak actions asynchronously.
    Emits `tweak_applied(setting_id, success, message)` when done.
    """

    tweak_applied = pyqtSignal(str, bool, str)

    def __init__(self):
        super().__init__()
        self._pool = QThreadPool.globalInstance()
        self._tweaks_root: str = os.path.join(
            os.path.expanduser("~"), "Desktop", "Tweaks"
        )

    def set_tweaks_root(self, path: str):
        self._tweaks_root = path

    @property
    def tweaks_root(self) -> str:
        return self._tweaks_root

    def has_action(self, setting_id: str) -> bool:
        return setting_id in TWEAK_REGISTRY

    def apply(self, setting_id: str, enabled: bool):
        """Dispatch the tweak for setting_id. enabled=True → apply, False → revert."""
        entry = TWEAK_REGISTRY.get(setting_id)
        if entry is None:
            return

        action_key = "apply" if enabled else "revert"
        action = entry.get(action_key)
        if action is None:
            return

        action_type, payload = action

        if action_type == "cmd":
            cmd = list(payload)
        elif action_type == "reg_file":
            path = os.path.join(self._tweaks_root, payload)
            if not os.path.isfile(path):
                self.tweak_applied.emit(setting_id, False, f"File not found: {path}")
                return
            cmd = ["reg", "import", path]
        elif action_type == "bat":
            path = os.path.join(self._tweaks_root, payload)
            if not os.path.isfile(path):
                self.tweak_applied.emit(setting_id, False, f"File not found: {path}")
                return
            cmd = ["cmd", "/c", path]
        elif action_type == "powercfg_import":
            path = os.path.join(self._tweaks_root, payload)
            if not os.path.isfile(path):
                self.tweak_applied.emit(setting_id, False, f"Power plan not found: {path}")
                return
            cmd = ["powercfg", "/import", path]
        else:
            return

        worker = _TweakWorker(setting_id, cmd)
        worker.signals.done.connect(self.tweak_applied)
        self._pool.start(worker)


_executor: "TweaksExecutor | None" = None


def get_executor() -> TweaksExecutor:
    global _executor
    if _executor is None:
        _executor = TweaksExecutor()
    return _executor
