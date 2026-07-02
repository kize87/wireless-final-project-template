"""组帧/解析模块单元测试。"""
import numpy as np
import pytest

from src.framing import build_frame, parse_frame, PREAMBLE_BITS, _crc16
from src.modulation import qpsk_modulate, qpsk_demodulate


def test_build_parse_reversible_even():
    payload = [int(x) for x in np.random.default_rng(2027).integers(0, 2, size=257)]
    frame = build_frame(payload)
    parsed = parse_frame(frame["bits"])
    assert parsed["payload"][:257] == payload
    assert parsed["length"] == 257


def test_build_parse_reversible_odd_with_padding():
    payload = [int(x) for x in np.random.default_rng(2030).integers(0, 2, size=255)]
    frame = build_frame(payload)
    syms = qpsk_modulate(frame["bits"])
    rx = qpsk_demodulate(syms)
    parsed = parse_frame(rx)
    assert parsed["payload"][:255] == payload


def test_build_parse_reversible_one_bit():
    payload = [1]
    frame = build_frame(payload)
    parsed = parse_frame(frame["bits"])
    assert parsed["payload"] == [1]
    assert parsed["length"] == 1


def test_build_frame_returns_crc_valid_true():
    frame = build_frame([1, 0, 1, 1, 0])
    assert frame["crc_valid"] is True


def test_parse_frame_crc_valid_when_no_error():
    payload = [int(x) for x in np.random.default_rng(1).integers(0, 2, size=100)]
    frame = build_frame(payload)
    parsed = parse_frame(frame["bits"])
    assert parsed["crc_valid"] is True


def test_parse_frame_detects_payload_bit_flip():
    payload = [int(x) for x in np.random.default_rng(2).integers(0, 2, size=100)]
    frame = build_frame(payload)
    bits = list(frame["bits"])
    bits[70] ^= 1  # payload 区域翻转
    parsed = parse_frame(bits)
    assert parsed["crc_valid"] is False
    assert parsed["crc_mismatch"] is True


def test_parse_frame_detects_crc_bit_flip():
    payload = [int(x) for x in np.random.default_rng(3).integers(0, 2, size=100)]
    frame = build_frame(payload)
    bits = list(frame["bits"])
    crc_start = 66 + 100
    bits[crc_start] ^= 1  # CRC 区域翻转
    parsed = parse_frame(bits)
    assert parsed["crc_valid"] is False


def test_frame_total_length():
    payload = [0] * 200
    frame = build_frame(payload)
    assert len(frame["bits"]) == 50 + 16 + 200 + 16


def test_parse_frame_short_does_not_raise():
    parsed = parse_frame([1, 0, 1])
    assert isinstance(parsed, dict)
    assert parsed["crc_valid"] is False  # 帧不完整


def test_parse_frame_dict_input_with_bits():
    payload = [1, 0, 1, 0]
    frame = build_frame(payload)
    parsed = parse_frame(frame)  # dict 输入（含 bits）
    assert parsed["payload"] == payload
    assert parsed["crc_valid"] is True


def test_length_truncates_padding():
    payload = [int(x) for x in np.random.default_rng(2030).integers(0, 2, size=255)]
    frame = build_frame(payload)
    rx = qpsk_demodulate(qpsk_modulate(frame["bits"]))
    parsed = parse_frame(rx)
    assert len(parsed["payload"]) == 255
