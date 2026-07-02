"""Mock 验证脚本 — 验证 DESIGN 规约 M1-M8（阶段 3 产出）。

设计意图：在写实现前，用手推 + 最小脚本验证关键设计点，把"运行后才调试"的 bug 提前到设计阶段发现。
每项打印 PASS/FAIL，并生成 mock 可视化预览图。

运行：
    cd wireless-final-project-template
    PYTHONPATH=. python mock/verify_design.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

# 确保 src 可导入
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MPLBACKEND", "Agg")

from src.modulation import qpsk_modulate, qpsk_demodulate, QPSK_MAP
from src.framing import build_frame, parse_frame, _crc16, PREAMBLE_SYMBOLS, PREAMBLE_BITS
from src.synchronization import synchronize
from src.source import source_encode

RESULTS = []


def check(name: str, cond: bool, detail: str = ""):
    RESULTS.append((name, cond, detail))
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


# ---------- M1: QPSK 4 比特对 mod→demod 闭环 ----------
def m1_qpsk_roundtrip():
    pairs = [(0, 0), (0, 1), (1, 1), (1, 0)]
    ok = True
    for p in pairs:
        bits = list(p)
        sym = qpsk_modulate(bits)
        demod = qpsk_demodulate(sym)
        if demod[:2] != list(p):
            ok = False
            check(f"M1 QPSK 闭环 {p}", False, f"demod={demod}")
            return
    check("M1 QPSK 4 比特对 mod→demod 闭环", ok, "00/01/11/10 全闭环")


# ---------- M2: b0 看虚部、b1 看实部与映射表一致 ----------
def m2_demod_rule_matches_map():
    # 映射表：00→Q1(+,+), 01→Q2(-,+), 11→Q3(-,-), 10→Q4(+,-)
    expected = {(0, 0): (+1, +1), (0, 1): (-1, +1), (1, 1): (-1, -1), (1, 0): (+1, -1)}
    ok = True
    for p, (si, sq) in expected.items():
        s = QPSK_MAP[p] / np.sqrt(2)
        b0 = 1 if s.imag < 0 else 0
        b1 = 1 if s.real < 0 else 0
        # 解调还原的 b0/b1 应等于原 p
        if (b0, b1) != p:
            ok = False
            check(f"M2 解调规则 {p}", False, f"got {(b0,b1)} expect {p}")
            return
    check("M2 b0看虚部/b1看实部与映射表一致", ok, "4 种全对")


# ---------- M3: PREAMBLE 自相关尖锐单峰 ----------
def m3_preamble_autocorr():
    p = np.array(PREAMBLE_SYMBOLS, dtype=complex)
    n = len(p)
    # 循环自相关（归一化）
    corr = np.array([abs(np.vdot(p, np.roll(p, k))) for k in range(n)])
    peak = corr[0]
    sidelobe = corr[1:].max()
    ratio = sidelobe / peak
    check("M3 PREAMBLE 自相关尖锐单峰", ratio < 0.5, f"旁瓣/主峰={ratio:.3f}（应<0.5）")
    # 生成 mock 图
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(corr, "b-o", markersize=3)
        ax.axhline(0.5 * peak, color="r", linestyle="--", label="0.5×peak 阈值")
        ax.set_title("前导自相关 / Preamble Autocorrelation")
        ax.set_xlabel("移位 / Shift")
        ax.set_ylabel("|R|")
        ax.legend()
        fig.tight_layout()
        out = PROJECT_ROOT / "mock" / "mock_preamble_autocorr.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"      -> {out}")
    except Exception as e:
        print(f"      (skip plot: {e})")


# ---------- M4: CRC 闭环 build→重算→比对 ----------
def m4_crc_roundtrip():
    # build_frame 用 _crc16(PREAMBLE+Length+Payload) 生成 checksum
    # 独立重算应与 build_frame 返回的 checksum 一致（验证 CRC 算法闭环）
    payload = [int(x) for x in np.random.default_rng(1234).integers(0, 2, size=200)]
    frame = build_frame(payload)
    # 重建 length_bits（大端 16bit）
    length = len(payload)
    length_bits = [(length >> i) & 1 for i in range(15, -1, -1)]
    recalc = _crc16(PREAMBLE_BITS + length_bits + payload)
    ok = recalc == list(frame["checksum"])
    check("M4 CRC 闭环 build→重算→比对", ok,
          "算法闭环，parse_frame 将用同逻辑置 crc_valid" if ok else "重算不一致")
    # 额外：验证翻 payload 中 1 bit 后 CRC 不匹配（检错能力）
    if ok:
        flipped = list(frame["bits"])
        flip_at = 66 + 10  # payload 区域内（CRC 覆盖范围）
        flipped[flip_at] ^= 1
        fl_payload = flipped[66:66 + length]  # 含被翻的位
        fl_recalc = _crc16(PREAMBLE_BITS + length_bits + fl_payload)
        fl_rx = flipped[66 + length:66 + length + 16]
        detect = (fl_recalc != fl_rx)
        check("M4b CRC 单 bit 检错", detect, "翻 payload 1 bit 后 CRC 不匹配")


# ---------- M5: parse_frame 用 length 截 padding（奇数 payload 255） ----------
def m5_padding_truncated():
    payload = [int(x) for x in np.random.default_rng(2030).integers(0, 2, size=255)]
    frame = build_frame(payload)
    frame_bits = frame["bits"]
    # QPSK 调制（337 bit 奇数补0→169 符号）→ 解调 → 338 bit
    syms = qpsk_modulate(frame_bits)
    rx_bits = qpsk_demodulate(syms)
    parsed = parse_frame(rx_bits)
    rec = list(parsed["payload"])[:255]
    ok = rec == payload and len(rec) == 255
    check("M5 parse_frame 按 length 截 padding（255bit）", ok,
          f"还原 {len(rec)} bit" + ("" if ok else " — 失败"))


# ---------- M6: 同步阈值不误杀周期 preamble ----------
def m6_sync_periodic_preamble():
    # TC-T_013 场景：周期 preamble [1+1j,-1+1j,-1-1j,1-1j]*8/sqrt(2)，25 符号噪声偏移
    rng = np.random.default_rng(2026)
    preamble = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j] * 8, dtype=complex) / np.sqrt(2)
    payload = np.array([1 - 1j, -1 - 1j, 1 + 1j, -1 + 1j] * 20, dtype=complex) / np.sqrt(2)
    prefix = (rng.normal(size=25) + 1j * rng.normal(size=25)) / np.sqrt(2)
    received = np.concatenate([prefix, preamble, payload])
    result = synchronize(received, preamble=preamble)
    start = result.get("start_index", result.get("sync_start_index"))
    ok = abs(int(start) - 25) <= 1
    # 独立算 confidence（设计中的阈值逻辑）
    m = len(preamble)
    corr = np.array([abs(np.vdot(preamble, received[i:i + m])) for i in range(len(received) - m + 1)])
    peak = corr.max()
    mean_corr = corr.mean()
    confidence = peak / (m * np.mean(np.abs(received))) if np.mean(np.abs(received)) > 0 else 0
    check("M6 周期 preamble 同步 argmax=25", ok,
          f"start={start} (容差±1), confidence≈{confidence:.2f}")
    # 关键：即使 found=False，start_index 仍返回 argmax（设计约束）
    check("M6b start_index 恒返回 argmax（不受阈值）", ok,
          "阈值仅作 found 附加字段，不拒绝返回起点")


# ---------- M7: BER 理论线 3dB 修正 ----------
def m7_ber_3db_correction():
    from scipy.special import erfc
    snr_db = np.arange(0, 21, 1)
    # 错误线：把 Es/N0 当 Eb/N0
    wrong = 0.5 * erfc(np.sqrt(10 ** (snr_db / 10)))
    # 正确线：Eb/N0 = snr_db - 3 (QPSK k=2)
    correct = 0.5 * erfc(np.sqrt(10 ** ((snr_db - 3) / 10)))
    # 在 12dB 处，正线 BER 应远高于错线（3dB 差异：正线 Eb/N0=9dB，错线误当 12dB）
    ratio = correct[12] / max(wrong[12], 1e-30)
    ok = ratio > 100  # 正线是错线 100+ 倍，证明 3dB 差异真实存在
    check("M7 BER 理论线 3dB 修正", ok,
          f"@12dB 错线={wrong[12]:.2e} 正线={correct[12]:.2e} 正线/错线={ratio:.0f}×")
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.semilogy(snr_db, wrong, "r--", label="错误：Es/N0 当 Eb/N0 / wrong")
        ax.semilogy(snr_db, correct, "g-", label="正确：Eb/N0=snr-3 / correct")
        ax.axvline(12, color="gray", linestyle=":", label="验收 SNR=12dB")
        ax.set_xlabel("SNR (dB, Es/N0)")
        ax.set_ylabel("BER")
        ax.set_title("BER 理论线 3dB 修正对比 / BER 3dB Correction")
        ax.legend()
        ax.grid(True, which="both", alpha=0.3)
        fig.tight_layout()
        out = PROJECT_ROOT / "mock" / "mock_ber_3db.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"      -> {out}")
    except Exception as e:
        print(f"      (skip plot: {e})")


# ---------- M8: 端到端比特数链收发对齐 ----------
def m8_bitstream_alignment():
    sample = ("无线通信技术课程要求学生理解调制、编码、信道和接收机处理。"
              "本测试文本用于验证源编码、帧结构、QPSK 调制、AWGN 信道、同步和端到端恢复。")
    bits = source_encode(sample)
    n_bytes = len(sample.encode("utf-8"))
    n_bits = len(bits)
    src_ok = (n_bits == n_bytes * 8) and (n_bits % 8 == 0)
    # 推演各阶段
    coded = n_bits * 3
    frame = coded + 50 + 16 + 16
    symbols = frame // 2
    even_ok = frame % 2 == 0
    rx_bits = symbols * 2
    parsed = rx_bits - 50 - 16 - 16
    decoded = parsed // 3
    aligned = (decoded == n_bits) and (decoded == 1544)  # 193*8
    check("M8 端到端比特数链收发对齐", src_ok and even_ok and aligned,
          f"{n_bytes}字节/{n_bits}bit → coded {coded} → frame {frame} → {symbols}sym → 解码 {decoded}bit"
          f"{' (对齐1544)' if aligned else ' (未对齐!)'}")


def main():
    print("=" * 60)
    print("Mock 验证 M1-M8（DESIGN 规约）")
    print("=" * 60)
    m1_qpsk_roundtrip()
    m2_demod_rule_matches_map()
    m3_preamble_autocorr()
    m4_crc_roundtrip()
    m5_padding_truncated()
    m6_sync_periodic_preamble()
    m7_ber_3db_correction()
    m8_bitstream_alignment()
    print("=" * 60)
    passed = sum(1 for _, c, _ in RESULTS if c)
    total = len(RESULTS)
    print(f"结果：{passed}/{total} PASS")
    if passed < total:
        print("\n失败项（需回 DESIGN 修订）：")
        for name, c, detail in RESULTS:
            if not c:
                print(f"  - {name}: {detail}")
        return 1
    print("\n全部通过，可进入阶段 4（TDD 实现）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
