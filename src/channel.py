"""
AWGN 信道模块 — 添加高斯白噪声。
"""

import numpy as np


def awgn(symbols, snr_db=12, seed=2026):
    """为复数信号添加 AWGN 噪声。

    Parameters
    ----------
    symbols : array-like
        输入复数符号
    snr_db : float
        信噪比 (dB)
    seed : int
        随机种子

    Returns
    -------
    noisy : np.ndarray
        加噪后的复数信号
    """
    symbols = np.array(symbols, dtype=complex)
    rng = np.random.default_rng(seed)

    # 计算信号功率
    signal_power = float(np.mean(np.abs(symbols) ** 2))

    # 根据 SNR 计算噪声方差
    # SNR = signal_power / noise_power
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear

    # 复高斯噪声：实部和虚部各自独立，总方差 = noise_power
    noise_std = np.sqrt(noise_power / 2)  # 每维方差

    noise = rng.normal(0, noise_std, size=len(symbols)) + 1j * rng.normal(0, noise_std, size=len(symbols))

    return symbols + noise


# 别名
awgn_channel = awgn
add_awgn = awgn
add_noise = awgn
