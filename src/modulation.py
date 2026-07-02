"""QPSK 调制/解调模块 — Gray 编码映射，可插拔策略。

象限映射规则（PRD Gray 编码，红线不可改 — TC-T_009）:
  00 → ( 1+1j)/√2   Q1
  01 → (-1+1j)/√2   Q2
  11 → (-1-1j)/√2   Q3
  10 → ( 1-1j)/√2   Q4
"""
from __future__ import annotations

from typing import Callable

import numpy as np

# Gray 编码 QPSK 星座映射表（红线不可改，TC-T_009）
QPSK_MAP = {
    (0, 0): complex(1, 1),
    (0, 1): complex(-1, 1),
    (1, 1): complex(-1, -1),
    (1, 0): complex(1, -1),
}


def qpsk_modulate(bits: list[int]) -> np.ndarray:
    """比特列表 → QPSK 复数符号。奇数比特自动补 0，单位功率。"""
    bits = [int(x) for x in list(bits)]
    if len(bits) % 2 != 0:
        bits = bits + [0]
    norm = 1.0 / np.sqrt(2)
    symbols = [QPSK_MAP[(bits[i], bits[i + 1])] * norm for i in range(0, len(bits), 2)]
    return np.array(symbols, dtype=complex)


def qpsk_demodulate(symbols) -> list[int]:
    """QPSK 复数符号 → 比特列表。b0 看虚部符号，b1 看实部符号。"""
    if hasattr(symbols, "tolist"):
        symbols = symbols.tolist()
    bits: list[int] = []
    for s in symbols:
        s = complex(s)
        b0 = 1 if s.imag < 0 else 0
        b1 = 1 if s.real < 0 else 0
        bits.extend([b0, b1])
    return bits


# 可插拔调制策略注册表（默认 qpsk；为 BPSK/16QAM 留接口）
MODULATION_SCHEMES: dict[str, tuple[Callable, Callable]] = {
    "qpsk": (qpsk_modulate, qpsk_demodulate),
}


# 别名
modulate_qpsk = qpsk_modulate
demodulate_qpsk = qpsk_demodulate
qpsk_mapper = qpsk_modulate
qpsk_demapper = qpsk_demodulate
modulate = qpsk_modulate
demodulate = qpsk_demodulate
