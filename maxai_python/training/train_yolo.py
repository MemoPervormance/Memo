"""
CroixAI — YOLOv8 Training Script.

Trains a named CroixAI model (PHANTOM-V, KRIEG-CS, etc.) using Ultralytics YOLOv8.
Requires: pip install ultralytics>=8.2

Usage:
    python training/train_yolo.py --model PHANTOM-V --data training/data_configs/valorant.yaml
    python training/train_yolo.py --model NEXUS-UNI --data training/data_configs/universal.yaml
    python training/train_yolo.py --model KRIEG-CS --epochs 200 --imgsz 640
    python training/train_yolo.py --model WARLOCK-WZ --data training/data_configs/warzone.yaml --device 0

After training, run:
    python training/train_yolo.py --model PHANTOM-V --export   # → ONNX + TRT
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent to path so we can import model_registry
sys.path.insert(0, str(Path(__file__).parent.parent))
from model_registry import MODELS, get_model_info


# ---------------------------------------------------------------------------
# Game-specific augmentation profiles
# ---------------------------------------------------------------------------

GAME_AUGMENTS = {
    "valorant": {
        "hsv_h":     0.010,   # Valorant has very distinct hue (purple/orange outlines)
        "hsv_s":     0.50,
        "hsv_v":     0.35,
        "degrees":   5.0,
        "translate": 0.10,
        "scale":     0.40,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.10,
        "copy_paste":0.15,
        "erasing":   0.30,
    },
    "cs2": {
        "hsv_h":     0.015,   # Handles smoke (grey), T-side (orange), CT (blue)
        "hsv_s":     0.60,
        "hsv_v":     0.50,
        "degrees":   8.0,
        "translate": 0.12,
        "scale":     0.50,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.20,
        "copy_paste":0.20,
        "erasing":   0.40,    # Simulate smoke occlusion
    },
    "apex": {
        "hsv_h":     0.020,   # Wide colour range across all legends + skins
        "hsv_s":     0.70,
        "hsv_v":     0.45,
        "degrees":   10.0,
        "translate": 0.15,    # High movement — wide translate
        "scale":     0.60,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.15,
        "copy_paste":0.15,
        "erasing":   0.25,
    },
    "fortnite": {
        "hsv_h":     0.025,   # Very colourful skins + building materials
        "hsv_s":     0.80,
        "hsv_v":     0.50,
        "degrees":   8.0,
        "translate": 0.12,
        "scale":     0.55,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.20,
        "copy_paste":0.20,
        "erasing":   0.30,
    },
    "warzone": {
        "hsv_h":     0.012,   # Dark, muted palette; lots of greys + browns
        "hsv_s":     0.40,
        "hsv_v":     0.60,    # High brightness variation (dark rooms vs snow)
        "degrees":   6.0,
        "translate": 0.10,
        "scale":     0.70,    # Large blob (640) — more scale variance needed
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.25,
        "copy_paste":0.10,
        "erasing":   0.20,
    },
    "r6": {
        "hsv_h":     0.012,
        "hsv_s":     0.45,
        "hsv_v":     0.40,
        "degrees":   4.0,     # Siege is precision — less rotation
        "translate": 0.08,
        "scale":     0.40,    # Tight corridors — less scale variance
        "fliplr":    0.50,
        "mosaic":    0.80,
        "mixup":     0.10,
        "copy_paste":0.25,    # Simulate partial wall peeks
        "erasing":   0.45,    # Simulate wall occlusion heavily
    },
    "rust": {
        "hsv_h":     0.018,   # Naked/hazmat/geared players + day-night
        "hsv_s":     0.60,
        "hsv_v":     0.70,    # Huge brightness range (noon vs night)
        "degrees":   8.0,
        "translate": 0.12,
        "scale":     0.50,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.15,
        "copy_paste":0.15,
        "erasing":   0.25,
    },
    "universal": {
        "hsv_h":     0.025,
        "hsv_s":     0.70,
        "hsv_v":     0.55,
        "degrees":   10.0,
        "translate": 0.12,
        "scale":     0.55,
        "fliplr":    0.50,
        "mosaic":    1.00,
        "mixup":     0.20,
        "copy_paste":0.20,
        "erasing":   0.35,
    },
}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(
    model_name: str,
    data_yaml: str,
    epochs: int = 150,
    imgsz: int | None = None,
    batch: int = 16,
    device: str = "0",
    project: str = "runs/train",
    resume: bool = False,
    patience: int = 50,
) -> None:
    try:
        from ultralytics import YOLO  # type: ignore[import]
    except ImportError:
        print("ERROR: ultralytics not installed. Run: pip install ultralytics>=8.2")
        sys.exit(1)

    info = get_model_info(model_name)
    if info is None:
        print(f"ERROR: Unknown model '{model_name}'")
        print(f"Available: {', '.join(MODELS.keys())}")
        sys.exit(1)

    arch      = info["arch"]           # yolov8n / yolov8s / yolov8m
    blob_size = imgsz or info["blob_size"]
    game_key  = info["training"]
    aug       = GAME_AUGMENTS.get(game_key, GAME_AUGMENTS["universal"])

    print(f"\n{'='*60}")
    print(f"  CroixAI Model Training")
    print(f"  Model  : {model_name}  ({info['game']})")
    print(f"  Arch   : {arch}  |  imgsz={blob_size}  |  epochs={epochs}")
    print(f"  Data   : {data_yaml}")
    print(f"  Device : {device}")
    print(f"{'='*60}\n")

    model = YOLO(f"{arch}.pt")

    model.train(
        data       = data_yaml,
        epochs     = epochs,
        imgsz      = blob_size,
        batch      = batch,
        device     = device,
        project    = project,
        name       = model_name.lower().replace("-", "_"),
        resume     = resume,
        patience   = patience,
        save       = True,
        save_period= 10,
        plots      = True,
        # Augmentation — game-specific
        hsv_h      = aug["hsv_h"],
        hsv_s      = aug["hsv_s"],
        hsv_v      = aug["hsv_v"],
        degrees    = aug["degrees"],
        translate  = aug["translate"],
        scale      = aug["scale"],
        fliplr     = aug["fliplr"],
        mosaic     = aug["mosaic"],
        mixup      = aug["mixup"],
        copy_paste = aug["copy_paste"],
        erasing    = aug.get("erasing", 0.3),
        # Training hyperparams
        lr0        = 0.01,
        lrf        = 0.01,
        momentum   = 0.937,
        weight_decay = 0.0005,
        warmup_epochs = 3,
        warmup_momentum = 0.8,
        box        = 7.5,
        cls        = 0.5,
        dfl        = 1.5,
        # Optimization
        optimizer  = "AdamW",
        cos_lr     = True,
        amp        = True,
        workers    = 8,
    )
    print(f"\n✓ Training complete. Weights saved in {project}/{model_name.lower().replace('-','_')}/weights/")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_model(model_name: str, weights_path: str | None = None, trt: bool = False) -> None:
    try:
        from ultralytics import YOLO  # type: ignore[import]
    except ImportError:
        print("ERROR: ultralytics not installed.")
        sys.exit(1)

    info = get_model_info(model_name)
    if info is None:
        print(f"ERROR: Unknown model '{model_name}'")
        sys.exit(1)

    if weights_path is None:
        name = model_name.lower().replace("-", "_")
        weights_path = f"runs/train/{name}/weights/best.pt"

    if not Path(weights_path).exists():
        print(f"ERROR: Weights not found at {weights_path}")
        sys.exit(1)

    blob_size = info["blob_size"]
    out_name  = info["filename"]
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(exist_ok=True)

    model = YOLO(weights_path)

    # Export ONNX
    print(f"Exporting {model_name} → ONNX ({blob_size}px)…")
    onnx_path = model.export(format="onnx", imgsz=blob_size, simplify=True, opset=17, dynamic=False)
    import shutil
    shutil.copy(onnx_path, models_dir / out_name)
    print(f"✓ ONNX saved → models/{out_name}")

    # Export TRT
    if trt:
        trt_name = out_name.replace(".onnx", ".engine")
        print(f"Exporting {model_name} → TensorRT…")
        trt_path = model.export(format="engine", imgsz=blob_size, half=True, device=0)
        shutil.copy(trt_path, models_dir / trt_name)
        print(f"✓ TRT engine saved → models/{trt_name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="CroixAI — Train or export a named model")
    p.add_argument("--model",   required=True,       help="Model name (PHANTOM-V, KRIEG-CS, etc.)")
    p.add_argument("--data",    default=None,        help="Path to YOLO dataset YAML")
    p.add_argument("--epochs",  type=int, default=150)
    p.add_argument("--imgsz",   type=int, default=None, help="Override blob size")
    p.add_argument("--batch",   type=int, default=16)
    p.add_argument("--device",  default="0",         help="GPU index or 'cpu'")
    p.add_argument("--project", default="runs/train")
    p.add_argument("--resume",  action="store_true")
    p.add_argument("--patience",type=int, default=50)
    p.add_argument("--export",  action="store_true", help="Export best.pt to ONNX/TRT")
    p.add_argument("--weights", default=None,        help="Path to .pt for export")
    p.add_argument("--trt",     action="store_true", help="Also export TensorRT .engine")
    p.add_argument("--list",    action="store_true", help="List all available models")
    args = p.parse_args()

    if args.list:
        print("\nCroixAI — Available Models\n")
        for name, info in MODELS.items():
            perf_badge = {"ultra_fast":"⚡","fast":"🚀","balanced":"⚖","accurate":"🎯","precise":"🔬"}.get(info["perf"],"")
            print(f"  {info['icon']} {name:15s} {perf_badge} | {info['arch']:10s} | {info['blob_size']}px | {info['game']}")
            print(f"     {info['description'][:90]}…\n")
        return

    if args.export:
        export_model(args.model, args.weights, args.trt)
        return

    info = get_model_info(args.model)
    data_yaml = args.data
    if data_yaml is None:
        training_key = info["training"] if info else "universal"
        data_yaml = str(Path(__file__).parent / "data_configs" / f"{training_key}.yaml")
        if not Path(data_yaml).exists():
            print(f"ERROR: No data YAML found. Specify with --data or create {data_yaml}")
            sys.exit(1)

    train(
        model_name = args.model,
        data_yaml  = data_yaml,
        epochs     = args.epochs,
        imgsz      = args.imgsz,
        batch      = args.batch,
        device     = args.device,
        project    = args.project,
        resume     = args.resume,
        patience   = args.patience,
    )


if __name__ == "__main__":
    main()
