# LocalI2V V0.1 — Project Plan (Antigravity 100%)
> **Owner:** Antigravity Pro | **Version:** Plan Rev.2 | **Cập nhật:** 2026-08

---

## LEGEND — KÝ HIỆU THEO DÕI

| Ký hiệu | Ý nghĩa |
|---|---|
| `[ ]` | Chưa bắt đầu |
| `[→]` | Đang thực hiện |
| `[✓]` | Hoàn thành |
| `[✗]` | Failed / Blocked |
| 🔴 **AUDIT KỸ** | Dừng bắt buộc — kiểm tra kỹ trước khi tiếp tục |
| 🟡 **AUDIT SƠ BỘ** | Kiểm tra nhanh — đủ điều kiện mới chạy task tiếp |
| 🟢 **SELF-CHECK** | Antigravity tự verify — không cần dừng |

---

## PHASE 0 — BOOTSTRAP
> **Mục tiêu:** Môi trường chạy được. Không viết bất kỳ feature logic nào.
> **Thời gian:** 0.5 ngày

---

### LV-001 · Tạo Repository Structure
**Owner:** Antigravity
**Input:** Không có
**Output:** Thư mục repo đúng cấu trúc

```
LocalI2V/
├── app/
│   ├── ui/
│   ├── orchestration/
│   ├── presets/
│   ├── jobs/
│   └── postprocess/
├── comfyui/           ← symlink hoặc submodule
├── models/            ← placeholder
├── outputs/
├── history/
├── tests/
├── docs/
├── requirements.txt
└── README.md
```

**Deliverable:** `tree LocalI2V/` output sạch đúng cấu trúc.

---

### LV-002 · Python Environment
**Owner:** Antigravity
**Input:** LV-001 ✓
**Output:** `venv` chạy được, `requirements.txt` đầy đủ

Packages tối thiểu:
```
torch
torchvision
gradio>=4.0
Pillow
opencv-python
ffmpeg-python
requests
sqlite3  (built-in)
```

**Deliverable:** `python -c "import torch; print(torch.cuda.is_available())"` → True

---

### 🟡 AUDIT SƠ BỘ · LV-002-CHK
**Người audit:** Bạn (owner)
**Checklist:**
- [ ] `torch.cuda.is_available()` → True
- [ ] GPU name hiển thị đúng (GTX 1070)
- [ ] VRAM report ≥ 7.5GB free
- [ ] Không lỗi import nào trong requirements

> **Nếu fail:** Dừng. Fix môi trường trước. Không tiếp tục LV-003.

---

### LV-003 · GPU Detection Module
**Owner:** Antigravity
**Input:** LV-002 ✓
**Output:** `app/system/gpu_info.py`

```python
# GPU info module — Antigravity viết
def get_gpu_info() -> dict:
    # Trả về: name, vram_total, vram_free, cuda_version, compute_capability
    pass

def check_minimum_requirements() -> bool:
    # VRAM >= 6GB, CUDA available
    pass
```

**Deliverable:** Script chạy in ra GPU info đầy đủ.

---

### LV-004 · ComfyUI Installation & Verify
**Owner:** Antigravity
**Input:** LV-002 ✓
**Output:** ComfyUI chạy được ở API mode

Steps:
1. Clone ComfyUI vào `comfyui/`
2. Install ComfyUI requirements
3. Download LTX-Video node/extension
4. Verify API server start: `python main.py --listen 127.0.0.1 --port 8188`
5. Ping `/system_stats` endpoint → response OK

**Deliverable:** `curl http://127.0.0.1:8188/system_stats` trả về JSON với GPU info.

---

### 🔴 AUDIT KỸ · LV-004-CHK — HARDWARE GATE
**Người audit:** Bạn (owner)
**Đây là gate quan trọng nhất của Phase 0.**

**Checklist:**
- [ ] ComfyUI start không lỗi
- [ ] API endpoint `/system_stats` trả về GTX 1070
- [ ] VRAM hiển thị đúng trong ComfyUI
- [ ] LTX-Video node xuất hiện trong node list
- [ ] Thử load model thủ công qua ComfyUI UI (không qua code) → model load được

**Test thủ công bắt buộc:**
> Mở ComfyUI UI tại `http://127.0.0.1:8188`
> Load workflow I2V mẫu của LTX-Video
> Chạy với ảnh test bất kỳ
> Xem có ra video không (dù xấu)

**Nếu model không load được trên GTX 1070:**
> → Thử SVD-XT thay LTX-Video
> → Thử CogVideoX-2B
> → Không tiếp tục Phase 1 cho đến khi có ít nhất 1 model chạy được

---

### LV-005 · Gradio Shell
**Owner:** Antigravity
**Input:** LV-002 ✓ (độc lập với LV-004)
**Output:** `app/ui/main_ui.py` — Gradio app khung rỗng

Chỉ cần:
- Layout đúng vị trí các component
- Không có logic thật
- Placeholder cho tất cả inputs
- Start/stop không crash

