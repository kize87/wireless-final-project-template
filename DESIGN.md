# 系统设计文档 — 无线通信基带仿真系统

> **Spec freeze v1**（2026-07-02）。本文档为重做后的冻结规约。阶段 4 起任何接口/数值约定变更须在下方"变更记录"表留痕，并同步 MOCK_TEST_REPORT.md。

## 变更记录

| 版本 | 日期 | 变更点 | 原因 | 影响模块 |
|------|------|--------|------|----------|
| v1 | 2026-07-02 | 初次冻结（高标准重做规约） | 修复 8 条硬伤 + 2 条新发现 | 全部 |

---

## 1. 系统概述

本系统实现一个完整的**无线通信基带仿真链路**，将 UTF-8 中文文本编码为比特流，经过发射端处理、信道传输、接收端处理后恢复原始文本。重做目标：每个环节"真实正确"（指标非写死、CRC 真验证、CLI 真生效、BER 曲线与端到端一致），配 TDD + 覆盖率门禁 + 中英双语可视化。

## 2. 系统链路

```
[文本输入] → Source Encode → Scramble/Encrypt → Channel Encode
    → Frame Build → QPSK Modulate → AWGN Channel
    → Synchronization → QPSK Demodulate → Frame Parse
    → Channel Decode → Descramble/Decrypt → Source Decode → [文本输出]
                                          → Metrics / Plots
```

## 3. 模块规约

### 3.1 Source Encode（信源编码）— `src/source.py`

```python
def source_encode(text: str) -> list[int]      # UTF-8→字节→MSB-first 比特，长度恒为 8 倍数
def source_decode(bits: list[int]) -> str       # 8 位分组→字节→UTF-8 解码（errors="replace"）
```
- **边界**：`source_encode("")` → `[]`；`source_decode([])` → `""`。
- **可逆性**：对任意 UTF-8 文本 `t`，`source_decode(source_encode(t)) == t`。
- **别名**：`text_to_bits`、`bits_to_text`（保留，公开测试用）。
- **为什么**：原实现已正确，仅补类型标注与空文本显式处理，避免下游 `len([])` 除零。

### 3.2 Scramble / Encrypt（加扰/解扰）— `src/crypto.py`

```python
def scramble(bits: list[int], seed: int = 2026) -> list[int]
def descramble(bits: list[int], seed: int = 2026) -> list[int]
```
- **规约**：`rng = np.random.default_rng(seed)`，生成与 `bits` 等长伪随机比特 `r`，输出 `b XOR r`。XOR 自逆 ⇒ `descramble(scramble(b, s), s) == b` 对任意 `s`。
- **seed 来源**：CLI `--seed`，收发两端必须一致。
- **声明**：本模块是**加扰（能量扩散）而非加密**——PRNG 可逆、种子公开，仅用于打散长串 0/1 以利于同步与均衡，不具备保密性。
- **别名**：`scramble_bits`/`descramble_bits`/`encrypt`/`decrypt`/`encrypt_bits`/`decrypt_bits`（保留）。

### 3.3 Channel Encode（信道编码）— `src/channel_coding.py`

```python
def channel_encode(bits: list[int]) -> list[int]      # (3,1) 重复码，每比特×3，编码率 1/3
def channel_decode(coded: list[int]) -> list[int]      # 每 3 比特多数投票（sum≥2→1）
CODING_SCHEMES: dict[str, tuple[Callable, Callable]] = {"rep3": (channel_encode, channel_decode)}
```
- **可逆性**：无噪声下 `channel_decode(channel_encode(b)) == b`。
- **容错**：3 比特组错 1 可纠，错 2 判错。
- **可插拔**：为 Level3 汉明(7,4) 留 `CODING_SCHEMES["hamming74"]` 注册点，main.py 按 `--code` 选（默认 `rep3`）。
- **别名**：`encode`/`decode`/`encode_bits`/`decode_bits`/`fec_encode`/`fec_decode`（保留）。

### 3.4 Frame Build（组帧）★重点 — `src/framing.py`

```python
def build_frame(payload_bits: list[int]) -> dict
    # 返回 {preamble, length, payload, checksum, bits, crc_valid: True}

def parse_frame(frame, *, verify_crc: bool = True) -> dict
    # 返回 {preamble, length, payload, checksum, crc_valid: bool, crc_mismatch: bool}
    # verify_crc=True 时重算 CRC 并与帧尾比对，置 crc_valid；不抛异常（best-effort 解码）
```

帧字段固化（不可变）：

