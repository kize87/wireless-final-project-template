"""端到端测试 — 验证 CLI、metrics 真实化、图集、错误参数。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_TEXT = (
    "无线通信技术课程要求学生理解调制、编码、信道和接收机处理。"
    "本测试文本用于验证源编码、帧结构、QPSK 调制、AWGN 信道、同步和端到端恢复。"
)


def run_cli(*extra, snr=12, seed=2026, timeout=60):
    cmd = [sys.executable, "main.py", "--input", "Test.txt",
           "--output", "results/received.txt", "--snr", str(snr), "--seed", str(seed),
           "--mod", "qpsk", "--channel", "awgn"]
    cmd += list(extra)
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    return subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, capture_output=True,
                           text=True, timeout=timeout)


@pytest.fixture
def write_test_file():
    p = PROJECT_ROOT / "Test.txt"
    p.write_text(SAMPLE_TEXT, encoding="utf-8")
    return p


@pytest.fixture
def clean_results():
    import shutil
    r = PROJECT_ROOT / "results"
    if r.exists():
        shutil.rmtree(r)
    r.mkdir(parents=True, exist_ok=True)
    return r


def test_end_to_end_12db_recovers(write_test_file, clean_results):
    result = run_cli()
    assert result.returncode == 0, result.stderr
    received = (PROJECT_ROOT / "results" / "received.txt").read_text(encoding="utf-8")
    assert received == SAMPLE_TEXT
    metrics = json.loads((PROJECT_ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    assert float(metrics["text_match_rate"]) == 1.0
    assert float(metrics["ber"]) == 0.0


def test_metrics_has_real_fields(write_test_file, clean_results):
    result = run_cli()
    assert result.returncode == 0, result.stderr
    metrics = json.loads((PROJECT_ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    assert "crc_valid" in metrics
    assert "sync_confidence" in metrics
    assert "eb_n0_db" in metrics
    assert metrics["checksum_pass"] is True  # 真实，非写死
    assert metrics["crc_valid"] is True
    assert metrics["sync_found"] is True


def test_invalid_mod_exits_nonzero(write_test_file, clean_results):
    result = run_cli("--mod", "nonexistent_mod")
    assert result.returncode != 0


def test_invalid_channel_exits_nonzero(write_test_file, clean_results):
    result = run_cli("--channel", "nonexistent_channel")
    assert result.returncode != 0


def test_six_plots_generated(write_test_file, clean_results):
    result = run_cli()
    assert result.returncode == 0, result.stderr
    results_dir = PROJECT_ROOT / "results"
    old_names = ["constellation.png", "ber_curve.png", "sync_peak.png"]
    new_names = ["frame_structure.png", "error_pattern.png", "channel_response.png"]
    for n in old_names:
        assert (results_dir / n).exists() and (results_dir / n).stat().st_size > 0
    for n in new_names:
        assert (results_dir / n).exists()


def test_low_snr_has_higher_ber(write_test_file, clean_results):
    r2 = run_cli(snr=2)
    assert r2.returncode == 0, r2.stderr
    m2 = json.loads((PROJECT_ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    r12 = run_cli(snr=12)
    m12 = json.loads((PROJECT_ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    assert m2["ber"] >= m12["ber"]  # 低 SNR 误码不少于高 SNR