**Deliverable:** `python app/ui/main_ui.py` → browser mở được, UI hiển thị.

---

### LV-006 · Folder Structure + Local Logging
**Owner:** Antigravity
**Input:** LV-001 ✓
**Output:** `app/system/logger.py`, auto-create `outputs/` và `history/`

Log format:
```
[2026-08-27 10:00:00] [INFO] Job LV-xxx started
[2026-08-27 10:00:05] [INFO] ComfyUI response: OK
[2026-08-27 10:00:05] [ERROR] ...
```

Log chỉ ghi local. Không bất kỳ remote call nào.

**Deliverable:** Log file xuất hiện tại `history/app.log` khi chạy app.

---

### 🟢 SELF-CHECK · Phase 0 Complete
**Antigravity tự verify:**
- [ ] Repo structure đúng
- [ ] GPU detect OK
- [ ] ComfyUI API chạy được
- [ ] Gradio shell load được
- [ ] Logging ghi file

**Báo cáo cho owner:** Screenshot terminal + browser UI

---

## PHASE 1 — MODEL BENCHMARK
> **Mục tiêu:** Tìm model fit GTX 1070, đạt Source Preservation usable.
> **Thời gian:** 1–2 ngày
> **Quan trọng:** Không có model → không có product. Đây là phase rủi ro cao nhất.

---

### LV-010 · Benchmark Workflow Builder
**Owner:** Antigravity
**Input:** LV-004 ✓ (ComfyUI chạy được)
**Output:** `tests/benchmark/workflow_builder.py`

```python
def build_i2v_workflow(
    image_path: str,
    prompt: str,
    negative_prompt: str = "",
    seed: int = 42,
    steps: int = 20,
    duration_frames: int = 24,   # ~3s ở 8fps
    model_name: str = "ltx-video"
) -> dict:
    # Trả về ComfyUI workflow JSON
    pass
```

**Deliverable:** Function trả về valid JSON, submit được vào ComfyUI API.

---

### LV-011 · Benchmark Test Runner
**Owner:** Antigravity
**Input:** LV-010 ✓
**Output:** `tests/benchmark/runner.py`

Test cases bắt buộc:

| Test ID | Mô tả | Image | Prompt |
|---|---|---|---|
| TEST-A | Breathing | 1 nhân vật | "Character breathes slowly. Camera static." |
| TEST-B | Head Turn | 1 nhân vật | "Character turns head slowly to the left." |
| TEST-C | One Subject | 2 nhân vật | "Only character A moves slightly. Character B stays still." |
| TEST-D | Body Motion | 1 nhân vật | "Character shifts body weight slightly." |
| TEST-E | Longer Clip | 1 nhân vật | "Character breathes. 5 seconds." |

Runner tự động:
1. Submit workflow → ComfyUI
2. Poll đến khi done
3. Fetch output video
4. Save tại `tests/benchmark/results/TEST-X_modelname.mp4`
5. Log thời gian, VRAM peak

**Deliverable:** Chạy `python runner.py` → 5 video xuất hiện trong `results/`.

---

### LV-012 · Benchmark Score Sheet
**Owner:** Antigravity
**Input:** LV-011 ✓ (videos đã có)
**Output:** `tests/benchmark/score_sheet.md` — template để bạn điền

Template:

```markdown
## Model: LTX-Video [version]
## Date: YYYY-MM-DD
## Hardware: GTX 1070 8GB

| Metric | TEST-A | TEST-B | TEST-C | TEST-D | TEST-E | AVG |
|---|---|---|---|---|---|---|
| Face Preservation /10 | | | | | | |
| Body Preservation /10 | | | | | | |
| Detail Preservation /10 | | | | | | |
| Background Stability /10 | | | | | | |
| Motion Accuracy /10 | | | | | | |
| Temporal Stability /10 | | | | | | |
| One-Subject Control /10 | | | | | | |
| Speed (s/video) | | | | | | |
| VRAM Peak (GB) | | | | | | |
| VRAM Pass (≤7.5GB) | | | | | | |
| RAM Pass (≤14GB) | | | | | | |
| Pascal Compat. | | | | | | |

## Notes:
```

**Deliverable:** Template file sẵn sàng để điền tay.

---

### 🔴 AUDIT KỸ · GATE-A — MODEL SELECTION
**Người audit:** Bạn (owner)
**Đây là quyết định không thể đảo ngược về hướng đi.**

**Bạn tự xem video và điền score sheet.**

**Tiêu chí PASS tối thiểu:**
- Face Preservation AVG ≥ 6/10
- Background Stability AVG ≥ 7/10
- VRAM Pass: True (không OOM)
- Temporal Stability AVG ≥ 6/10

**Quyết định:**
- [ ] Model A (LTX-Video) → PASS → tiếp tục Phase 2
- [ ] Model B (SVD-XT) → PASS → tiếp tục Phase 2
- [ ] Model C (CogVideoX-2B) → PASS → tiếp tục Phase 2
- [ ] Không model nào PASS → **DỪNG. Tìm model khác. Không build UI.**

