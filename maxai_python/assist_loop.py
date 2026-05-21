"""
Assist loop — runs in a dedicated thread.

Frame cycle:
  capture → detect → align → trigger → input
"""
from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config import AppConfig, ConfigManager
from capture_dxgi import DXGICapture, screen_size
from detector_yolo import YOLODetector, Detection
from aligner import CrosshairAligner
from auto_fire import AutoFireModule
from input_backends import InputBackend
import hotkeys

logger = logging.getLogger("maxai.loop")


@dataclass
class SharedState:
    """Thread-safe state shared between assist loop and web server."""
    running: bool = False
    enabled: bool = True
    fps: float = 0.0
    detection_count: int = 0
    aim_active: bool = False
    status_text: str = "Idle"
    model_path: str = ""
    model_found: bool = False
    error: str = ""
    provider: str = "none"
    tunnel_url: Optional[str] = None
    input_backend_name: str = "relative_mouse"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running":          self.running,
                "enabled":          self.enabled,
                "fps":              round(self.fps, 1),
                "detection_count":  self.detection_count,
                "aim_active":       self.aim_active,
                "status_text":      self.status_text,
                "model_path":       self.model_path,
                "model_found":      self.model_found,
                "error":            self.error,
                "provider":         self.provider,
                "tunnel_url":       self.tunnel_url,
                "input_backend":    self.input_backend_name,
            }

    def set(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)


class AssistLoop:
    """Manages the main per-frame processing loop in a background thread."""

    def __init__(
        self,
        state: SharedState,
        config_mgr: ConfigManager,
        backend: InputBackend,
        backend_name: str,
    ) -> None:
        self._state      = state
        self._cfg_mgr    = config_mgr
        self._backend    = backend
        self._thread: Optional[threading.Thread] = None
        self._stop_flag  = threading.Event()
        state.input_backend_name = backend_name

    def start(self) -> bool:
        if self._state.running:
            return False
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="assist-loop"
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._backend.release_all()
        self._state.set(running=False, aim_active=False, status_text="Stopped")

    # ------------------------------------------------------------------

    def _run(self) -> None:
        self._state.set(running=True, status_text="Initialising…", error="")
        cfg = self._cfg_mgr.get()

        # Model
        model_path = self._resolve_model(cfg.detection.model_path)
        self._state.set(model_path=str(model_path), model_found=model_path.exists())

        if not model_path.exists():
            self._state.set(
                running=False,
                status_text="Error",
                error=f"Model not found: {model_path}",
            )
            logger.error(f"Model not found: {model_path}")
            return

        # Detector
        try:
            detector = YOLODetector(
                model_path=str(model_path),
                confidence_threshold=cfg.detection.confidence_threshold,
                nms_threshold=cfg.detection.nms_threshold,
                max_detections=cfg.detection.max_detections,
                use_cuda=cfg.detection.use_cuda,
                use_tensorrt=cfg.detection.use_tensorrt,
            )
            self._state.set(provider=detector.provider)
            logger.info(f"Provider: {detector.provider}")
        except Exception as exc:
            self._state.set(running=False, status_text="Error", error=str(exc))
            logger.error(f"Detector init failed: {exc}")
            return

        # Capture
        capture = DXGICapture(
            monitor=cfg.capture.monitor,
            capture_size=cfg.capture.capture_size,
        )

        # Sub-systems
        aligner = CrosshairAligner(cfg.aim, cfg.controller, cfg.crosshair)
        trigger = AutoFireModule(cfg.triggerbot)

        # Screen geometry
        sw, sh     = screen_size()
        cap_size   = cfg.capture.capture_size
        cap_off_x  = sw // 2 - cap_size // 2
        cap_off_y  = sh // 2 - cap_size // 2
        screen_cx  = float(sw // 2)
        screen_cy  = float(sh // 2)

        # FPS tracking
        fps_counter  = 0
        fps_timer    = time.monotonic()
        frame_index  = 0
        enabled      = cfg.aim.enabled

        self._state.set(status_text="Running")
        logger.info("Assist loop started.")

        while not self._stop_flag.is_set():
            # --- Exit key ---
            if hotkeys.is_pressed(cfg.aim.exit_key):
                logger.info("Exit key pressed.")
                break

            # --- FPS ---
            fps_counter += 1
            now = time.monotonic()
            if now - fps_timer >= 1.0:
                self._state.set(fps=fps_counter / (now - fps_timer))
                fps_counter = 0
                fps_timer   = now

            # --- Live config reload every 15 frames ---
            frame_index += 1
            if frame_index % 15 == 0:
                if self._cfg_mgr.reload_if_changed():
                    cfg = self._cfg_mgr.get()
                    cap_size  = cfg.capture.capture_size
                    cap_off_x = sw // 2 - cap_size // 2
                    cap_off_y = sh // 2 - cap_size // 2
                    aligner.update_config(cfg.aim, cfg.controller, cfg.crosshair)
                    trigger.update_config(cfg.triggerbot)
                    detector._conf_thresh = cfg.detection.confidence_threshold
                    detector._nms_thresh  = cfg.detection.nms_threshold
                    detector._max_det     = cfg.detection.max_detections

            # --- Toggle ---
            if hotkeys.was_pressed(cfg.aim.toggle_key):
                enabled = not enabled
                self._state.set(enabled=enabled)

            # --- Capture ---
            frame = capture.grab()
            if frame is None:
                time.sleep(0.002)
                continue

            # --- Detect ---
            detections: List[Detection] = detector.detect(
                frame,
                offset_x=cap_off_x,
                offset_y=cap_off_y,
                target_classes=cfg.detection.target_classes or None,
            )
            self._state.set(detection_count=len(detections))

            # --- Assist key ---
            assist_active = enabled and hotkeys.is_pressed(cfg.aim.aim_key)
            self._state.set(aim_active=assist_active)

            # --- Trigger ---
            trig_result = {"should_fire": False}
            if cfg.triggerbot.enabled and hotkeys.is_pressed(cfg.triggerbot.trigger_key):
                result = trigger.update(
                    detections, screen_cx, screen_cy,
                    frame_bgra=frame,
                    crop_offset=(cap_off_x, cap_off_y),
                )
                trig_result = {"should_fire": result.should_fire}
            else:
                trigger.reset()

            # --- Align + move ---
            if not assist_active:
                aligner.reset()
                self._backend.release_all()
            else:
                if detections:
                    dx, dy = aligner.update(
                        detections, screen_cx, screen_cy,
                        priority_classes=cfg.detection.priority_classes or None,
                        target_classes=cfg.detection.target_classes or None,
                    )
                    self._backend.move_cursor(dx, dy)

                # ADS (lt_while_aim)
                if cfg.controller.lt_while_aim:
                    self._backend.press_ads()
                else:
                    self._backend.release_ads()

            # --- Fire ---
            self._backend.set_fire(trig_result["should_fire"])
            self._backend.flush()

            # --- Steady FPS ---
            if cfg.capture.steady_fps > 0:
                target_dt = 1.0 / cfg.capture.steady_fps
                elapsed = time.monotonic() - now
                remaining = target_dt - elapsed
                if remaining > 0:
                    time.sleep(remaining)

        # Cleanup
        self._backend.release_all()
        self._state.set(
            running=False, aim_active=False, fps=0.0,
            detection_count=0, status_text="Idle",
        )
        logger.info("Assist loop stopped.")

    @staticmethod
    def _resolve_model(model_path: str) -> Path:
        p = Path(model_path)
        if p.is_absolute():
            return p
        # Relative to script dir
        script_dir = Path(__file__).parent
        return script_dir / p