| 字段 | 比特 | 偏移 | 说明 |
|------|------|------|------|
| Preamble | 50 | 0 | 25 QPSK 符号，`rng=default_rng(42)` 伪随机，保持 `PREAMBLE_SYMBOLS`/`PREAMBLE_BITS` |
| Length | 16 | 50 | 大端，payload 比特数 |
| Payload | N | 66 | 信道编码后比特 |
| CRC-16 | 16 | 66+N | CRC-CCITT（poly 0xA001, init 0xFFFF），覆盖 PREAMBLE+Length+Payload |

- **CRC 真实验证**（修复硬伤#4）：`parse_frame` 重算 `_crc16(received_preamble + length + payload)`，与接收 checksum 比对 → `crc_valid`。**不抛异常**——保 TC-T_006/011 在噪声下也能返回 payload 供测试断言；main.py 用 `crc_valid` 算真 FER。
- **padding**：QPSK 奇数比特补 0 由 modulation 负责；parse_frame 一律按 Length 截取 payload，丢弃尾部 padding 与多余位。
- **为什么**：原 `parse_frame:104` 只提 checksum 不验，纠错检错能力为零。改为返回标志而非抛异常，兼顾"真实验证"与"测试可断言"。

### 3.5 QPSK Modulate / Demodulate（调制/解调）— `src/modulation.py`

```python
def qpsk_modulate(bits: list[int]) -> np.ndarray[complex]      # 奇数补 0，单位功率
def qpsk_demodulate(symbols: np.ndarray[complex]) -> list[int]
MODULATION_SCHEMES = {"qpsk": (qpsk_modulate, qpsk_demodulate)}
```

Gray 编码映射表（`QPSK_MAP`，**红线不可改**，TC-T_009）：

| 比特对 | 象限 | 复数 |
|--------|------|------|
| (0,0) | Q1 | (1+1j)/√2 |
| (0,1) | Q2 | (-1+1j)/√2 |
| (1,1) | Q3 | (-1-1j)/√2 |
| (1,0) | Q4 | (1-1j)/√2 |

- **解调规则**（已验证正确）：`b0 = 1 if s.imag<0 else 0`（看虚部），`b1 = 1 if s.real<0 else 0`（看实部）。
- **单位功率**：每符号 |s|²=1，平均功率=1（断言 ∈[0.8,1.2]）。
- **可插拔**：为 BPSK/16QAM 留 `MODULATION_SCHEMES` 注册点；默认仅实现 qpsk（Level2 稳）。main.py 按 `--mod` 查表，未注册值 `sys.exit(报错)`。
- **别名**：`modulate_qpsk`/`demodulate_qpsk`/`qpsk_mapper`/`qpsk_demapper`/`modulate`/`demodulate`（保留）。

### 3.6 Channel（AWGN 信道）— `src/channel.py`

```python
def awgn(symbols: np.ndarray[complex], snr_db: float = 12, seed: int = 2026) -> np.ndarray[complex]
CHANNEL_SCHEMES = {"awgn": awgn}
```

**SNR 定义（必须明确，修复硬伤#7）**：`snr_db` 为 **Es/N0（符号信噪比）**。
- `signal_power = mean(|s|²) = Es`
- `noise_power = Es / 10^(snr_db/10)`
- 复噪声实/虚部各 `N(0, √(noise_power/2))`，总方差 = `noise_power`
- BER 曲线横轴用 **Eb/N0 = Es/N0 − 10·log10(k)**，QPSK k=2 ⇒ **Eb/N0 = snr_db − 3 dB**

- **可复现**：`rng = np.random.default_rng(seed)`，同 seed 同输出（TC-T_012 红线）。
- **可插拔**：为 Level3 Rayleigh 留 `CHANNEL_SCHEMES["rayleigh"]`，main.py 按 `--channel` 选，未注册报错退出。
- **别名**：`awgn_channel`/`add_awgn`/`add_noise`（保留）。

### 3.7 Synchronization（同步）★重点 — `src/synchronization.py`

```python
def synchronize(received, preamble=None, *, threshold_ratio: float = 0.3) -> dict
    # 返回 {
    #   start_index: int,      # 始终返回 argmax（保 TC-T_013 红线）
    #   confidence: float,     # peak / (|preamble|·E[|r|])
    #   peak: float,
    #   found: bool,           # peak >= threshold_ratio * (|preamble|·E[|r|])
    # }
```
- **阈值**：`found = peak >= threshold_ratio * (|preamble|·E[|r|])`（相对阈值，默认 0.3）。`start_index` 恒为 argmax，**不因阈值拒绝返回**（保 TC-T_013 周期 preamble 也能给起点）。
- **无帧处理**：`found=False` 时 main.py 仍尽力解调，FER=1、`sync_confidence` 如实报告。
- **FFT 加速**：用 `scipy.signal.correlate(received, conj(preamble), method='fft')` 替换原 O(n·m) Python 循环；原循环保留为 fallback（测试用）。
- **为什么**：原实现无阈值、无无帧分支、O(n·m) 慢（硬伤#5）。`found` 给 main.py 算真 FER 的依据；FFT 把数千符号同步降到一次性卷积。
- **别名**：`detect_frame_start`/`find_preamble`/`sync`（保留）。

