"""信源编码模块单元测试。"""
import pytest

from src.source import source_encode, source_decode, text_to_bits, bits_to_text


def test_empty_text_roundtrip():
    assert source_encode("") == []
    assert source_decode([]) == ""


def test_chinese_reversible():
    t = "无线通信技术课程"
    assert source_decode(source_encode(t)) == t


def test_ascii_reversible():
    t = "hello QPSK 123"
    assert source_decode(source_encode(t)) == t


def test_emoji_reversible():
    t = "通信📡emoji混合"
    assert source_decode(source_encode(t)) == t


def test_bitstream_length_multiple_of_8():
    bits = source_encode("测试文本abc")
    assert len(bits) % 8 == 0
    assert len(bits) == len("测试文本abc".encode("utf-8")) * 8


def test_msb_first_order():
    # 'A' = 0x41 = 0b01000001
    assert source_encode("A") == [0, 1, 0, 0, 0, 0, 0, 1]


def test_invalid_utf8_bytes_replaced_not_raised():
    # 0xFF 是非法 UTF-8 起始字节，errors="replace" 应返回含替换符的串而非抛异常
    bits = [1, 1, 1, 1, 1, 1, 1, 1]  # 0xFF
    result = source_decode(bits)
    assert isinstance(result, str)


def test_aliases():
    assert text_to_bits is source_encode
    assert bits_to_text is source_decode
