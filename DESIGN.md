# 系统设计文档 — 无线通信基带仿真系统

## 1. 系统概述

本系统实现了一个完整的**无线通信基带仿真链路**，将 UTF-8 中文文本编码为比特流，经过发射端处理、信道传输、接收端处理后恢复原始文本。

## 2. 系统链路

整个通信链路按以下顺序处理：

```
[文本输入] → Source Encode → Scramble/Encrypt → Channel Encode
    → Frame Build → QPSK Modulate → AWGN Channel
    → Synchronization → QPSK Demodulate → Frame Parse
    → Channel Decode → Descramble/Decrypt → Source Decode → [文本输出]
```

### 2.1 Source Encode（信源编码）

将 UTF-8 中文文本编码为比特流。每个字符先 UTF-8 编码为字节，每个字节拆为 8 个比特。比特流长度总是 8 的倍数。

- 模块：`src/source.py`
- 函数：`source_encode(text)` → `source_decode(bits)`

### 2.2 Scramble / Encrypt（加扰/加密）

使用基于 PRNG（`numpy.random.default_rng(seed)`）生成的伪随机比特序列，与信源编码输出进行 XOR 操作，实现比特级可逆加扰。

- 模块：`src/crypto.py`
- 函数：`scramble(bits, seed)` → `descramble(bits, seed)`

### 2.3 Channel Encode（信道编码）

采用 (3,1) 重复码进行前向纠错（FEC）。每个比特重复 3 次传输，接收端通过多数投票解码。编码率 = 1/3，提供较强的纠错能力。

- 模块：`src/channel_coding.py`
- 函数：`channel_encode(bits)` → `channel_decode(bits)`

### 2.4 Frame Build（组帧）

帧结构设计：
| 字段 | 长度 | 说明 |
|------|------|------|
| Preamble | 50 bits (25 QPSK 符号) | 同步用已知序列 |
| Length | 16 bits | Payload 比特数 |
| Payload | 可变 | 编码后的数据 |
| Checksum | 16 bits | CRC-16 校验 |

- 模块：`src/framing.py`
- 函数：`build_frame(payload)` → `parse_frame(frame)`

### 2.5 QPSK Modulate / Demodulate（调制/解调）

采用 Gray 编码 QPSK 调制，比特对到星座点映射如下：

| 比特对 | 象限 | 复数符号 |
|--------|------|----------|
| 00 | Q1 | (1+1j)/√2 |
| 01 | Q2 | (-1+1j)/√2 |
| 11 | Q3 | (-1-1j)/√2 |
| 10 | Q4 | (1-1j)/√2 |

符号平均功率为 1（单位功率）。奇数比特时自动补 0。

- 模块：`src/modulation.py`
- 函数：`qpsk_modulate(bits)` → `qpsk_demodulate(symbols)`

### 2.6 Channel（AWGN 信道）

模拟加性高斯白噪声信道。根据指定的 SNR（dB）和信号功率计算噪声方差，生成复高斯噪声叠加到信号上。使用固定随机种子确保可重现性。

- 模块：`src/channel.py`
- 函数：`awgn(symbols, snr_db, seed)`

### 2.7 Synchronization（同步）

使用互相关峰值检测法。接收端已知 Preamble 符号序列，对接收信号滑动计算互相关（取共轭匹配滤波），峰值位置即为帧起始索引。

- 模块：`src/synchronization.py`
- 函数：`synchronize(received, preamble)`

### 2.8 Channel Decode（信道解码）

(3,1) 重复码的多数投票解码。每 3 个比特一组，取多数值作为解码结果。

### 2.9 Source Decode（信源解码）

将比特流按 8 位一组恢复为字节，再 UTF-8 解码为中文文本。

### 2.10 Metrics（指标计算）

计算并输出：
- **BER**（比特错误率）：错误比特数 / 总比特数
- **FER**（帧错误率）：0 或 1
- **text_match_rate**：恢复文本与原始文本的字符匹配率
- **checksum_pass**：CRC 校验结果
- **sync_start_index**：同步检测到的帧起始位置

## 3. 数据流推演

以 Test.txt（262 字符中文，UTF-8 编码后 766 字节）为例，推演比特数变化链，验证收发两端能对齐：

