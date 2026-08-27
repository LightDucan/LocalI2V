from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
import psutil

COMFY_URL = 'http://127.0.0.1:8188'
ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_TEMPLATE = ROOT / 'app' / 'orchestration' / 'workflow_ltxv_i2v.json'
OUTPUTS_DIR = ROOT / 'outputs' / 'benchmark'
COMFY_OUTPUT_DIR = ROOT / 'comfyui' / 'output'
COMFY_INPUT_DIR = ROOT / 'comfyui' / 'input'


def get_memory_stats() -> dict:
    ram = psutil.virtual_memory()
    stats = {
        'ram_used_gb': round((ram.total - ram.available) / (1024**3), 2),
        'ram_total_gb': round(ram.total / (1024**3), 2),
        'vram_used_gb': 0.0,
        'vram_total_gb': 8.0,
    }
    try:
        import torch
        if torch.cuda.is_available():
            free_b, total_b = torch.cuda.mem_get_info()
            stats['vram_used_gb'] = round((total_b - free_b) / (1024**3), 2)
            stats['vram_total_gb'] = round(total_b / (1024**3), 2)
    except Exception:
        pass
    return stats


def run_generation(test_name: str, prompt: str, image_name: str, seed: int = 42, steps: int = 8, width: int = 512, height: int = 288, length: int = 25, fps: float = 8.0) -> dict:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORKFLOW_TEMPLATE, 'r', encoding='utf-8') as f:
        wf = json.load(f)

    prefix = f'bench_{test_name}_{int(time.time())}'
    wf['3']['inputs']['text'] = prompt
    wf['4']['inputs']['text'] = 'low quality, worst quality, deformed, distorted, blurry, jerky motion'
    wf['5']['inputs']['frame_rate'] = fps
    wf['6']['inputs']['image'] = image_name
    wf['7']['inputs']['width'] = width
    wf['7']['inputs']['height'] = height
    wf['7']['inputs']['length'] = length
    wf['7']['inputs']['batch_size'] = 1
    if 'batch_type' in wf['7']['inputs']:
        del wf['7']['inputs']['batch_type']
    wf['8']['inputs']['seed'] = seed
    wf['8']['inputs']['steps'] = steps
    wf['8']['inputs']['cfg'] = 3.0
    wf['10']['inputs']['filename_prefix'] = prefix

    client_id = str(uuid.uuid4())
    req_data = json.dumps({'prompt': wf, 'client_id': client_id}).encode('utf-8')
    req = urllib.request.Request(f'{COMFY_URL}/prompt', data=req_data, headers={'Content-Type': 'application/json'})

    t0 = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read())
    prompt_id = res['prompt_id']

    peak_ram = 0.0
    peak_vram = 0.0
    completed = False
    output_files = []

    for _ in range(600):
        m = get_memory_stats()
        peak_ram = max(peak_ram, m['ram_used_gb'])
        peak_vram = max(peak_vram, m['vram_used_gb'])

        try:
            with urllib.request.urlopen(f'{COMFY_URL}/history/{prompt_id}') as h_resp:
                h_data = json.loads(h_resp.read())
                if prompt_id in h_data:
                    item = h_data[prompt_id]
                    status = item.get('status', {})
                    if status.get('completed', False):
                        completed = True
                        node_outputs = item.get('outputs', {})
                        for n_id, n_out in node_outputs.items():
                            if 'images' in n_out:
                                output_files = [img['filename'] for img in n_out['images']]
                        break
        except Exception:
            pass
        time.sleep(1)

    t1 = time.perf_counter()
    wall_time = round(t1 - t0, 2)

    mp4_path = OUTPUTS_DIR / f'{test_name}.mp4'
    if output_files:
        temp_list = COMFY_OUTPUT_DIR / f'{prefix}_filelist.txt'
        with open(temp_list, 'w', encoding='utf-8') as f:
            for fname in sorted(output_files):
                fpath = (COMFY_OUTPUT_DIR / fname).resolve().as_posix()
                f.write(f"file '{fpath}'\n")
                f.write(f"duration {1.0/fps}\n")
            last_path = (COMFY_OUTPUT_DIR / sorted(output_files)[-1]).resolve().as_posix()
            f.write(f"file '{last_path}'\n")

        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(temp_list),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
            str(mp4_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if temp_list.exists():
            temp_list.unlink()

    meta = {
        'test_name': test_name,
        'prompt': prompt,
        'image_name': image_name,
        'seed': seed,
        'steps': steps,
        'resolution': f'{width}x{height}',
        'frames': length,
        'fps': fps,
        'duration_sec': round(length / fps, 2),
        'wall_time_sec': wall_time,
        'peak_ram_gb': round(peak_ram, 2),
        'peak_vram_gb': round(peak_vram, 2),
        'completed': completed,
        'video_path': str(mp4_path) if mp4_path.exists() else None,
        'frame_count': len(output_files),
    }
    meta_path = OUTPUTS_DIR / f'{test_name}.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    return meta


def main():
    benchmarks = [
        ('benchmark_A', 'Character breathes slowly. Camera static.', 'character_portrait.png'),
        ('benchmark_B', 'Character turns head slowly to the left. Camera static.', 'character_portrait.png'),
        ('benchmark_C', 'Character shifts body weight slightly. Camera static.', 'character_portrait.png'),
        ('benchmark_two_subject', 'Two characters talking quietly. Camera static.', 'two_subject_image.png'),
    ]

    results = []
    print('Starting TASK-01 minimal benchmark suite...')
    for name, prompt, img in benchmarks:
        print(f'=== Running {name}: "{prompt}" ===')
        res = run_generation(name, prompt, img)
        results.append(res)
        print(f'Done {name}: wall_time={res["wall_time_sec"]}s, peak_VRAM={res["peak_vram_gb"]}GB, peak_RAM={res["peak_ram_gb"]}GB, video={res["video_path"]}')

    summary_path = OUTPUTS_DIR / 'benchmark_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print('All benchmarks completed. Summary written to:', summary_path)


if __name__ == '__main__':
    main()
