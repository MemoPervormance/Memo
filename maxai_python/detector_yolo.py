"""
YOLO ONNX / TensorRT detection engine.
Supports .onnx (DML/CUDA/CPU) and .engine (TensorRT) models.
Provider priority: TRT → CUDA → DML → CPU.
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def w(self) -> float:
        return self.x2 - self.x1

    @property
    def h(self) -> float:
        return self.y2 - self.y1

    def box(self) -> Tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2


# ---------------------------------------------------------------------------
# ORT runtime selection
# ---------------------------------------------------------------------------

def _select_ort_runtime() -> str:
    base = Path(sys.executable).parent
    gpu_dll = base / "onnxruntime_gpu.dll"
    std_dll = base / "onnxruntime.dll"
    cpu_dll = base / "onnxruntime_cpu.dll"

    cuda_path = os.environ.get("CUDA_PATH", "")
    has_cudnn = bool(cuda_path and list(Path(cuda_path, "bin").glob("cudnn*.dll")))

    if has_cudnn and gpu_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(gpu_dll)
        return "gpu"
    if std_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(std_dll)
        return "directml"
    if cpu_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(cpu_dll)
        return "cpu"
    return "default"


def _validate_model_file(model_path: str) -> None:
    """Raise a clear error if the file is not a valid ONNX/TRT model."""
    p = Path(model_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Model-Datei nicht gefunden: {model_path}\n"
            f"→ Lege eine echte .onnx Datei in den models\\ Ordner."
        )
    size = p.stat().st_size
    if size < 1024:
        raise ValueError(
            f"Model-Datei zu klein ({size} Bytes): {p.name}\n"
            f"→ Das ist kein echtes trainiertes Model. Lege eine gültige .onnx Datei ab.\n"
            f"→ Placeholder-Dateien aus der ZIP funktionieren nicht — du brauchst ein trainiertes Model."
        )
    if p.suffix == ".onnx":
        # ONNX files start with valid protobuf — first byte is 0x0A or 0x08 or similar field tags
        with open(p, "rb") as f:
            header = f.read(8)
        # Check it's not HTML (placeholder or download error)
        if header[:5] in (b"<!DOC", b"<html", b"<?xml", b"<HTML"):
            raise ValueError(
                f"Model-Datei ist HTML, kein ONNX: {p.name}\n"
                f"→ Der Download hat eine Webseite statt das Model gespeichert.\n"
                f"→ Lade das Model manuell herunter und lege es in models\\ ab."
            )
        if len(header) < 4:
            raise ValueError(f"Model-Datei ist leer oder beschädigt: {p.name}")


def _build_session(
    model_path: str,
    use_cuda: bool,
    use_tensorrt: bool,
    blob_size: int,
):
    """Create ORT InferenceSession with best available provider."""
    import onnxruntime as ort  # type: ignore[import]

    is_engine = model_path.lower().endswith(".engine")

    providers = []
    if use_tensorrt or is_engine:
        trt_opts = {
            "trt_engine_cache_enable": True,
            "trt_engine_cache_path": str(Path(model_path).parent),
            "trt_max_workspace_size": 1 << 30,
        }
        if is_engine:
            trt_opts["trt_engine_cache_path"] = str(Path(model_path).parent)
        providers.append(("TensorrtExecutionProvider", trt_opts))

    if use_cuda and not is_engine:
        providers.append("CUDAExecutionProvider")

    if not is_engine:
        providers.append("DmlExecutionProvider")

    providers.append("CPUExecutionProvider")

    available = ort.get_available_providers()
    selected: list = []
    for p in providers:
        name = p[0] if isinstance(p, tuple) else p
        if name in available:
            selected.append(p)
    if not selected:
        selected = ["CPUExecutionProvider"]

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(model_path, sess_options=opts, providers=selected)
    provider_used = selected[0][0] if isinstance(selected[0], tuple) else selected[0]
    return session, provider_used


# ---------------------------------------------------------------------------
# NMS
# ---------------------------------------------------------------------------

def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float) -> List[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        rest = order[1:]
        ix1 = np.maximum(x1[i], x1[rest])
        iy1 = np.maximum(y1[i], y1[rest])
        ix2 = np.minimum(x2[i], x2[rest])
        iy2 = np.minimum(y2[i], y2[rest])
        inter = np.maximum(0, ix2 - ix1) * np.maximum(0, iy2 - iy1)
        union = areas[i] + areas[rest] - inter
        iou   = np.where(union > 0, inter / union, 0.0)
        order = rest[iou <= iou_thresh]
    return keep


# ---------------------------------------------------------------------------
# YOLODetector
# ---------------------------------------------------------------------------

class YOLODetector:
    """ONNX/TRT YOLO detector — thread-safe single-threaded inference."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        max_detections: int = 10,
        use_cuda: bool = True,
        use_tensorrt: bool = False,
        blob_size: int = 320,
    ) -> None:
        self._conf_thresh = confidence_threshold
        self._nms_thresh  = nms_threshold
        self._max_det     = max_detections
        self._blob_size   = blob_size
        self._provider    = "none"
        self._input_name  = ""
        self._model_h     = blob_size
        self._model_w     = blob_size

        _select_ort_runtime()
        _validate_model_file(model_path)
        self._session, self._provider = _build_session(
            model_path, use_cuda, use_tensorrt, blob_size
        )
        meta = self._session.get_inputs()[0]
        self._input_name = meta.name
        shape = meta.shape
        if len(shape) == 4:
            h = shape[2]; w = shape[3]
            if isinstance(h, int) and h > 0:
                self._model_h = h
            else:
                self._model_h = blob_size
            if isinstance(w, int) and w > 0:
                self._model_w = w
            else:
                self._model_w = blob_size

        # Warmup
        dummy = np.zeros((1, 3, self._model_h, self._model_w), dtype=np.float32)
        for _ in range(3):
            self._session.run(None, {self._input_name: dummy})

    @property
    def provider(self) -> str:
        return self._provider

    def detect(
        self,
        frame_bgra: np.ndarray,
        offset_x: int = 0,
        offset_y: int = 0,
        target_classes: Optional[List[int]] = None,
    ) -> List[Detection]:
        tensor  = self._preprocess(frame_bgra)
        outputs = self._session.run(None, {self._input_name: tensor})
        return self._postprocess(outputs, offset_x, offset_y, target_classes or [])

    # ------------------------------------------------------------------

    def _preprocess(self, frame_bgra: np.ndarray) -> np.ndarray:
        h, w = frame_bgra.shape[:2]
        rgb   = frame_bgra[:, :, :3][:, :, ::-1]   # BGRA → RGB
        if h != self._model_h or w != self._model_w:
            try:
                from PIL import Image  # type: ignore[import]
                img = Image.fromarray(rgb).resize(
                    (self._model_w, self._model_h), Image.BILINEAR
                )
                rgb = np.array(img)
            except ImportError:
                ri = (np.arange(self._model_h) * h / self._model_h).astype(int)
                ci = (np.arange(self._model_w) * w / self._model_w).astype(int)
                rgb = rgb[ri][:, ci]
        t = rgb.astype(np.float32) / 255.0
        return np.ascontiguousarray(t.transpose(2, 0, 1)[np.newaxis])

    def _postprocess(
        self,
        outputs: list,
        ox: int, oy: int,
        target_classes: List[int],
    ) -> List[Detection]:
        raw = outputs[0]

        if raw.ndim == 3:
            data = raw[0] if raw.shape[1] > raw.shape[2] else raw[0].T
        else:
            return []

        if data.shape[1] < 5:
            return []

        n_extra = data.shape[1] - 4
        if n_extra == 1:
            obj  = data[:, 4]
            cls  = np.zeros(len(data), dtype=int)
            conf = obj
        else:
            obj   = data[:, 4]
            cls_s = data[:, 5:]
            cls   = cls_s.argmax(axis=1)
            conf  = obj * cls_s.max(axis=1)

        mask = conf >= self._conf_thresh
        data, cls, conf = data[mask], cls[mask], conf[mask]
        if len(data) == 0:
            return []

        cxs, cys, ws, hs = data[:, 0], data[:, 1], data[:, 2], data[:, 3]
        if cxs.max() <= 1.5:
            cxs = cxs * self._model_w
            cys = cys * self._model_h
            ws  = ws  * self._model_w
            hs  = hs  * self._model_h

        x1s = cxs - ws / 2
        y1s = cys - hs / 2
        x2s = cxs + ws / 2
        y2s = cys + hs / 2

        boxes = np.stack([x1s, y1s, x2s, y2s], axis=1)
        kept  = _nms(boxes, conf, self._nms_thresh)[: self._max_det]

        results: List[Detection] = []
        for i in kept:
            cid = int(cls[i])
            if target_classes and cid not in target_classes:
                continue
            results.append(Detection(
                x1=float(x1s[i]) + ox,
                y1=float(y1s[i]) + oy,
                x2=float(x2s[i]) + ox,
                y2=float(y2s[i]) + oy,
                confidence=float(conf[i]),
                class_id=cid,
            ))
        return results
