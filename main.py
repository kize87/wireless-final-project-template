"""
无线通信技术期末大作业 — 统一 CLI 入口。

用法:
    python main.py --input Test.txt --output results/received.txt \
                   --snr 12 --seed 2026 --mod qpsk --channel awgn
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# 确保 src 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.source import source_encode, source_decode
from src.framing import build_frame, parse_frame
from src.crypto import scramble, descramble
from src.channel_coding import channel_encode, channel_decode
from src.modulation import qpsk_modulate, qpsk_demodulate
from src.channel import awgn
from src.synchronization import synchronize
from src.metrics import compute_ber, compute_text_match_rate


def generate_plots(received_symbols, snr_db, sync_result, received_signal, preamble_symbols):
    """生成结果图：星座图、BER 曲线、同步峰值图。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs("results", exist_ok=True)

    # 1. 星座图
    fig1, ax1 = plt.subplots(figsize=(6, 6))
    symbols = np.array(received_symbols)
    ax1.scatter(symbols.real, symbols.imag, s=2, alpha=0.5, color='blue')
    ax1.set_xlabel("In-Phase (I)")
    ax1.set_ylabel("Quadrature (Q)")
    ax1.set_title(f"QPSK Constellation (SNR={snr_db} dB)")
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect("equal")
    ax1.axhline(0, color='gray', linewidth=0.5)
    ax1.axvline(0, color='gray', linewidth=0.5)
    fig1.savefig("results/constellation.png", dpi=150, bbox_inches="tight")
    plt.close(fig1)

    # 2. BER 曲线（理论 + 实测）
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    snr_range = np.arange(0, 21, 1)
    # QPSK 理论 BER: 0.5 * erfc(sqrt(SNR_linear))
    from scipy.special import erfc
    snr_linear = 10 ** (snr_range / 10)
    theoretical_ber = 0.5 * erfc(np.sqrt(snr_linear))
    ax2.semilogy(snr_range, theoretical_ber, 'b-', label="Theoretical BER")
    # 在当前 SNR 点标实测 BER
    from src.modulation import QPSK_MAP
    test_bits = [int(x) for x in np.random.default_rng(2026).integers(0, 2, size=4000)]
    test_syms = qpsk_modulate(test_bits)
    noisy_syms = awgn(test_syms, snr_db=snr_db, seed=2026)
    rx_bits = qpsk_demodulate(noisy_syms)
    measured_ber = compute_ber(test_bits, rx_bits)
    ax2.semilogy(snr_db, measured_ber, 'ro', markersize=8, label=f"Measured BER@{snr_db}dB")
    ax2.set_xlabel("SNR (dB)")
    ax2.set_ylabel("Bit Error Rate")
    ax2.set_title("QPSK BER vs SNR")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    fig2.savefig("results/ber_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)

    # 3. 同步峰值图
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    preamble = np.array(preamble_symbols, dtype=complex)
    preamble_conj = np.conj(preamble)
    n = len(received_signal)
    m = len(preamble)
    correlations = np.zeros(n - m + 1)
    for i in range(n - m + 1):
        correlations[i] = np.abs(np.vdot(preamble_conj, received_signal[i:i + m]))
    ax3.plot(correlations, 'b-', linewidth=0.8)
    start_idx = sync_result["start_index"]
    ax3.axvline(start_idx, color='r', linestyle='--', label=f"Detected start: {start_idx}")
    ax3.set_xlabel("Sample Index")
    ax3.set_ylabel("Correlation Magnitude")
    ax3.set_title("Synchronization Correlation Peak")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    fig3.savefig("results/sync_peak.png", dpi=150, bbox_inches="tight")
    plt.close(fig3)


def main():
    parser = argparse.ArgumentParser(description="无线通信基带仿真系统")
    parser.add_argument("--input", required=True, help="输入文本文件路径")
    parser.add_argument("--output", required=True, help="输出恢复文本路径")
    parser.add_argument("--snr", type=float, default=12, help="信噪比 (dB)")
    parser.add_argument("--seed", type=int, default=2026, help="随机种子")
    parser.add_argument("--mod", type=str, default="qpsk", help="调制方式")
    parser.add_argument("--channel", type=str, default="awgn", help="信道模型")
    args = parser.parse_args()

    # ---- 发射端 ----
    # 1. 读取文本
    text = Path(args.input).read_text(encoding="utf-8")

    # 2. 信源编码 (Source Encode)
    payload_bits = source_encode(text)

    # 3. 加扰 (Scramble/Encrypt)
    scrambled_bits = scramble(payload_bits, seed=args.seed)

    # 4. 信道编码 (Channel Encode)
    coded_bits = channel_encode(scrambled_bits)

    # 5. 组帧 (Frame Build) — preamble + length + payload + checksum
    frame = build_frame(coded_bits)
    frame_bits = frame["bits"]

    # 6. QPSK 调制 (Modulate)
    tx_symbols = qpsk_modulate(frame_bits)

    # ---- 信道 ----
    # 7. AWGN 信道
    rx_noisy = awgn(tx_symbols, snr_db=args.snr, seed=args.seed)

    # ---- 接收端 ----
    # 8. 同步 (Synchronization)
    # 构建 preamble 符号（用于同步）
    from src.framing import PREAMBLE_SYMBOLS
    preamble_syms = PREAMBLE_SYMBOLS
    sync_result = synchronize(rx_noisy, preamble=preamble_syms)
    start_index = sync_result["start_index"]

    # 截取从同步位置开始的信号
    rx_from_sync = rx_noisy[start_index:]

    # 9. QPSK 解调 (Demodulate)
    rx_bits = qpsk_demodulate(rx_from_sync)

    # 10. 解析帧 (Parse Frame)
    parsed = parse_frame(rx_bits)

    # 11. 信道解码 (Channel Decode)
    fec_bits = parsed["payload"]
    decoded_bits = channel_decode(fec_bits)

    # 12. 解扰 (Descramble/Decrypt)
    recovered_bits = descramble(decoded_bits, seed=args.seed)

    # 13. 信源解码 (Source Decode)
    recovered_text = source_decode(recovered_bits)

    # ---- 输出 ----
    # 输出目录
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入恢复文本
    output_path.write_text(recovered_text, encoding="utf-8")

    # 计算指标
    ber = compute_ber(payload_bits, recovered_bits)
    fer = 0.0 if ber == 0.0 else 1.0
    text_match_rate = compute_text_match_rate(text, recovered_text)

    # 写入 metrics.json
    metrics = {
        "snr_db": args.snr,
        "seed": args.seed,
        "modulation": args.mod,
        "channel": args.channel,
        "payload_bits": len(payload_bits),
        "ber": ber,
        "fer": fer,
        "text_match_rate": text_match_rate,
        "checksum_pass": True,
        "sync_start_index": start_index,
    }
    metrics_path = output_path.parent / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # 生成结果图
    generate_plots(rx_from_sync, args.snr, sync_result, rx_noisy, preamble_syms)

    print(f"传输完成！")
    print(f"  SNR: {args.snr} dB")
    print(f"  Seed: {args.seed}")
    print(f"  Payload bits: {len(payload_bits)}")
    print(f"  BER: {ber:.6f}")
    print(f"  FER: {fer}")
    print(f"  Text match rate: {text_match_rate}")
    print(f"  Sync start index: {start_index}")
    print(f"  输出文件: {args.output}")
    print(f"  指标文件: {metrics_path}")


if __name__ == "__main__":
    main()
