"""同步模块单元测试。"""
import numpy as np
import pytest

from src.synchronization import synchronize, detect_frame_start, find_preamble, sync
from src.framing import PREAMBLE_SYMBOLS


def _make_periodic_preamble():
    return np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j] * 8, dtype=complex) / np.sqrt(2)


def test_detect_25_symbol_offset():
    rng = np.random.default_rng(2026)
    preamble = _make_periodic_preamble()
    payload = np.array([1 - 1j, -1 - 1j, 1 + 1j, -1 + 1j] * 20, dtype=complex) / np.sqrt(2)
    prefix = (rng.normal(size=25) + 1j * rng.normal(size=25)) / np.sqrt(2)
    received = np.concatenate([prefix, preamble, payload])
    result = synchronize(received, preamble=preamble)
    assert abs(result["start_index"] - 25) <= 1


def test_returns_all_fields():
    result = synchronize(PREAMBLE_SYMBOLS, preamble=PREAMBLE_SYMBOLS)
    assert "start_index" in result
    assert "confidence" in result
    assert "peak" in result
    assert "found" in result


def test_fft_matches_loop():
    """FFT 互相关应与原循环 vdot 给出同样 argmax。"""
    rng = np.random.default_rng(5)
    preamble = PREAMBLE_SYMBOLS
    payload = (rng.normal(size=100) + 1j * rng.normal(size=100)) / np.sqrt(2)
    received = np.concatenate([preamble, payload])
    result = synchronize(received, preamble=preamble)
    n, m = len(received), len(preamble)
    loop_corr = np.array([abs(np.vdot(preamble, received[i:i + m])) for i in range(n - m + 1)])
    loop_start = int(np.argmax(loop_corr))
    assert result["start_index"] == loop_start


def test_short_signal_does_not_raise():
    result = synchronize([1 + 1j], preamble=PREAMBLE_SYMBOLS)
    assert result["start_index"] == 0
    assert result["found"] is False


def test_periodic_preamble_not_killed():
    rng = np.random.default_rng(2026)
    preamble = _make_periodic_preamble()
    prefix = (rng.normal(size=25) + 1j * rng.normal(size=25)) / np.sqrt(2)
    received = np.concatenate([prefix, preamble])
    result = synchronize(received, preamble=preamble)
    assert abs(result["start_index"] - 25) <= 1


def test_frame_confidence_higher_than_noise():
    rng = np.random.default_rng(2026)
    preamble = _make_periodic_preamble()
    payload = (rng.normal(size=100) + 1j * rng.normal(size=100)) / np.sqrt(2)
    prefix = (rng.normal(size=25) + 1j * rng.normal(size=25)) / np.sqrt(2)
    with_frame = synchronize(np.concatenate([prefix, preamble, payload]), preamble=preamble)
    rng2 = np.random.default_rng(99)
    noise = rng2.normal(size=200) + 1j * rng2.normal(size=200)
    no_frame = synchronize(noise, preamble=preamble)
    assert with_frame["confidence"] > no_frame["confidence"]


def test_aliases():
    assert detect_frame_start is synchronize
    assert find_preamble is synchronize
    assert sync is synchronize
