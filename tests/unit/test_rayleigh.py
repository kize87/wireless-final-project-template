"""Rayleigh 信道单元测试。"""
import numpy as np
import pytest

from src.channel import rayleigh, CHANNEL_SCHEMES


def test_reproducible_same_seed():
    symbols = np.array([1 + 1j] * 100, dtype=complex) / np.sqrt(2)
    assert np.allclose(rayleigh(symbols, snr_db=12, seed=2026),
                       rayleigh(symbols, snr_db=12, seed=2026))


def test_different_seed_different_output():
    symbols = np.array([1 + 1j] * 100, dtype=complex) / np.sqrt(2)
    assert not np.allclose(rayleigh(symbols, seed=2026), rayleigh(symbols, seed=2027))


def test_registered():
    assert "rayleigh" in CHANNEL_SCHEMES
    assert CHANNEL_SCHEMES["rayleigh"] is rayleigh


def test_introduces_fading():
    symbols = np.array([1 + 1j] * 100, dtype=complex) / np.sqrt(2)
    out = rayleigh(symbols, snr_db=100, seed=2026)  # 高 SNR，噪声可忽略
    # 衰落改变幅度（|out| 不全等于 |symbols|）
    assert not np.allclose(np.abs(out), np.abs(symbols))


def test_empty_input():
    assert len(rayleigh([], seed=2026)) == 0
