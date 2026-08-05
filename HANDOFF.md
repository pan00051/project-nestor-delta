# HANDOFF · Nestor Delta 工程交接

> **这是工程交接文档(快变量)，记录「现在做到哪、下一步干嘛」。几乎每次工作会话结束都应更新。**
> 方向与边界不在这里，在 `BLUEPRINT.md`(慢变量)。接手时：**先读 BLUEPRINT 知道规矩，再读本文件知道进度。**
> 本 repo 范围仅为 **Nestor Delta(数据层)**。Insight / 完整版 Nestor 是另外的独立交付，不在此 repo 处理。
> 本文件与 BLUEPRINT 冲突时，以 BLUEPRINT 为准；若发现冲突，提示作者。

---

## 使用说明(给每一个接手的 AI / 未来的作者)

1. 进场先读 `BLUEPRINT.md` 全文，再读本文件的「当前焦点」与「最近进展」。
2. 只在「当前焦点」这**一个** Sprint 上推进，不擅自开新战场(防膨胀，见 BLUEPRINT 第 5 节)。
3. 会话结束前，更新本文件的「最近进展」「下一步」「待决事项」「给下一棒的话」。
4. 任何方向级变更，先改 BLUEPRINT 并留 commit，再回来。

---

## 里程碑总览(Delta)

| 里程碑 | 名称 | 内容 | 是否可交付点 |
|--------|------|------|--------------|
| **M0** | 地基 | 评测协议 + 数据 + baseline，让一切可测、可复现 | 内部里程碑 |
| **M1** | MVP 核心 | 通用权重机制 + 三变量预测(Stage 1) | ✅ **第一个可写进简历的完整作品** |
| **M2** | 深度/差异化(上限) | 动态权重变化(Stage 2)+ 忽略值/资源自适应(Stage 3) | ✅ 增强版作品 |
| — | 星辰大海(不做) | 大规模导入、视角切换、动态二级分组(Stage 4) | ❌ 一年内不碰，见 BLUEPRINT 第 6 节 |

**关键：做完 M1 就可以停下来交付。M2 是加分项，不是义务。** 一次只推进一个 Sprint。

---

## Sprint 划分与验收标准

> 时间提示：这是研究性工程，不是 Push 那种已知路径。**Sprint 会因为“调不准/假设不成立”而延期，这是常态，不是失败。** 下面的周数是“顺利情况”的粗估，别拿它当死线自责。

### 通用完成门槛(Definition of Done · 每个 Sprint 都必须满足)

- [ ] 该 Sprint 的产出已 commit，commit message 写清“做了什么、为什么”。
- [ ] 涉及数字的结论，都建立在**锁定的评测协议**上(M0 定义，全程不改)。
- [ ] 一次只引入一个变量/一个模块(单变量消融，便于归因)。
- [ ] 关键数字**多次运行**，报均值 + 波动范围，不信单次。
- [ ] 产出可**一键复现**(脚本/配置齐全)。
- [ ] HANDOFF 已更新。

---

### M0 · 地基

**Sprint 0 — 锁定评测协议 + 环境(顺利约 1 周)**
- 目标：把“标尺”钉死，全程不再改。
- 产出：
  - `EVALUATION.md`：固定一个任务定义、一个数据集(可先用公开或合成的多变量时间序列)、一套指标(建议：预测误差 MAE/RMSE；后期加运行时/内存)，以及要对比的 baseline 清单。
  - repo 目录结构 + 可复现的开发环境(依赖锁定)。
- 验收：
  - [ ] `EVALUATION.md` 存在，任务/数据/指标/baseline 四项明确且冻结。
  - [ ] 环境可一键重建。

**Sprint 1 — 数据 + baseline(顺利约 1 周)**
- 目标：测出“什么都不做”时的参照零点。
- 产出：数据加载管线 + 至少两个朴素 baseline(如 persistence/上一值，和一个简单线性/VAR 模型)+ baseline 指标表。
- 验收：
  - [ ] baseline 指标已测出并 commit，作为后续一切“提升”的分母。
  - [ ] baseline 可一键复现。