| 阶段 | 计算 | 比特/符号数 |
|------|------|-----------|
| Source Encode | 766 字节 × 8 | 6128 bit |
| Scramble | 长度不变 | 6128 bit |
| Channel Encode (3,1) | × 3 | 18384 bit |
| Frame Build | + 50(前导) + 16(长度) + 16(CRC) | 18466 bit |
| QPSK Modulate | ÷ 2（偶数，无需补 0） | 9233 符号 |
| AWGN Channel | 长度不变 | 9233 符号 |
| Synchronization | 定位起点 | — |
| QPSK Demodulate | × 2 | 18466 bit |
| Frame Parse | − 50 − 16 − 16 | 18384 bit |
| Channel Decode | ÷ 3（多数投票） | 6128 bit |
| Descramble | 长度不变 | 6128 bit |
| Source Decode | ÷ 8 | 766 字节 → 文本 |

> 收发两端比特数完全对齐（6128 → 6128），证明帧结构长度字段能正确剥离 padding，链路逻辑闭环。

## 4. 预期风险

提前列设计风险，供 mock 阶段验证。每个风险写：现象 + 根因 + 缓解。

### 风险 1：前导序列自相关伪峰值
- **现象**：BER≈0.5，同步检测到的起始位置远偏真实起点
- **根因**：若用周期性序列（如 `[1+1j,-1+1j,...]` 循环），其循环移位与自身高度相关，自相关到处是峰
- **缓解**：用独立种子生成的伪随机 QPSK 符号作前导，保证自相关尖锐单峰（mock 阶段用 3 行脚本算自相关验证）

### 风险 2：QPSK 解调判决规则错误
- **现象**：无噪声下调制→解调就有大量比特错误（应 0 个）
- **根因**：`b0`/`b1` 到底由实部还是虚部决定容易搞混
- **缓解**：mock 阶段手推 4 种比特对的调制→解调闭环，明确规则（`b0` 看虚部符号，`b1` 看实部符号）

### 风险 3：低 SNR 下 (3,1) 重复码纠错能力不足
- **现象**：SNR < 3 dB 时 BER 过高，无法恢复文本
- **根因**：(3,1) 重复码仅能纠单比特错误，低 SNR 下 3 中错 2 概率上升
- **缓解**：实际验收在 SNR=12 dB 运行，该 SNR 下重复码绰绰有余；若需更低 SNR 可换汉明/卷积码

### 风险 4：奇数比特 padding 处理
- **现象**：QPSK 调制时奇数比特补 0，接收端若不按 Length 字段剥离会多出 padding 比特
- **根因**：padding 比特混入 payload 导致后续解码错位
- **缓解**：帧结构用 Length 字段精确标明 payload 比特数，parse 时按 Length 截取

### 风险 5：AWGN 复噪声方差分配
- **现象**：噪声功率偏大或偏小，SNR 不准
- **根因**：复噪声实部、虚部方差分配错误（应各为 noise_power/2）
- **缓解**：明确公式 noise_std = √(signal_power / 10^(snr/10) / 2)，固定种子保证可复现

## 5. 文件结构

```
wireless-final-project-template/
├── main.py              # CLI 统一入口
├── DESIGN.md            # 本文件
├── TEST_PLAN.md         # 测试计划
├── MOCK_TEST_REPORT.md  # Mock 测试报告
├── AI_LOG.md            # AI 使用日志
├── src/
│   ├── __init__.py
│   ├── source.py        # 信源编码
│   ├── crypto.py        # 加扰/解扰
│   ├── channel_coding.py # 信道编码
│   ├── framing.py       # 组帧/解析
│   ├── modulation.py    # QPSK 调制/解调
│   ├── channel.py       # AWGN 信道
│   ├── synchronization.py # 同步
│   └── metrics.py       # 指标计算
├── tests/               # 学生自测
├── public_tests/        # 公开测试（20 个用例）
└── results/             # 输出目录
```

## 6. 运行方式

```bash
python main.py --input Test.txt --output results/received.txt \
               --snr 12 --seed 2026 --mod qpsk --channel awgn
```

输出：
- `results/received.txt` — 恢复的文本
- `results/metrics.json` — 性能指标
- `results/constellation.png` — QPSK 星座图
- `results/ber_curve.png` — BER 曲线
- `results/sync_peak.png` — 同步峰值图
