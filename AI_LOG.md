# AI 使用日志 — 无线通信基带仿真系统（高标准重做）

## 概述

本项目在已有可运行实现（22 条公开测试全过）基础上进行高标准重做，遵循升级版 Vibe Coding Workflow：Understand → Plan（spec freeze）→ Mock Verify → TDD Build → Run & Debug → Visualize → Verify。以下记录关键 prompt 交互、人工修改与采纳理由。

---

## Prompt 1：项目摸底与硬伤识别

**AI Prompt：**
> "我对当前期末大作业成果不太满意，想以更高标准重做一遍，按 vibe coding workflow 流程，更多可视化、更完备的 design 与 TDD"

**AI 输出摘要：**
- 并行 3 个 Explore 子代理摸清作业要求、已有实现、测试集
- 发现已有实现 22 条公开测试全过，但存在 8 条硬伤：CLI 参数摆设（`--mod`/`--channel` 硬编码）、FER 由 BER 二值推算、`checksum_pass` 写死 True、CRC 只生成不验证、同步无阈值且 O(n·m) 慢、BER 曲线另造 4000bit、BER 理论线 3dB 错、tests/ 空目录无单元测试
- Plan 子代理额外发现 2 个新问题：BER 理论线把 Es/N0 当 Eb/N0（差 3dB）、DESIGN 数据流"262字符/766字节"与实际 Test.txt（193字节）不符

**人工修改：**
- 用户拍板 4 个方向决策：原地深度重构、Level2 完美+选择性提高、丰富静态报告图集、pytest 红绿重构+覆盖率门禁
- 用户提醒"教师 GitHub 自动考核接口别动"，据此识别 `.github/workflows/grading.yml`、`public_tests/`、`grading/`、`.feature`、`PRD.docx`、`requirements.txt` 为不可修改资产

**采纳理由：**
摸底确认实现"能跑但非真确"，重做有明确价值。3dB 错与数据流错误是隐藏的设计缺陷，必须在 DESIGN 修正。教师资产边界的明确使后续改造不会误伤 CI 评分链路。

---

## Prompt 2：高标准重做方案设计

**AI Prompt：**
> "基于摸底结果，设计升级版 Vibe Coding Workflow + 完备 DESIGN 规约 + TDD 计划 + 可视化图集"

**AI 输出摘要：**
- 9 阶段升级版 workflow，每阶段带门禁/可视化/AI_LOG 节点与 spec freeze 机制
- 每模块真实化规约：CRC 真验（parse_frame 重算）、CLI 工厂选路、FFT 加速同步、FER 基于 CRC、BER 曲线真实多 SNR 扫描
- Mock 验证清单 M1-M8
- 测试金字塔（unit/property/integration/e2e）+ 覆盖率门禁 90%

**人工修改：**
- **覆盖率门禁策略修正**：原方案把 `--cov-fail-under=90` 写进 `pyproject.toml` 全局 addopts，但 CI 跑 `pytest public_tests -q` 会触发 cov 门禁，public_tests 对 src 覆盖率不足 90% 会挂 CI。改为：pyproject 只配 `[tool.coverage]`，门禁靠本地命令 `pytest tests --cov=... --cov-fail-under=90` 显式触发
- **依赖位置修正**：`pytest-cov`/`hypothesis` 放新建的 `student_requirements.txt`（grading.yml:31 会自动装），不动教师 `requirements.txt`

**采纳理由：**
方案具体可执行，且充分考虑了不破坏教师考核基础设施。覆盖率门禁与 CI 隔离的修正避免了误杀 CI——这是识别"教师考核接口别动"约束后才发现的真实风险。

---

## Prompt 3：Mock 验证设计

**AI Prompt：**
> "手推 + 最小脚本验证 M1-M8 设计点，把运行后才调试的 bug 提前到设计阶段发现"