> ⚠️ Ghi rõ model được chọn vào `docs/selected_model.md` trước khi giao LV-020.

---

## PHASE 2 — CORE I2V PIPELINE
> **Mục tiêu:** End-to-end pipeline: ảnh vào → video ra.
> **Thời gian:** 1–2 ngày
> **Dependency:** GATE-A passed. Model đã chọn.

---

### LV-020 · Image Input Handler
**Owner:** Antigravity
**Input:** GATE-A ✓
**Output:** `app/orchestration/image_handler.py`

```python
def load_image(source) -> dict:
    # source: filepath hoặc Gradio upload object
    # Validate: format (PNG/JPG/WEBP), size, readable
    # Convert sang PNG nếu cần
    # Trả về: {path, width, height, format, temp_path}
    pass

def prepare_for_inference(image_dict: dict) -> str:
    # Copy sang temp folder an toàn
    # Trả về temp_path để pass vào workflow
    pass
```

**Deliverable:** Unit test với 3 loại ảnh khác nhau → tất cả pass.

---

### LV-021 · Prompt Pipeline (RAW Mode)
**Owner:** Antigravity
**Input:** LV-020 ✓
**Output:** `app/orchestration/prompt_handler.py`

```python
def process_prompt(
    user_prompt: str,
    mode: str = "raw"  # "raw" | "cinematic" | "simple"
) -> dict:
    # RAW mode: user_prompt == inference_prompt, không sửa gì
    # Simple mode: thêm technical suffix (không sửa semantic)
    # Cinematic mode: thêm cinematic preset suffix
    # Trả về: {inference_prompt, negative_prompt, mode_applied}
    pass
```

**Quan trọng:** RAW mode tuyệt đối không được modify `user_prompt`.

**Deliverable:** Unit test verify `raw_mode_output == raw_mode_input`.

---

### LV-022 · ComfyUI API Client
**Owner:** Antigravity
**Input:** LV-021 ✓
**Output:** `app/orchestration/comfyui_client.py`

```python
class ComfyUIClient:
    def __init__(self, host="127.0.0.1", port=8188): pass

    def submit_workflow(self, workflow: dict) -> str:
        # Trả về job_id (prompt_id trong ComfyUI)
        pass

    def get_status(self, job_id: str) -> dict:
        # Trả về: {status, progress_pct, queue_position}
        pass

    def get_output(self, job_id: str) -> list:
        # Trả về: list output filenames
        pass

    def cancel_job(self, job_id: str) -> bool: pass

    def get_system_stats(self) -> dict: pass
```

**Deliverable:** Client connect được, submit test workflow, nhận output.

---

### LV-023 · Progress Monitor + WebSocket
**Owner:** Antigravity
**Input:** LV-022 ✓
**Output:** `app/orchestration/progress_monitor.py`

- Connect ComfyUI WebSocket tại `ws://127.0.0.1:8188/ws`
- Parse progress events
- Expose callback để UI update progress bar

**Deliverable:** Progress bar trong Gradio update real-time khi đang generate.

---

### LV-024 · Job Manager (Submit / Cancel / Status)
**Owner:** Antigravity
**Input:** LV-022 ✓, LV-023 ✓
**Output:** `app/jobs/job_manager.py`

```python
class JobManager:
    def submit(self, image_path, prompt, settings) -> str: pass  # job_id
    def cancel(self, job_id: str) -> bool: pass
    def get_status(self, job_id: str) -> dict: pass
    def list_active(self) -> list: pass
```

**Deliverable:** Submit job → Cancel mid-way → verify ComfyUI queue cleared.

---

### LV-025 · Seed Control
**Owner:** Antigravity
**Input:** LV-024 ✓
**Output:** Seed được inject vào workflow, reproducible

- Random seed khi không set
- Fixed seed khi user set
- Seed được lưu vào metadata

**Deliverable:** Cùng seed + cùng ảnh + cùng prompt → output tương đồng (không cần identical).

---

### LV-026 · Output Fetcher + Save MP4
**Owner:** Antigravity
**Input:** LV-022 ✓
**Output:** `app/orchestration/output_handler.py`

```python
def fetch_and_save(job_id: str, output_dir: str) -> dict:
    # Fetch video từ ComfyUI /view endpoint
    # Save tại outputs/YYYYMMDD_HHMMSS_seed.mp4
    # Trả về: {filepath, filename, size_mb, duration_s}
    pass
```

**Deliverable:** Video file xuất hiện đúng chỗ sau generation.

---

### LV-027 · Metadata Logger
**Owner:** Antigravity
**Input:** LV-026 ✓
**Output:** JSON sidecar file cạnh mỗi video

```json
{
  "version": "LocalI2V-0.1",
  "timestamp": "2026-08-27T10:00:00",
  "model": "ltx-video-v0.9",
  "seed": 12345,
  "prompt": "...",
  "negative_prompt": "...",
  "mode": "raw",
  "preserve_level": "balanced",
  "motion_level": "subtle",
  "camera": "static",
  "duration_frames": 48,
  "resolution": "512x288",
  "steps": 25,
  "source_image": "input_original.png",
  "output_video": "20260827_100000_12345.mp4"
}
```

