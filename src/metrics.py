"""
指标计算模块 — 计算 BER、FER、text_match_rate 等。
"""


def compute_ber(original_bits, received_bits):
    """计算比特错误率 (BER)。"""
    original_bits = [int(x) for x in list(original_bits)]
    received_bits = [int(x) for x in list(received_bits)]
    n = min(len(original_bits), len(received_bits))
    if n == 0:
        return 0.0
    errors = sum(1 for i in range(n) if original_bits[i] != received_bits[i])
    return errors / n


def compute_text_match_rate(original_text, received_text):
    """计算文本匹配率。"""
    if original_text == received_text:
        return 1.0
    n = max(len(original_text), len(received_text))
    if n == 0:
        return 1.0
    matches = sum(1 for a, b in zip(original_text, received_text) if a == b)
    return matches / n


def compute_checksum_pass(original_checksum, received_checksum):
    """验证校验和是否通过。"""
    return list(original_checksum) == list(received_checksum)
