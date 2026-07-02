# 测试计划 — 无线通信基带仿真系统

## 1. 测试概述

本测试计划覆盖系统的**模块级测试**和**端到端集成测试**，确保每个功能模块正确工作，整个通信链路在指定 SNR 条件下能 100% 恢复原始文本。

## 2. 测试用例

### 2.1 结构文档测试（TC-T-001 ~ TC-T-003, TC-T-018 ~ TC-T-020）

| 用例 | 描述 | 预期结果 |
|------|------|----------|
| TC-T-001 | 必需项目文件存在 | DESIGN.md, TEST_PLAN.md, MOCK_TEST_REPORT.md, AI_LOG.md, main.py, src/, tests/ 全部存在 |
| TC-T-002 | DESIGN.md 覆盖系统链路 | 包含 Source Encode, Encrypt, Scramble, Channel Encode, Frame Build, QPSK 等关键词 |
| TC-T-003 | MOCK_TEST_REPORT.md 包含修订记录 | ≥3 个 mock 测试、≥1 个风险/缺陷、修订记录 |
| TC-T-018 | AI_LOG.md 记录 AI 协助 | ≥3 次 prompt、人工修改、采纳理由 |
| TC-T-019 | 报告解释结果 | QPSK 星座图、BER、text_match_rate、失败原因 |
| TC-T-020 | 无反复制快捷方式 | 代码中无 shutil.copy 等可疑模式 |

### 2.2 模块级测试（TC-T-004 ~ TC-T-012）

| 用例 | 描述 | 测试方法 |
|------|------|----------|
| TC-T-004 | UTF-8 信源编解码可逆 | 编码→解码恢复原文，比特数 8 整除 |
| TC-T-005 | 帧包含必要字段 | 帧含 preamble, length, payload, checksum |
| TC-T-006 | 组帧/解析可逆 | build_frame → parse_frame 恢复 payload |
| TC-T-007 | 加扰/解扰可逆 | scramble → descramble 恢复原始比特 |
| TC-T-008 | 信道编码无噪声可逆 | encode → decode 恢复原始比特 |
| TC-T-009 | QPSK 象限映射正确 | 00→Q1, 01→Q2, 11→Q3, 10→Q4，单位功率 |
| TC-T-010 | QPSK 无噪声零误码 | modulate → demodulate 无误码 |
| TC-T-011 | QPSK padding 正确 | 奇数长度 payload 正确处理 |
| TC-T-012 | AWGN 可重现 | 相同 seed 输出相同 |

### 2.3 端到端测试（TC-T-013 ~ TC-T-017）

| 用例 | 描述 | 测试方法 |
|------|------|----------|
| TC-T-013 | 同步检测偏移 | 25 符号偏移检测误差 ≤1 |
| TC-T-014 | metrics.json 字段完整 | 包含所有必需字段 |
| TC-T-015 | 端到端文本恢复 | SNR=12dB 时 text_match_rate == 1.0 |
| TC-T-016 | 生成至少 2 张图 | constellation.png, ber_curve.png, sync_peak.png 中 ≥2 存在 |
| TC-T-017 | CLI 非交互式运行 | 20 秒内完成，无交互提示 |

## 3. 测试运行

```bash
PYTHONPATH=. pytest public_tests/ -v
```

## 4. 测试策略

- **单元测试**：每个模块独立测试编解码可逆性
- **集成测试**：端到端完整链路测试
- **边界测试**：奇数长度 payload、不同 SNR 值
- **可重现性测试**：固定种子确保结果一致
