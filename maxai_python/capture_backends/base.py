"""Abstract capture backend interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class CaptureBackend(ABC):
    @abstractmethod
    def grab(self) -> Optional[np.ndarray]:
        """Return (H, W, 4) BGRA uint8 or None on failure."""

    @abstractmethod
    def crop_offset(self) -> Tuple[int, int]:
        """Return (offset_x, offset_y) — top-left of crop on screen."""

    @abstractmethod
    def reset(self) -> None:
        """Re-initialise after repeated failures."""

    def return_buffer(self) -> None:
        """Optional buffer-pool hook."""

    @property
    def capture_size(self) -> int:
        return getattr(self, "_capture_size", 320)
