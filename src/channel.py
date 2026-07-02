"""AWGN 信道模块 — 加性高斯白噪声，Es/N0 定义，可插拔策略。

SNR 定义（DESIGN §4）：snr_db 为 Es/N0（符号信噪比）。
  signal_power = mean(|s|²) = Es
  noise_power  = Es / 10^(snr_db/10)
  复噪声实/虚部各 N(0, sqrt(noise_power/2))，总方差 = noise_power
BER 曲线横轴用 Eb/N0 = Es/N0 - 10·log10(k)，QPSK k=2 ⇒ Eb/N0 = snr_db - 3 dB。
"""
from __future__ import annotations

from typing import Callable

import numpy as np


def awgn(symbols, snr_db: float = 12, seed: int = 2026) -> np.ndarray:
    """为复数信号添加 AWGN 噪声（固定 seed 可复现）。"""
    symbols = np.array(symbols, dtype=complex)
    if len(symbols) == 0:
        return symbols
    rng = np.random.default_rng(seed)

    signal_power = float(np.mean(np.abs(symbols) ** 2))  # Es
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear
    noise_std = np.sqrt(noise_power / 2)  # 每维方差，总方差 = noise_power

    noise = rng.normal(0, noise_std, size=len(symbols)) + 1j * rng.normal(0, noise_std, size=len(symbols))
    return symbols + noise


def rayleigh(symbols, snr_db: float = 12, seed: int = 2026) -> np.ndarray:
    """Rayleigh 衰落 + AWGN 信道（快衰落，每符号独立复高斯系数）。

    h ~ CN(0,1)，接收 = h*symbols + noise。
    注：引入随机相位旋转，QPSK 解调需信道估计/均衡，否则 BER 高（展示衰落影响）。
    """
    symbols = np.array(symbols, dtype=complex)
    if len(symbols) == 0:
        return symbols
    rng = np.random.default_rng(seed)
    h = (rng.normal(size=len(symbols)) + 1j * rng.normal(size=len(symbols))) / np.sqrt(2)
    signal_power = float(np.mean(np.abs(symbols) ** 2))
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear
    noise_std = np.sqrt(noise_power / 2)
    noise = rng.normal(0, noise_std, size=len(symbols)) + 1j * rng.normal(0, noise_std, size=len(symbols))
    return h * symbols + noise


# 可插拔信道策略注册表（awgn 默认；Level3 Rayleigh）
CHANNEL_SCHEMES: dict[str, Callable] = {"awgn": awgn, "rayleigh": rayleigh}


# 别名
awgn_channel = awgn
add_awgn = awgn
add_noise = awgn
