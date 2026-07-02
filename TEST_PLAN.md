# 测试计划 — 无线通信基带仿真系统（高标准重做）

## 1. 测试金字塔

```
        ┌─────────────┐
        │   E2E (e2e)  │  不同文本/SNR/seed/偏移/异常 CLI/metrics/图集
        ├─────────────┤
        │ Integration  │  相邻模块串联可逆性
        ├─────────────┤
        │   Property   │  hypothesis 随机化性质测试（可逆/检错/可复现）
        ├─────────────┤
        │    Unit      │  每模块可逆性/边界/数值容差/异常
        └─────────────┘
```

| 层 | 目录 | 内容 |
|----|------|------|
| Unit | `tests/unit/` | 每模块独立测试，覆盖正常/边界/异常 |
| Property | `tests/property/` | hypothesis 随机输入验证不变式 |
| Integration | `tests/integration/` | 相邻模块串联 |
| E2E | `tests/e2e/` | 端到端 CLI + 不同参数 |

教师公开测试 `public_tests/` 不修改，作为回归基线。

## 2. 每模块单元测试场景

| 模块 | 必测场景 |
|------|----------|
| source | 空文本→[]→""；中文/ASCII/emoji 可逆；比特数%8==0；非法 UTF-8 字节 errors=replace |
| crypto | 任意比特加解扰可逆；不同 seed 输出不同；同 seed 可复现；空比特；别名等价 |
| channel_coding | 无噪可逆；3 比特组错 1 纠、错 2 判错；非 3 倍数容错；空输入；CODING_SCHEMES 注册 |
| framing | build→parse 可逆（偶/奇/极短/1bit）；CRC 翻 1bit→crc_valid=False；length 截 padding；帧总长=50+16+N+16；crc_valid 真实；不抛异常 |
| modulation | 4 比特对映射象限正确；单位功率∈[0.8,1.2]；奇数补0；无噪零误码；MODULATION_SCHEMES 注册；别名等价 |
| channel | 同 seed 可复现(allclose)；不同 seed 不同；SNR↑噪声↓(单调)；噪声方差=Es/snr/2 每维；CHANNEL_SCHEMES 注册 |
| synchronization | 25 偏移检测±1；无帧 found=False 但 start_index 仍返回；FFT 与循环结果一致；周期 preamble 不误杀；confidence 合理 |
| metrics | ber 0/全错/部分；fer 单帧 crc 真/假、多帧失败比例；text_match 全等/部分/空；checksum_pass 比对 |

## 3. Property-based 测试（hypothesis）

| 性质 | 策略 | 断言 |
|------|------|------|
| 信源可逆 | `st.text()` 任意 UTF-8 | `decode(encode(t))==t` |
| 加扰可逆 | `st.lists(st.integers(0,1))` + `st.integers()` seed | `descramble(scramble(b,s),s)==b` |
| 重复码可逆 | 任意比特 | `decode(encode(b))==b` |
| QPSK 无噪零误码 | 偶数比特 | `demod(mod(b))==b` |
| CRC 单 bit 检错 | 任意 payload + 翻 1 bit | `crc_valid==False` |
| 帧 build→parse 还原 | 任意 payload | payload 还原、length==len |
| AWGN 可复现 | 固定 seed | 两次 allclose |

## 4. 端到端测试

- 不同中文文本（短/长/含 ASCII/emoji）
- 不同 SNR（0/6/12/18 dB）
- 不同 seed（2026/2027/随机）
- 随机同步偏移（前缀噪声符号 0~50）
- 空文本、1 字符极短
- 低 SNR（BER>0 且 text_match<1）
- 错误 CLI（`--mod foo`/`--channel bar` 非零退出）
- metrics.json 字段与值校验（含新字段 crc_valid/sync_confidence）
- 图集文件存在性（≥6 张 + 旧 3 名）

## 5. 覆盖率门禁（不污染 CI）

**关键约束**：CI（`grading.yml`）跑 `pytest public_tests -q`，无 `--no-cov`。因此覆盖率门禁**不能**写进 `pyproject.toml` 全局 `addopts`，否则 CI 跑 public_tests 时也触发 cov 门禁，public_tests 对 src 覆盖率不足 90% 会挂 CI。

策略：
- `pyproject.toml` 只配 `[tool.coverage.run]`/`[tool.coverage.report]`，**不**配 `[tool.pytest.ini_options].addopts`。
- 覆盖率门禁靠本地命令显式触发：
  ```bash
  pytest tests --cov=src --cov=main --cov-fail-under=90 --cov-report=term-missing --cov-report=html
  ```
- 目标：`src/` + `main.py` 行覆盖率 ≥ 90%。

## 6. 红绿重构执行顺序（依赖拓扑）

```
source → crypto → channel_coding → framing → modulation → channel → synchronization → metrics → main
```

每模块循环：
1. 写失败 unit 测试（红）
2. 最小实现（绿）
3. 重构（去冗余 + 类型标注 + docstring）
4. `pytest tests/unit/test_<mod> --cov=<mod>` 覆盖率 ≥ 90%
5. `pytest public_tests -q` 回归（保绿）

## 7. 公开测试回归策略

- 每完成一模块，**立即** `pytest public_tests -q`；红则定位碰了哪条红线（接口名/映射/字段），回退。
- git 分支 `feature/redesign`，每模块绿后 commit，回归时 `git diff` 缩范围。
- `conftest.py` 的 `SAMPLE_TEXT` 为端到端 fixture，学生测试复用同源文本。

## 8. 测试运行命令

```bash
# 公开测试（红线，CI 同款）
pytest public_tests -q

# 学生测试 + 覆盖率门禁（本地）
pytest tests --cov=src --cov=main --cov-fail-under=90 --cov-report=term-missing

# 单模块快速迭代
pytest tests/unit/test_framing.py -v

# Mock 设计验证
PYTHONPATH=. python mock/verify_design.py

# 端到端
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```
