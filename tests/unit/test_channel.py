"""信道模块单元测试。"""
import numpy as np
import pytest

from src.channel import awgn, CHANNEL_SCHEMES, awgn_channel, add_awgn, add_noise


def test_reproducible_same_seed():
    symbols = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=complex) / np.sqrt(2)
    out1 = awgn(symbols, snr_db=12, seed=2026)
    out2 = awgn(symbols, snr_db=12, seed=2026)
    assert np.allclose(out1, out2)


def test_different_seed_different_output():
    symbols = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=complex) / np.sqrt(2)
    assert not np.allclose(awgn(symbols, seed=2026), awgn(symbols, seed=2027))


def test_higher_snr_less_noise():
    symbols = np.array([1 + 1j] * 100, dtype=complex) / np.sqrt(2)
    low_snr = awgn(symbols, snr_db=0, seed=2026)
    high_snr = awgn(symbols, snr_db=20, seed=2026)
    assert np.mean(np.abs(low_snr - symbols) ** 2) > np.mean(np.abs(high_snr - symbols) ** 2)


def test_noise_variance_matches_es_over_snr():
    # 单位功率符号 Es=1，snr=12dB → noise_power=1/10^1.2≈0.0631
    symbols = np.array([1 + 1j] * 10000, dtype=complex) / np.sqrt(2)
    out = awgn(symbols, snr_db=12, seed=2026)
    noise = out - symbols
    total_var = float(np.mean(np.abs(noise) ** 2))
    expected = 1.0 / 10 ** (12 / 10)
    assert abs(total_var - expected) / expected < 0.1  # 10% 容差


def test_channel_schemes_registry():
    assert "awgn" in CHANNEL_SCHEMES
    assert CHANNEL_SCHEMES["awgn"] is awgn


def test_aliases():
    assert awgn_channel is awgn
    assert add_awgn is awgn
    assert add_noise is awgn


def test_empty_input():
    assert len(awgn([], seed=2026)) == 0
