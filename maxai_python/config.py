"""Config management — TOML schema, load/save, live-reload, pydantic models."""
from __future__ import annotations
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

import toml
from pydantic import BaseModel, Field


class CaptureConfig(BaseModel):
    monitor: int = 0
    capture_size: int = 320
    fps_limit: int = 0
    steady_fps: int = 100


class PredictionConfig(BaseModel):
    enabled: bool = True
    lead_factor: float = 80.0
    min_speed: float = 30.0
    max_offset: float = 25.0
    lead_max_jump: float = 120.0


class AimConfig(BaseModel):
    enabled: bool = True
    aim_key: str = "mouse5"
    toggle_key: str = "f6"
    exit_key: str = "f12"
    fov_radius: float = 200.0
    aim_smoothness: float = 1.0
    aim_speed: float = 0.001
    head_from_top: float = 0.10
    snap_zone_px: float = 22.0
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)


class DetectionConfig(BaseModel):
    model_path: str = "model.onnx"
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.45
    target_classes: List[int] = Field(default_factory=list)
    priority_classes: List[int] = Field(default_factory=list)
    use_cuda: bool = True
    use_tensorrt: bool = False
    max_detections: int = 10


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
    min_confidence: float = 0.65
    crosshair_radius: float = 8.0
    min_frames: int = 3
    delay_ms: int = 30
    burst_ms: int = 80
    cooldown_ms: int = 120
    visibility_check: bool = True
    min_pixel_variance: float = 15.0
    sample_size: int = 5


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
    debug: DebugConfig = Field(default_factory=DebugConfig)
    info: InfoConfig = Field(default_factory=InfoConfig)


def _find_config_path() -> Path:
    # Priority: beside script, then %APPDATA%/maxai/
    local = Path(__file__).parent / "config.toml"
    if local.exists():
        return local
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        remote = Path(appdata) / "maxai" / "config.toml"
        if remote.exists():
            return remote
    return local  # default write location


def _parse_capture_size_from_model(model_path: str) -> Optional[int]:
    """Parse capture size from model filename, e.g. model_320.onnx → 320."""
    import re
    name = Path(model_path).stem
    m = re.search(r"_(\d+)$", name)
    if m:
        return int(m.group(1))
    return None


def load_config(path: Optional[Path] = None) -> AppConfig:
    p = path or _find_config_path()
    if not p.exists():
        cfg = AppConfig()
        return cfg
    raw = toml.load(str(p))
    cfg = AppConfig.model_validate(raw)
    # Auto-detect capture_size from model filename
    auto_size = _parse_capture_size_from_model(cfg.detection.model_path)
    if auto_size and auto_size != cfg.capture.capture_size:
        cfg.capture.capture_size = auto_size
    return cfg


def save_config(cfg: AppConfig, path: Optional[Path] = None) -> None:
    p = path or _find_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump()
    with open(p, "w", encoding="utf-8") as f:
        toml.dump(data, f)


class ConfigManager:
    """Thread-safe live-reloading config manager."""

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
