"""
Config management — full product spec schema with Pydantic + TOML.
Supports Game Profiles, all capture/input backends, predictions, overlay, recoil, wind-mouse.
"""
from __future__ import annotations
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

import toml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class CaptureConfig(BaseModel):
    backend: str = "dxgi"         # dxgi / winrt / capture_card / udp / ndi
    monitor: int = 0
    capture_size: int = 320       # blob size: 160 / 320 / 640
    fps_limit: int = 0
    steady_fps: int = 100
    circle_mask: bool = False
    # UDP capture
    udp_host: str = "0.0.0.0"
    udp_port: int = 9999
    # NDI
    ndi_source: str = ""
    # Capture card (DirectShow source name)
    capture_card_source: str = ""


class PredictionConfig(BaseModel):
    enabled: bool = True
    lead_factor: float = 80.0
    min_speed: float = 30.0
    max_offset: float = 25.0
    lead_max_jump: float = 120.0
    interval: float = 0.0         # 0.00–0.50 s lookahead step
    future_positions: int = 5     # 1–40 dots to project


class RecoilConfig(BaseModel):
    enabled: bool = False
    strength: float = 1.0         # 0.1–10.0
    smoothness: float = 2.0


class WindMouseConfig(BaseModel):
    enabled: bool = False
    gravity: float = 9.0
    wind: float = 3.0
    min_wait: float = 2.0
    max_wait: float = 10.0
    max_step: float = 8.0
    target_area: float = 8.0


class StickyTargetConfig(BaseModel):
    enabled: bool = False
    hold_duration: float = 1.5    # seconds before switching target
    static_filter: bool = False   # ignore stationary targets


class AimConfig(BaseModel):
    enabled: bool = True
    aim_key: str = "mouse5"
    toggle_key: str = "f6"
    exit_key: str = "f12"
    pause_key: str = "pause"
    overlay_key: str = "insert"
    screenshot_key: str = "f8"

    position: str = "head"        # head / body
    fov_x: float = 60.0          # 10–120
    fov_y: float = 60.0
    speed: float = 1.0            # 0.1–3.0
    auto_aim: bool = False
    auto_shoot: bool = False
    snap_radius: float = 22.0
    near_radius: float = 80.0
    scope_multiplier: float = 1.0

    head_from_top: float = 0.10
    smoothness: float = 1.0
    aim_speed: float = 0.001

    sticky_target: StickyTargetConfig = Field(default_factory=StickyTargetConfig)
    prediction: PredictionConfig   = Field(default_factory=PredictionConfig)
    recoil: RecoilConfig           = Field(default_factory=RecoilConfig)
    wind_mouse: WindMouseConfig    = Field(default_factory=WindMouseConfig)


class DetectionConfig(BaseModel):
    backend: str = "dml"           # dml / trt
    model_path: str = "model.onnx"
    confidence_threshold: float = 0.5   # 0.10–1.0
    nms_threshold: float = 0.45
    target_classes: List[int] = Field(default_factory=list)
    priority_classes: List[int] = Field(default_factory=list)
    use_cuda: bool = True
    use_tensorrt: bool = False
    max_detections: int = 10
    blob_size: int = 320           # 160 / 320 / 640


class ControllerConfig(BaseModel):
    stick_sensitivity: float = 0.75
    stick_deadzone_px: float = 1.0
    stick_smoothing: float = 0.35
    stick_acceleration: float = 1.4
    stick_y_invert: bool = True
    stick_x_invert: bool = False
    rs_min_magnitude: float = 0.16
    lt_while_aim: bool = False


class CrosshairConfig(BaseModel):
    offset_x: float = 0.0
    offset_y: float = 0.0
    parallax_x: float = 0.0
    parallax_y: float = 0.0


class TriggerbotConfig(BaseModel):
    enabled: bool = False
    trigger_key: str = "mouse4"
    confidence_threshold: float = 0.65
    crosshair_radius: float = 8.0
    min_frames: int = 3
    fire_delay_ms: int = 30
    burst_frames: int = 3
    cooldown_ms: int = 120
    color_check: bool = True
    min_pixel_variance: float = 15.0
    sample_size: int = 5


class OverlayConfig(BaseModel):
    enabled: bool = False
    detection_boxes: bool = True
    box_color: str = "#FF0000"     # hex
    box_thickness: int = 2
    future_dots: bool = False
    future_dot_color: str = "#00FF00"
    capture_border: bool = False
    target_icons: bool = False
    target_icon_path: str = ""
    opacity: float = 0.8