### 3.8 Channel Decode（信道解码）— `src/channel_coding.py`

(3,1) 重复码多数投票，每 3 比特一组 `sum≥2→1`。见 §3.3。

### 3.9 Source Decode（信源解码）— `src/source.py`

比特流按 8 位一组恢复字节，UTF-8 解码（errors="replace"）。见 §3.1。

### 3.10 Metrics（指标计算，真实化）★重点 — `src/metrics.py`

```python
def compute_ber(original_bits, received_bits) -> float
def compute_fer(crc_valid: bool | list[bool]) -> float       # 新增：单帧 0/1，多帧 failed/total
def compute_text_match_rate(original_text, received_text) -> float
def compute_checksum_pass(tx_checksum, rx_checksum) -> bool   # 已存在，main.py 真正调用
```
- **FER 真实化**（修复硬伤#2）：单帧 `fer = 0.0 if crc_valid else 1.0`；多帧扫描 `failed/total`。**不再** `0.0 if ber==0.0 else 1.0`。
- **checksum_pass**（修复硬伤#3）：main.py 调用 `compute_checksum_pass` 或直接用 `crc_valid`。

### 3.11 main.py（CLI 真正生效 + 真实曲线 + 工厂选路）★重点

- **工厂选路**（修复硬伤#1，替换 main.py:125,129 硬编码）：
  ```python
  mod_fn, demod_fn = MODULATION_SCHEMES[args.mod]   # KeyError → sys.exit(报错)
  channel_fn = CHANNEL_SCHEMES[args.channel]
  tx_symbols = mod_fn(frame_bits)
  rx_noisy = channel_fn(tx_symbols, args.snr, args.seed)
  ```
- **metrics 真实化**（替换 main.py:168,181）：
  ```python
  parsed = parse_frame(rx_bits)
  crc_valid = parsed["crc_valid"]
  ber = compute_ber(payload_bits, recovered_bits)
  fer = 0.0 if crc_valid else 1.0
  checksum_pass = crc_valid
  # 新增字段（不破坏 TC-T_014）：sync_confidence, crc_valid, eb_n0_db
  ```
- **BER 曲线真实化**（修复硬伤#6,7，替换 main.py:52-74）：删另造 4000bit；对**真实帧**在 SNR∈{0,2,4,6,8,10,12,14} dB 各跑完整链路，记录端到端 BER/FER。横轴 **Eb/N0 = snr_db − 3**。叠加：理论未编码 QPSK `0.5·erfc(√(Eb/N0))`、理论 (3,1) 重复码 BER。
- **generate_plots 重构**：模块顶部 `import matplotlib`（去函数内 import）；新增图集函数；每图 try/except 包裹（一图失败不阻断）。

## 4. SNR 与 BER 约定（本次重做核心修正）

- `channel.py` 的 `snr_db` = **Es/N0**（符号信噪比）。
- BER 曲线横轴 = **Eb/N0** = Es/N0 − 10·log10(bits_per_symbol)；QPSK 每符号 2 比特 ⇒ Eb/N0 = snr_db − 3 dB。
- 理论未编码 QPSK BER（AWGN）= `0.5 · erfc(√(Eb/N0_linear))`，其中 `Eb/N0_linear = 10^((snr_db−3)/10)`。
- 原 main.py:58 用 `0.5·erfc(√(10^(snr_db/10)))` 把 Es/N0 当 Eb/N0，导致理论线左移 3dB、实测点"挂在曲线之上"。本次修正。

## 5. 数据流推演（M8 验证，用 conftest SAMPLE_TEXT 实际值）

输入 `SAMPLE_TEXT`（UTF-8 编码 = 193 字节，与 metrics.json `payload_bits=1544` 吻合，193×8=1544）：

