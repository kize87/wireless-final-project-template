"""
源编码模块 — 负责 UTF-8 中文文本与比特流之间的转换。
"""


def source_encode(text: str) -> list:
    """将文本 UTF-8 编码为比特列表（8 位对齐）。"""
    raw = text.encode("utf-8")
    bits = []
    for byte in raw:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def source_decode(bits: list) -> str:
    """将比特列表恢复为 UTF-8 文本。"""
    # 补齐到 8 的倍数
    bits = list(bits)
    remainder = len(bits) % 8
    if remainder:
        bits += [0] * (8 - remainder)
    bytes_list = []
    for i in range(0, len(bits), 8):
        val = 0
        for b in bits[i : i + 8]:
            val = (val << 1) | int(b)
        bytes_list.append(val)
    return bytes(bytes_list).decode("utf-8", errors="replace")


# 别名（测试用）
text_to_bits = source_encode
bits_to_text = source_decode
