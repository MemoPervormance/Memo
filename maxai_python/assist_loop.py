"""
Assist loop — main per-frame processing thread.
Integrates all backends, predictions, recoil, wind mouse, overlay, game profiles.
"""
from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config import AppConfig, ConfigManager, ProfileManager
from capture_backends import create_capture, CaptureBackend
from detector_yolo import YOLODetector, Detection
from aligner import CrosshairAligner
from auto_fire import AutoFireModule
from recoil import RecoilCompensator
from overlay import OverlayWindow
from input_backends import InputBackend
import hotkeys

logger = logging.getLogger("maxai.loop")


@dataclass
class SharedState:
    running: bool = False
    enabled: bool = True
    paused: bool = False
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
    capture_backend_name: str = "dxgi"
    active_profile: str = "default"
    overlay_visible: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running":          self.running,
                "enabled":          self.enabled,
                "paused":           self.paused,
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
                "capture_backend":  self.capture_backend_name,
                "active_profile":   self.active_profile,
                "overlay_visible":  self.overlay_visible,
            }

    def set(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)


class AssistLoop:
    def __init__(
        self,
        state: SharedState,
        config_mgr: ConfigManager,
        profile_mgr: ProfileManager,
        backend: InputBackend,
        backend_name: str,
    ) -> None:
        self._state      = state
        self._cfg_mgr    = config_mgr
        self._prof_mgr   = profile_mgr
        self._backend    = backend
        self._thread: Optional[threading.Thread] = None
        self._stop_flag  = threading.Event()
        state.input_backend_name = backend_name

    def start(self) -> bool:
        if self._state.running:
            return False
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="assist-loop")
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

        # Resolve model
        model_path = _resolve_model(cfg.detection.model_path)
        self._state.set(model_path=str(model_path), model_found=model_path.exists())

        if not model_path.exists():
            msg = f"Model not found: {model_path}"
            self._state.set(running=False, status_text="Error", error=msg)
            logger.error(msg)
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
                blob_size=cfg.detection.blob_size,
            )
            self._state.set(provider=detector.provider)
            logger.info(f"Provider: {detector.provider}")
        except Exception as exc:
            self._state.set(running=False, status_text="Error", error=str(exc))
            logger.error(f"Detector init: {exc}")
            return

        # Capture
        try:
            capture: CaptureBackend = create_capture(cfg)
            self._state.set(capture_backend_name=cfg.capture.backend)
        except Exception as exc:
            self._state.set(running=False, status_text="Error", error=str(exc))
            logger.error(f"Capture init: {exc}")
            return

        # Sub-systems
        aligner  = CrosshairAligner(cfg.aim, cfg.controller, cfg.crosshair)
        trigger  = AutoFireModule(cfg.triggerbot)
        recoil   = RecoilCompensator(cfg.aim.recoil)
        overlay  = OverlayWindow(cfg.overlay)

        # Screen geometry
        import sys
        if sys.platform == "win32":
            import ctypes
            u = ctypes.windll.user32; u.SetProcessDPIAware()
            sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
        else:
            sw, sh = 1920, 1080

        cap_size  = cfg.capture.capture_size
        cap_off_x, cap_off_y = capture.crop_offset()
        screen_cx = float(sw // 2)
        screen_cy = float(sh // 2)

        fps_counter  = 0
        fps_timer    = time.monotonic()
        frame_index  = 0
        enabled      = cfg.aim.enabled
        paused       = False
        fire_held    = False

        # Auto-save timer
        last_save    = time.monotonic()
        AUTO_SAVE_S  = 30.0

        self._state.set(status_text="Running")
        logger.info("Assist loop started.")

        while not self._stop_flag.is_set():

            # --- Exit key ---
            if hotkeys.is_pressed(cfg.aim.exit_key):
                logger.info("Exit key pressed.")
                break

            # --- Pause key ---
            if hotkeys.was_pressed(cfg.aim.pause_key):
                paused = not paused
                self._state.set(paused=paused)

            # --- Overlay toggle ---
            if hotkeys.was_pressed(cfg.aim.overlay_key):
                cfg_overlay = cfg.overlay
                new_visible = not self._state.overlay_visible
                self._state.set(overlay_visible=new_visible)
                overlay.update_config(type(cfg_overlay)(
                    **{**cfg_overlay.model_dump(), "enabled": new_visible}
                ))

            # --- Screenshot ---
            if hotkeys.was_pressed(cfg.aim.screenshot_key):
                _take_screenshot()

            # --- FPS counter ---
            fps_counter += 1
            now = time.monotonic()
            if now - fps_timer >= 1.0:
                self._state.set(fps=fps_counter / (now - fps_timer))
                fps_counter = 0
                fps_timer   = now

            # --- Live config reload (F4 or file change, every 15 frames) ---
            frame_index += 1
            if frame_index % 15 == 0:
                if self._cfg_mgr.reload_if_changed():
                    cfg = self._cfg_mgr.get()
                    cap_size    = cfg.capture.capture_size
                    cap_off_x, cap_off_y = capture.crop_offset()
                    aligner.update_config(cfg.aim, cfg.controller, cfg.crosshair)
                    trigger.update_config(cfg.triggerbot)
                    recoil.update_config(cfg.aim.recoil)
                    overlay.update_config(cfg.overlay)
                    detector._conf_thresh = cfg.detection.confidence_threshold
                    detector._nms_thresh  = cfg.detection.nms_threshold
                    detector._max_det     = cfg.detection.max_detections

            # --- F4 force reload ---
            if hotkeys.was_pressed("f4"):
                cfg = self._cfg_mgr.get()

            # --- Toggle ---
            if hotkeys.was_pressed(cfg.aim.toggle_key):
                enabled = not enabled
                self._state.set(enabled=enabled)

            # --- Profile switch via active_profile in config ---
            active_profile = self._prof_mgr.active_name
            self._state.set(active_profile=active_profile)

            # Auto-save
            if now - last_save >= AUTO_SAVE_S:
                self._cfg_mgr.save()
                last_save = now

            if paused:
                self._backend.release_all()
                time.sleep(0.016)
                continue

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

            # --- Assist key / auto-aim ---
            assist_key_held = hotkeys.is_pressed(cfg.aim.aim_key)
            assist_active   = enabled and (assist_key_held or cfg.aim.auto_aim)
            self._state.set(aim_active=assist_active)

            # --- Auto-shoot / Trigger ---
            shoot_key_held = hotkeys.is_pressed(cfg.triggerbot.trigger_key)
            trig_should_fire = False
            if cfg.triggerbot.enabled and (shoot_key_held or cfg.aim.auto_shoot):
                result = trigger.update(
                    detections, screen_cx, screen_cy,
                    frame_bgra=frame,
                    crop_offset=(cap_off_x, cap_off_y),
                )
                trig_should_fire = result.should_fire
            else:
                trigger.reset()

            # --- Align + move ---
            if not assist_active:
                aligner.reset()
                recoil.reset()
                self._backend.release_all()
                fire_held = False
            else:
                dx, dy = 0, 0
                future_dots = []
                if detections:
                    scoped = hotkeys.is_pressed("mouse2")  # RMB = scoped
                    dx, dy = aligner.update(
                        detections, screen_cx, screen_cy,
                        priority_classes=cfg.detection.priority_classes or None,
                        target_classes=cfg.detection.target_classes or None,
                        scoped=scoped,
                    )
                    if cfg.aim.prediction.enabled and cfg.overlay.future_dots:
                        best = detections[0]
                        future_dots = aligner.get_future_dots(best)

                # Recoil compensation
                dy = recoil.apply(dy, fire_held)

                self._backend.move_cursor(dx, dy)

                # ADS
                if cfg.controller.lt_while_aim:
                    self._backend.press_ads()
                else:
                    self._backend.release_ads()

                # Update overlay
                if cfg.overlay.enabled:
                    overlay.update_frame(detections, future_dots)

            # --- Fire ---
            fire_held = trig_should_fire
            self._backend.set_fire(trig_should_fire)
            self._backend.flush()

            # --- Steady FPS ---
            if cfg.capture.steady_fps > 0:
                target_dt = 1.0 / cfg.capture.steady_fps
                elapsed   = time.monotonic() - now
                remaining = target_dt - elapsed
                if remaining > 0.001:
                    time.sleep(remaining)

        # Cleanup
        overlay.stop()
        self._backend.release_all()
        self._state.set(
            running=False, aim_active=False, fps=0.0,
            detection_count=0, status_text="Idle",
        )
        logger.info("Assist loop stopped.")


def _resolve_model(model_path: str) -> Path:
    p = Path(model_path)
    if p.is_absolute():
        return p
    return Path(__file__).parent / p


def _take_screenshot() -> None:
    try:
        import ctypes
        import datetime
        fname = Path(__file__).parent / f"screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
        try:
            from PIL import ImageGrab  # type: ignore[import]
            img = ImageGrab.grab()
            img.save(str(fname))
            logger.info(f"Screenshot saved: {fname}")
        except ImportError:
            pass
    except Exception as exc:
        logger.warning(f"Screenshot failed: {exc}")
