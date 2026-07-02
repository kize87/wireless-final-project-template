"""组帧/解析模块 — 帧结构设计 + CRC 真实验证。

帧格式:
  [Preamble 50 bits (25 QPSK 符号)] [Length 16 bits] [Payload 变长] [Checksum 16 bits]
CRC-16 覆盖 PREAMBLE + Length + Payload。parse_frame 重算 CRC 与帧尾比对，置 crc_valid。
"""
from __future__ import annotations

import numpy as np


def _generate_preamble_symbols(n: int = 25) -> np.ndarray:
    """使用固定种子生成伪随机 QPSK 符号作为 preamble（良好自相关特性）。"""
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
PREAMBLE_BITS: list[int] = []
for s in PREAMBLE_SYMBOLS:
    b0 = 1 if s.imag < 0 else 0
    b1 = 1 if s.real < 0 else 0
    PREAMBLE_BITS.extend([b0, b1])


def _crc16(bits: list[int]) -> list[int]:
    """16 位 CRC 校验和（poly 0xA001, init 0xFFFF，覆盖输入比特）。"""
    crc = 0xFFFF
    for b in bits:
        crc ^= int(b)
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return [(crc >> i) & 1 for i in range(15, -1, -1)]


def build_frame(payload_bits: list[int]) -> dict:
    """组帧：Preamble + Length + Payload + Checksum。返回含 bits 与 crc_valid 的 dict。"""
    payload_bits = [int(x) for x in list(payload_bits)]
    length = len(payload_bits)

    # Length 字段：16 比特大端
    length_bits = [(length >> i) & 1 for i in range(15, -1, -1)]

    # Checksum：CRC-16，覆盖 PREAMBLE + Length + Payload
    data_for_crc = PREAMBLE_BITS + length_bits + payload_bits
    checksum_bits = _crc16(data_for_crc)

    frame_bits = PREAMBLE_BITS + length_bits + payload_bits + checksum_bits
    return {
        "preamble": list(PREAMBLE_BITS),
        "length": length,
        "payload": payload_bits,
        "checksum": checksum_bits,
        "bits": frame_bits,
        "crc_valid": True,  # 发送端生成的帧 CRC 必然有效
    }


def parse_frame(frame, *, verify_crc: bool = True) -> dict:
    """从帧比特列表解析各字段，并重算 CRC 验证完整性。

    verify_crc=True 时重算 CRC 与帧尾比对，置 crc_valid；**不抛异常**（best-effort 解码），
    保证噪声下也能返回 payload 供下游处理。返回:
      {preamble, length, payload, checksum, crc_valid, crc_mismatch}
    """
    # 统一为比特列表
    if isinstance(frame, dict):
        if "bits" in frame:
            frame_bits = [int(x) for x in list(frame["bits"])]
        else:
            # 已是解析后的 dict，补 crc_valid 后返回
            result = dict(frame)
            result.setdefault("crc_valid", True)
            result.setdefault("crc_mismatch", False)
            return result
    else:
        frame_bits = [int(x) for x in list(frame)]

    # 解析 preamble (50 bits)
    preamble = frame_bits[:50]

    # 解析 length (16 bits)
    length_bits = frame_bits[50:66]
    length_val = 0
    for b in length_bits:
        length_val = (length_val << 1) | int(b)

    # 解析 payload
    payload = frame_bits[66:66 + length_val]

    # 解析 checksum (16 bits)
    checksum = frame_bits[66 + length_val:66 + length_val + 16]

    # 重算 CRC 并比对（CRC 覆盖 PREAMBLE + Length + Payload）
    recalc = _crc16(preamble + list(length_bits) + payload)
    checksum_norm = [int(x) for x in checksum]
    crc_valid = (recalc == checksum_norm) if verify_crc else True
    crc_mismatch = (not crc_valid) if verify_crc else False

    return {
        "preamble": preamble,
        "length": length_val,
        "payload": payload,
        "checksum": checksum_norm,
        "crc_valid": crc_valid,
        "crc_mismatch": crc_mismatch,
    }
