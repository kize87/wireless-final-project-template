"""信道编码模块单元测试。"""
import numpy as np
import pytest

from src.channel_coding import (
    channel_encode, channel_decode, CODING_SCHEMES,
    encode, decode, fec_encode, fec_decode,
)


def test_reversible_noiseless():
    bits = [int(x) for x in np.random.default_rng(2028).integers(0, 2, size=400)]
    assert channel_decode(channel_encode(bits))[:400] == bits


def test_empty():
    assert channel_encode([]) == []
    assert channel_decode([]) == []


def test_rate_one_third():
    bits = [1, 0, 1]
    assert len(channel_encode(bits)) == 9


def test_corrects_single_bit_error():
    bits = [1, 0, 1, 1]
    coded = channel_encode(bits)
    coded[1] ^= 1  # 翻第 2 个比特（第一组错 1 个）
    assert channel_decode(coded) == bits


def test_fails_on_double_error_in_triple():
    bits = [1]
    coded = channel_encode(bits)  # [1,1,1]
    coded[0] ^= 1
    coded[1] ^= 1  # 错 2 个
    assert channel_decode(coded) == [0]


def test_non_multiple_of_3_tolerant():
    bits = [1, 0, 1, 1, 0]  # 5 bit
    coded = channel_encode(bits)  # 15
    decoded = channel_decode(coded + [1, 1])  # 17, 多余 2 个被忽略
    assert decoded == bits


def test_coding_schemes_registry():
    assert "rep3" in CODING_SCHEMES
    enc, dec = CODING_SCHEMES["rep3"]
    assert enc is channel_encode
    assert dec is channel_decode


def test_aliases():
    assert encode is channel_encode
    assert decode is channel_decode
    assert fec_encode is channel_encode
    assert fec_decode is channel_decode
