"""加扰/解扰模块单元测试。"""
import numpy as np
import pytest

from src.crypto import (
    scramble, descramble, scramble_bits, descramble_bits, encrypt, decrypt,
)


def test_scramble_reversible():
    bits = [int(x) for x in np.random.default_rng(2026).integers(0, 2, size=511)]
    assert descramble(scramble(bits, seed=2026), seed=2026)[:511] == bits


def test_empty_bits():
    assert scramble([], seed=2026) == []
    assert descramble([], seed=2026) == []


def test_different_seed_different_output():
    bits = [1, 0, 1, 1, 0, 0, 1, 0] * 10
    assert scramble(bits, seed=2026) != scramble(bits, seed=2027)


def test_same_seed_reproducible():
    bits = [1, 0, 1, 1, 0, 0, 1, 0] * 10
    assert scramble(bits, seed=2026) == scramble(bits, seed=2026)


def test_scramble_diffuses_zeros():
    bits = [0] * 100
    s = scramble(bits, seed=2026)
    assert any(b == 1 for b in s)


def test_aliases():
    assert scramble_bits is scramble
    assert descramble_bits is descramble
    assert encrypt is scramble
    assert decrypt is descramble