---

### M1 · MVP 核心(做完即第一个可交付作品)

**Sprint 2 — 通用权重机制(底座)(顺利约 1-2 周)**
- 目标：做那个**被复用最多的地基**，一个与“层”无关的通用权重机制(输入一组变量的历史，输出它们之间的关系权重)。
- 必须先写清(这是本 Sprint 的核心产出，不只是代码)：
  - 输入是什么、输出是什么。
  - **它明确不管什么**(决定它能否独立、能否被复用)。
  - “怎么算调好了”的验证标准。
- 验收：
  - [ ] 模块接口(输入/输出/不管什么)已写进 README 或模块说明。
  - [ ] 有最小测试证明它能独立运行、结果可复现。
  - [ ] 该机制被设计成**通用、可被上层复用**，而非绑死在某一场景。

**Sprint 3 — 三变量预测(Stage 1)(顺利约 1-2 周)**
- 目标：用上面的权重，做“固定一个目标变量，用另两个的走向预估目标走向”，并证明它有效。
- 验收：
  - [ ] 在锁定测试集上，预测误差**优于朴素 baseline**，差距可量化(报均值±波动)。
  - [ ] 全流程一键复现。
  - [ ] 一篇简短 writeup(方法 + 结果表 + 诚实的局限)。

> ✅ **到此为止，Delta 已是一个可写进简历的完整作品。** 叙事：“构建了一个多变量关系分析模块，当前实现了三变量关系加权与预测，并规划了通向动态漂移与资源自适应的路径。” 可以在这里停下来收尾，也可以继续 M2。

---

### M2 · 深度 / 差异化(上限，非必须)

**Sprint 4 — 动态权重变化能力(Stage 2)(顺利约 2-3 周)**
- 目标：把“动态变化”做成一个**通用能力模块**(能套用在任意权重上)，而非为数据层专写一遍(见 BLUEPRINT 架构原则第 4 节)。让权重能随时间漂移被追踪；可选：根据权重历史预测其短期变化。
- 对应领域：在线时间序列 / 概念漂移(concept drift)。
- 验收：
  - [ ] “动态变化”是层无关的独立模块，被权重机制复用，**未修改** Sprint 2 的既有逻辑(开闭原则)。
  - [ ] 在含漂移的数据上，动态版本优于静态版本，差距可量化。

**Sprint 5 — 忽略值 / 资源自适应(Stage 3)(顺利约 2-3 周)**
- 目标：实现“忽略值”，剪掉过弱的关系；算力吃紧时自动拉高忽略值(相当于约分省算力)。**这是作者最有原创感的设计，也是差异化亮点。**
- 验收(这条指标最能进作品集)：
  - [ ] 能证明：开启忽略值后**算力/内存下降 X%，而预测精度只下降 Y%**(X、Y 为实测)。
  - [ ] 忽略值作为独立能力接入，未破坏前面模块。

---

## 当前焦点(同一时间只允许一个)

> **Sprint 2 — 通用权重机制(底座)。**
> Sprint 2 已完成，等待作者验收。不要自动进入 Sprint 3；不要实现动态权重或忽略值。

---

## 最近进展(倒序，最新在上)

