# Mock 测试报告 — 无线通信基带仿真系统（高标准重做）

> 阶段 3 产出。本文档记录在写实现前，用手推 + 最小脚本（`mock/verify_design.py`）验证 DESIGN 规约 M1-M8 的全过程，提前把"运行后才调试"的 bug 发现并修正到设计阶段。

## 1. Mock 验证场景（M1-M8）

运行 `PYTHONPATH=. python mock/verify_design.py`，结果 **10/10 PASS**。

### Mock 1（M1）：QPSK 4 比特对 mod→demod 闭环
- **场景**：验证 4 种比特对 (00/01/11/10) 调制后解调能还原。
- **预期**：4 种全闭环。
- **实际**：PASS — 4 对全闭环。
- **对应历史 bug**：解调规则搞反（已修复，b0 看虚部、b1 看实部）。

### Mock 2（M2）：解调规则与映射表一致
- **场景**：手推 b0/b1 判决规则与 QPSK_MAP 映射表一致。
- **预期**：4 种比特对判决结果等于原输入。
- **实际**：PASS — 4 种全对。

### Mock 3（M3）：PREAMBLE 自相关尖锐单峰
- **场景**：默认前导序列（seed=42 伪随机）循环自相关应尖锐单峰。
- **预期**：旁瓣/主峰 < 0.5。
- **实际**：PASS — 旁瓣/主峰=0.291。生成 `mock/mock_preamble_autocorr.png`。
- **对应历史 bug**：前导伪峰值（若用周期序列会到处是峰；伪随机序列避免此问题）。

### Mock 4（M4）：CRC 闭环 build→重算→比对
- **场景**：`build_frame` 用 `_crc16(PREAMBLE+Length+Payload)` 生成 checksum，独立重算应一致；翻 payload 1 bit 应被检出。
- **预期**：重算一致；翻 1 bit 后 CRC 不匹配。
- **实际**：PASS — 算法闭环；翻 payload 1 bit 后 CRC 不匹配（M4b 检错通过）。
- **对应硬伤**：#4 CRC 只生不验。本次 parse_frame 将用同逻辑重算并置 `crc_valid`。

### Mock 5（M5）：parse_frame 按 length 截 padding
- **场景**：奇数 payload（255 bit）经组帧、QPSK 调制（补 0 → 169 符号）、解调（338 bit）、解析，应还原 255 bit。
- **预期**：还原 payload 长度 255。
- **实际**：PASS — 还原 255 bit。

### Mock 6（M6）：同步阈值不误杀周期 preamble
- **场景**：TC-T_013 用周期 preamble 测 25 符号偏移；验证 `start_index` 恒返回 argmax，阈值仅作附加字段。
- **预期**：argmax=25（容差±1），confidence 可低但起点正确。
- **实际**：PASS — start=25, confidence≈1.02。
- **对应新风险**：R5 同步阈值误杀。设计约束：`start_index` 恒 argmax，阈值不拒绝返回。

### Mock 7（M7）：BER 理论线 3dB 修正
- **场景**：对比错误线（Es/N0 当 Eb/N0）与正确线（Eb/N0=snr−3）。
- **预期**：12dB 处两线差异显著（正线 BER 远高于错线）。
- **实际**：PASS — @12dB 错线=9.01e-09，正线=3.36e-05，正线/错线=3734×。生成 `mock/mock_ber_3db.png`。
- **对应硬伤**：#7 BER 理论线 3dB 错。实测点会"挂在错线之上"造成视觉误读；本次修正横轴为 Eb/N0。

### Mock 8（M8）：端到端比特数链收发对齐
- **场景**：用 conftest SAMPLE_TEXT（UTF-8 = 193 字节）推演各阶段比特数。
- **预期**：收发对齐（1544 → 1544）。
- **实际**：PASS — 193字节/1544bit → coded 4632 → frame 4714 → 2357sym → 解码 1544bit（对齐 1544）。

## 2. 发现的风险与缺陷

### 风险 1：低 SNR 下 (3,1) 重复码纠错能力不足
- **描述**：SNR < 3 dB 时 3 中错 2 概率上升，BER 过高。
- **影响**：端到端低 SNR 场景可能失败。
- **缓解**：验收在 SNR=12 dB 运行，绰绰有余；Level3 可选汉明(7,4) 提升编码率与纠错。

### 缺陷 1：Mock 脚本 M4b 翻转位置错误（已修正）
- **描述**：初版 M4b 翻 `flip_at=60`（Length 字段），但用原始 length 重算 CRC，未翻到有效 payload 区，导致"检测不到"假失败。
- **根因**：验证脚本未模拟 parse_frame 从帧解析 length 的真实流程，且翻转位置选在 Length 字段。
- **修正**：改为翻 payload 区域（`flip_at=66+10`），M4b 通过。这本身证明 CRC 对 payload 翻转有检错能力。

### 缺陷 2：Mock 脚本 M7 断言方向写反（已修正）
- **描述**：初版 M7 断言 `wrong/correct > 100`，但实际错线 BER（9.01e-09）< 正线（3.36e-05），比值 < 1，假失败。
- **根因**：误以为"错线更悲观"，实则错线把 Es/N0 当 Eb/N0 高估了比特信噪比，BER 更乐观（更低）。
- **修正**：改为 `correct/wrong > 100`，M7 通过（3734×）。这反向印证了 3dB 错的真实方向：原 main.py 理论线偏乐观，实测点会显得"差于理论"。

### 风险 2：CRC 不保护 Length 字段被误解
- **描述**：若噪声翻转 Length 高位，parse_frame 解析出错误 length，取错误 payload 范围，CRC 可能误判。
- **影响**：极端噪声下帧解析失败。
- **缓解**：CRC 覆盖 Length 字段（重算时用解析出的 length），翻转 Length 会使重算 CRC 与接收 CRC 大概率不匹配 → `crc_valid=False`，main.py 据此算 FER。验收 SNR=12 下 Length 翻转概率极低。

## 3. DESIGN.md 修订记录

### 修订 1：spec freeze v1 — 真实化改造规约
- **修改内容**：按 8 条硬伤重写各模块规约：CRC 真实验证（parse_frame 重算并返回 `crc_valid`）、CLI 工厂选路、FER 基于 CRC、BER 曲线真实多 SNR 扫描 + Eb/N0 横轴、同步加阈值与 FFT 加速。
- **修改时间**：2026-07-02
- **理由**：修复硬伤 #1-#8，使指标真实、链路正确。

### 修订 2：修正 SNR 定义与 BER 横轴约定
- **修改内容**：明确 `snr_db` = Es/N0；BER 曲线横轴 = Eb/N0 = snr_db − 3 dB（QPSK k=2）。
- **修改时间**：2026-07-02
- **理由**：M7 验证发现原理论线 3dB 错（错线/正线差 3734×）。

### 修订 3：修正数据流推演
- **修改内容**：从陈旧的"262字符/766字节/6128bit"修正为 conftest SAMPLE_TEXT 实际值"193字节/1544bit"。
- **修改时间**：2026-07-02
- **理由**：M8 验证用实际文本核对，旧推演与 Test.txt 不符。

## 4. 结论

Mock 验证 10/10 通过，DESIGN 规约 v1 成立，可进入阶段 4（TDD 实现）。两个脚本缺陷（M4b/M7）在 Mock 阶段即被发现并修正，未流入实现，体现了"先验证设计再写代码"的价值。
