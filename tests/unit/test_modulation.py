"""调制模块单元测试。"""
import math

import numpy as np
import pytest

from src.modulation import (
    qpsk_modulate, qpsk_demodulate, QPSK_MAP, MODULATION_SCHEMES,
    modulate_qpsk, demodulate_qpsk, qpsk_mapper, qpsk_demapper, modulate, demodulate,
)


def test_mapping_quadrants():
    symbols = qpsk_modulate([0, 0, 0, 1, 1, 1, 1, 0])
    expected = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    for s, (si, sq) in zip(symbols[:4], expected):
        assert math.copysign(1, s.real) == si
        assert math.copysign(1, s.imag) == sq


def test_unit_power():
    symbols = qpsk_modulate([0, 0, 0, 1, 1, 1, 1, 0])
    avg = float(np.mean(np.abs(np.array(symbols[:4])) ** 2))
    assert 0.8 <= avg <= 1.2


def test_odd_bits_padded():
    syms = qpsk_modulate([1, 0, 1])  # 奇数 → 补 0
    assert len(syms) == 2


def test_noiseless_zero_error():
    bits = [int(x) for x in np.random.default_rng(2029).integers(0, 2, size=512)]
    assert qpsk_demodulate(qpsk_modulate(bits))[:512] == bits


def test_modulation_schemes_registry():
    assert "qpsk" in MODULATION_SCHEMES
    mod, demod = MODULATION_SCHEMES["qpsk"]
    assert mod is qpsk_modulate
    assert demod is qpsk_demodulate


def test_aliases():
    assert modulate_qpsk is qpsk_modulate
    assert demodulate_qpsk is qpsk_demodulate
    assert qpsk_mapper is qpsk_modulate
    assert qpsk_demapper is qpsk_demodulate
    assert modulate is qpsk_modulate
    assert demodulate is qpsk_demodulate


def test_empty_bits():
    assert len(qpsk_modulate([])) == 0
