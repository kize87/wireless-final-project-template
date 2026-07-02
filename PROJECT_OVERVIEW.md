# 📡 无线通信基带仿真系统 — 项目介绍（高标准重做版）

> 一句话概括：把一段中文文本"发"过一条模拟无线信道，再在接收端"原样"还原——每一级处理都**真实可验证**（指标非写死、CRC 真验证、CLI 真生效、BER 曲线与端到端一致）。

---

## 一、这个项目能干什么？

实现一个**端到端无线通信基带仿真系统**，模拟 4G/5G、Wi-Fi 中从"按下发送"到"对方收到"之间的底层信号处理。

| 能力 | 说明 |
|------|------|
| 📝 **文本传输** | 任意 UTF-8 中文文本编码为比特流，传输后一字不差恢复 |
| 🌊 **完整通信链路** | Source Encode → Scramble → Channel Encode → Frame Build → QPSK → AWGN → Sync → Demod → Parse → Decode → Descramble → Source Decode |
| 📡 **QPSK 调制** | Gray 编码，单位功率，收发星座图可视化 |
| 🔊 **AWGN 信道** | Es/N0 定义明确，固定 seed 可复现 |
| 🎯 **帧同步** | FFT 加速互相关 + 置信度阈值，`start_index` 恒返回 argmax |
| 🛡️ **纠错编码** | (3,1) 重复码（默认）/ (7,4) 汉明码（Level3），可插拔 |
| ✅ **CRC 真实验证** | parse_frame 重算 CRC-16 并比对，返回 `crc_valid` |
| 📊 **真实指标** | BER、FER（基于 CRC）、text_match_rate、sync_confidence、eb_n0_db |
| 📈 **6 张双语图** | 星座图、BER/FER 曲线、同步峰、帧结构、误码模式、信道噪声分布 |
| 🔧 **CLI 工厂选路** | `--mod`/`--channel`/`--code` 真正生效，未注册值报错退出 |

---

## 二、设计链路总览

```
[文本] → Source Encode → Scramble → Channel Encode → Frame Build → QPSK Modulate
      → AWGN Channel → Synchronization → QPSK Demodulate → Frame Parse
      → Channel Decode → Descramble → Source Decode → [文本] + Metrics + Plots
```

每一级可逆——发射端做什么，接收端"反着做"。信道是唯一破坏数据的环节，信道编码 + 同步 + CRC 共同在噪声中救回数据。

---

## 三、模块详解（`src/`）

| 模块 | 职责 | 重做要点 |
|------|------|----------|
| `source.py` | UTF-8 文本↔比特 | 类型标注 + 空文本边界 |
| `crypto.py` | PRNG XOR 加扰 | 明确"加扰非加密"，对称性规约 |
| `channel_coding.py` | (3,1) 重复码 + (7,4) 汉明码 | CODING_SCHEMES 可插拔注册表 |
| `framing.py` | Preamble+Length+Payload+CRC-16 | **parse_frame 重算 CRC 真实验证**，返回 crc_valid |
| `modulation.py` | Gray QPSK | QPSK_MAP 锁定（红线）+ MODULATION_SCHEMES 注册 |
| `channel.py` | AWGN + Rayleigh | 明确 Es/N0 定义 + CHANNEL_SCHEMES 注册 |
| `synchronization.py` | 互相关帧同步 | **FFT 加速 + confidence/found**，start_index 恒 argmax |
| `metrics.py` | BER/FER/text_match | **FER 基于 CRC 真实计算**（新增 compute_fer） |

**QPSK Gray 映射（红线不可改）**：00→Q1, 01→Q2, 11→Q3, 10→Q4，单位功率。

**帧结构**：Preamble(50bit) + Length(16bit) + Payload(变长) + CRC-16(16bit)，CRC 覆盖前三个字段。

**SNR 约定（本次修正）**：`snr_db` = Es/N0；BER 曲线横轴 = Eb/N0 = snr_db − 3 dB（QPSK k=2）。原实现把 Es/N0 当 Eb/N0，差 3dB，已修正。

---

## 四、入口与使用

### 运行（核心命令）

```bash
python main.py --input Test.txt --output results/received.txt \
               --snr 12 --seed 2026 --mod qpsk --channel awgn
```

| 参数 | 含义 | 默认 |
|------|------|------|
| `--input`/`--output` | 输入/输出文本路径 | 必填 |
| `--snr` | Es/N0 (dB) | 12 |
| `--seed` | 随机种子 | 2026 |
| `--mod` | 调制方式 | qpsk |
| `--channel` | 信道模型 | awgn |
| `--code` | 信道编码 | rep3 |

