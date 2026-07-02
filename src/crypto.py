"""
加扰/解扰模块 — 基于 PRNG 的 XOR 比特级加扰。
"""

import numpy as np


def scramble(bits, seed=2026):
    """使用 PRNG 生成伪随机序列与输入比特 XOR 进行加扰。"""
    bits = [int(x) for x in list(bits)]
    rng = np.random.default_rng(seed)
    # 生成与 bits 等长的伪随机比特序列
    random_bits = rng.integers(0, 2, size=len(bits)).tolist()
    return [b ^ r for b, r in zip(bits, random_bits)]


def descramble(bits, seed=2026):
    """使用相同种子解扰（XOR 自逆操作）。"""
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