- **[2026-08-06 · Sprint 2 完成]** 已实现层无关的通用关系权重机制：`src/nestor_delta/relation_weights.py`。接口文档写入 `docs/WEIGHTING.md`，明确输入、输出、不负责什么、验证标准。机制输入为任意命名数值历史，输出有向 `source -> target` 的 `RelationWeight(source, target, lag, weight, score, sample_count)`；不做预测、不做业务解释、不做动态变化、不做忽略值。
- **[2026-08-06 · Sprint 2 验证结果]** 已运行 `scripts/run_weights.py`，在 5 个冻结 synthetic seed 上验证 `target` 的已知驱动信号排序。结果：`driver_a` mean rank `1.00`、range `1-1`、mean score `0.595528`、score range `0.548573-0.663159`；`driver_b` mean rank `2.00`、range `2-2`、mean score `0.393421`、score range `0.331254-0.464283`；`noise` mean rank `3.00`、range `3-3`、mean score `0.059127`、score range `0.020952-0.093188`。明细在 `reports/weight_validation.csv`，汇总在 `reports/weight_validation_summary.md`。
- **[2026-08-06 · Sprint 2 命令记录]** 已执行：`.venv/bin/python scripts/run_weights.py`、`.venv/bin/python -m unittest discover -s tests`、`.venv/bin/python scripts/run_baselines.py`。baseline 回归数字保持 Sprint 1 原结果。新增测试文件 `tests/test_relation_weights.py`，用标准库 unittest 验证确定性与已知 lag 驱动排序。
- **[2026-08-06 · Sprint 2 问题与处理]** 本轮没有新增依赖，也没有引入 sklearn/NumPy。权重机制采用 lagged Pearson correlation，作为可复用工程底座，不声称算法创新。未发现需要改变 `EVALUATION.md` 的事项。
- **[2026-08-06 · S1 验证固化]** 根据外部审查结论，新增标准库 `unittest` 测试：同 seed 生成 CSV 字节一致、OLS 在 seed `11` 训练集上还原已知驱动系数。测试命令为 `python -m unittest discover -s tests`。`EVALUATION.md` 标为 `v1`，`reports/baseline_summary.md` 补充正确性自检说明，`baselines.py` 注明正规方程的数值稳定性取舍。该远端提交已在本轮 rebase 中保留。
- **[2026-08-06 · Sprint 1 完成]** 已实现合成数据生成管线和两个 baseline：persistence / previous value、simple linear regression。实现文件：`src/nestor_delta/synthetic.py`、`src/nestor_delta/splits.py`、`src/nestor_delta/baselines.py`、`src/nestor_delta/metrics.py`、`src/nestor_delta/reporting.py`；一键入口：`scripts/run_baselines.py`。没有实现通用权重机制、动态权重或忽略值。
- **[2026-08-06 · Sprint 1 结果]** 已按 `EVALUATION.md` 的 5 seed 协议运行 baseline 并保存报告。test 指标：linear_regression MAE mean `0.428163`、range `0.381239-0.470460`；RMSE mean `0.540204`、range `0.478609-0.592253`。persistence MAE mean `0.566021`、range `0.508144-0.624679`；RMSE mean `0.703043`、range `0.632300-0.789040`。per-seed 表在 `reports/baseline_metrics.csv`，汇总在 `reports/baseline_summary.md`。
- **[2026-08-06 · Sprint 1 命令记录]** 已执行：`python scripts/run_baselines.py`、`python3 scripts/run_baselines.py`、`.venv/bin/python scripts/run_baselines.py`、`python3 -m compileall src scripts`、`env PYTHONPYCACHEPREFIX=/private/tmp/nestor-delta-pycache python3 -m compileall src scripts`、`wc -l data/synthetic/synthetic_seed_11.csv data/synthetic/synthetic_seed_23.csv data/synthetic/synthetic_seed_37.csv data/synthetic/synthetic_seed_41.csv data/synthetic/synthetic_seed_53.csv`。`python3` 与 `.venv/bin/python` 的 baseline 输出一致。
- **[2026-08-06 · Sprint 1 问题与处理]** 第一次执行 `python scripts/run_baselines.py` 失败，因为当前 shell 未激活 venv 且系统没有 `python` 命令；按 README 激活 venv 后可使用 `python`，未激活时使用 `python3 scripts/run_baselines.py`。第一次执行 `python3 -m compileall src scripts` 失败，因为 macOS Python 试图写入不可用的用户 cache；已用 `PYTHONPYCACHEPREFIX=/private/tmp/nestor-delta-pycache` 重跑并通过。
- **[2026-08-06 · Sprint 0 加严]** 已按验收反馈补强 `EVALUATION.md`：冻结合成数据生成公式、噪声分布、随机数抽样顺序、初始滞后值、无标准化策略、CSV 精度、600 行的 train/validation/test 精确边界、5-step lag 的监督样本归属规则、persistence 与 OLS baseline 的实现细节、以及禁止数据泄漏规则。未写建模代码。
- **[2026-08-06 · 环境可验]** 已新增 `REPRODUCIBILITY.md`，列出 Sprint 0 验收命令与预期结果，并明确 Sprint 0 不产生 baseline 数字。README 已链接该文件。本轮已再次执行 `python3 --version`、`python3 -m venv .venv`、`.venv/bin/python -m pip install -r requirements-lock.txt`；结果为 Python `3.9.6`，venv 创建成功，依赖安装成功且无第三方依赖。pip cache 目录不可写警告仍存在，但不影响复现。
- **[2026-08-06 · Sprint 0 完成]** 已新增 `EVALUATION.md`，冻结 M0 的任务定义、数据方案、指标与 baseline 清单。数据选择已按本轮指令/协议冻结为“合成多变量时间序列”第一版：5 个固定 seed(`11/23/37/41/53`)、每条 600 行、70/15/15 时间切分、一步预测 `target`。指标冻结为 MAE/RMSE，并要求多 seed 报均值与 min-max 波动范围。
- **[2026-08-06 · 环境与结构]** 已新增 `pyproject.toml`、`requirements-lock.txt`、`src/nestor_delta/`、`scripts/`、`data/synthetic/`、`reports/`。Sprint 0 环境刻意保持无第三方运行依赖，仅要求 Python `>=3.9`；README 已加入从 clean checkout 重建环境的命令。
- **[2026-08-06 · 本轮命令记录]** 已执行：`git remote add origin https://github.com/pan00051/project-nestor-delta.git`、`git fetch origin main`、`git checkout -B main origin/main`、`sed -n '1,260p' BLUEPRINT.md`、`sed -n '1,260p' HANDOFF.md`、`python3 -m venv .venv`、`.venv/bin/python -m pip install -r requirements-lock.txt`、`.venv/bin/python --version`。本轮只完成 Sprint 0 文件与文档，不运行 baseline 数字。
- **[2026-08-06 · 验证结果]** 本机 Python 为 `3.9.6`；虚拟环境创建成功；`requirements-lock.txt` 安装成功且无第三方依赖。pip 提示用户 cache 目录不可写并自动禁用缓存，不影响环境重建。
- **[2026-08-06 · 遇到的问题]** 当前 Codex 可写目录最初是空 git repo，remote 未配置；已按用户给定 GitHub repo 设置 `origin` 并检出 `origin/main`。部分 `.git` 操作受沙箱限制，已通过授权执行。用户消息在 `...` 处截断，因此本轮只按 repo 权威文件推进 Sprint 0，未凭旧上下文扩展到 Sprint 1。
- **[运行规则补充]** `RUNBOOK.md` 已新增防死循环规则：遇到难以解决的问题时，不用同一种方式反复尝试；最多尝试三种有实质差异的解决路径，仍失败则提前停止，并把现象、尝试、失败原因、判断和后续方向写进 HANDOFF，等待作者决策。
- **[规范性审查]** 已检查 `BLUEPRINT.md`、`HANDOFF.md`、`RUNBOOK.md`、`README.md`：当前焦点唯一，Delta repo 边界清楚，里程碑/Sprint 与 README 口径一致。`RUNBOOK.md` 已补充“上下文卫生与记录协议”，要求后续 AI 默认只查 BLUEPRINT/HANDOFF，并把改动、尝试、问题和后续方向沉淀进 HANDOFF。
- **[蓝图对齐]** `BLUEPRINT.md` 已调整为 Delta repo 专属，不再把当前焦点拉回 Insight；`HANDOFF.md` 已替换为 Delta 工程 Sprint 版本。
- **[repo 建立]** GitHub repo `pan00051/project-nestor-delta` 已创建并公开，四份文档(BLUEPRINT/HANDOFF/RUNBOOK/README)已提交。README 与蓝图一致。尚无任何建模实现。
- **[初始]** 项目蓝图与规则确立(BLUEPRINT.md v1)。目标=可验证作品集；结构=三作品；架构与收敛纪律确立。

