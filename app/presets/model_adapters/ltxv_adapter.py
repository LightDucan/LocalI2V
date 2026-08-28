from __future__ import annotations

import copy
from typing import Any


class LTXVModelAdapter:
    """
    Adapter for LTX-Video 2B distilled checkpoint workflow in ComfyUI.
    Encapsulates all node IDs and model-specific parameter mappings.
    """

    # Semantic mappings for Preserve Fidelity
    PRESERVE_PROFILES = {
        "low": {"steps": 8, "cfg": 2.5, "denoise": 1.0, "strength": 0.90},
        "balanced": {"steps": 8, "cfg": 3.0, "denoise": 1.0, "strength": 1.0},
        "normal": {"steps": 8, "cfg": 3.0, "denoise": 1.0, "strength": 1.0},
        "high": {"steps": 8, "cfg": 3.5, "denoise": 0.92, "strength": 1.0},
        "maximum": {"steps": 10, "cfg": 4.0, "denoise": 0.85, "strength": 1.0},
    }

    # Semantic mappings for Motion Dynamics
    MOTION_PROFILES = {
        "subtle": {"frame_rate": 12.0, "cfg_delta": -0.5},
        "normal": {"frame_rate": 8.0, "cfg_delta": 0.0},
        "strong": {"frame_rate": 6.0, "cfg_delta": 0.5},
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
        Returns a modified copy of the workflow dictionary.
        """
        wf = copy.deepcopy(workflow)

        preserve_cfg = cls.PRESERVE_PROFILES.get(preserve.lower(), cls.PRESERVE_PROFILES["normal"])
        motion_cfg = cls.MOTION_PROFILES.get(motion.lower(), cls.MOTION_PROFILES["normal"])

        steps = custom_steps if custom_steps is not None else preserve_cfg["steps"]
        base_cfg = preserve_cfg["cfg"]
        cfg = custom_cfg if custom_cfg is not None else max(1.0, base_cfg + motion_cfg["cfg_delta"])
        denoise = preserve_cfg["denoise"]
        strength = preserve_cfg["strength"]
        frame_rate = motion_cfg["frame_rate"]

        # Node 5: LTXVConditioning -> frame_rate
        if "5" in wf and "inputs" in wf["5"]:
            wf["5"]["inputs"]["frame_rate"] = float(frame_rate)

        # Node 7: LTXVImgToVideo -> strength, batch_size
        if "7" in wf and "inputs" in wf["7"]:
            wf["7"]["inputs"]["strength"] = float(strength)
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
