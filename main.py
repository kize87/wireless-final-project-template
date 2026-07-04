"""无线通信技术期末大作业 — 统一 CLI 入口（高标准重做）。

工厂选路（--mod/--channel/--code 真正生效）、FER 基于 CRC、BER 曲线真实多 SNR 扫描、
6 张中英双语可视化图。指标真实化（checksum_pass / crc_valid / sync_confidence）。

用法:
    python main.py --input Test.txt --output results/received.txt \\
                   --snr 12 --seed 2026 --mod qpsk --channel awgn
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.special import erfc
from scipy.signal import correlate as scipy_correlate
from scipy.stats import norm

# 确保 src 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.source import source_encode, source_decode
from src.framing import build_frame, parse_frame, PREAMBLE_SYMBOLS
from src.crypto import scramble, descramble
from src.channel_coding import channel_encode, channel_decode, CODING_SCHEMES
from src.modulation import qpsk_modulate, qpsk_demodulate, MODULATION_SCHEMES
from src.channel import awgn, CHANNEL_SCHEMES
from src.synchronization import synchronize
from src.metrics import compute_ber, compute_fer, compute_text_match_rate

# 中文字体（中英双语标注）
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

SNR_SWEEP = [0, 2, 4, 6, 8, 10, 12, 14]
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run_pipeline(text, snr_db, seed, mod_fn, demod_fn, channel_fn, code_encode, code_decode):
    """跑一次完整端到端链路，返回各阶段数据与指标。"""
    payload_bits = source_encode(text)
    scrambled = scramble(payload_bits, seed=seed)
    coded = code_encode(scrambled)
    frame = build_frame(coded)
    frame_bits = frame["bits"]
    tx_symbols = mod_fn(frame_bits)
    rx_noisy = channel_fn(tx_symbols, snr_db=snr_db, seed=seed)
    sync_result = synchronize(rx_noisy, preamble=PREAMBLE_SYMBOLS)
    start = sync_result["start_index"]
    rx_from_sync = rx_noisy[start:]
    rx_bits = demod_fn(rx_from_sync)
    parsed = parse_frame(rx_bits)
    fec_bits = parsed["payload"]
    decoded = code_decode(fec_bits)
    recovered_bits = descramble(decoded, seed=seed)
    recovered_text = source_decode(recovered_bits)
    ber = compute_ber(payload_bits, recovered_bits)
    return {
        "payload_bits": payload_bits,
        "frame": frame,
        "frame_bits": frame_bits,
        "tx_symbols": tx_symbols,
        "rx_noisy": rx_noisy,
        "rx_from_sync": rx_from_sync,
        "sync_result": sync_result,
        "parsed": parsed,
        "recovered_bits": recovered_bits,
        "recovered_text": recovered_text,
        "ber": ber,
        "crc_valid": parsed["crc_valid"],
    }


def sweep_ber_fer(text, seed, mod_fn, demod_fn, channel_fn, code_encode, code_decode):
    """多 SNR 扫描端到端 BER/FER（真实链路数据）。"""
    results = []
    for snr in SNR_SWEEP:
        r = run_pipeline(text, snr, seed, mod_fn, demod_fn, channel_fn, code_encode, code_decode)
        results.append({
            "snr": snr, "ber": r["ber"], "fer": compute_fer(r["crc_valid"]),
            "crc_valid": r["crc_valid"],
        })
    return results


def _safe_save(fig, out):
    try:
        fig.tight_layout()
    except Exception:
        pass
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_constellation(tx_symbols, rx_symbols, snr_db, out):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, syms, title in [
        (axes[0], tx_symbols, "发送星座 / TX Constellation"),
        (axes[1], rx_symbols, f"接收星座 / RX Constellation (SNR={snr_db}dB)"),
    ]:
        s = np.array(syms, dtype=complex)
        ax.scatter(s.real, s.imag, s=3, alpha=0.5, color="blue", label="实测 received")
        ax.scatter([1, -1, 1, -1], [1, 1, -1, -1], c="red", marker="x", s=100, label="理想 ideal")
        ax.set_xlabel("同相分量 In-Phase (I)")
        ax.set_ylabel("正交分量 Quadrature (Q)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")
        ax.axhline(0, color="gray", lw=0.5)
        ax.axvline(0, color="gray", lw=0.5)
        ax.legend(fontsize=8)
    _safe_save(fig, out)


def plot_ber_fer(sweep, out):
    snrs = np.array([r["snr"] for r in sweep])
    eb_n0 = snrs - 3  # QPSK k=2
    bers = [max(r["ber"], 1e-10) for r in sweep]
    fers = [max(r["fer"], 1e-10) for r in sweep]
    eb_linear = 10 ** (eb_n0 / 10)
    theo_ber = 0.5 * erfc(np.sqrt(eb_linear))  # 理论未编码 QPSK BER
    theo_rep = np.array([3 * p ** 2 * (1 - p) + p ** 3 for p in theo_ber])  # 理论 (3,1) 重复码

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.semilogy(eb_n0, theo_ber, "g--", label="理论 BER 未编码 / Theoretical uncoded")
    ax.semilogy(eb_n0, theo_rep, "m:", label="理论 BER (3,1)重复码 / Theoretical rep3")
    ax.semilogy(eb_n0, bers, "ro-", markersize=6, label="实测 BER / Measured")
    ax.semilogy(eb_n0, fers, "bs-", markersize=6, label="实测 FER / Measured")
    ax.set_xlabel("Eb/N0 (dB) = SNR - 3")
    ax.set_ylabel("BER / FER")
    ax.set_title("BER/FER vs Eb/N0 — 端到端扫描 / End-to-end sweep")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_ylim(1e-6, 2)
    _safe_save(fig, out)


def plot_sync_correlation(received, preamble, sync_result, out):
    corr = scipy_correlate(np.array(received, dtype=complex),
                           np.array(preamble, dtype=complex), mode="valid", method="fft")
    corr_mag = np.abs(corr)
    start = sync_result["start_index"]
    peak = sync_result["peak"]
    conf = sync_result["confidence"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(corr_mag, "b-", lw=0.8, label="互相关 |R| / correlation")
    ax.axvline(start, color="r", linestyle="--", label=f"检测起点 / start={start}")
    ax.axhline(peak, color="g", linestyle=":", alpha=0.5, label=f"峰值 / peak={peak:.1f}")
    ax.set_xlabel("采样偏移 / Sample offset")
    ax.set_ylabel("互相关幅值 / Correlation magnitude")
    ax.set_title(f"同步互相关峰 / Sync correlation (置信度 conf={conf:.2f})")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    _safe_save(fig, out)


def plot_frame_structure(frame, out):
    fields = [
        ("Preamble\n前导", 50, "#4C72B0"),
        ("Length\n长度", 16, "#55A868"),
        ("Payload\n载荷", len(frame["payload"]), "#C44E52"),
        ("CRC-16\n校验", 16, "#8172B3"),
    ]
    fig, ax = plt.subplots(figsize=(11, 3))
    x = 0
    for name, width, color in fields:
        ax.barh(0, width, left=x, height=0.5, color=color, edgecolor="black")
        ax.text(x + width / 2, 0, f"{name}\n{width} bit", ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        x += width
    ax.set_xlim(0, sum(w for _, w, _ in fields))
    ax.set_ylim(-0.5, 0.5)
    ax.set_xlabel("比特 / Bits")
    ax.set_title("帧结构 / Frame structure")
    ax.set_yticks([])
    _safe_save(fig, out)


def plot_error_pattern(tx_bits, rx_bits, out):
    n = min(len(tx_bits), len(rx_bits))
    if n == 0:
        n = 1
        tx_bits = [0]
        rx_bits = [0]
    errors = [1 if tx_bits[i] != rx_bits[i] else 0 for i in range(n)]
    arr = np.array(errors).reshape(1, -1)
    fig, ax = plt.subplots(figsize=(11, 2.5))
    ax.imshow(arr, aspect="auto", cmap="Reds", interpolation="nearest")
    ax.set_xlabel("比特索引 / Bit index")
    ax.set_ylabel("误码 / Error")
    n_err = sum(errors)
    ax.set_title(f"误码位置 / Error pattern — {n_err}/{n} errors (BER={n_err / max(n, 1):.4f})")
    ax.set_yticks([])
    _safe_save(fig, out)


def plot_channel_response(rx_noisy, tx_symbols, out):
    noise = np.array(rx_noisy, dtype=complex) - np.array(tx_symbols, dtype=complex)
    real_part = np.real(noise)
    if len(real_part) == 0:
        real_part = np.zeros(1)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(real_part, bins=50, density=True, alpha=0.6, color="steelblue",
            label="实测噪声实部 / noise real")
    sigma = np.std(real_part) if np.std(real_part) > 0 else 1e-6
    x = np.linspace(real_part.min(), real_part.max(), 200)
    ax.plot(x, norm.pdf(x, 0, sigma), "r-", lw=2, label="理论高斯 / Gaussian fit")
    ax.set_xlabel("噪声幅度 / Noise amplitude")
    ax.set_ylabel("概率密度 / PDF")
    ax.set_title("AWGN 噪声分布 / AWGN noise distribution")
    ax.legend(fontsize=8)
    _safe_save(fig, out)


def generate_plots(main_result, sweep, out_dir):
    """生成全部 6 张图（每图 try/except，一图失败不阻断）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    plots = [
        ("constellation.png", lambda: plot_constellation(
            main_result["tx_symbols"], main_result["rx_from_sync"],
            main_result["snr_db"], out_dir / "constellation.png")),
        ("ber_curve.png", lambda: plot_ber_fer(sweep, out_dir / "ber_curve.png")),
        ("sync_peak.png", lambda: plot_sync_correlation(
            main_result["rx_noisy"], PREAMBLE_SYMBOLS, main_result["sync_result"],
            out_dir / "sync_peak.png")),
        ("frame_structure.png", lambda: plot_frame_structure(
            main_result["frame"], out_dir / "frame_structure.png")),
        ("error_pattern.png", lambda: plot_error_pattern(
            main_result["error_tx"], main_result["error_rx"],
            out_dir / "error_pattern.png")),
        ("channel_response.png", lambda: plot_channel_response(
            main_result["rx_noisy"], main_result["tx_symbols"],
            out_dir / "channel_response.png")),
    ]
    for name, fn in plots:
        try:
            fn()
        except Exception as e:  # pragma: no cover
            print(f"  [warn] 生成 {name} 失败: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="无线通信基带仿真系统")
    parser.add_argument("--input", required=True, help="输入文本文件路径")
    parser.add_argument("--output", required=True, help="输出恢复文本路径")
    parser.add_argument("--snr", type=float, default=12, help="信噪比 Es/N0 (dB)")
    parser.add_argument("--seed", type=int, default=2026, help="随机种子")
    parser.add_argument("--mod", type=str, default="qpsk", help="调制方式")
    parser.add_argument("--channel", type=str, default="awgn", help="信道模型")
    parser.add_argument("--code", type=str, default="rep3", help="信道编码方案")
    args = parser.parse_args()

    # SNR 范围校验（PPT 讲评：invalid_snr 是头号共性扣分点，CLI 必须显式拒绝非法输入）
    # argparse 的 type=float 已拦截非数值（exit 2），这里再挡 NaN/Inf 与超范围数值。
    if not np.isfinite(args.snr) or not (-20.0 <= args.snr <= 60.0):
        print(f"Error: invalid --snr {args.snr!r}, expected finite value in [-20, 60] dB",
              file=sys.stderr)
        sys.exit(1)

    # 工厂选路（CLI 真正生效，替换原硬编码）
    if args.mod not in MODULATION_SCHEMES:
        print(f"Error: unsupported --mod {args.mod}, available: {list(MODULATION_SCHEMES)}",
              file=sys.stderr)
        sys.exit(1)
    mod_fn, demod_fn = MODULATION_SCHEMES[args.mod]
    if args.channel not in CHANNEL_SCHEMES:
        print(f"Error: unsupported --channel {args.channel}, available: {list(CHANNEL_SCHEMES)}",
              file=sys.stderr)
        sys.exit(1)
    channel_fn = CHANNEL_SCHEMES[args.channel]
    if args.code not in CODING_SCHEMES:
        print(f"Error: unsupported --code {args.code}, available: {list(CODING_SCHEMES)}",
              file=sys.stderr)
        sys.exit(1)
    code_encode, code_decode = CODING_SCHEMES[args.code]

    # 读取文本
    text = Path(args.input).read_text(encoding="utf-8")

    # 主链路（验收 SNR）
    main_result = run_pipeline(text, args.snr, args.seed, mod_fn, demod_fn, channel_fn,
                               code_encode, code_decode)
    main_result["snr_db"] = args.snr

    # 低 SNR(2dB) 用于误码图（展示真实退化）
    try:
        low = run_pipeline(text, 2, args.seed, mod_fn, demod_fn, channel_fn, code_encode, code_decode)
        main_result["error_tx"] = low["payload_bits"]
        main_result["error_rx"] = low["recovered_bits"]
    except Exception:  # pragma: no cover
        main_result["error_tx"] = main_result["payload_bits"]
        main_result["error_rx"] = main_result["recovered_bits"]

    # 多 SNR 扫描（真实 BER/FER 曲线数据）
    sweep = sweep_ber_fer(text, args.seed, mod_fn, demod_fn, channel_fn, code_encode, code_decode)

    # 写入恢复文本
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(main_result["recovered_text"], encoding="utf-8")

    # 指标（真实化）
    crc_valid = main_result["crc_valid"]
    ber = main_result["ber"]
    fer = compute_fer(crc_valid)
    text_match_rate = compute_text_match_rate(text, main_result["recovered_text"])
    metrics = {
        "snr_db": args.snr,
        "seed": args.seed,
        "modulation": args.mod,
        "channel": args.channel,
        "code": args.code,
        "payload_bits": len(main_result["payload_bits"]),
        "ber": ber,
        "fer": fer,
        "text_match_rate": text_match_rate,
        "checksum_pass": crc_valid,  # 真实，基于 CRC（原写死 True）
        "sync_start_index": main_result["sync_result"]["start_index"],
        # 新增真实字段（不破坏 TC-T_014 旧字段）
        "crc_valid": crc_valid,
        "sync_confidence": main_result["sync_result"].get("confidence"),
        "sync_found": main_result["sync_result"].get("found"),
        "eb_n0_db": args.snr - 3,
    }
    metrics_path = output_path.parent / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # 生成图集
    generate_plots(main_result, sweep, RESULTS_DIR)

    # 控制台输出
    print("传输完成！")
    print(f"  SNR: {args.snr} dB (Eb/N0={args.snr - 3} dB)")
    print(f"  Seed: {args.seed}")
    print(f"  Mod/Channel/Code: {args.mod}/{args.channel}/{args.code}")
    print(f"  Payload bits: {len(main_result['payload_bits'])}")
    print(f"  BER: {ber:.6f}")
    print(f"  FER: {fer} (crc_valid={crc_valid})")
    print(f"  Text match rate: {text_match_rate}")
    print(f"  Sync start: {main_result['sync_result']['start_index']} "
          f"(conf={main_result['sync_result'].get('confidence'):.2f})")
    print(f"  输出文件: {args.output}")
    print(f"  指标文件: {metrics_path}")


if __name__ == "__main__":
    main()
