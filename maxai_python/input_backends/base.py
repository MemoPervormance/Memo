"""Abstract base interface for all input backends."""
from __future__ import annotations
from abc import ABC, abstractmethod


class InputBackend(ABC):
    """Common interface every input backend must implement."""

    @abstractmethod
    def move_cursor(self, dx: int, dy: int) -> None:
        """Send a relative mouse/stick movement of (dx, dy) pixels."""

    @abstractmethod
    def press_fire(self) -> None:
        """Begin a fire action (left-click / right-trigger)."""

    @abstractmethod
    def release_fire(self) -> None:
        """End fire action."""

    @abstractmethod
    def press_ads(self) -> None:
        """Begin ADS action (right-click / left-trigger)."""

    @abstractmethod
    def release_ads(self) -> None:
        """End ADS action."""

    @abstractmethod
    def release_all(self) -> None:
        """Release every held input immediately."""

    def set_fire(self, active: bool) -> None:
        """Convenience: toggle fire state."""
        if active:
            self.press_fire()
        else:
            self.release_fire()

    def set_ads(self, active: bool) -> None:
        """Convenience: toggle ADS state."""
        if active:
            self.press_ads()
        else:
            self.release_ads()

    def flush(self) -> None:
        """Flush any buffered inputs (optional override)."""
