"""汉明(7,4) 码单元测试。"""
import numpy as np
import pytest

from src.channel_coding import hamming_encode, hamming_decode, CODING_SCHEMES


def test_reversible_noiseless():
    bits = [int(x) for x in np.random.default_rng(1).integers(0, 2, size=400)]
    assert hamming_decode(hamming_encode(bits))[:400] == bits


def test_rate_4_over_7():
    assert len(hamming_encode([1, 0, 1, 1])) == 7


def test_corrects_single_bit_error():
    bits = [1, 0, 1, 1, 0, 1, 0, 0]
    coded = hamming_encode(bits)  # 14 bit
    coded[3] ^= 1  # 翻第一个块的 1 个 bit
    assert hamming_decode(coded)[:8] == bits


def test_corrects_error_in_each_block():
    bits = [int(x) for x in np.random.default_rng(7).integers(0, 2, size=40)]
    coded = hamming_encode(bits)
    coded[0] ^= 1  # 块 1
    coded[10] ^= 1  # 块 2
    assert hamming_decode(coded)[:40] == bits


def test_padding_to_multiple_of_4():
    coded = hamming_encode([1, 0, 1])  # 3 bit → 补到 4 → 7
    assert len(coded) == 7


def test_registered():
    assert "hamming74" in CODING_SCHEMES
    enc, dec = CODING_SCHEMES["hamming74"]
    assert enc is hamming_encode
    assert dec is hamming_decode


def test_empty():
    assert hamming_encode([]) == []
    assert hamming_decode([]) == []
