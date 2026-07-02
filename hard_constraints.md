# 硬约束清单 — 无线通信基带仿真系统（高标准重做）

> 阶段 1（Understand）产出。本文档固化需求理解、测试覆盖矩阵、硬伤清单、公开测试红线、教师考核基础设施边界。后续 DESIGN 规约以此为准。

## 1. 系统硬约束（来自 PRD + 公开测试 + .feature）

### 1.1 固定链路顺序（不可变）
```
Test.txt → Source Encode → Scramble/Encrypt → Channel Encode
        → Frame Build → QPSK Modulate → AWGN Channel → Synchronization
        → QPSK Demodulate → Frame Parse → Channel Decode → Descramble/Decrypt
        → Source Decode → received.txt + metrics.json + 可视化图
```

### 1.2 统一 CLI（TC-T-017，conftest.run_cli 固定调用）
```bash
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```
- 必须非交互运行（无 `input()`/`请输入`），20 秒内退出。
- `--mod`/`--channel` 当前是摆设（main.py:125,129 硬编码）→ **重做必须真正生效**。

### 1.3 帧字段（TC-T-005，framing.py）
`Preamble(50bit/25QPSK符号) + Length(16bit,大端) + Payload(可变) + CRC-16(16bit)`，CRC 覆盖 PREAMBLE+Length+Payload。

### 1.4 QPSK Gray 映射（TC-T-009，modulation.py:14-19，**红线不可动**）
| 比特对 | 象限 | 复数 |
|--------|------|------|
| (0,0) | Q1 | (1+1j)/√2 |
| (0,1) | Q2 | (-1+1j)/√2 |
| (1,1) | Q3 | (-1-1j)/√2 |
| (1,0) | Q4 | (1-1j)/√2 |
平均功率 ∈ [0.8, 1.2]。解调：b0 看虚部符号，b1 看实部符号（已验证正确）。

### 1.5 SNR 定义（channel.py，**本次修正重点**）
`snr_db` 实为 **Es/N0**（符号信噪比）：`signal_power = mean(|s|²) = Es`；`noise_power = Es / 10^(snr_db/10)`；复噪声实/虚部各 `N(0, √(noise_power/2))`，总方差 = noise_power。固定 seed 可复现（TC-T_012）。
- BER 曲线横轴必须用 **Eb/N0 = Es/N0 − 10·log10(k)**，QPSK k=2 ⇒ **Eb/N0 = snr_db − 3 dB**。原 main.py:58 把 snr_linear 当 Eb/N0，差 3dB（M7 验证点）。

### 1.6 同步（TC-T-013，synchronization.py）
- 用**周期性** preamble `[1+1j,-1+1j,-1-1j,1-1j]*8 /√2` 测 25 符号偏移，容差 ±1。
- `start_index` **恒返回 argmax**（红线），阈值只能作附加 `confidence`/`found` 字段。

### 1.7 metrics.json 必需字段（TC-T-014）
`snr_db, seed, modulation, channel, payload_bits, ber, fer, text_match_rate, checksum_pass, sync_start_index`（10 个，新增字段不删旧字段）。

### 1.8 可视化（TC-T-016）
`constellation.png`/`ber_curve.png`/`sync_peak.png` 至少 2 个非空（**三个旧文件名必须保留**）。

### 1.9 文档（TC-T-001/002/003/018/019）
- 必须存在：DESIGN.md, TEST_PLAN.md, MOCK_TEST_REPORT.md, AI_LOG.md, main.py, src/, tests/
- DESIGN.md 必须含 ≥9 个链路关键词且含 "QPSK"
- MOCK_TEST_REPORT.md：≥3 个 "mock" 词、含风险词、含修订词
- AI_LOG.md：≥3 个 "prompt"/"提示"、含人工修改词、含采纳理由词
- 报告须解释 QPSK 星座、BER/text_match_rate、失败/误码原因

## 2. 测试覆盖矩阵（TC → 模块/文件）

| TC | 场景 | 模块 | 当前状态 |
|----|------|------|----------|
| TC-T-001 | 必需文件存在 | 项目结构 | ✓ |
| TC-T-002 | DESIGN 覆盖链路 | DESIGN.md | ✓（需重写保关键词） |
| TC-T-003 | Mock 报告含修订 | MOCK_TEST_REPORT.md | ✓（需真实化重写） |
| TC-T-004 | UTF-8 源编码可逆 | source.py | ✓ |
| TC-T-005 | 帧含字段 | framing.py | ✓ |
| TC-T-006 | 帧封装解析可逆 | framing.py | ✓ |
| TC-T-007 | 加扰可逆 | crypto.py | ✓ |
| TC-T-008 | 信道编码无噪可逆 | channel_coding.py | ✓ |
| TC-T-009 | QPSK 映射 | modulation.py | ✓（红线） |
| TC-T-010 | QPSK 无噪零误码 | modulation.py | ✓ |
| TC-T-011 | padding 靠 length 去除 | framing+modulation | ✓ |
| TC-T-012 | AWGN 固定 seed 可复现 | channel.py | ✓ |
| TC-T-013 | 同步检测 25 偏移 | synchronization.py | ✓ |
| TC-T-014 | metrics.json 字段 | main.py | ✓（需真实化） |
| TC-T-015 | SNR=12 端到端恢复 | main.py 全链 | ✓ |
| TC-T-016 | ≥2 张图 | main.py generate_plots | ✓（需升级图集） |
| TC-T-017 | CLI 非交互运行 | main.py | ✓ |
| TC-T-018 | AI_LOG 记录 | AI_LOG.md | ✓（需重写） |
| TC-T-019 | 报告解释结果 | ANALYSIS/DESIGN | ✓（需新增 ANALYSIS） |
| TC-T-020 | 无直接复制捷径 | src+main.py | ✓（重做须保持） |

