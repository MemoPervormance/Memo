"""YOLO ONNX detection engine — provider selection, preprocess, NMS, postprocess."""
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


def _select_ort_runtime() -> str:
    """Mirror Rust select_ort_runtime: prefer GPU DLL, fall back to CPU."""
    base = Path(sys.executable).parent
    gpu_dll   = base / "onnxruntime_gpu.dll"
    std_dll   = base / "onnxruntime.dll"
    cpu_dll   = base / "onnxruntime_cpu.dll"

    cuda_path = os.environ.get("CUDA_PATH", "")
    has_cuda_cudnn = False
    if cuda_path:
        cudnn_candidates = list(Path(cuda_path, "bin").glob("cudnn*.dll"))
        has_cuda_cudnn = bool(cudnn_candidates)

    if has_cuda_cudnn and gpu_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(gpu_dll)
        return "gpu"
    if std_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(std_dll)
        return "directml"
    if cpu_dll.exists():
        os.environ["ORT_DYLIB_PATH"] = str(cpu_dll)
        return "cpu"
    return "default"


def _build_session(model_path: str, use_cuda: bool, use_tensorrt: bool):
    """Create ORT InferenceSession with best available provider."""
    import onnxruntime as ort  # type: ignore[import]

    providers = []
    if use_tensorrt:
        providers.append("TensorrtExecutionProvider")
    if use_cuda:
        providers.append("CUDAExecutionProvider")
    providers.append("DmlExecutionProvider")
    providers.append("CPUExecutionProvider")

    available = ort.get_available_providers()
    selected = [p for p in providers if p in available]
    if not selected:
        selected = ["CPUExecutionProvider"]

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(model_path, sess_options=opts, providers=selected)
    return session, selected[0]


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float) -> List[int]:
    """Non-maximum suppression, returns kept indices."""
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
        iou = np.where(union > 0, inter / union, 0.0)
        order = rest[iou <= iou_thresh]
    return keep


class YOLODetector:
    """ONNX-based YOLO detector. Thread-safe for single-threaded inference."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        max_detections: int = 10,
        use_cuda: bool = True,
        use_tensorrt: bool = False,
    ) -> None:
        self._conf_thresh = confidence_threshold
        self._nms_thresh  = nms_threshold
        self._max_det     = max_detections
        self._provider    = "none"
        self._input_name: str = ""
        self._model_w = 640
        self._model_h = 640

        _select_ort_runtime()
        self._session, self._provider = _build_session(model_path, use_cuda, use_tensorrt)
        meta = self._session.get_inputs()[0]
        self._input_name = meta.name
        shape = meta.shape  # [1, 3, H, W] or similar
        if len(shape) == 4:
            self._model_h = int(shape[2]) if isinstance(shape[2], int) else 640
            self._model_w = int(shape[3]) if isinstance(shape[3], int) else 640

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
        """
        Run inference on a BGRA frame, return detections in screen coordinates.
        offset_x/y = crop top-left on screen.
        """
        tensor = self._preprocess(frame_bgra)
        outputs = self._session.run(None, {self._input_name: tensor})
        return self._postprocess(outputs, offset_x, offset_y, target_classes or [])

    # ------------------------------------------------------------------

    def _preprocess(self, frame_bgra: np.ndarray) -> np.ndarray:
        """BGR→RGB, resize to model dims, /255, CHW, batch dim."""
        h, w = frame_bgra.shape[:2]
        rgb = frame_bgra[:, :, :3][:, :, ::-1]  # BGRA → RGB (drop alpha, reverse channels)
        if h != self._model_h or w != self._model_w:
            # Simple resize via numpy (no cv2 dependency)
            try:
                from PIL import Image  # type: ignore[import]
                img = Image.fromarray(rgb).resize((self._model_w, self._model_h), Image.BILINEAR)
                rgb = np.array(img)
            except ImportError:
                # Nearest-neighbour fallback
                row_idx = (np.arange(self._model_h) * h / self._model_h).astype(int)
                col_idx = (np.arange(self._model_w) * w / self._model_w).astype(int)
                rgb = rgb[row_idx][:, col_idx]
        tensor = rgb.astype(np.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)[np.newaxis]  # (1,3,H,W)
        return np.ascontiguousarray(tensor)

    def _postprocess(
        self,
        outputs: list,
        ox: int, oy: int,
        target_classes: List[int],
    ) -> List[Detection]:
        raw = outputs[0]  # shape (1, N, 5+C) or (1, 5+C, N)

        if raw.ndim == 3:
            if raw.shape[1] > raw.shape[2]:
                # (1, N, 5+C) standard format
                data = raw[0]
            else:
                # (1, 5+C, N) transposed
                data = raw[0].T
        else:
            return []

        # data: (N, 5+C)  cols: cx, cy, w, h, obj, cls...
        if data.shape[1] < 5:
            return []

        # Determine if format is (cx,cy,w,h,obj,cls) or (cx,cy,w,h,cls_scores...)
        n_extra = data.shape[1] - 4
        if n_extra == 1:
            # Only objectness, no class scores
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

        # cx,cy,w,h → x1,y1,x2,y2 in crop-space
        cxs, cys, ws, hs = data[:, 0], data[:, 1], data[:, 2], data[:, 3]
        # Normalised vs pixel — detect by value range
        if cxs.max() <= 1.5:
            cxs = cxs * self._model_w
            cys = cys * self._model_h
            ws  = ws  * self._model_w
            hs  = hs  * self._model_h
        x1s = cxs - ws / 2
        y1s = cys - hs / 2
        x2s = cxs + ws / 2
        y2s = cys + hs / 2

        boxes  = np.stack([x1s, y1s, x2s, y2s], axis=1)
        kept   = _nms(boxes, conf, self._nms_thresh)
        kept   = kept[: self._max_det]

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