**Deliverable:** Mỗi video có 1 file `.json` cùng tên kèm theo.

---

### LV-028 · Error Handling Layer
**Owner:** Antigravity
**Input:** Tất cả LV-020 → LV-027
**Output:** Centralized error handler

Các lỗi phải handle:
- ComfyUI không chạy / không connect
- OOM (Out of Memory)
- Model chưa load
- Image format không hỗ trợ
- Generation timeout (>5 phút)
- Output file không tìm thấy

Tất cả lỗi: hiển thị message rõ ràng trong UI, log vào file, **không crash app**.

**Deliverable:** Test từng lỗi trên → app hiển thị error message, không crash.

---

### 🔴 AUDIT KỸ · PHASE 2 GATE — END-TO-END TEST
**Người audit:** Bạn (owner)
**Test script:** Antigravity cung cấp `tests/e2e/test_core_pipeline.py`

**Test sequence:**
1. [ ] Mở app từ terminal mới (fresh start)
2. [ ] Drop ảnh → image preview hiển thị
3. [ ] Nhập prompt → submit
4. [ ] Progress bar chạy
5. [ ] Video xuất hiện trong UI sau khi done
6. [ ] File `.mp4` có trong `outputs/`
7. [ ] File `.json` metadata có cạnh video
8. [ ] Thử Cancel mid-generation → queue cleared
9. [ ] Thử ảnh sai format → error message (không crash)
10. [ ] Log file có ghi đầy đủ

**Nếu bất kỳ step nào fail:** Antigravity fix trước khi nhận Phase 3.

---

## PHASE 3 — PRESERVE + MOTION CONTROL
> **Mục tiêu:** User control được chất lượng preservation và motion intensity.
> **Thời gian:** 0.5–1 ngày

---

### LV-030 · Preserve Preset System
**Owner:** Antigravity
**Input:** Phase 2 ✓
**Output:** `app/presets/preserve/` — 4 preset files

```json
// preserve_low.json
{
  "image_strength": 0.70,
  "noise_aug_strength": 0.08,
  "description": "More creative freedom, less source fidelity"
}

// preserve_balanced.json
{
  "image_strength": 0.82,
  "noise_aug_strength": 0.04,
  "description": "Default — good balance"
}

// preserve_high.json
{
  "image_strength": 0.90,
  "noise_aug_strength": 0.02,
  "description": "Strong source preservation"
}

// preserve_maximum.json
{
  "image_strength": 0.95,
  "noise_aug_strength": 0.01,
  "description": "Maximum — subtle motion only"
}
```

> ⚠️ Các giá trị trên là placeholder. Antigravity phải calibrate từ benchmark thực tế với model đã chọn.

**Deliverable:** 4 presets tạo ra output khác nhau rõ ràng khi test.

---

### LV-031 · Motion Preset System
**Owner:** Antigravity
**Input:** LV-030 ✓
**Output:** `app/presets/motion/` — 3 preset files

```json
// motion_subtle.json
{
  "motion_bucket_id": 30,
  "fps": 8,
  "description": "Minimal motion — breathing, micro-expression"
}

// motion_normal.json
{
  "motion_bucket_id": 60,
  "fps": 8,
  "description": "Normal motion — head turn, gesture"
}

// motion_strong.json
{
  "motion_bucket_id": 100,
  "fps": 8,
  "description": "Strong — experimental on GTX 1070"
}
```

**Deliverable:** Motion Subtle vs Normal vs Strong tạo ra output khác nhau rõ.

---

### LV-032 · Camera Preset System
**Owner:** Antigravity
**Input:** Phase 2 ✓
**Output:** `app/presets/camera/` — 5 preset files

| Preset | Prompt Suffix Added |
|---|---|
| Static | "Fixed camera. No camera movement." |
| Slow Push In | "Very slow subtle push in. Minimal zoom." |
| Slow Pull Out | "Very slow subtle pull out. Minimal zoom out." |
| Small Pan Left | "Very subtle pan left. Slow." |
| Small Pan Right | "Very subtle pan right. Slow." |

Default: **Static**

**Deliverable:** Camera preset inject đúng suffix vào prompt. RAW mode bỏ qua camera preset.

---

### LV-033 · Preset Mapper (Model-Specific)
**Owner:** Antigravity
**Input:** LV-030, LV-031, LV-032 ✓
**Output:** `app/presets/preset_mapper.py`

```python
def map_presets_to_workflow(
    workflow: dict,
    model_name: str,
    preserve_preset: dict,
    motion_preset: dict,
    camera_preset: dict
) -> dict:
    # Inject preset values vào đúng node của workflow
    # Mỗi model có node ID khác nhau
    pass
```

**Deliverable:** Preset changes phản ánh trong workflow JSON trước khi submit.

---

### LV-034 · RAW Mode Implementation
**Owner:** Antigravity
**Input:** LV-021 ✓, LV-033 ✓
**Output:** RAW mode toggle trong UI + pipeline

