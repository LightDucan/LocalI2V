from __future__ import annotations

import copy
from typing import Any


class LTXVModelAdapter:
    """
    Adapter for LTX-Video 2B distilled checkpoint workflow in ComfyUI.
    Encapsulates all node IDs and model-specific parameter mappings.
    Calibrated in V0.1.1 to enable noticeable subject motion while preserving identity.
    """

    # Semantic mappings for Preserve Fidelity
    PRESERVE_PROFILES = {
        "low": {"steps": 8, "cfg": 3.2, "denoise": 1.0, "strength": 0.72},
        "balanced": {"steps": 8, "cfg": 3.0, "denoise": 1.0, "strength": 0.82},
        "normal": {"steps": 8, "cfg": 3.0, "denoise": 1.0, "strength": 0.82},
        "high": {"steps": 8, "cfg": 3.4, "denoise": 0.95, "strength": 0.92},
        "maximum": {"steps": 8, "cfg": 3.8, "denoise": 0.90, "strength": 0.98},
    }

    # Semantic mappings for Motion Dynamics
    MOTION_PROFILES = {
        "subtle": {"frame_rate": 10.0, "cfg_delta": -0.2, "strength_delta": 0.06},
        "normal": {"frame_rate": 8.0, "cfg_delta": 0.0, "strength_delta": 0.0},
        "strong": {"frame_rate": 6.0, "cfg_delta": 0.4, "strength_delta": -0.08},
    }

    @classmethod
    def apply_controls(
        cls,
        workflow: dict[str, Any],
        preserve: str = "normal",
        motion: str = "normal",
        custom_seed: int | None = None,
        custom_steps: int | None = None,
        custom_cfg: float | None = None,
    ) -> dict[str, Any]:
        """
        Applies semantic Preserve and Motion settings to the LTX-Video workflow graph.
        Returns a modified copy of the workflow dictionary with safe parameter clamping.
        """
        wf = copy.deepcopy(workflow)

        preserve_cfg = cls.PRESERVE_PROFILES.get(preserve.lower(), cls.PRESERVE_PROFILES["normal"])
        motion_cfg = cls.MOTION_PROFILES.get(motion.lower(), cls.MOTION_PROFILES["normal"])

        steps = custom_steps if custom_steps is not None else preserve_cfg["steps"]
        base_cfg = preserve_cfg["cfg"]
        cfg = round(custom_cfg if custom_cfg is not None else (base_cfg + motion_cfg["cfg_delta"]), 3)
        
        # Calculate effective strength
        base_strength = preserve_cfg["strength"]
        effective_strength = round(max(0.60, min(1.0, base_strength + motion_cfg["strength_delta"])), 3)
        
        denoise = preserve_cfg["denoise"]
        frame_rate = motion_cfg["frame_rate"]

        # Safe parameter clamping for distilled LTXV
        steps = max(6, min(10, int(steps)))
        cfg = max(2.0, min(4.5, float(cfg)))
        denoise = max(0.80, min(1.0, float(denoise)))

        # Node 5: LTXVConditioning -> frame_rate
        if "5" in wf and "inputs" in wf["5"]:
            wf["5"]["inputs"]["frame_rate"] = float(frame_rate)

        # Node 7: LTXVImgToVideo -> strength, batch_size
        if "7" in wf and "inputs" in wf["7"]:
            wf["7"]["inputs"]["strength"] = float(effective_strength)
            wf["7"]["inputs"]["batch_size"] = 1
            if "batch_type" in wf["7"]["inputs"]:
                del wf["7"]["inputs"]["batch_type"]

        # Node 8: KSampler -> seed, steps, cfg, denoise
        if "8" in wf and "inputs" in wf["8"]:
            if custom_seed is not None and custom_seed >= 0:
                wf["8"]["inputs"]["seed"] = int(custom_seed)
            wf["8"]["inputs"]["steps"] = int(steps)
            wf["8"]["inputs"]["cfg"] = float(cfg)
            wf["8"]["inputs"]["denoise"] = float(denoise)

        return wf
