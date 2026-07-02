"""main.py 单元测试（in-process，提高 main.py 覆盖率）。"""
import json
from pathlib import Path

import pytest

import main as main_mod
from src.modulation import MODULATION_SCHEMES
from src.channel import CHANNEL_SCHEMES
from src.channel_coding import CODING_SCHEMES

TEXT = "测试文本abc123无线通信"
MOD, DEMOD = MODULATION_SCHEMES["qpsk"]
CH = CHANNEL_SCHEMES["awgn"]
ENC, DEC = CODING_SCHEMES["rep3"]


def test_run_pipeline_recovers_at_high_snr():
    r = main_mod.run_pipeline(TEXT, 12, 2026, MOD, DEMOD, CH, ENC, DEC)
    assert r["recovered_text"] == TEXT
    assert r["ber"] == 0.0
    assert r["crc_valid"] is True


def test_run_pipeline_low_snr_degrades():
    r = main_mod.run_pipeline(TEXT, 0, 2026, MOD, DEMOD, CH, ENC, DEC)
    assert r["ber"] > 0 or not r["crc_valid"]


def test_sweep_returns_all_snr_points():
    sweep = main_mod.sweep_ber_fer(TEXT, 2026, MOD, DEMOD, CH, ENC, DEC)
    assert len(sweep) == len(main_mod.SNR_SWEEP)
    assert all("ber" in s and "fer" in s and "snr" in s for s in sweep)


def test_generate_plots_creates_all_files(tmp_path):
    r = main_mod.run_pipeline(TEXT, 12, 2026, MOD, DEMOD, CH, ENC, DEC)
    r["snr_db"] = 12
    r["error_tx"] = r["payload_bits"]
    r["error_rx"] = r["recovered_bits"]
    sweep = main_mod.sweep_ber_fer(TEXT, 2026, MOD, DEMOD, CH, ENC, DEC)
    main_mod.generate_plots(r, sweep, tmp_path)
    expected = ["constellation.png", "ber_curve.png", "sync_peak.png",
                "frame_structure.png", "error_pattern.png", "channel_response.png"]
    for name in expected:
        assert (tmp_path / name).exists()


def test_main_in_process(monkeypatch, tmp_path):
    test_file = tmp_path / "Test.txt"
    test_file.write_text(TEXT, encoding="utf-8")
    out_file = tmp_path / "received.txt"
    monkeypatch.setattr(main_mod, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr("sys.argv", [
        "main.py", "--input", str(test_file), "--output", str(out_file),
        "--snr", "12", "--seed", "2026", "--mod", "qpsk", "--channel", "awgn",
    ])
    main_mod.main()
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == TEXT
    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["text_match_rate"] == 1.0
    assert metrics["crc_valid"] is True
