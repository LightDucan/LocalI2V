# LocalI2V V0.1 — Release Specification & User Guide

**Release Version:** V0.1  
**Release Status:** RELEASED  
**Release Gate:** OWNER GATE M3 = PASS  
**Target Hardware:** NVIDIA GeForce GTX 1070 8GB VRAM (Pascal `sm_61`), 16GB System RAM, Windows 10/11.  

---

## 1. System & Component Versions

| Component | Pinned Version / Checksum | Notes |
|---|---|---|
| **Selected Checkpoint** | `ltxv-2b-0.9.6-distilled-04-25.safetensors` | SHA256: `94891bd4bd08de30d484befbfc54fdcffe6d1596a131baad700b9baa5e1de86b` |
| **Text Encoder** | `t5xxl_fp8_e4m3fn.safetensors` | SHA256: `7d330da4816157540d6bb7838bf63a0f02f573fc48ca4d8de34bb0cbfd514f09` |
| **Python Runtime** | `3.10.11` | Virtual environment pinned at `.venv/` |
| **PyTorch Family** | `torch==2.13.0+cu126`, `torchvision==0.28.0+cu126`, `torchaudio==2.11.0+cu126` | Pinned cu126 runtime index |
| **ComfyUI Backend** | `v0.33.1` (Commit: `8aef9f3`) | ComfyUI v0.33.1 pinned by bootstrap/local checkout |
| **Upscaling Tool** | `realesrgan-ncnn-vulkan` `v0.2.5.0` (`realesr-animevideov3-x2` for 2x) | Hardware Vulkan GPU acceleration |
| **Interpolation Tool** | `rife-ncnn-vulkan` `v20221029` (`rife-v4.6`) | Hardware Vulkan GPU acceleration |
| **Video Encoding** | FFmpeg 8.1.1-essentials / FFprobe | H.264, yuv420p, CRF 18 |
| **Database** | SQLite 3 (Python standard library `sqlite3`) | `outputs/locali2v_history.db` |
| **User Interface** | Gradio 6.5.1 | Bound strictly to `127.0.0.1:7860`, `share=False` |

---

## 2. Quickstart & Windows Launch

To start LocalI2V with a single command from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_locali2v.ps1
```

This automated launcher will:
1. Validate the local Python and GPU environment (`scripts/check_env.py`).
2. Start or detect the local ComfyUI backend on `127.0.0.1:8188` using validated flags:
   `--listen 127.0.0.1 --port 8188 --disable-xformers --use-split-cross-attention --lowvram`
3. Launch the LocalI2V Gradio Web UI on `http://127.0.0.1:7860`.

---

## 3. Verified Performance Baselines (GTX 1070 8GB)

| Metric | Raw Generation Baseline | Enhanced Output |
|---|---|---|
| **Resolution** | `512x288` (16:9) | `1024x576` (2x upscale, 16:9 preserved) |
| **Frame Rate** | `8.0 fps` | `24.0 fps` (smooth temporal interpolation) |
| **Frame Count** | 25-26 frames | 76 frames |
| **Clip Duration** | ~3.12 - 3.17 seconds | ~3.12 - 3.17 seconds |
| **Generation Time** | ~60s - 64s (steady-state 8 steps) | ~60s - 64s |
| **Post-Processing Time** | N/A | **~5.3s - 6.6s** (2x Real-ESRGAN + RIFE 24fps) |
| **Total Turnaround Time** | ~64s | **~70s** |
| **Peak VRAM Usage** | **7.84 GB / 8.00 GB** (`nvidia-smi` across processes) | Zero OOM |
| **Peak RAM Usage** | **14.08 GB / 16.00 GB** (`psutil` system RAM) | Safe system headroom |

---

## 4. Privacy & Offline Invariant

- **Generation Runtime Privacy**: Generation runtime was verified using localhost services only after all models/tools were installed. Outbound socket monitoring confirmed zero non-loopback connections during generation.
- **Offline Capable**: Once model weights and standalone Vulkan tools are present, zero internet access is required for operation.
- **RAW Mode Invariant**: When prompt mode is set to `RAW`, `inference_prompt == user_prompt` byte-for-byte with zero unsolicited camera, cinematic, or subject suffixes.

---

## 5. Known Limitations & V0.1 Operating Guidance

1. **Prompt Motion Adherence**: Subtle character motion (e.g. eye blinks, gentle head turns) is well captured; however, complex multi-step body actions have modest prompt adherence in the 2B distilled model.
2. **Two-Subject Control**: Two-subject identity separation is marked **Experimental** in the UI due to identity blending observed on complex multi-character scenes.
3. **Native Generation Resolution**: Base diffusion generates at `512x288` to guarantee ~60-64 seconds generation time and zero OOM on 8GB VRAM. High-definition output is achieved via the integrated 2x Vulkan upscaler.
4. **Hardware Compatibility**: The Pascal GTX 1070 path relies on the pinned `torch==2.13.0+cu126` and ComfyUI `--disable-xformers --use-split-cross-attention --lowvram` flags.
5. **PSNR Guard Fallback**: If an AI upscale tile anomaly is detected ($\text{PSNR} < 18.0\text{ dB}$), the pipeline automatically and safely falls back to FFmpeg Lanczos 2x upscaling without failing the user job.
