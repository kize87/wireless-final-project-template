"""
同步模块 — 基于互相关的帧起始检测。
"""

import numpy as np

from .framing import PREAMBLE_SYMBOLS


def synchronize(received, preamble=None):
    """使用互相关检测帧起始位置。

    Parameters
    ----------
    received : array-like
        接收到的复数信号
    preamble : array-like, optional
        已知的 preamble 符号序列

    Returns
    -------
    dict with 'start_index'
    """
    received = np.array(received, dtype=complex)

    if preamble is None:
        preamble = PREAMBLE_SYMBOLS
    else:
        preamble = np.array(preamble, dtype=complex)

    n = len(received)
    m = len(preamble)

    if n < m:
        return {"start_index": 0}

    # 互相关（匹配滤波）：对每个偏移位置计算内积幅值
    correlations = np.zeros(n - m + 1)
    for i in range(n - m + 1):
        correlations[i] = np.abs(np.vdot(preamble, received[i:i + m]))

    # 找到峰值位置
    start = int(np.argmax(correlations))

    return {"start_index": start}


# 别名
detect_frame_start = synchronize
find_preamble = synchronize
sync = synchronize
