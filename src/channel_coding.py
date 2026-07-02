"""
信道编码模块 — (3,1) 重复码 FEC。
"""


def channel_encode(bits):
    """每比特重复 3 次进行编码。"""
    bits = [int(x) for x in list(bits)]
    coded = []
    for b in bits:
        coded.extend([b, b, b])
    return coded


def channel_decode(coded_bits):
    """3 比特一组，多数投票解码。"""
    coded_bits = [int(x) for x in list(coded_bits)]
    n = len(coded_bits) // 3
    decoded = []
    for i in range(n):
        triple = coded_bits[3 * i : 3 * i + 3]
        # 多数投票
        if sum(triple) >= 2:
            decoded.append(1)
        else:
            decoded.append(0)
    return decoded


# 别名
encode = channel_encode
decode = channel_decode
encode_bits = channel_encode
decode_bits = channel_decode
fec_encode = channel_encode
fec_decode = channel_decode
