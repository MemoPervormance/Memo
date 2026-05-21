"""
CroixAI — Training Data Collector.

Captures game frames and helps you label them for YOLO training.
Supports:
  - Auto-label mode: color-based enemy detection (works for games with distinct enemy colors)
  - Manual mode: saves raw frames for labeling with LabelImg / Label Studio / Roboflow

Usage:
    python training/dataset_collector.py --game valorant --output datasets/valorant --mode auto
    python training/dataset_collector.py --game cs2     --output datasets/cs2      --mode manual --interval 0.5
    python training/dataset_collector.py --game apex    --output datasets/apex     --mode auto   --limit 5000

Auto-labeling works by detecting pixels matching each game's known enemy-color signature,
computing bounding boxes, and writing YOLO-format .txt label files.

After collection, split with:
    python training/dataset_collector.py --split datasets/valorant --train 0.85 --val 0.15
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import threading
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Enemy color signatures per game (HSV ranges for auto-labeling)
# Each entry: (H_low, H_high, S_low, S_high, V_low, V_high)
# These match the typical enemy highlight/outline color in each game.
# ---------------------------------------------------------------------------

GAME_COLORS: Dict[str, Dict[str, List[Tuple[int,int,int,int,int,int]]]] = {
    "valorant": {
        # Valorant uses distinct yellow/orange enemy outlines (default settings)
        "head": [
            (15, 35, 150, 255, 180, 255),   # orange-yellow outline (head arc)
        ],
        "body": [
            (15, 35, 150, 255, 120, 255),   # same hue, slightly darker
        ],
    },
    "cs2": {
        # CS2 enemy color can be customized — default is orange/yellow CT, green T
        "head": [
            (5, 25, 180, 255, 180, 255),    # orange
            (35, 75, 120, 255, 120, 255),   # green (T side)
        ],
        "body": [
            (5, 25, 130, 255, 130, 255),
            (35, 75, 80, 255, 80, 255),
        ],
    },
    "apex": {
        # Apex has a red damage indicator outline on enemies
        "head": [
            (0, 15, 180, 255, 150, 255),    # red
            (160, 180, 180, 255, 150, 255), # red (wraps)
        ],
        "body": [
            (0, 15, 130, 255, 100, 255),
            (160, 180, 130, 255, 100, 255),
        ],
    },
    "fortnite": {
        # Fortnite has white/cyan outline around enemies when nearby
        "head": [
            (85, 100, 80, 255, 200, 255),   # cyan
            (0, 180, 0, 30, 220, 255),      # near-white
        ],
        "body": [
            (85, 100, 50, 255, 150, 255),
            (0, 180, 0, 20, 200, 255),
        ],
    },
    "warzone": {
        # Warzone doesn't have outlines by default — collect raw frames
        "head": [],
        "body": [],
    },
    "r6": {
        # R6 Siege has a yellow/white outline option (Pro League HUD)
        "head": [
            (20, 40, 150, 255, 200, 255),   # yellow outline
        ],
        "body": [
            (20, 40, 100, 255, 150, 255),
        ],
    },
    "rust": {
        # Rust has no outlines — collect raw frames
        "head": [],
        "body": [],
    },
    "universal": {
        "head": [],
        "body": [],
    },
}

# Class indices
CLASS_HEAD = 0
CLASS_BODY = 1
CLASS_NAMES = {0: "head", 1: "body", 2: "limb", 3: "drone", 4: "vehicle", 5: "horse"}


# ---------------------------------------------------------------------------
# Auto-labeler
# ---------------------------------------------------------------------------

def _color_mask(frame_rgb: np.ndarray, ranges: List[Tuple]) -> np.ndarray:
    """Return binary mask where pixels match any of the given HSV ranges."""
    try:
        import cv2  # type: ignore[import]
    except ImportError:
        return np.zeros(frame_rgb.shape[:2], dtype=np.uint8)
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for (hl, hh, sl, sh, vl, vh) in ranges:
        lo = np.array([hl, sl, vl], dtype=np.uint8)
        hi = np.array([hh, sh, vh], dtype=np.uint8)
        mask |= cv2.inRange(hsv, lo, hi)
    return mask


def _boxes_from_mask(mask: np.ndarray, min_area: int = 20, max_area_frac: float = 0.15) -> List[Tuple[int,int,int,int]]:
    """Find bounding boxes from a binary mask using connected components."""
    try:
        import cv2  # type: ignore[import]
    except ImportError:
        return []
    h, w = mask.shape
    max_area = int(h * w * max_area_frac)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    boxes = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area or area > max_area:
            continue
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        boxes.append((x, y, x + bw, y + bh))
    return boxes


def auto_label_frame(
    frame_bgra: np.ndarray,
    game: str,
) -> List[Tuple[int, float, float, float, float]]:
    """
    Auto-label a frame using color detection.
    Returns list of (class_id, cx_norm, cy_norm, w_norm, h_norm).
    """
    h, w = frame_bgra.shape[:2]
    rgb = frame_bgra[:, :, :3][:, :, ::-1]  # BGRA → RGB
    colors = GAME_COLORS.get(game, {})
    annotations: List[Tuple[int, float, float, float, float]] = []

    for cls_name, ranges in colors.items():
        if not ranges:
            continue
        cls_id = CLASS_HEAD if cls_name == "head" else CLASS_BODY
        mask = _color_mask(rgb, ranges)
        boxes = _boxes_from_mask(mask)
        for (x1, y1, x2, y2) in boxes:
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            annotations.append((cls_id, cx, cy, bw, bh))
    return annotations


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class DatasetCollector:
    def __init__(
        self,
        game: str,
        output_dir: Path,
        mode: str = "manual",
        interval: float = 0.3,
        limit: int = 10_000,
        hotkey: str = "f9",
        capture_size: int = 640,
    ) -> None:
        self._game       = game
        self._out        = output_dir
        self._mode       = mode
        self._interval   = interval
        self._limit      = limit
        self._hotkey     = hotkey
        self._capture_size = capture_size
        self._count      = 0
        self._running    = False
        self._lock       = threading.Lock()

        (self._out / "images" / "train").mkdir(parents=True, exist_ok=True)
        (self._out / "images" / "val").mkdir(parents=True, exist_ok=True)
        (self._out / "labels" / "train").mkdir(parents=True, exist_ok=True)
        (self._out / "labels" / "val").mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self._running = True
        print(f"\nCroixAI Dataset Collector — {self._game.upper()}")
        print(f"Mode: {self._mode} | Interval: {self._interval}s | Limit: {self._limit}")
        if self._mode == "manual":
            print(f"Press [{self._hotkey.upper()}] to capture a frame. [Q] to quit.")
        else:
            print(f"Auto-capturing every {self._interval}s. Press [Q] to quit.")
        print()

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from capture_backends.dxgi import DXGICapture
            cap = DXGICapture(capture_size=self._capture_size)
        except Exception as e:
            print(f"DXGI capture failed: {e}")
            print("Install dxcam: pip install dxcam")
            return

        try:
            import cv2  # type: ignore[import]
        except ImportError:
            print("Install opencv-python: pip install opencv-python")
            return

        last_cap = 0.0
        while self._running and self._count < self._limit:
            frame = cap.grab()
            if frame is None:
                time.sleep(0.01)
                continue

            now = time.monotonic()

            if self._mode == "auto":
                if now - last_cap >= self._interval:
                    self._save_frame(frame, cv2)
                    last_cap = now

            # Show preview
            preview = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            cv2.putText(preview, f"CroixAI Collector | {self._game.upper()} | Frames: {self._count}",
                        (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,230,255), 1)
            cv2.imshow("CroixAI Data Collector (Q=quit, F9=capture)", preview)

            key = cv2.waitKey(16) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif self._mode == "manual" and key == ord('z'):  # z = quick capture
                self._save_frame(frame, cv2)

        cv2.destroyAllWindows()
        print(f"\n✓ Collection complete. {self._count} frames saved to {self._out}")

    def _save_frame(self, frame_bgra: np.ndarray, cv2) -> None:
        import hashlib
        # Split 85/15 train/val
        split = "train" if random.random() < 0.85 else "val"
        idx = f"{self._count:06d}"
        name = f"{self._game}_{idx}"

        img_path = self._out / "images" / split / f"{name}.jpg"
        cv2.imwrite(str(img_path), cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])

        if self._mode == "auto":
            annots = auto_label_frame(frame_bgra, self._game)
            lbl_path = self._out / "labels" / split / f"{name}.txt"
            with open(lbl_path, "w") as f:
                for (cls_id, cx, cy, bw, bh) in annots:
                    f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
        else:
            # Empty label file — user will label manually
            lbl_path = self._out / "labels" / split / f"{name}.txt"
            lbl_path.touch()

        with self._lock:
            self._count += 1
        if self._count % 50 == 0:
            print(f"  {self._count} frames collected…")


# ---------------------------------------------------------------------------
# Dataset splitter
# ---------------------------------------------------------------------------

def split_dataset(dataset_dir: Path, train_frac: float = 0.85) -> None:
    """Move all images from root images/ into train/ and val/ splits."""
    img_root = dataset_dir / "images"
    lbl_root = dataset_dir / "labels"
    (img_root / "train").mkdir(exist_ok=True)
    (img_root / "val").mkdir(exist_ok=True)
    (lbl_root / "train").mkdir(exist_ok=True)
    (lbl_root / "val").mkdir(exist_ok=True)

    imgs = sorted(list(img_root.glob("*.jpg")) + list(img_root.glob("*.png")))
    random.shuffle(imgs)
    split_at = int(len(imgs) * train_frac)

    for i, img_path in enumerate(imgs):
        split = "train" if i < split_at else "val"
        lbl_path = lbl_root / (img_path.stem + ".txt")
        img_path.rename(img_root / split / img_path.name)
        if lbl_path.exists():
            lbl_path.rename(lbl_root / split / lbl_path.name)

    print(f"✓ Split {len(imgs)} images → train={split_at}, val={len(imgs)-split_at}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="CroixAI — Dataset Collector")
    p.add_argument("--game",    required=True,        help="Game name (valorant/cs2/apex/…)")
    p.add_argument("--output",  required=True,        help="Output dataset directory")
    p.add_argument("--mode",    default="auto",       choices=["auto","manual"])
    p.add_argument("--interval",type=float,default=0.3)
    p.add_argument("--limit",   type=int,  default=10000)
    p.add_argument("--size",    type=int,  default=640, help="Capture size")
    p.add_argument("--split",   default=None,         help="Split existing flat dataset dir")
    p.add_argument("--train",   type=float,default=0.85)
    args = p.parse_args()

    if args.split:
        split_dataset(Path(args.split), args.train)
        return

    collector = DatasetCollector(
        game        = args.game,
        output_dir  = Path(args.output),
        mode        = args.mode,
        interval    = args.interval,
        limit       = args.limit,
        capture_size= args.size,
    )
    collector.start()


if __name__ == "__main__":
    main()
