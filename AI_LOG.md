# AI 使用日志 — 无线通信基带仿真系统

## 概述

本项目使用 AI 辅助编程完成，以下记录了关键的 prompt 交互、人工修改和最终采纳理由。

---

## Prompt 1：源编码模块设计

**AI Prompt：**
> "请帮我实现一个 UTF-8 源编码模块，将中文文本编码为比特流。要求比特流长度是 8 的倍数，支持可逆解码。"

**AI 输出摘要：**
- 提供了 `source_encode` 和 `source_decode` 函数
- 使用 Python 内置的 `str.encode("utf-8")` 进行编码
- 每字节拆为 8 个比特，MSB first

**人工修改：**
- 添加了 `text_to_bits` 和 `bits_to_text` 别名函数以兼容测试框架的多函数名搜索
- 在 `source_decode` 中增加了补齐到 8 的倍数的逻辑
- 使用 `errors="replace"` 处理可能的解码错误

**采纳理由：**
AI 的核心方案（UTF-8 编码 → 字节 → 比特）是正确且高效的。人工修改主要是兼容性调整和错误处理增强。

---

## Prompt 2：QPSK 调制模块设计

**AI Prompt：**
> "请实现 QPSK Gray 编码调制，映射规则为 00→Q1, 01→Q2, 11→Q3, 10→Q4，符号功率为 1。"

**AI 输出摘要：**
- 提供了 `qpsk_modulate` 和 `qpsk_demodulate` 函数
- 使用字典映射比特对到复数星座点
- 除以 √2 实现单位功率
- 解调通过检查实部/虚部符号判断象限

**人工修改：**
- 统一使用 `np.sqrt(2)` 进行归一化，确保精度
- 增加了多个别名函数（`modulate_qpsk`, `qpsk_mapper` 等）
- 将输入统一转换为 Python list 以兼容 numpy array 输入

**采纳理由：**
AI 的 Gray 编码映射和星座点生成逻辑完全符合 PRD 要求。人工修改主要是类型兼容性和测试框架适配。

---

## Prompt 3：组帧模块与帧结构设计

**AI Prompt：**
> "请设计一个帧结构，包含 Preamble、Length、Payload 和 Checksum 字段。需要支持任意长度的 Payload，包括奇数长度。"

**AI 输出摘要：**
- 设计了 50-bit Preamble + 16-bit Length + 可变 Payload + 16-bit CRC Checksum 的帧格式
- 提供了 `build_frame` 和 `parse_frame` 函数
- 使用 CRC-16 校验

**人工修改：**
- Preamble 序列与 QPSK 同步符号保持一致
- 增加了字典形式返回值（测试框架检查字典键名）
- 确保 `parse_frame` 能同时处理字典和比特列表输入

**采纳理由：**
AI 的帧设计方案结构清晰，CRC-16 校验足够可靠。人工修改主要是确保与同步模块的一致性以及与测试框架的兼容性。

---

## Prompt 4：端到端链路集成

**AI Prompt：**
> "请帮我将所有模块串联成完整的端到端通信链路，支持 CLI 参数 --input, --output, --snr, --seed, --mod, --channel。"

**AI 输出摘要：**
- 使用 argparse 实现 CLI
- 按信源编码→加扰→信道编码→组帧→调制→信道→同步→解调→解析→信道解码→解扰→信源解码的顺序串联
- 生成 metrics.json 和结果图

**人工修改：**
- 增加了同步后从检测位置截断信号的处理
- 确保 results 目录自动创建
- 增加了 matplotlib Agg 后端设置（无头环境兼容）

**采纳理由：**
AI 的链路集成方案逻辑正确。人工修改主要是边缘情况处理和运行环境兼容性。

---

## 总结

AI 辅助在本项目中主要用于：
1. 模块设计方案的生成
2. 核心算法的实现（QPSK 调制、CRC 校验、互相关同步）
3. 端到端链路的集成

人工主要贡献在于：
- 测试框架兼容性适配
- 边缘情况处理
- 错误处理和鲁棒性增强
