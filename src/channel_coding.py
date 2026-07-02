"""信道编码模块 — (3,1) 重复码 FEC，可插拔策略。

默认 (3,1) 重复码：每比特重复 3 次，多数投票解码，编码率 1/3。
通过 CODING_SCHEMES 注册表支持扩展（如 Level3 汉明(7,4)）。
"""
from __future__ import annotations

from typing import Callable


def channel_encode(bits: list[int]) -> list[int]:
    """(3,1) 重复码：每比特重复 3 次。"""
    bits = [int(x) for x in list(bits)]
    coded: list[int] = []
    for b in bits:
        coded.extend([b, b, b])
    return coded


def channel_decode(coded_bits: list[int]) -> list[int]:
    """多数投票解码：每 3 比特一组，sum >= 2 判 1。"""
    coded_bits = [int(x) for x in list(coded_bits)]
    n = len(coded_bits) // 3
    decoded: list[int] = []
    for i in range(n):
        triple = coded_bits[3 * i : 3 * i + 3]
        decoded.append(1 if sum(triple) >= 2 else 0)
    return decoded


def hamming_encode(bits: list[int]) -> list[int]:
    """(7,4) 汉明码：每 4 bit → 7 bit，可纠 1 bit 错。编码率 4/7。

    码字位置 1-7：p1,p2,d3,p4,d5,d6,d7（p 为校验位，d 为数据位）。
    """
    bits = [int(x) for x in list(bits)]
    if len(bits) % 4 != 0:
        bits = bits + [0] * (4 - len(bits) % 4)
    coded: list[int] = []
    for i in range(0, len(bits), 4):
        d3, d5, d6, d7 = bits[i], bits[i + 1], bits[i + 2], bits[i + 3]
        p1 = d3 ^ d5 ^ d7
        p2 = d3 ^ d6 ^ d7
        p4 = d5 ^ d6 ^ d7
        coded.extend([p1, p2, d3, p4, d5, d6, d7])  # 码字位置 1-7
    return coded


def hamming_decode(coded_bits: list[int]) -> list[int]:
    """(7,4) 汉明码译码：每 7 bit → 4 bit，纠 1 bit 错。

    syndrome (s4,s2,s1) 二进制值 = 错误位置（1-indexed），0=无错。
    """
    coded = [int(x) for x in list(coded_bits)]
    decoded: list[int] = []
    for i in range(len(coded) // 7):
        b = coded[i * 7:i * 7 + 7]  # [p1,p2,d3,p4,d5,d6,d7]
        p1, p2, d3, p4, d5, d6, d7 = b
        s1 = p1 ^ d3 ^ d5 ^ d7
        s2 = p2 ^ d3 ^ d6 ^ d7
        s4 = p4 ^ d5 ^ d6 ^ d7
        pos = s1 + s2 * 2 + s4 * 4  # 错误位置（1-indexed），0=无错
        if pos != 0:
            b[pos - 1] ^= 1  # 纠错
        decoded.extend([b[2], b[4], b[5], b[6]])  # 数据位 3,5,6,7
    return decoded


# 可插拔编码策略注册表（rep3 默认；Level3 汉明码）
CODING_SCHEMES: dict[str, tuple[Callable[[list[int]], list[int]], Callable[[list[int]], list[int]]]] = {
    "rep3": (channel_encode, channel_decode),
    "hamming74": (hamming_encode, hamming_decode),
}


# 别名
encode = channel_encode
decode = channel_decode
encode_bits = channel_encode
decode_bits = channel_decode
fec_encode = channel_encode
fec_decode = channel_decode