Khi RAW mode ON:
- `inference_prompt = user_prompt` (byte-for-byte)
- Camera preset không được append
- Cinematic suffix không được thêm
- Chỉ technical parameters (steps, seed, resolution) được set

**Deliverable:** Unit test assert `inference_prompt == user_prompt` trong RAW mode.

---

### 🟡 AUDIT SƠ BỘ · Phase 3 Gate
**Người audit:** Bạn (owner)
**Test nhanh (15–20 phút):**
- [ ] Thay đổi Preserve từ Low → Maximum → video khác nhau rõ
- [ ] Thay đổi Motion từ Subtle → Normal → motion khác nhau
- [ ] RAW mode: nhập prompt lạ → output không bị sửa prompt
- [ ] Camera Static → không có camera movement trong output

---

## PHASE 4A — POST-PROCESSING PIPELINE
> **Mục tiêu:** Nâng resolution và FPS của output — đây là quality driver chính.
> **Thời gian:** 1 ngày

---

### LV-040 · FFmpeg Integration
**Owner:** Antigravity
**Input:** Phase 2 ✓
**Output:** `app/postprocess/ffmpeg_tools.py`

```python
def extract_frames(video_path: str, output_dir: str) -> list:
    # FFmpeg: video → PNG sequence
    # Trả về: list frame paths

def encode_video(
    frames_dir: str,
    output_path: str,
    fps: int = 24,
    codec: str = "libx264",
    crf: int = 18
) -> str:
    # FFmpeg: PNG sequence → MP4
    # Trả về: output_path

def get_video_info(video_path: str) -> dict:
    # ffprobe: duration, fps, resolution, codec
    pass
```

**Deliverable:** Extract frames → re-encode → output video bình thường.

---

### LV-041 · Real-ESRGAN Upscaler
**Owner:** Antigravity
**Input:** LV-040 ✓
**Output:** `app/postprocess/upscaler.py`

Setup:
```bash
pip install realesrgan
# Download weights: RealESRGAN_x4plus.pth hoặc RealESRGAN_x4plus_anime_6B.pth
```

```python
def upscale_frames(
    input_frames: list,
    output_dir: str,
    scale: int = 4,
    model: str = "anime"  # "anime" | "realistic"
) -> list:
    # Input: 480×270 PNG list
    # Output: 1920×1080 PNG list
    pass

def upscale_video(video_path: str, output_path: str, scale: int = 4) -> str:
    # Convenience: video → upscale → video
    pass
```

> ⚠️ Real-ESRGAN sử dụng GPU. Test VRAM không OOM khi chạy sau generation.

**Deliverable:** 480p frames → 1080p frames, không OOM trên GTX 1070.

---

### 🟡 AUDIT SƠ BỘ · LV-041-CHK — VRAM CHECK
**Người audit:** Bạn (owner)
**Checklist:**
- [ ] Upscale 24 frames 480p → 1080p thành công
- [ ] VRAM không OOM trong quá trình upscale
- [ ] Thời gian upscale ≤ 2 phút cho 24 frames
- [ ] Output quality rõ ràng tốt hơn input

> Nếu VRAM OOM: Antigravity thêm option "upscale on CPU" (chậm hơn nhưng không OOM).

---

### LV-042 · RIFE Frame Interpolation
**Owner:** Antigravity
**Input:** LV-041 ✓
**Output:** `app/postprocess/interpolator.py`

Setup:
```bash
# Dùng rife-ncnn-vulkan (không cần CUDA riêng)
# hoặc ECCV2022-RIFE Python package
```

```python
def interpolate_frames(
    input_frames: list,
    output_dir: str,
    target_fps: int = 24,
    source_fps: int = 8
) -> list:
    # Input: 8fps frame list
    # Output: 24fps frame list (interpolated)
    pass
```

**Deliverable:** 8fps video → 24fps video, motion mượt hơn, không artifact nặng.

---

### LV-043 · CodeFormer Face Restore (Optional Tool)
**Owner:** Antigravity
**Input:** LV-041 ✓
**Output:** `app/postprocess/face_restorer.py`

```python
def restore_faces(
    input_frames: list,
    output_dir: str,
    fidelity: float = 0.7  # 0=quality, 1=fidelity
) -> list:
    # Dùng CodeFormer hoặc GFPGAN
    # Chạy sau upscale, trước encode
    pass
```

> ⚠️ Đây là **optional** — chỉ bật khi user yêu cầu. Toggle riêng trong UI.
> Thứ tự: Generate → Upscale → **Face Restore** → Interpolate → Encode

**Deliverable:** Face detail rõ hơn sau restore, không tạo artifact kỳ lạ.

---

### LV-044 · Post-Process Orchestrator
**Owner:** Antigravity
**Input:** LV-040, LV-041, LV-042, LV-043 ✓
**Output:** `app/postprocess/pipeline.py`