---

## 下一步(具体、可执行)

1. 验收 Sprint 2：确认 `docs/WEIGHTING.md` 的接口边界、`tests/test_relation_weights.py` 的最小测试、`reports/weight_validation_summary.md` 的验证结果是否满足通用权重底座要求。
2. 下一步只能是 Sprint 3 的准备工作；不要自动开始 Sprint 3。
3. Sprint 3 开始前，应先写清三变量预测流程如何组合 Sprint 1 baseline 与 Sprint 2 权重机制，并沿用 M0 锁定测试集。

---

## 验收状态

- **Sprint 0 / `EVALUATION.md`：完成。** 任务、数据、指标、baseline、切分边界、数据公式、baseline 实现细节和防泄漏规则已冻结。
- **Sprint 0 / 环境可重建：完成。** 已在 Python `3.9.6` 验证：`python3 -m venv .venv` 与 `.venv/bin/python -m pip install -r requirements-lock.txt` 成功。
- **Sprint 0 / 输出边界：完成。** 明确 Sprint 0 不产生 baseline 数字；baseline 指标留到 Sprint 1。
- **Sprint 1 / 数据管线：完成。** `python scripts/run_baselines.py` 会生成 5 个固定 seed 的合成 CSV；每个文件 601 行(header + 600 data rows)。
- **Sprint 1 / baseline：完成。** persistence 与 simple linear regression 均已实现并运行。
- **Sprint 1 / 指标报告：完成。** 已生成并保存 per-seed 指标表与汇总报告，报告均值和 min-max 波动范围。
- **Sprint 1 / 一键复现：完成。** README 与 `REPRODUCIBILITY.md` 已记录完整命令。
- **Sprint 1 / 自动化验证：完成。** 已新增 `python -m unittest discover -s tests` 标准库测试，固化确定性复跑和已知系数还原两个审查验证。
- **Sprint 2 / 模块接口：完成。** `docs/WEIGHTING.md` 已写清输入、输出、不负责什么和验证标准。
- **Sprint 2 / 独立实现：完成。** `src/nestor_delta/relation_weights.py` 可独立计算层无关的 lagged relation weights。
- **Sprint 2 / 最小测试：完成。** `.venv/bin/python -m unittest discover -s tests` 通过。
- **Sprint 2 / 验证报告：完成。** `reports/weight_validation.csv` 与 `reports/weight_validation_summary.md` 已保存 5 seed 均值和 min-max 波动范围。