| 阶段 | 计算 | 比特/符号数 |
|------|------|-----------|
| Source Encode | 193 字节 × 8 | 1544 bit |
| Scramble | 长度不变 | 1544 bit |
| Channel Encode (3,1) | × 3 | 4632 bit |
| Frame Build | + 50 + 16 + 16 | 4714 bit |
| QPSK Modulate | ÷ 2（偶数，无需补 0） | 2357 符号 |
| AWGN Channel | 长度不变 | 2357 符号 |
| Synchronization | 定位起点 | — |
| QPSK Demodulate | × 2 | 4714 bit |
| Frame Parse | − 50 − 16 − 16 | 4632 bit |
| Channel Decode | ÷ 3（多数投票） | 1544 bit |
| Descramble | 长度不变 | 1544 bit |
| Source Decode | ÷ 8 | 193 字节 → 文本 |

收发两端比特数完全对齐（1544 → 1544），帧结构 Length 字段能正确剥离 padding，链路逻辑闭环。

> 旧版 DESIGN 写"262字符/766字节/6128bit"为陈旧错误，本次修正为 193 字节/1544 bit。

## 6. 可视化规约（中英双语，数据绑定真实链路）

| 图 | 文件名 | 数据来源 |
|----|--------|----------|
| 收发星座图对比 | `constellation.png`（旧名保留） | 真实 tx_symbols 与 rx_from_sync |
| BER/FER vs Eb/N0 | `ber_curve.png`（旧名保留） | 真实多 SNR 扫描 + 理论线 |
| 同步互相关峰+阈值 | `sync_peak.png`（旧名保留） | 真实 rx_noisy 与 PREAMBLE 互相关 |
| 帧结构时序图 | `frame_structure.png` | build_frame 字段 |
| 误码位置热力图 | `error_pattern.png` | 真实低 SNR(2dB) tx vs rx |
| 信道噪声分布 | `channel_response.png` | awgn 噪声样本直方图+理论高斯 |

标题 `中 / English`；轴标 `同相分量 In-Phase (I)`；`rcParams['font.sans-serif']=['Arial Unicode MS','Noto Sans CJK SC']`。

## 7. 预期风险（供 mock 阶段验证）

| # | 风险 | 现象 | 根因 | 缓解 | Mock 点 |
|---|------|------|------|------|---------|
| R1 | QPSK 解调规则搞反 | 无噪下大量误码 | b0/b1 实虚部搞混 | 手推 4 对闭环 | M1/M2 |
| R2 | 前导自相关伪峰 | 同步偏真起点 | 周期序列循环相关 | 伪随机 preamble | M3 |
| R3 | CRC 只生不验 | 检错能力为零 | parse_frame 不重算 | parse_frame 重算+返回 crc_valid | M4 |
| R4 | padding 误判 | 多出 padding 比特 | 不按 Length 截 | parse_frame 按 Length 截 | M5 |
| R5 | 同步阈值误杀周期 preamble | TC-T_013 失败 | 阈值拒绝返回 | start_index 恒 argmax，阈值仅附加 | M6 |
| R6 | BER 理论线 3dB 错 | 实测点挂曲线之上 | Es/N0 当 Eb/N0 | 横轴 Eb/N0=snr−3 | M7 |
| R7 | 低 SNR 重复码不足 | SNR<3dB BER 过高 | (3,1) 仅纠单错 | 验收 SNR=12；可选汉明码 | — |
| R8 | 收发比特数不对齐 | 解码错位 | 数据流推演错 | 用实际 193 字节核对 | M8 |

## 8. 文件结构

```
wireless-final-project-template/
├── main.py              # CLI 统一入口（工厂选路 + 真实曲线）
├── DESIGN.md            # 本文件（spec freeze v1）
├── hard_constraints.md  # 硬约束清单（阶段1产出）
├── TEST_PLAN.md         # 测试计划（金字塔 + 覆盖率门禁）
├── MOCK_TEST_REPORT.md  # Mock 测试报告（M1-M8）
├── AI_LOG.md            # AI 使用日志
├── ANALYSIS.md          # 实验分析报告
├── student_requirements.txt  # 学生额外依赖（pytest-cov, hypothesis）
├── pyproject.toml       # coverage 配置（不配全局 cov addopts）
├── src/                 # 实现（9 模块）
├── tests/               # 学生自测（unit/property/integration/e2e）
├── public_tests/        # 教师公开测试（不改）
└── results/             # 输出（received.txt, metrics.json, 6 张图）
```

## 9. 运行方式

```bash
python main.py --input Test.txt --output results/received.txt \
               --snr 12 --seed 2026 --mod qpsk --channel awgn
```

输出：`results/received.txt`、`results/metrics.json`（含真实 ber/fer/checksum_pass/crc_valid/sync_confidence）、`results/*.png`（6 张图）。