## 3. 硬伤清单（已逐行验证，重做必须修复）

| # | 硬伤 | 位置 | 修复方案 |
|---|------|------|----------|
| 1 | `--mod`/`--channel` 摆设，硬编码 QPSK/AWGN | main.py:125,129 | 工厂选路 `MODULATION_SCHEMES[args.mod]`/`CHANNEL_SCHEMES[args.channel]` |
| 2 | FER 由 BER 二值推算 | main.py:168 | 新增 `compute_fer(crc_valid)` 基于 CRC |
| 3 | checksum_pass 写死 True | main.py:181 | 调用 `compute_checksum_pass` / 用 `crc_valid` |
| 4 | CRC 只生成不验证 | framing.py:104（parse_frame 提取不比对） | parse_frame 重算 CRC 返回 `crc_valid` |
| 5 | 同步无阈值、无无帧分支、O(n·m) 慢 | synchronization.py:38-43 | 加 confidence/found + FFT 加速，start_index 恒 argmax |
| 6 | BER 曲线另造 4000bit 与端到端两张皮 | main.py:62 | 改为真实帧多 SNR 扫描 |
| 7 | BER 理论线 3dB 错（Es/N0 当 Eb/N0） | main.py:58 | 横轴 Eb/N0=snr−3 |
| 8 | tests/ 空目录无单元测试；类型标注稀疏；函数内 import；无异常处理 | 多处 | TDD 补全 + 重构 |

## 4. 公开测试红线（不可动断言）

- `QPSK_MAP`（modulation.py:14-19）— TC-T-009 硬断言映射+功率
- 所有模块公开函数多别名 — conftest.find_function — **保留全部别名**
- `parse_frame` 返回 dict 含 `payload`/`length` — TC-T-006/011
- `synchronize` 的 `start_index` 恒 argmax — TC-T-013（周期 preamble）
- metrics 回填 args 值（modulation=qpsk, channel=awgn, seed=2026, snr_db≈12）— TC-T-014/015
- 三个旧图文件名 — TC-T-016
- `pytest public_tests -q` 全绿 — grading.yml CI

## 5. 教师考核基础设施（绝对不修改，只读）

| 资产 | 说明 |
|------|------|
| `.github/workflows/grading.yml` | CI：PR→装依赖（含 student_requirements.txt）→pytest public_tests→summarize→评论 PR |
| `.github/pull_request_template.md` | PR 模板 |
| `grading/summarize_public_tests.py` | 按 passed/total×100 估分 |
| `public_tests/` | 教师公开测试套件，不改 |
| `wireless_project_test_set_20.feature` | 教师 Gherkin 测试集 |
| `PRD.docx` | 教师需求文档 |
| `requirements.txt` | 教师基础依赖，不动；学生额外依赖写 `student_requirements.txt` |
| `LICENSE` / `README.md` | 许可/模板 |

## 6. 数据流推演（M8 验证，用 conftest SAMPLE_TEXT 实际值）

`SAMPLE_TEXT` = "无线通信技术课程要求学生理解调制、编码、信道和接收机处理。本测试文本用于验证源编码、帧结构、QPSK 调制、AWGN 信道、同步和端到端恢复。"

UTF-8 编码 = **193 字节**（句1 87 字节 + 句2 106 字节，含 QPSK/AWGN ASCII 与空格）→ 与 metrics.json `payload_bits=1544` 吻合（193×8=1544）。

| 阶段 | 计算 | 比特/符号 |
|------|------|----------|
| Source Encode | 193 字节 × 8 | 1544 bit |
| Scramble | 不变 | 1544 bit |
| Channel Encode (3,1) | ×3 | 4632 bit |
| Frame Build | +50+16+16 | 4714 bit |
| QPSK Modulate | ÷2（偶数，无需补0） | 2357 符号 |
| AWGN | 不变 | 2357 符号 |
| Sync | 定位起点 | — |
| QPSK Demod | ×2 | 4714 bit |
| Frame Parse | −50−16−16 | 4632 bit |
| Channel Decode | ÷3 | 1544 bit |
| Descramble | 不变 | 1544 bit |
| Source Decode | ÷8 | 193 字节 → 文本 |

收发对齐（1544 → 1544），链路闭环。（注：4714 为偶数，QPSK 无需补 0。）

> 旧 DESIGN.md 写"262字符/766字节/6128bit"是陈旧错误，本次重写修正为 193 字节/1544 bit。
