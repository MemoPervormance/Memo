import json
import os
from PyQt6.QtCore import QObject, pyqtSignal

DATA_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "InfinityHub")
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")


class AppState(QObject):
    setting_changed = pyqtSignal(str, object)
    profile_changed = pyqtSignal(str)
    favorites_changed = pyqtSignal()
    page_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        os.makedirs(DATA_DIR, exist_ok=True)
        self._settings: dict = {}
        self._favorites: set = set()
        self._current_profile = "Default"
        self._profiles: dict = {}
        self._current_page = "dashboard"
        self._load()

    # ── settings ────────────────────────────────────
    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value
        self.setting_changed.emit(key, value)
        self._save_settings()

    # ── favorites ───────────────────────────────────
    def is_favorite(self, setting_id: str) -> bool:
        return setting_id in self._favorites

    def toggle_favorite(self, setting_id: str):
        if setting_id in self._favorites:
            self._favorites.discard(setting_id)
        else:
            self._favorites.add(setting_id)
        self._save_favorites()
        self.favorites_changed.emit()

    def get_favorites(self) -> list:
        return list(self._favorites)

    # ── profiles ────────────────────────────────────
    def save_profile(self, name: str):
        self._profiles[name] = dict(self._settings)
        self._current_profile = name
        self._save_profiles()
        self.profile_changed.emit(name)

    def load_profile(self, name: str):
        if name in self._profiles:
            self._settings = dict(self._profiles[name])
            self._current_profile = name
            self.profile_changed.emit(name)
            self._save_settings()

    def get_profile_names(self) -> list:
        defaults = ["Competitive", "Maximum FPS", "Balanced", "Streaming", "Performance"]
        custom = [k for k in self._profiles if k not in defaults]
        return defaults + custom

    @property
    def current_profile(self) -> str:
        return self._current_profile

    @property
    def current_page(self) -> str:
        return self._current_page

    def navigate(self, page: str):
        self._current_page = page
        self.page_changed.emit(page)

    # ── persistence ─────────────────────────────────
    def _load(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                self._settings = json.load(f)
        except Exception:
            self._settings = {}
        try:
            with open(PROFILES_FILE, "r") as f:
                self._profiles = json.load(f)
        except Exception:
            self._profiles = {}
        try:
            with open(FAVORITES_FILE, "r") as f:
                self._favorites = set(json.load(f))
        except Exception:
            self._favorites = set()

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def _save_profiles(self):
        try:
            with open(PROFILES_FILE, "w") as f:
                json.dump(self._profiles, f, indent=2)
        except Exception:
            pass

    def _save_favorites(self):
        try:
            with open(FAVORITES_FILE, "w") as f:
                json.dump(list(self._favorites), f)
        except Exception:
            pass


# Singleton
_state: AppState | None = None

def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
