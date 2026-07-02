"""指标计算模块 — BER、FER、text_match_rate、checksum_pass。

FER 基于 CRC 校验结果（真实化，不再由 BER 二值推算）。
"""
from __future__ import annotations

from typing import Iterable, Union


def compute_ber(original_bits, received_bits) -> float:
    """比特错误率：错误比特数 / 比较比特数。"""
    original_bits = [int(x) for x in list(original_bits)]
    received_bits = [int(x) for x in list(received_bits)]
    n = min(len(original_bits), len(received_bits))
    if n == 0:
        return 0.0
    errors = sum(1 for i in range(n) if original_bits[i] != received_bits[i])
    return errors / n


def compute_fer(crc_valid: Union[bool, Iterable[bool]]) -> float:
    """帧错误率，基于 CRC 校验结果。

    - 单帧（bool）：通过→0.0，失败→1.0
    - 多帧（list[bool]）：失败帧数 / 总帧数
    """
    if isinstance(crc_valid, bool):
        return 0.0 if crc_valid else 1.0
    results = [bool(v) for v in crc_valid]
    if not results:
        return 0.0
    failed = sum(1 for v in results if not v)
    return failed / len(results)


def compute_text_match_rate(original_text: str, received_text: str) -> float:
    """文本字符匹配率。"""
    if original_text == received_text:
        return 1.0
    n = max(len(original_text), len(received_text))
    if n == 0:
        return 1.0
    matches = sum(1 for a, b in zip(original_text, received_text) if a == b)
    return matches / n


def compute_checksum_pass(original_checksum, received_checksum) -> bool:
    """校验和比对：两段比特序列是否一致。"""
    return list(original_checksum) == list(received_checksum)
