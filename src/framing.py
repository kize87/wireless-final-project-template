"""
组帧/解析模块 — 帧结构设计。

帧格式:
  [Preamble 50 bits (25 QPSK symbols)] [Length 16 bits] [Payload variable] [Checksum 16 bits]
"""

import numpy as np


def _generate_preamble_symbols(n=25):
    """使用 LFSR 生成伪随机 QPSK 符号作为 preamble（良好自相关特性）。"""
    rng = np.random.default_rng(42)  # 固定种子
    bits = rng.integers(0, 2, size=n * 2).tolist()
    symbols = []
    norm = 1.0 / np.sqrt(2)
    for i in range(0, len(bits), 2):
        b0, b1 = bits[i], bits[i + 1]
        if b0 == 0 and b1 == 0:
            s = complex(1, 1)
        elif b0 == 0 and b1 == 1:
            s = complex(-1, 1)
        elif b0 == 1 and b1 == 1:
            s = complex(-1, -1)
        else:  # b0 == 1 and b1 == 0
            s = complex(1, -1)
        symbols.append(s * norm)
    return np.array(symbols, dtype=complex)


# 固定的 preamble 序列（25 个单位功率 QPSK 符号）
PREAMBLE_SYMBOLS = _generate_preamble_symbols(25)

# 将 preamble 符号映射为比特（与 QPSK 调制器映射一致）
# b0: imag < 0 → 1, imag ≥ 0 → 0
# b1: real < 0 → 1, real ≥ 0 → 0
PREAMBLE_BITS = []
for s in PREAMBLE_SYMBOLS:
    b0 = 1 if s.imag < 0 else 0
    b1 = 1 if s.real < 0 else 0
    PREAMBLE_BITS.extend([b0, b1])


def _crc16(bits):
    """简单的 16 位 CRC 校验和。"""
    crc = 0xFFFF
    for b in bits:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    result = []
    for i in range(15, -1, -1):
        result.append((crc >> i) & 1)
    return result


def build_frame(payload_bits):
    """组帧：Preamble + Length + Payload + Checksum。"""
    payload_bits = [int(x) for x in list(payload_bits)]
    length = len(payload_bits)

    # Length 字段：16 比特大端
    length_bits = []
    for i in range(15, -1, -1):
        length_bits.append((length >> i) & 1)

    # Checksum：CRC-16
    data_for_crc = PREAMBLE_BITS + length_bits + payload_bits
    checksum_bits = _crc16(data_for_crc)

    # 返回帧结构（字典形式）
    frame_bits = PREAMBLE_BITS + length_bits + payload_bits + checksum_bits
    return {
        "preamble": list(PREAMBLE_BITS),
        "length": length,
        "payload": payload_bits,
        "checksum": checksum_bits,
        "bits": frame_bits,
    }


def parse_frame(frame):
    """从帧比特列表中解析各字段。"""
    if isinstance(frame, dict):
        return frame
    frame_bits = [int(x) for x in list(frame)]

    # 解析 preamble (50 bits)
    preamble = frame_bits[:50]

    # 解析 length (16 bits)
    length_bits = frame_bits[50:66]
    length_val = 0
    for b in length_bits:
        length_val = (length_val << 1) | b

    # 解析 payload
    payload = frame_bits[66:66 + length_val]

    # 解析 checksum (16 bits)
    checksum = frame_bits[66 + length_val:66 + length_val + 16]

    return {
        "preamble": preamble,
        "length": length_val,
        "payload": payload,
        "checksum": checksum,
    }