```python
class PostProcessPipeline:
    def __init__(self, config: dict): pass

    def run(self, input_video: str, output_path: str) -> dict:
        # Step 1: Extract frames
        # Step 2: Upscale (nếu enabled)
        # Step 3: Face Restore (nếu enabled)
        # Step 4: Interpolate (nếu enabled)
        # Step 5: Encode final MP4
        # Trả về: {output_path, resolution, fps, duration, size_mb}
        pass
```

Config example:
```python
config = {
    "upscale": True,
    "upscale_model": "anime",
    "face_restore": False,
    "interpolate": True,
    "target_fps": 24,
    "output_codec": "libx264",
    "output_crf": 18
}
```

**Deliverable:** Pipeline chạy end-to-end: raw video → final 1080p/24fps MP4.

---

### 🔴 AUDIT KỸ · Phase 4A GATE — QUALITY CHECK
**Người audit:** Bạn (owner)

**Test với video từ Phase 2:**

| Bước | Input | Output | Kiểm tra |
|---|---|---|---|
| Raw output | 480p / 8fps / 3s | — | Source video |
| Sau upscale | → | 1080p / 8fps / 3s | Rõ hơn, không artifact |
| Sau interpolate | → | 1080p / 24fps / 3s | Mượt hơn, không ghost |
| Sau encode | → | Final MP4 | Play OK, size hợp lý |

**Checklist:**
- [ ] 1080p output rõ ràng hơn 480p raw
- [ ] 24fps mượt hơn 8fps rõ ràng
- [ ] Không có ghosting artifact nặng ở interpolation
- [ ] Face detail được giữ tốt sau upscale
- [ ] Total post-process time ≤ 5 phút
- [ ] Không OOM trong suốt pipeline

---

## PHASE 4B — SUBJECT CONTROL (Prompt-Based)
> **Mục tiêu:** User có thể chỉ định subject nào chuyển động — V0.1 dùng prompt engineering.
> **Thời gian:** 0.5 ngày

---

### LV-045 · Subject Prompt Builder
**Owner:** Antigravity
**Input:** Phase 2 ✓
**Output:** `app/orchestration/subject_handler.py`

```python
def build_subject_prompt(
    base_prompt: str,
    animate_target: str = "primary_subject",
    # "primary_subject" | "left_character" | "right_character" | "foreground" | custom text
    static_targets: list = []
) -> str:
    # Construct prompt với subject control hints
    # RAW mode: bypass hoàn toàn
    pass
```

Ví dụ output:
```
"[base_prompt] Focus motion on the left character only.
 The right character remains completely still.
 Background is static. Camera is fixed."
```

**Deliverable:** Subject selector trong UI → prompt được build đúng → submit.

---

### LV-046 · Subject Selection UI
**Owner:** Antigravity
**Input:** LV-045 ✓
**Output:** UI component trong Gradio

Options:
- Auto (không chỉ định)
- Primary Subject
- Left Character
- Right Character
- Foreground Subject
- Custom (free text)

**Deliverable:** Dropdown hoạt động, selection ảnh hưởng đến generated prompt.

---

### 🟢 SELF-CHECK · Phase 4B
**Antigravity tự verify:**
- [ ] Subject selection thay đổi prompt output đúng
- [ ] RAW mode bypass subject handler
- [ ] UI dropdown không crash với bất kỳ selection nào

---

## PHASE 5 — QUEUE + HISTORY
> **Mục tiêu:** Quản lý jobs, xem lại lịch sử, reproduce generation.
> **Thời gian:** 0.5–1 ngày

---

### LV-050 · SQLite Job Database
**Owner:** Antigravity
**Input:** Phase 2 ✓
**Output:** `app/jobs/job_db.py`

Schema:
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    status TEXT,           -- queued|running|done|failed|cancelled
    created_at TEXT,
    completed_at TEXT,
    image_path TEXT,
    prompt TEXT,
    settings_json TEXT,
    output_video TEXT,
    metadata_json TEXT,
    error_message TEXT
);
```

**Deliverable:** Jobs persist qua restart app.

---

### LV-051 · History Panel UI
**Owner:** Antigravity
**Input:** LV-050 ✓
**Output:** History tab trong Gradio

Hiển thị:
- Thumbnail của output video
- Prompt (truncated)
- Timestamp
- Status badge (done/failed)
- Buttons: Play / Open Folder / Retry / Duplicate Settings

**Deliverable:** History tab hiển thị 10 jobs gần nhất, persist qua restart.

---

### LV-052 · Retry + Duplicate Settings
**Owner:** Antigravity
**Input:** LV-051 ✓
**Output:** Actions trong history

- **Retry:** Load lại exact settings → submit job mới
- **Duplicate:** Load settings → user chỉnh → submit
- **Reuse Seed:** Copy seed sang new job

**Deliverable:** Retry tạo job mới với settings giống hệt job cũ.

---

### LV-053 · Open Output Folder
**Owner:** Antigravity
**Input:** LV-026 ✓
**Output:** Button "Open Folder" mở file explorer tại `outputs/`

```python
import subprocess, platform

