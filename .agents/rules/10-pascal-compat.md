# GTX 1070 / Pascal Compatibility Rules

Target hardware: NVIDIA GTX 1070 8GB, Pascal compute capability sm_61, 16GB system RAM.

1. Do not install default/current CUDA 13.x PyTorch wheels. Pascal is on the CUDA 12.6 legacy path.
2. Baseline runtime: Python 3.10 x64 + PyTorch 2.13.0 / TorchVision 0.28.0 from the `cu126` index.
3. Verify `sm_61` appears in `torch.cuda.get_arch_list()` before model work.
4. Do not install the current `ComfyUI-LTXVideo` extension as the default path: current extension targets LTX-2-class hardware. Start with ComfyUI core LTXV support and legacy LTX-Video 2B.
5. First model candidate: `ltxv-2b-0.9.6-distilled` using its I2V workflow. Try 0.9.8 2B distilled only if needed.
6. SVD-XT is hardware fallback only; it cannot satisfy text-controlled motion requirements. Do not present it as feature-equivalent.
7. Remove CogVideoX-2B from I2V candidates; the official I2V line is 5B-I2V.
8. LTXV frame counts must follow the workflow/node constraint (9 + 8n). Use 25 frames for ~3s at 8fps and 41 frames for ~5s, not 24/48.
9. Start ComfyUI conservatively with `--disable-xformers --use-split-cross-attention --lowvram`; change flags only with measured evidence.
10. Do not force FP32 globally unless debugging correctness; it increases memory pressure on an 8GB card.
11. Fixed generation timeout of 5 minutes is forbidden until a real baseline exists. Derive timeout from benchmark measurements.
12. With only 16GB RAM, check Windows pagefile and disk headroom before long/offloaded inference. Prefer system-managed pagefile with ample free disk.
