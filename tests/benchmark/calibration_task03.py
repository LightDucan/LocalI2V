from __future__ import annotations

import json
import os
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image
from app.orchestration.pipeline import I2VPipeline

ROOT = Path(__file__).resolve().parents[2]
INPUT_IMAGE = ROOT / "history" / "benchmark_assets" / "character_portrait.png"
OUTPUT_DIR = ROOT / "outputs" / "calibration"


def run_calibration():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pipeline = I2VPipeline(output_dir=OUTPUT_DIR)

    test_matrix = [
        ("calib_motion_subtle", "subtle", "normal", "raw", "static"),
        ("calib_motion_normal", "normal", "normal", "raw", "static"),
        ("calib_motion_strong", "strong", "normal", "raw", "static"),
        ("calib_preserve_low", "normal", "low", "raw", "static"),
        ("calib_preserve_high", "normal", "high", "raw", "static"),
    ]

    results = []
    prompt = "Character turns head slowly to the left. Camera static."

    print("Starting TASK-03 calibration runs...")
    for name, motion, preserve, mode, cam in test_matrix:
        print(f"=== Running {name}: motion={motion}, preserve={preserve}, mode={mode} ===")
        res = pipeline.generate(
            image_path=INPUT_IMAGE,
            prompt=prompt,
            seed=42,
            width=512,
            height=288,
            length=25,
            fps=8.0,
            mode=mode,
            motion=motion,
            preserve=preserve,
            camera_preset=cam,
        )
        assert res.success is True, f"Failed {name}: {res.error_message}"
        results.append({
            "name": name,
            "motion": motion,
            "preserve": preserve,
            "mode": mode,
            "generation_time": res.generation_time,
            "video_path": res.video_path,
            "metadata_path": res.metadata_path,
        })
        print(f"Done {name} in {res.generation_time}s -> {res.video_path}")

    summary_path = OUTPUT_DIR / "calibration_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"All calibration runs completed. Summary written to {summary_path}")


if __name__ == "__main__":
    run_calibration()