def open_folder(path: str):
    if platform.system() == "Windows":
        subprocess.Popen(["explorer", path])
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
```

**Deliverable:** Button click → folder mở trong OS file explorer.

---

### 🟢 SELF-CHECK · Phase 5
**Antigravity tự verify:**
- [ ] Generate 3 jobs → tất cả xuất hiện trong History
- [ ] Restart app → History vẫn còn
- [ ] Retry job → video mới được tạo
- [ ] Open Folder button hoạt động

---

## PHASE 6 — UI FINAL CLEANUP
> **Mục tiêu:** UI gọn gàng, usable, không rối.
> **Thời gian:** 0.5 ngày

---

### LV-060 · UI Layout Final
**Owner:** Antigravity
**Input:** Tất cả phases ✓
**Output:** UI hoàn chỉnh, layout đúng

```
┌─────────────────────────────────────────────────────┐
│  LocalI2V V0.1                                      │
├──────────────────┬──────────────────────────────────┤
│                  │  MOTION PROMPT                   │
│  [ Drop Image ]  │  ________________________________│
│  [ Preview ]     │                                  │
│                  │  SUBJECT:   [Auto ▼]             │
│                  │  PRESERVE:  [Balanced ▼]         │
│                  │  MOTION:    [Subtle ▼]           │
│                  │  CAMERA:    [Static ▼]           │
│                  │  DURATION:  [5s ▼]               │
│                  │                                  │
│                  │  [ ▶ GENERATE ]                  │
│                  │  [ ■ CANCEL ]                    │
│                  │                                  │
│                  │  ▼ Advanced                      │
│                  │    Seed / Steps / Mode (Raw)     │
│                  │    Negative Prompt               │
├──────────────────┴──────────────────────────────────┤
│ POST-PROCESS:                                       │
│ [✓ Upscale 4x] [✓ Interpolate 24fps] [Face Restore]│
├─────────────────────────────────────────────────────┤
│ PROGRESS: [████████░░] 80% — Step 20/25             │
├─────────────────────────────────────────────────────┤
│ OUTPUT PREVIEW: [ video player ]                    │
├─────────────────────────────────────────────────────┤
│ HISTORY                                             │
│ [▸ Job 1 — done] [▸ Job 2 — done] [▸ Job 3 — fail] │
└─────────────────────────────────────────────────────┘
```

**Deliverable:** UI sạch, không component thừa.

---

### LV-061 · Mode Toggle (Simple / Cinematic / Raw)
**Owner:** Antigravity
**Input:** LV-034 ✓
**Output:** Mode selector rõ ràng trong UI

- **Simple:** Chỉ cần drop ảnh + prompt → generate. Tool tự chọn settings.
- **Cinematic:** Preset bật tự động (stable, preserve cao).
- **Raw:** Tất cả preset bị bypass. User kiểm soát hoàn toàn.

**Deliverable:** Switching mode thay đổi UI (ẩn/hiện controls phù hợp).

---

### LV-062 · Startup Checker
**Owner:** Antigravity
**Input:** LV-003 ✓
**Output:** `app/system/startup_check.py` — chạy khi app start

Checks:
1. GPU available?
2. ComfyUI running?
3. Model loaded?
4. Output folder writable?
5. FFmpeg available?

Hiển thị status trong UI header:
```
● GPU: GTX 1070 (7.8GB free)  ● ComfyUI: Connected  ● Model: LTX-Video
```

**Deliverable:** Status bar hiển thị accurate system state.

---

### 🔴 AUDIT KỸ · GATE-C — RELEASE CHECKLIST
**Người audit:** Bạn (owner)
**Test Fresh Start hoàn toàn — không dùng state từ session trước.**

**End-to-End Test:**
1. [ ] Restart máy tính (optional nhưng khuyến khích)
2. [ ] Start ComfyUI: `python comfyui/main.py --listen 127.0.0.1`
3. [ ] Start app: `python app/ui/main_ui.py`
4. [ ] Status bar hiển thị GPU + ComfyUI connected
5. [ ] Drop ảnh → preview đúng
6. [ ] Nhập prompt → Generate → progress bar chạy
7. [ ] Video xuất hiện trong Output Preview
8. [ ] Post-process chạy: 1080p / 24fps
9. [ ] Metadata JSON có đủ fields
10. [ ] Open Folder → file explorer mở đúng
11. [ ] History hiển thị job vừa tạo
12. [ ] Lấy seed từ job → Retry → output tương đồng
13. [ ] Tắt app → Start lại → History vẫn còn
14. [ ] RAW mode: prompt không bị sửa

**Privacy Check:**
- [ ] Mở Network Monitor → không có outbound request trong Generation
- [ ] Không file nào được upload lên internet

**Nếu tất cả pass:** V0.1 Released ✓

---

## TỔNG QUAN TASK TRACKER

| Phase | Task | Status | Audit Required |
|---|---|---|---|
| **P0** | LV-001 Repo Structure | `[ ]` | 🟢 Self |
| **P0** | LV-002 Python Env | `[ ]` | 🟡 Sơ bộ |
| **P0** | LV-003 GPU Detection | `[ ]` | 🟢 Self |
| **P0** | LV-004 ComfyUI Setup | `[ ]` | 🔴 **KỸ** |
| **P0** | LV-005 Gradio Shell | `[ ]` | 🟢 Self |
| **P0** | LV-006 Logging | `[ ]` | 🟢 Self |
| **P1** | LV-010 Workflow Builder | `[ ]` | 🟢 Self |
| **P1** | LV-011 Benchmark Runner | `[ ]` | 🟢 Self |
| **P1** | LV-012 Score Sheet | `[ ]` | 🔴 **GATE-A** |
| **P2** | LV-020 Image Handler | `[ ]` | 🟢 Self |
| **P2** | LV-021 Prompt Pipeline | `[ ]` | 🟢 Self |
| **P2** | LV-022 ComfyUI Client | `[ ]` | 🟢 Self |
| **P2** | LV-023 Progress Monitor | `[ ]` | 🟢 Self |
| **P2** | LV-024 Job Manager | `[ ]` | 🟢 Self |
| **P2** | LV-025 Seed Control | `[ ]` | 🟢 Self |
| **P2** | LV-026 Output Saver | `[ ]` | 🟢 Self |
| **P2** | LV-027 Metadata Logger | `[ ]` | 🟢 Self |
| **P2** | LV-028 Error Handler | `[ ]` | 🔴 **KỸ** |
| **P3** | LV-030 Preserve Presets | `[ ]` | 🟢 Self |
| **P3** | LV-031 Motion Presets | `[ ]` | 🟢 Self |
| **P3** | LV-032 Camera Presets | `[ ]` | 🟢 Self |
| **P3** | LV-033 Preset Mapper | `[ ]` | 🟡 Sơ bộ |
| **P3** | LV-034 RAW Mode | `[ ]` | 🟡 Sơ bộ |
| **P4A** | LV-040 FFmpeg Tools | `[ ]` | 🟢 Self |
| **P4A** | LV-041 ESRGAN Upscaler | `[ ]` | 🟡 Sơ bộ |
| **P4A** | LV-042 RIFE Interpolator | `[ ]` | 🟢 Self |
| **P4A** | LV-043 Face Restorer | `[ ]` | 🟢 Self |
| **P4A** | LV-044 Post Pipeline | `[ ]` | 🔴 **KỸ** |
| **P4B** | LV-045 Subject Prompt | `[ ]` | 🟢 Self |
| **P4B** | LV-046 Subject UI | `[ ]` | 🟢 Self |
| **P5** | LV-050 SQLite DB | `[ ]` | 🟢 Self |
| **P5** | LV-051 History Panel | `[ ]` | 🟢 Self |
| **P5** | LV-052 Retry/Duplicate | `[ ]` | 🟢 Self |
| **P5** | LV-053 Open Folder | `[ ]` | 🟢 Self |
| **P6** | LV-060 UI Final | `[ ]` | 🟢 Self |
| **P6** | LV-061 Mode Toggle | `[ ]` | 🟢 Self |
| **P6** | LV-062 Startup Checker | `[ ]` | 🔴 **GATE-C** |

---

## AUDIT GATES SUMMARY

| Gate | Trigger | Người audit | Action nếu fail |
|---|---|---|---|
| 🟡 LV-002-CHK | Sau LV-002 | Bạn | Fix môi trường trước |
| 🔴 LV-004-CHK | Sau LV-004 | Bạn | Thử model khác |
| 🔴 GATE-A | Sau Phase 1 | Bạn | Không build UI nếu không có model |
| 🔴 P2-GATE | Sau Phase 2 | Bạn | Fix pipeline trước khi nhận P3 |
| 🟡 P3-GATE | Sau Phase 3 | Bạn | Check preset effect |
| 🟡 LV-041-CHK | Sau LV-041 | Bạn | Fallback CPU upscale |
| 🔴 P4A-GATE | Sau Phase 4A | Bạn | Quality baseline decision |
| 🔴 GATE-C | Sau Phase 6 | Bạn | Final release sign-off |

---

## RULES CHO ANTIGRAVITY

```
1. Hoàn thành từng Task → báo cáo output cụ thể trước khi nhận Task tiếp.
2. Không gộp nhiều Task thành 1 lần commit lớn.
3. Không tự ý thêm feature ngoài scope của Task.
4. Không tự restructure repo khi không được yêu cầu.
5. Mỗi Task phải có Deliverable cụ thể, testable.
6. Tại các AUDIT KỸ (🔴): dừng, báo cáo, đợi confirm mới tiếp.
7. RAW mode: không bao giờ modify user_prompt.
8. Privacy: không có remote call trong generation pipeline.
```

---

## KHÔNG THUỘC SCOPE V0.1

- Text-to-Video
- Audio / Music / Lip Sync
- Cloud / API / Account
- Multi-shot / Timeline
- Training models
- SAM2 segmentation (→ V0.2)
- Multi-keyframe (→ V0.3)
