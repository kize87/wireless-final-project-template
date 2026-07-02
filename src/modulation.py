"""
QPSK 调制/解调模块 — Gray 编码映射。

象限映射规则（PRD Gray 编码）:
  00 → ( 1+1j)/√2   Q1
  01 → (-1+1j)/√2   Q2
  11 → (-1-1j)/√2   Q3
  10 → ( 1-1j)/√2   Q4
"""

import numpy as np

# Gray 编码 QPSK 星座映射表
QPSK_MAP = {
    (0, 0): complex(1, 1),
    (0, 1): complex(-1, 1),
    (1, 1): complex(-1, -1),
    (1, 0): complex(1, -1),
}


def qpsk_modulate(bits):
    """将比特列表调制为 QPSK 复数符号。奇数比特时自动补 0。"""
    bits = [int(x) for x in list(bits)]
    # 补偶
    if len(bits) % 2 != 0:
        bits = bits + [0]
    symbols = []
    norm = 1.0 / np.sqrt(2)
    for i in range(0, len(bits), 2):
        pair = (bits[i], bits[i + 1])
        s = QPSK_MAP[pair] * norm
        symbols.append(s)
    return np.array(symbols, dtype=complex)


def qpsk_demodulate(symbols):
    """将 QPSK 复数符号解调为比特列表。"""
    if hasattr(symbols, 'tolist'):
        symbols = symbols.tolist()
    symbols = [complex(s) for s in symbols]
    bits = []
    for s in symbols:
        # 根据 QPSK Gray 编码映射：
        # b0: imag ≥ 0 → 0, imag < 0 → 1
        # b1: real < 0 → 1, real ≥ 0 → 0
        b0 = 1 if s.imag < 0 else 0
        b1 = 1 if s.real < 0 else 0
        bits.extend([b0, b1])
    return bits


# 别名
modulate_qpsk = qpsk_modulate
demodulate_qpsk = qpsk_demodulate
qpsk_mapper = qpsk_modulate
qpsk_demapper = qpsk_demodulate
modulate = qpsk_modulate
demodulate = qpsk_demodulate