Level3 示例：`--code hamming74 --channel rayleigh`

### 运行结果（SNR=12）

```
传输完成！
  SNR: 12.0 dB (Eb/N0=9.0 dB)
  Mod/Channel/Code: qpsk/awgn/rep3
  Payload bits: 1544
  BER: 0.000000
  FER: 0.0 (crc_valid=True)
  Text match rate: 1.0
  Sync start: 0 (conf=1.00)
```

`results/` 生成：`received.txt`、`metrics.json`（含真实 crc_valid/sync_confidence/eb_n0_db）、6 张 png（constellation/ber_curve/sync_peak + frame_structure/error_pattern/channel_response）。

### 环境准备

```bash
cd wireless-final-project-template
pip install -r requirements.txt        # 教师基础依赖
pip install -r student_requirements.txt  # 学生额外依赖（pytest-cov, hypothesis）
```

---

## 五、测试与验证

```bash
# 公开测试（CI 同款）
pytest public_tests -q

# 学生测试 + 覆盖率门禁
pytest tests --cov=src --cov=main --cov-fail-under=90

# Mock 设计验证
PYTHONPATH=. python mock/verify_design.py
```

**结果**：公开测试 22 passed、学生测试 90 passed、覆盖率 96.19%、Mock 10/10。

---

## 六、文档体系

| 文档 | 作用 |
|------|------|
| `DESIGN.md` | 系统设计（spec freeze v1，含变更记录） |
| `hard_constraints.md` | 硬约束 + 测试覆盖矩阵 + 硬伤红线清单 |
| `TEST_PLAN.md` | 测试金字塔 + 覆盖率门禁策略 |
| `MOCK_TEST_REPORT.md` | M1-M8 验证 + 风险缺陷 + 修订记录 |
| `AI_LOG.md` | AI 辅助 prompt + 人工修改 + 采纳理由 |
| `ANALYSIS.md` | 实验分析（sweep 数据、图表解读、失败原因） |
| `verification_report.md` | §H 验证结果 + 覆盖率明细 |

---

## 七、目录结构

```
wireless-final-project-template/
├── main.py                     # CLI 入口（工厂选路 + 真实曲线 + 6 图）
├── requirements.txt            # 教师基础依赖（不动）
├── student_requirements.txt    # 学生额外依赖（pytest-cov, hypothesis）
├── pyproject.toml              # coverage 配置（不污染 CI）
├── Test.txt                    # 示例输入
├── src/                        # 8 核心模块
├── tests/                      # 学生测试（unit/property/integration/e2e）
├── mock/                       # Mock 设计验证脚本
├── public_tests/               # 教师公开测试（不改）
├── grading/                    # 教师评分脚本（不改）
├── .github/                    # CI 评分工作流（不改）
├── results/                    # 运行输出
├── DESIGN.md / hard_constraints.md / TEST_PLAN.md / MOCK_TEST_REPORT.md
├── AI_LOG.md / ANALYSIS.md / PROJECT_OVERVIEW.md / verification_report.md
└── PRD.docx                    # 教师需求文档
```

---

## 八、关键设计决策

1. **CRC 真实验证**：原 parse_frame 只提取 checksum 不比对，纠错检错能力为零。重做后重算 CRC 返回 `crc_valid`，FER 基于此真实计算（非 BER 推算）。
2. **Es/N0 vs Eb/N0**：明确 `snr_db` 为 Es/N0，BER 曲线横轴用 Eb/N0=snr−3，修正原 3dB 理论错误。
3. **FFT 同步**：`scipy.signal.correlate(method='fft')` 替换 O(n·m) 循环，加 confidence/found，start_index 恒 argmax（保 TC-T_013 红线）。
4. **CLI 工厂选路**：MODULATION/CHANNEL/CODING_SCHEMES 注册表，未注册值报错退出，`--mod`/`--channel`/`--code` 真正生效。
5. **覆盖率门禁与 CI 隔离**：不写进 pyproject 全局 addopts（否则 CI 跑 public_tests 触发 cov 门禁挂），靠本地命令显式触发。
6. **教师考核资产不动**：grading.yml/public_tests/grading/.feature/PRD.docx/requirements.txt 只读，学生依赖写 student_requirements.txt。

---

*本项目为无线通信技术课程期末大作业，MIT License，Copyright (c) 2026*
