"""源编码模块 — UTF-8 中文文本与比特流之间的转换。"""
from __future__ import annotations


def source_encode(text: str) -> list[int]:
    """UTF-8 文本 → MSB-first 比特列表（长度恒为 8 的倍数）。

    空文本返回空列表。每个字符先 UTF-8 编码为字节，每字节拆 8 比特（高位在前）。
    """
    raw = text.encode("utf-8")
    bits: list[int] = []
    for byte in raw:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def source_decode(bits: list[int]) -> str:
    """比特列表 → UTF-8 文本。空列表返回空串。

    按 8 位分组恢复字节（不足 8 的倍数补 0），UTF-8 解码（errors="replace" 容错）。
    """
    bits = list(bits)
    remainder = len(bits) % 8
    if remainder:
        bits = bits + [0] * (8 - remainder)
    bytes_list = bytearray()
    for i in range(0, len(bits), 8):
        val = 0
        for b in bits[i : i + 8]:
            val = (val << 1) | int(b)
        bytes_list.append(val)
    return bytes(bytes_list).decode("utf-8", errors="replace")


# 别名（公开测试 conftest.find_function 多别名搜索）
text_to_bits = source_encode
bits_to_text = source_decode