**AI 输出摘要：**
- 写 `mock/verify_design.py` 验证 M1-M8
- 首跑 8/10 PASS，2 个 FAIL（M4b CRC 单 bit 检错、M7 BER 3dB 修正）

**人工修改：**
- **M4b 修正**：原翻 `flip_at=60` 落在 Length 字段，但用原始 length 重算 CRC，未翻到有效 payload 区，导致"检测不到"假失败。改为翻 payload 区域（`flip_at=66+10`）
- **M7 修正**：原断言 `wrong/correct > 100` 方向写反——实际错线 BER（9.01e-09）比正线（3.36e-05）更乐观（更低），因为高估了 Eb/N0。改为 `correct/wrong > 100`，得 3734×，3dB 差异成立
- 修正后 10/10 PASS

**采纳理由：**
两个失败都是验证脚本自身 bug，非 DESIGN 问题。但正是 Mock 阶段发现并修正，未流入实现，体现了"先验证设计再写代码"的价值。M7 的修正反向印证了 3dB 错的真实方向（原 main.py 理论线偏乐观，实测点显得"差于理论"）。

---

## Prompt 4：TDD 实现各模块

**AI Prompt：**
> "按依赖拓扑红绿重构实现 source → crypto → channel_coding → framing → modulation → channel → synchronization → metrics → main"

**AI 输出摘要：**
- 每模块写失败单元测试 → 最小实现 → 重构加类型标注 → 覆盖率达标 → 公开测试回归
- framing：parse_frame 重算 CRC 返回 `crc_valid`/`crc_mismatch`，不抛异常
- synchronization：FFT 加速（`scipy.signal.correlate`）+ confidence/found，`start_index` 恒 argmax
- main：工厂选路替换硬编码、FER 真实化、BER 曲线真实多 SNR 扫描、6 张双语图

**人工修改：**
- 保留所有公开函数别名（conftest.find_function 多别名搜索红线）
- parse_frame 返回标志而非抛异常（保 TC-T_006/011 在噪声下也能返回 payload 供断言）
- `QPSK_MAP` 锁定不改（TC-T_009 红线）
- 三个旧图文件名保留（TC-T_016 红线）
- metrics 新增字段（crc_valid/sync_confidence/eb_n0_db）但不删旧字段（保 TC-T_014）

**采纳理由：**
TDD 节奏保证每模块覆盖率与回归。红线保护确保公开测试不 regress——实测公开测试 22 + 单元测试全绿，CRC 真验与 FFT 同步改造未破坏任何红线。

---

## Prompt 5：可视化图集

**AI Prompt：**
> "生成 6 张中英双语图，数据全部绑定真实链路"

**AI 输出摘要：**
- `constellation.png`/`ber_curve.png`/`sync_peak.png`（旧名保留）+ `frame_structure.png`/`error_pattern.png`/`channel_response.png`
- BER 曲线横轴 Eb/N0 = snr − 3，含理论未编码 QPSK 线 + 理论 (3,1) 重复码线 + 实测 BER/FER 点
- 每图 try/except 包裹（一图失败不阻断）

**人工修改：**
- BER 曲线用真实多 SNR 扫描端到端数据（替换原另造 4000bit）
- error_pattern 用低 SNR(2dB) 真实 tx/rx payload 比对
- 中文字体配置 `['Arial Unicode MS', 'Noto Sans CJK SC']`

**采纳理由：**
数据与端到端链路一致，消除原"两张皮"问题。中英双语标注便于答辩演示。

---

## 总结

本次重做 AI 辅助覆盖摸底、设计、Mock 验证、TDD 实现、可视化全流程。人工贡献在于：
1. 方向决策（4 个拍板）与教师资产边界保护
2. Mock 脚本 2 个 bug 的发现与修正
3. 覆盖率门禁与 CI 隔离的关键修正
4. 公开测试红线保护（别名/映射/字段/图名）

最终成果：公开测试 22 全绿、单元测试全绿、Mock 验证 10/10、CLI 真正生效、指标真实化、6 张双语图集。
