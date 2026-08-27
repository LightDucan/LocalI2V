from __future__ import annotations

import logging
from pathlib import Path
from app.system.gpu_info import get_gpu_info, check_minimum_requirements
from app.system.logger import configure_logging
from app.ui.main_ui import build_ui


def test_get_gpu_info():
    info = get_gpu_info()
    assert isinstance(info, dict)
    assert 'cuda_available' in info
    if info['cuda_available']:
        assert '1070' in info['name']
        assert info['compute_capability'] == '6.1'
        assert 'sm_61' in info['arch_list']
        assert info['vram_total_gb'] >= 7.0
        assert check_minimum_requirements(info) is True


def test_logger():
    logger = configure_logging()
    assert isinstance(logger, logging.Logger)
    logger.info('unit test log entry')
    log_file = Path('history/app.log')
    assert log_file.exists()
    assert 'unit test log entry' in log_file.read_text(encoding='utf-8')


def test_build_ui():
    demo = build_ui()
    assert demo is not None
