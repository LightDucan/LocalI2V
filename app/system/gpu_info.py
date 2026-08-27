from __future__ import annotations


def get_gpu_info() -> dict:
    try:
        import torch
    except Exception as exc:  # environment probe must not crash on missing torch
        return {"cuda_available": False, "error": f"torch import failed: {exc}"}

    if not torch.cuda.is_available():
        return {
            "cuda_available": False,
            "torch_version": torch.__version__,
            "cuda_runtime": torch.version.cuda,
        }

    index = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(index)
    free_bytes, total_bytes = torch.cuda.mem_get_info(index)
    return {
        "cuda_available": True,
        "name": props.name,
        "compute_capability": f"{props.major}.{props.minor}",
        "vram_total_gb": round(total_bytes / 1024**3, 2),
        "vram_free_gb": round(free_bytes / 1024**3, 2),
        "torch_version": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "arch_list": torch.cuda.get_arch_list(),
    }


def check_minimum_requirements(info: dict | None = None) -> bool:
    info = info or get_gpu_info()
    if not info.get("cuda_available"):
        return False
    return float(info.get("vram_total_gb", 0)) >= 7.0