class GameProfileConfig(BaseModel):
    name: str
    sensitivity: float = 1.0
    yaw: float = 0.022             # deg/count
    pitch: float = 0.022
    fov_scale: float = 1.0
    aim: AimConfig = Field(default_factory=AimConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    triggerbot: TriggerbotConfig = Field(default_factory=TriggerbotConfig)
    overlay: OverlayConfig = Field(default_factory=OverlayConfig)


class InputConfig(BaseModel):
    backend: str = "relative_mouse"
    # relative_mouse / virtual_gamepad / kernel_driver /
    # ghub / arduino / kmbox_net / makcu / rp2040 / rp2350 / titan_two

    # Serial backends (arduino / makcu / rp2040 / rp2350)
    serial_port: str = "COM3"
    serial_baud: int = 115200

    # KMBOX Net
    kmbox_ip: str = "192.168.2.188"
    kmbox_port: int = 1408

    # G-Hub (Logitech)
    ghub_port: int = 12010

    # Kernel driver
    driver_path: str = r"\\.\CroixAIDriver"


class DebugConfig(BaseModel):
    show_fps: bool = False
    show_detections: bool = False
    verbose: bool = False


class InfoConfig(BaseModel):
    discord_rpc: bool = True


class AppConfig(BaseModel):
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    aim: AimConfig = Field(default_factory=AimConfig)
    controller: ControllerConfig = Field(default_factory=ControllerConfig)
    crosshair: CrosshairConfig = Field(default_factory=CrosshairConfig)
    triggerbot: TriggerbotConfig = Field(default_factory=TriggerbotConfig)
    overlay: OverlayConfig = Field(default_factory=OverlayConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    info: InfoConfig = Field(default_factory=InfoConfig)
    active_profile: str = "default"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _find_config_path() -> Path:
    local = Path(__file__).parent / "config.toml"
    if local.exists():
        return local
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        remote = Path(appdata) / "croixai" / "config.toml"
        if remote.exists():
            return remote
    return local


def _parse_capture_size_from_model(model_path: str) -> Optional[int]:
    m = re.search(r"_(\d+)(?:\.onnx|\.engine)$", Path(model_path).name)
    return int(m.group(1)) if m else None


def load_config(path: Optional[Path] = None) -> AppConfig:
    p = path or _find_config_path()
    if not p.exists():
        return AppConfig()
    raw = toml.load(str(p))
    cfg = AppConfig.model_validate(raw)
    auto_size = _parse_capture_size_from_model(cfg.detection.model_path)
    if auto_size and auto_size != cfg.capture.capture_size:
        cfg.capture.capture_size = auto_size
    return cfg


def save_config(cfg: AppConfig, path: Optional[Path] = None) -> None:
    p = path or _find_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        toml.dump(cfg.model_dump(), f)


# ---------------------------------------------------------------------------
# Game Profile Manager
# ---------------------------------------------------------------------------

class ProfileManager:
    """
    Manages named game profiles stored as separate TOML files in profiles/ dir.
    Each profile overrides aim/detection/triggerbot/overlay per game.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._dir = (base_dir or Path(__file__).parent) / "profiles"
        self._dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._profiles: Dict[str, GameProfileConfig] = {}
        self._active = "default"
        self._load_all()

    def _load_all(self) -> None:
        for f in self._dir.glob("*.toml"):
            try:
                raw = toml.load(str(f))
                name = f.stem
                raw.setdefault("name", name)
                self._profiles[name] = GameProfileConfig.model_validate(raw)
            except Exception:
                pass
        if "default" not in self._profiles:
            self._profiles["default"] = GameProfileConfig(name="default")

    def list_profiles(self) -> List[str]:
        with self._lock:
            return sorted(self._profiles.keys())

    def get(self, name: str) -> Optional[GameProfileConfig]:
        with self._lock:
            return self._profiles.get(name)

    def get_active(self) -> GameProfileConfig:
        with self._lock:
            return self._profiles.get(self._active, GameProfileConfig(name="default"))

    def switch(self, name: str) -> bool:
        with self._lock:
            if name not in self._profiles:
                return False
            self._active = name
            return True

    def create(self, name: str) -> GameProfileConfig:
        with self._lock:
            if name in self._profiles:
                return self._profiles[name]
            p = GameProfileConfig(name=name)
            self._profiles[name] = p
            self._save_profile(p)
            return p

    def save_profile(self, profile: GameProfileConfig) -> None:
        with self._lock:
            self._profiles[profile.name] = profile
            self._save_profile(profile)

    def delete(self, name: str) -> bool:
        if name == "default":
            return False
        with self._lock:
            if name not in self._profiles:
                return False
            del self._profiles[name]
            f = self._dir / f"{name}.toml"
            if f.exists():
                f.unlink()
            if self._active == name:
                self._active = "default"
            return True

    def _save_profile(self, profile: GameProfileConfig) -> None:
        f = self._dir / f"{profile.name}.toml"
        with open(f, "w", encoding="utf-8") as fh:
            toml.dump(profile.model_dump(), fh)

    @property
    def active_name(self) -> str:
        return self._active


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _find_config_path()
        self._lock = threading.RLock()
        self._cfg = load_config(self._path)
        self._mtime: float = self._path.stat().st_mtime if self._path.exists() else 0.0

    def get(self) -> AppConfig:
        with self._lock:
            return self._cfg

    def reload_if_changed(self) -> bool:
        if not self._path.exists():
            return False
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return False
        if mtime != self._mtime:
            self._mtime = mtime
            with self._lock:
                self._cfg = load_config(self._path)
            return True
        return False

    def update(self, partial: dict) -> AppConfig:
        with self._lock:
            current = self._cfg.model_dump()
            _deep_merge(current, partial)
            self._cfg = AppConfig.model_validate(current)
            save_config(self._cfg, self._path)
            return self._cfg

    def save(self) -> None:
        with self._lock:
            save_config(self._cfg, self._path)

    @property
    def path(self) -> Path:
        return self._path


def _deep_merge(base: dict, overlay: dict) -> None:
    for k, v in overlay.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