---

## 待决事项(等作者拍板，不替他决定)

- **D1：(已解决)** 本 repo 做 Delta；Delta 内第一个建模模块 = 通用权重机制(Sprint 2)，忽略值推后到 M2。
- **D2：** repo 结构：三作品各独立 repo + 总纲，还是分散？可推迟。
- **D4：(已解决)** Sprint 0 第一版数据采用**合成多变量时间序列**。理由：关系可控、便于验证机制、可复现；真实数据可在合成 baseline 稳定后作为增强说服力的后续项，不属于 Sprint 0/1 必做。

---

## 关键设计选择(留痕，防止反复推翻)

| 编号 | 选择 | 状态 | 说明 |
|------|------|------|------|
| C1 | 预测内核优先用统计/时序方法，LLM 只放外围 | 倾向未定 | 见 BLUEPRINT 第 7 节 |
| C2 | 先做通用权重底座，忽略值/动态推后 | 已决 | 遵循“先做最被复用的地基” |
| C3 | M1 完成即为可交付停止点 | 已决 | M2 为上限，非义务 |
| C4 | M0 第一版数据使用合成多变量时间序列 | 已决 | 关系可控，便于后续验证权重机制；真实数据后续增强 |
| C5 | Sprint 2 首版权重机制使用 lagged Pearson correlation | 已决 | 标准库可复现、层无关、足够作为可验证工程底座；不声称算法创新 |

---

## 给下一棒的话

> Sprint 2 已完成：通用关系权重机制、接口文档、最小测试和 5 seed 验证报告都已落地。下一棒不要自动进入 Sprint 3；只能在作者验收后准备三变量预测流程。继续严禁提前实现动态权重或忽略值。
