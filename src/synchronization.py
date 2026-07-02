"""同步模块 — 互相关帧起始检测，FFT 加速 + 置信度阈值。

返回 start_index 始终为 argmax（保 TC-T_013 红线：周期 preamble 也能给起点）。
confidence/found 为附加字段，不拒绝返回起点；main.py 据此算真 FER。
"""
from __future__ import annotations

import numpy as np
from scipy.signal import correlate as scipy_correlate

from .framing import PREAMBLE_SYMBOLS


def synchronize(received, preamble=None, *, threshold_ratio: float = 0.3) -> dict:
    """互相关检测帧起始位置（匹配滤波）。

    Returns
    -------
    dict with:
      start_index : int   — 始终返回 argmax（保 TC-T_013 红线）
      confidence  : float — peak / (|preamble| * mean(|received|))
      peak        : float — 相关峰幅值
      found       : bool  — confidence >= threshold_ratio
    """
    received = np.array(received, dtype=complex)

    if preamble is None:
        preamble = PREAMBLE_SYMBOLS
    else:
        preamble = np.array(preamble, dtype=complex)

    n = len(received)
    m = len(preamble)

    if n < m:
        return {"start_index": 0, "confidence": 0.0, "peak": 0.0, "found": False}

    # FFT 加速互相关：scipy 对复数第二参数取共轭，等价匹配滤波 vdot(preamble, received[k:k+m])
    corr = scipy_correlate(received, preamble, mode="valid", method="fft")
    corr_mag = np.abs(corr)
    start = int(np.argmax(corr_mag))
    peak = float(corr_mag[start])

    # 置信度：归一化峰值得分
    mean_mag = float(np.mean(np.abs(received)))
    denom = m * mean_mag
    confidence = peak / denom if denom > 0 else 0.0
    found = confidence >= threshold_ratio

    return {
        "start_index": start,
        "confidence": confidence,
        "peak": peak,
        "found": found,
    }


# 别名
detect_frame_start = synchronize
find_preamble = synchronize
sync = synchronize
