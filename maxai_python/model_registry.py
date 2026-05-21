"""
CroixAI — AI Model Registry.
Defines all named model variants, their recommended settings per game,
and which training config to use.

Model naming convention:  <CODENAME>-<GAME_ABBR>  (e.g. PHANTOM-V)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Model Definitions
# ---------------------------------------------------------------------------

MODELS: Dict[str, Dict[str, Any]] = {

    # ── Universal ──────────────────────────────────────────────────────────
    "NEXUS-UNI": {
        "name":        "NEXUS-UNI",
        "codename":    "NEXUS",
        "game":        "Universal",
        "icon":        "🌐",
        "arch":        "yolov8s",
        "blob_size":   320,
        "classes":     ["head", "body"],
        "description": (
            "Universal multi-game model. Trained on enemy head & body across "
            "7 games. Best starting point if you don't have a game-specific model."
        ),
        "recommended_for": ["valorant", "cs2_faceit", "apex", "fortnite", "cod_warzone", "r6_siege", "rust"],
        "confidence":  0.50,
        "nms":         0.45,
        "training":    "universal",
        "filename":    "nexus_uni.onnx",
        "perf":        "balanced",
    },

    # ── Valorant ───────────────────────────────────────────────────────────
    "PHANTOM-V": {
        "name":        "PHANTOM-V",
        "codename":    "PHANTOM",
        "game":        "Valorant",
        "icon":        "🔺",
        "arch":        "yolov8n",
        "blob_size":   320,
        "classes":     ["head", "body"],
        "description": (
            "Optimized for Valorant's clean visual style, distinct agent silhouettes, "
            "and bright enemy outlines. Ultra-fast nano architecture for 300+ FPS inference. "
            "Trained on all maps (Ascent, Bind, Haven, Pearl, Lotus, Sunset, Abyss). "
            "Head-shot precision tuned."
        ),
        "recommended_for": ["valorant"],
        "confidence":  0.52,
        "nms":         0.40,
        "training":    "valorant",
        "filename":    "phantom_v.onnx",
        "perf":        "ultra_fast",
    },

    # ── CS2 / FaceIt ──────────────────────────────────────────────────────
    "KRIEG-CS": {
        "name":        "KRIEG-CS",
        "codename":    "KRIEG",
        "game":        "CS2 / FaceIt",
        "icon":        "🔫",
        "arch":        "yolov8s",
        "blob_size":   320,
        "classes":     ["head", "body", "limb"],
        "description": (
            "Counter-Strike 2 specialist. Handles smoke grenades (partial occlusion), "
            "flash-bang recovery, T-side / CT-side skin differentiation. "
            "Trained on all Dust2, Mirage, Inferno, Nuke, Vertigo, Ancient, Anubis. "
            "FaceIt AC hardened — only hardware movement, never SendInput."
        ),
        "recommended_for": ["cs2_faceit"],
        "confidence":  0.55,
        "nms":         0.45,
        "training":    "cs2",
        "filename":    "krieg_cs.onnx",
        "perf":        "fast",
    },

    # ── Apex Legends ──────────────────────────────────────────────────────
    "HAVOC-AX": {
        "name":        "HAVOC-AX",
        "codename":    "HAVOC",
        "game":        "Apex Legends",
        "icon":        "🦅",
        "arch":        "yolov8s",
        "blob_size":   320,
        "classes":     ["head", "body"],
        "description": (
            "Apex Legends tuned. Handles massive movement speeds, "
            "ziplines, slide-jumps, and bunny-hops. "
            "Trained across all legends (each has unique hitbox proportions). "
            "Recoil compensation patterns for Flatline, R-301, Wingman, Peacekeeper. "
            "Optimized for Kings Canyon, World's Edge, Olympus, Storm Point, Broken Moon."
        ),
        "recommended_for": ["apex"],
        "confidence":  0.48,
        "nms":         0.45,
        "training":    "apex",
        "filename":    "havoc_ax.onnx",
        "perf":        "fast",
    },

    # ── Fortnite ──────────────────────────────────────────────────────────
    "STORM-FN": {
        "name":        "STORM-FN",
        "codename":    "STORM",
        "game":        "Fortnite",
        "icon":        "🏗",
        "arch":        "yolov8n",
        "blob_size":   320,
        "classes":     ["head", "body"],
        "description": (
            "Fortnite-specific. Handles EAC anti-cheat (borderless-window). "
            "Trained on colourful Chapter 5 skins, building materials, "
            "vehicles, and third-person mode interactions. "
            "Ultra-low latency for high-movement battle royale. "
            "Works in Build and Zero Build modes."
        ),
        "recommended_for": ["fortnite"],
        "confidence":  0.50,
        "nms":         0.45,
        "training":    "fortnite",
        "filename":    "storm_fn.onnx",
        "perf":        "ultra_fast",
    },

    # ── COD Warzone / MW ──────────────────────────────────────────────────
    "WARLOCK-WZ": {
        "name":        "WARLOCK-WZ",
        "codename":    "WARLOCK",
        "game":        "COD Warzone / MW",
        "icon":        "💀",
        "arch":        "yolov8m",
        "blob_size":   640,
        "classes":     ["head", "body", "vehicle"],
        "description": (
            "Call of Duty Warzone & MW3 specialist. Medium model for long-range "
            "engagement accuracy. Handles dark environments (Night Mode, indoor), "
            "ADS detection (shrunk hitbox when scoped), prone/crouched stances, "
            "Gulag 1v1, and armoured vehicles. "
            "RICOCHET-hardened — borderless window + relative_mouse or hardware."
        ),
        "recommended_for": ["cod_warzone"],
        "confidence":  0.45,
        "nms":         0.45,
        "training":    "warzone",
        "filename":    "warlock_wz.onnx",
        "perf":        "accurate",
    },

    # ── Rainbow Six Siege ─────────────────────────────────────────────────
    "BREACH-R6": {
        "name":        "BREACH-R6",
        "codename":    "BREACH",
        "game":        "Rainbow Six Siege",
        "icon":        "🛡",
        "arch":        "yolov8s",
        "blob_size":   320,
        "classes":     ["head", "body", "drone"],
        "description": (
            "Rainbow Six Siege master. Trained for tight corridor angles, "
            "partial-body peeks, operator gadgets, and barricaded windows. "
            "Separate class for drones (Twitch, Jackal, Pulse). "
            "Handles all operator skins across attacker/defender roles. "
            "BattlEye-aware — hardware input backend strongly recommended."
        ),
        "recommended_for": ["r6_siege"],
        "confidence":  0.58,
        "nms":         0.40,
        "training":    "r6",
        "filename":    "breach_r6.onnx",
        "perf":        "precise",
    },

    # ── Rust ──────────────────────────────────────────────────────────────
    "FURNACE-RS": {
        "name":        "FURNACE-RS",
        "codename":    "FURNACE",
        "game":        "Rust",
        "icon":        "⚙",
        "arch":        "yolov8s",
        "blob_size":   320,
        "classes":     ["head", "body", "horse"],
        "description": (
            "Rust survival specialist. Handles day/night cycle lighting, "
            "naked/geared/hazmat player variants, horses, and helicopters. "
            "Extreme recoil patterns included for AK-47, LR-300, MP5, HMLMG. "
            "Long-range body-shot optimized (body hitbox larger in Rust). "
            "EAC — use hardware backend or borderless-window SendInput."
        ),
        "recommended_for": ["rust"],
        "confidence":  0.46,
        "nms":         0.45,
        "training":    "rust",
        "filename":    "furnace_rs.onnx",
        "perf":        "fast",
    },
}

MODEL_MAP = {m["filename"]: m for m in MODELS.values()}
MODEL_BY_NAME = MODELS  # alias


def get_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    return MODELS.get(model_name)


def get_recommended_model(game_id: str) -> Optional[Dict[str, Any]]:
    """Return the best model for a game_id."""
    for m in MODELS.values():
        if game_id in m.get("recommended_for", []):
            return m
    return MODELS.get("NEXUS-UNI")


def get_models_for_game(game_id: str) -> List[Dict[str, Any]]:
    """All models that support a game (primary first, then universal)."""
    primary = [m for m in MODELS.values() if game_id in m.get("recommended_for", []) and m["game"] != "Universal"]
    universal = [m for m in MODELS.values() if m["game"] == "Universal"]
    return primary + universal


def list_models() -> List[Dict[str, Any]]:
    return list(MODELS.values())


def get_download_status(models_dir: Path) -> Dict[str, bool]:
    """Check which model files are present on disk."""
    result = {}
    for name, info in MODELS.items():
        path = models_dir / info["filename"]
        result[name] = path.exists()
    return result
