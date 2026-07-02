"""加扰/解扰模块 — PRNG XOR 比特级加扰。

注：本模块是能量扩散加扰，**非加密**——PRNG 可逆、种子公开，
仅用于打散长串 0/1 以利于同步与均衡，不具备保密性。
"""
from __future__ import annotations

import numpy as np


def scramble(bits: list[int], seed: int = 2026) -> list[int]:
    """PRNG 生成与输入等长的伪随机比特，XOR 加扰。"""
    bits = [int(x) for x in list(bits)]
    rng = np.random.default_rng(seed)
    random_bits = rng.integers(0, 2, size=len(bits)).tolist()
    return [b ^ r for b, r in zip(bits, random_bits)]


def descramble(bits: list[int], seed: int = 2026) -> list[int]:
    """同种子解扰。XOR 自逆，与 scramble 完全对称。"""
    bits = [int(x) for x in list(bits)]
    rng = np.random.default_rng(seed)
    random_bits = rng.integers(0, 2, size=len(bits)).tolist()
    return [b ^ r for b, r in zip(bits, random_bits)]


# 别名
scramble_bits = scramble
descramble_bits = descramble
encrypt = scramble
decrypt = descramble
encrypt_bits = scramble
decrypt_bits = descramble
