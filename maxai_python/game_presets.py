"""
CroixAI — Game Presets.
Pre-configured profiles for popular games with recommended settings.
"""
from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Game preset definitions
# ---------------------------------------------------------------------------
# Each preset contains:
#   display_name, icon (emoji), description, tags,
#   recommended_input, recommended_capture,
#   config overrides (flat dict applied to ConfigManager)
# ---------------------------------------------------------------------------

GAME_PRESETS: List[Dict[str, Any]] = [
    {
        "id":          "valorant",
        "model":       "PHANTOM-V",
        "model_file":  "phantom_v.onnx",
        "name":        "Valorant",
        "icon":        "🔺",
        "description": "Riot Vanguard kernel anti-cheat. Hardware input backend REQUIRED. "
                       "Use DXGI or WinRT capture in borderless-window mode.",
        "tags":        ["Vanguard", "Kernel AC", "Hardware Only"],
        "badge":       "Requires Hardware",
        "badge_color": "rd",
        "recommended_input":   "kmbox_net",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            55.0,
            "aim.fov_y":            55.0,
            "aim.speed":            1.3,
            "aim.snap_radius":      20.0,
            "aim.near_radius":      75.0,
            "aim.scope_multiplier": 1.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.05,
            "aim.prediction.future_positions": 5,
            "aim.wind_mouse.enabled":  True,
            "aim.wind_mouse.gravity":  9.0,
            "aim.wind_mouse.wind":     3.5,
            "aim.wind_mouse.max_step": 7.0,
            "detection.confidence_threshold": 0.52,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
    {
        "id":          "cs2_faceit",
        "model":       "KRIEG-CS",
        "model_file":  "krieg_cs.onnx",
        "name":        "CS2 / FaceIt",
        "icon":        "🔫",
        "description": "CS2 with FaceIt anti-cheat. Hardware input backend strongly recommended. "
                       "Use DXGI capture. Enable wind-mouse for humanized movement.",
        "tags":        ["FaceIt", "Hardware Recommended"],
        "badge":       "HW Recommended",
        "badge_color": "or",
        "recommended_input":   "arduino",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            60.0,
            "aim.fov_y":            60.0,
            "aim.speed":            1.2,
            "aim.snap_radius":      22.0,
            "aim.near_radius":      80.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.04,
            "aim.prediction.future_positions": 6,
            "aim.wind_mouse.enabled":  True,
            "aim.wind_mouse.gravity":  9.0,
            "aim.wind_mouse.wind":     3.0,
            "aim.wind_mouse.max_step": 8.0,
            "aim.recoil.enabled":   True,
            "aim.recoil.strength":  1.2,
            "detection.confidence_threshold": 0.55,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
    {
        "id":          "apex",
        "model":       "HAVOC-AX",
        "model_file":  "havoc_ax.onnx",
        "name":        "Apex Legends",
        "icon":        "🦅",
        "description": "EA Easy Anti-Cheat. Borderless-window + relative_mouse works. "
                       "High recoil — enable recoil compensation. "
                       "Large target hit-boxes: increase FOV slightly.",
        "tags":        ["EAC", "Borderless OK"],
        "badge":       "BW + SendInput",
        "badge_color": "gr",
        "recommended_input":   "relative_mouse",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            70.0,
            "aim.fov_y":            70.0,
            "aim.speed":            1.1,
            "aim.snap_radius":      25.0,
            "aim.near_radius":      90.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.06,
            "aim.prediction.future_positions": 8,
            "aim.recoil.enabled":   True,
            "aim.recoil.strength":  2.0,
            "aim.recoil.smoothness": 2.5,
            "aim.wind_mouse.enabled":  False,
            "detection.confidence_threshold": 0.50,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
    {
        "id":          "fortnite",
        "model":       "STORM-FN",
        "model_file":  "storm_fn.onnx",
        "name":        "Fortnite",
        "icon":        "🏗",
        "description": "Easy Anti-Cheat. Borderless-window recommended. "
                       "High player movement — increase prediction. "
                       "Works with relative_mouse in BW mode.",
        "tags":        ["EAC", "Borderless OK"],
        "badge":       "BW + SendInput",
        "badge_color": "gr",
        "recommended_input":   "relative_mouse",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            65.0,
            "aim.fov_y":            65.0,
            "aim.speed":            1.15,
            "aim.snap_radius":      24.0,
            "aim.near_radius":      85.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.08,
            "aim.prediction.future_positions": 10,
            "aim.recoil.enabled":   False,
            "aim.wind_mouse.enabled":  False,
            "detection.confidence_threshold": 0.50,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
    {
        "id":          "cod_warzone",
        "model":       "WARLOCK-WZ",
        "model_file":  "warlock_wz.onnx",
        "name":        "COD: Warzone / MW",
        "icon":        "💀",
        "description": "RICOCHET anti-cheat. Borderless-window OK with relative_mouse. "
                       "Very high recoil — tune recoil compensation per weapon. "
                       "640 blob size recommended for distant targets.",
        "tags":        ["RICOCHET", "Borderless OK"],
        "badge":       "BW + SendInput",
        "badge_color": "gr",
        "recommended_input":   "relative_mouse",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            80.0,
            "aim.fov_y":            80.0,
            "aim.speed":            1.0,
            "aim.snap_radius":      20.0,
            "aim.near_radius":      85.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.07,
            "aim.prediction.future_positions": 7,
            "aim.recoil.enabled":   True,
            "aim.recoil.strength":  3.0,
            "aim.recoil.smoothness": 3.0,
            "aim.wind_mouse.enabled":  False,
            "detection.confidence_threshold": 0.48,
            "detection.blob_size":   640,
            "capture.backend":       "dxgi",
            "capture.capture_size":  640,
        },
    },
    {
        "id":          "r6_siege",
        "model":       "BREACH-R6",
        "model_file":  "breach_r6.onnx",
        "name":        "Rainbow Six Siege",
        "icon":        "🛡",
        "description": "BattlEye anti-cheat. Hardware input recommended for ranked. "
                       "Small targets, tight angles — use smaller FOV and higher confidence.",
        "tags":        ["BattlEye", "Hardware Recommended"],
        "badge":       "HW Recommended",
        "badge_color": "or",
        "recommended_input":   "arduino",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            45.0,
            "aim.fov_y":            45.0,
            "aim.speed":            1.4,
            "aim.snap_radius":      18.0,
            "aim.near_radius":      60.0,
            "aim.position":         "head",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.03,
            "aim.prediction.future_positions": 4,
            "aim.recoil.enabled":   True,
            "aim.recoil.strength":  1.5,
            "aim.wind_mouse.enabled":  True,
            "aim.wind_mouse.gravity":  10.0,
            "aim.wind_mouse.wind":     2.0,
            "aim.wind_mouse.max_step": 6.0,
            "detection.confidence_threshold": 0.58,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
    {
        "id":          "rust",
        "model":       "FURNACE-RS",
        "model_file":  "furnace_rs.onnx",
        "name":        "Rust",
        "icon":        "⚙",
        "description": "EAC. Borderless-window + relative_mouse or hardware. "
                       "Extreme recoil patterns — strong recoil compensation needed. "
                       "Use body position for larger hit area at distance.",
        "tags":        ["EAC", "High Recoil"],
        "badge":       "BW + SendInput",
        "badge_color": "gr",
        "recommended_input":   "relative_mouse",
        "recommended_capture": "dxgi",
        "config": {
            "aim.fov_x":            75.0,
            "aim.fov_y":            75.0,
            "aim.speed":            0.9,
            "aim.snap_radius":      22.0,
            "aim.near_radius":      90.0,
            "aim.position":         "body",
            "aim.auto_aim":         True,
            "aim.auto_shoot":       False,
            "aim.prediction.enabled":          True,
            "aim.prediction.interval":         0.06,
            "aim.prediction.future_positions": 6,
            "aim.recoil.enabled":   True,
            "aim.recoil.strength":  4.0,
            "aim.recoil.smoothness": 3.5,
            "aim.wind_mouse.enabled":  False,
            "detection.confidence_threshold": 0.48,
            "detection.blob_size":   320,
            "capture.backend":       "dxgi",
            "capture.capture_size":  320,
        },
    },
]


GAME_PRESET_MAP = {p["id"]: p for p in GAME_PRESETS}


def get_preset(game_id: str) -> Dict[str, Any] | None:
    return GAME_PRESET_MAP.get(game_id)


def apply_preset(game_id: str, config_mgr) -> bool:
    """Apply a game preset to ConfigManager.  Returns True on success."""
    preset = get_preset(game_id)
    if preset is None:
        return False

    cfg = config_mgr.get()
    flat = preset["config"]

    raw = cfg.model_dump()

    for dotkey, val in flat.items():
        parts = dotkey.split(".")
        node = raw
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = val

    from config import AppConfig
    config_mgr._cfg = AppConfig.model_validate(raw)
    config_mgr.save()
    return True
