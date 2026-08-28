import json
import shutil
import sys
import time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.history.database import HistoryDatabase
from app.jobs.job_manager import JobManager
from app.orchestration.pipeline import I2VPipeline

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "outputs" / "audit_pack"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_IMG = ROOT / "history" / "benchmark_assets" / "character_portrait.png"
if not SOURCE_IMG.exists():
    # Generate portrait if missing
    img = Image.new("RGB", (450, 600), color=(180, 140, 100))
    SOURCE_IMG = AUDIT_DIR / "source_image.png"
    img.save(SOURCE_IMG)
else:
    # Copy source image to audit pack
    shutil.copy2(SOURCE_IMG, AUDIT_DIR / "source_image.png")

print(f"Source image ready at {AUDIT_DIR / 'source_image.png'}")

db = HistoryDatabase()
job_mgr = JobManager(db=db)

# 1. Simple Mode Generation
print("\n[1/2] Generating Simple Mode Output...")
prompt_simple = "Character turns head slowly to the left. Camera static."
gen_simple = job_mgr.run_job_stream(
    image_path=str(AUDIT_DIR / "source_image.png"),
    prompt=prompt_simple,
    seed=42,
    mode="simple",
    preserve="normal",
    motion="strong",
    camera_preset="static",
    subject_mode="single",
    crop_fill=False,
    enhance_enabled=True,
)

simple_raw_path = None
simple_enh_path = None
for pct, status, vid, err in gen_simple:
    if vid:
        simple_enh_path = vid
    if err:
        print(f"Error in Simple: {err}")

# Find latest job in DB for simple
job_simple = db.get_latest_jobs(1)[0]
simple_raw_path = job_simple["raw_output"]
simple_enh_path = job_simple["enhanced_output"]

print(f"Simple raw: {simple_raw_path}")
print(f"Simple enhanced: {simple_enh_path}")

# Copy into audit pack
shutil.copy2(simple_raw_path, AUDIT_DIR / "simple_raw.mp4")
shutil.copy2(Path(simple_raw_path).with_suffix(".json"), AUDIT_DIR / "simple_raw.json")
shutil.copy2(simple_enh_path, AUDIT_DIR / "simple_enhanced.mp4")
shutil.copy2(Path(simple_enh_path).with_suffix(".json"), AUDIT_DIR / "simple_enhanced.json")

# Copy preprocessed input
with open(AUDIT_DIR / "simple_raw.json", "r", encoding="utf-8") as f:
    meta_s = json.load(f)
    if meta_s.get("preprocessed_image"):
        prep_path = ROOT / "outputs" / meta_s["preprocessed_image"]
        if prep_path.exists():
            shutil.copy2(prep_path, AUDIT_DIR / "preprocessed_input.png")

# 2. RAW Mode Generation
print("\n[2/2] Generating RAW Mode Output...")
prompt_raw = "Character turns head slowly to the left. Camera static."
gen_raw = job_mgr.run_job_stream(
    image_path=str(AUDIT_DIR / "source_image.png"),
    prompt=prompt_raw,
    seed=42,
    mode="raw",
    preserve="normal",
    motion="normal",
    camera_preset="static",
    subject_mode="single",
    crop_fill=False,
    enhance_enabled=True,
)

for pct, status, vid, err in gen_raw:
    if err:
        print(f"Error in RAW: {err}")

job_raw = db.get_latest_jobs(1)[0]
raw_mode_raw_path = job_raw["raw_output"]
raw_mode_enh_path = job_raw["enhanced_output"]

print(f"RAW raw: {raw_mode_raw_path}")
print(f"RAW enhanced: {raw_mode_enh_path}")

shutil.copy2(raw_mode_raw_path, AUDIT_DIR / "raw_mode_raw.mp4")
shutil.copy2(Path(raw_mode_raw_path).with_suffix(".json"), AUDIT_DIR / "raw_mode_raw.json")
shutil.copy2(raw_mode_enh_path, AUDIT_DIR / "raw_mode_enhanced.mp4")
shutil.copy2(Path(raw_mode_enh_path).with_suffix(".json"), AUDIT_DIR / "raw_mode_enhanced.json")

print("\nAudit pack successfully generated at outputs/audit_pack/!")
