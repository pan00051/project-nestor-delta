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
| **M1** | MVP 核心 | 通用权重机制 + 三变量预测(Stage 1) + 静态信任度门控(S3.1) | ✅ **第一个可写进简历的完整作品** |
| **M2** | 深度/差异化(上限) | 动态权重漂移(S4) + 忽略值/资源自适应(S5) | ✅ 增强版作品 |
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

**S3.1 — 静态信任度门控(已完成并验收)**
- 目标：把 Sprint 2 权重的绝对值作为信任度，在 OLS 前决定源信号准入强度；保留 Sprint 3 OLS 模式作为并列对照，证明权重数值会实际改变门控模式预测。
- 机制边界：静态、确定性、分段线性门控；源按方向与准入系数合成为共享关系信号后再交给 OLS。不得回改 Sprint 3，不包含动态权重或资源自适应。
- 验收：
  - [x] 门控是独立模块，组合 Sprint 2/Sprint 3 接口，未修改既有冻结逻辑。
  - [x] 噪声源被阻断、弱源保留正确方向与非零准入；同 seed 复跑一致。
  - [x] 五 seed 已报告 OLS 与门控 MAE/RMSE，并用反事实证明门控模式对权重数值敏感、OLS 模式对独立非零缩放不敏感。

> ✅ **到此为止，Delta 已是一个可写进简历的完整作品。** 叙事：“构建了一个多变量关系分析模块，当前实现了三变量关系加权与预测，并规划了通向动态漂移与资源自适应的路径。” 可以在这里停下来收尾，也可以继续 M2。

---

### M2 · 深度 / 差异化(上限，非必须)

**Sprint 4 — 动态权重漂移能力(Stage 2)(已完成并验收)**
- 目标：把“动态变化”做成一个层无关的通用能力模块，让权重随时间漂移被追踪；可选：根据权重历史预测其短期变化。
- 对应领域：在线时间序列 / 概念漂移(concept drift)。
- 验收：
  - [x] 动态变化是层无关的独立模块，被权重机制复用，未修改 Sprint 2 或 S3.1 的既有逻辑。
  - [x] 在含漂移的数据上，动态版本优于静态版本，差距可量化。

**Sprint 5 — 忽略值 / 资源自适应(Stage 3)(实现及工程验收完成，待作者验收/提交)**
- 目标：实现“忽略值”，剪掉过弱的关系；算力吃紧时自动拉高忽略值(相当于约分省算力)。**这是作者最有原创感的设计，也是差异化亮点。**
- 验收(这条指标最能进作品集)：
  - [x] 能证明：开启忽略值后**算力/内存下降 X%，而预测精度只下降 Y%**(X、Y 为实测)。
  - [x] 忽略值作为独立能力接入，未破坏前面模块。

---

## 当前焦点(同一时间只允许一个)

> **S6 — 真实数据案例 Runner：框架实现完成，等待作者准备真实案例 CSV。**
> 当前只做本地 CSV + config 的离线分析框架；不要做用户上传、API 接入、dashboard 或自动清洗。

---

## 最近进展(倒序，最新在上)

- **[2026-08-06 · S6 真实数据框架完成]** 新增 `real_data.py`、`real_case_analysis.py` 和一键入口 `scripts/run_real_case.py`。S6 输入为作者手工准备并已对齐的本地 CSV + JSON config；输出 `relation_ranking.csv`、`prediction_metrics.csv`、`predictions_vs_actual.csv`、`resource_tradeoff.csv` 和 `summary.md`，方便后续手动画图。
- **[2026-08-06 · S6 边界与防自欺]** 候选池可由作者定义，但 ranking/selection 必须由 train-only 数据自动生成；CSV 列顺序不代表优先级，loader 会把候选变量规范化排序。若真实数据候选共线导致 OLS 奇异，runner 会优先删除与更高排名信号重叠的低排名者；降到 0 个稳定信号时只保留 baseline。S6 只报告 co-movement / predictive usefulness，不抓 API、不做 dashboard、不自动清洗。
- **[2026-08-06 · S6 验证]** 新增 `docs/REAL_DATA_CASE_RUNNER.md`，`EVALUATION.md` 追加 S6 协议。新增 8 项测试覆盖报告输出、候选列顺序不影响 CSV 产物、未来 test 区间篡改不影响 train-only ranking/selection/系数、完整/部分/零稳定信号共线降级、坏 config 和脏 CSV 清晰失败。
- **[2026-08-06 · S5 资源自适应完成]** 新增层无关资源阈值模块 `resource_adaptive_ignore.py`、组合预测模块 `resource_adaptive_prediction.py`、高维压力夹具 `synthetic_resource_stress.py` 与冻结常量 `s5_config.py`。S5 使用双轨验收：原 S4 冻结数据作为 correctness regression，新增 15 候选变量 stress fixture 验证资源曲线；未修改 S0-S4 冻结代码和旧报告。
- **[2026-08-06 · S5 阈值与边界]** `budget_ratio` 五档固定为 `1.00/0.75/0.50/0.25/0.00`，阈值按 `0.06/0.17/0.28/0.39/0.50` 单调上升。`0.06` 仅表述为当前冻结合成数据 + 多 lag 最大相关的 benchmark noise floor，不表述为通用真实数据阈值。资源指标统一命名为 `downstream_compute_proxy` / `downstream_memory_proxy`，因为当前仍先计算所有候选关系，不声称 end-to-end compute reduction。
- **[2026-08-06 · S5 五 seed 结果]** 高维 `resource_stress` 轨：`budget_ratio=0.75` 时 retained mean `7.60`、downstream compute/memory proxy 均下降 `41.56%`，MAE mean `0.517833`、相对 full-budget MAE loss `4.11%`；`0.50` 时 proxy 下降 `73.00%`、MAE loss `55.23%`；`0.25` 时 proxy 下降 `84.49%`、MAE loss `81.77%`；`0.00` 时 proxy 下降 `98.46%`、MAE loss `137.57%`。S4 correctness 轨在 `0.75` 时仅下降 `13.33%`、MAE loss `0.14%`，并保留 `driver_a/driver_b`、阻断 `noise`。
- **[2026-08-06 · S5 验证]** 一键入口为 `scripts/run_resource_adaptive_ignore.py`；tracked 报告为 `reports/resource_adaptive_metrics.csv`、`resource_adaptive_retention.csv`、`resource_adaptive_summary.md`；接口说明为 `docs/RESOURCE_ADAPTIVE_IGNORE.md`，协议追加到 `EVALUATION.md` S5 小节。新增 7 项标准库测试覆盖阈值表、downstream proxy 公式、S4 低维防回归、高维单调保留/资源下降、弱信号先剪、防泄漏和 fixture 字节确定性。已复跑 S0-S5 全脚本；S0-S4 旧报告 SHA-256 与复跑前完全一致；`python -m unittest discover -s tests` 共 23 tests 通过，`compileall` 与 `git diff --check` 通过。
- **[2026-08-06 · S4 作者验收与收尾]** 作者已独立复核并验收 S4：防泄漏用篡改未来数据验证通过、5/5 种子追踪漂移已复现、120 行窗口冻结确认。本轮复跑完整验收，S0-S3.1 旧报告 SHA-256 与复跑前完全一致，`run_dynamic_weights.py` 复现动态 mean MAE/RMSE 相对静态降低 `7.52%/6.38%`；16 tests、compileall 与 `git diff --check` 通过。S4 标记为完成并验收；当前焦点切换到 S5，但本轮不启动 S5。
- **[2026-08-06 · S4 动态权重完成]** 新增平行漂移生成器 `synthetic_drift.py`、S4 独立常量、层无关滚动封装 `dynamic_weights.py` 和数据层对照预测 `dynamic_prediction.py`。`relation_weights.py` 与 S0-S3.1 冻结实现均未修改。
- **[2026-08-06 · S4 冻结数据]** 新 seed 为 `101/103/107/109/113`；`driver_a` lag-1 系数在 `0-419` 恒为 `0.15`，在 `420-599` 线性升至 `0.65`。主数据保持原五列，真相写入独立 sidecar；公式、随机顺序、窗口和 prequential 防泄漏规则已追加到 `EVALUATION.md` 独立 S4 小节。
- **[2026-08-06 · S4 机制与防泄漏]** 固定 120 行滑窗，在时点 `t` 只把 `t-120..t-1` 喂给 Sprint 2 静态权重函数。静态/动态模式使用相同 train-only top-2 源和训练标签 `120-419`；OLS 训练后冻结，测试中只更新关系权重，当前标签只可用于后续时点。
- **[2026-08-06 · S4 五 seed 结果]** `driver_a -> target` 动态权重从测试起点到终点五次均向已知正漂移方向上升。动态 MAE mean `0.506484`、range `0.463798-0.572600`，静态 MAE mean `0.547689`、range `0.490096-0.624914`，降低 `7.52%`；动态 RMSE mean `0.640280`、range `0.580674-0.715281`，静态 RMSE mean `0.683878`、range `0.636739-0.768990`，降低 `6.38%`。
- **[2026-08-06 · S4 产出]** 一键入口为 `scripts/run_dynamic_weights.py`；tracked 报告为 `reports/dynamic_weight_metrics.csv`、`dynamic_weight_trajectory.csv`、`dynamic_weight_tracking.csv`、`dynamic_weight_summary.md`；接口说明为 `docs/DYNAMIC_WEIGHTS.md`。新增 4 项标准库测试覆盖公式、字节确定性、当前/未来行排除和核心五 seed 验收。
- **[2026-08-06 · S4 回归验证]** 已复跑 `run_baselines.py`、`run_weights.py`、`run_stage1.py`、`run_trust_gating.py`、`run_dynamic_weights.py`；`python3 -m unittest discover -s tests` 共 16 tests 通过，`compileall` 与 `git diff --check` 通过。S0-S3.1 冻结模块和旧报告均无 diff；四份 S4 报告连续两次 SHA-256 完全一致。

- **[2026-08-06 · 编号纠正与验收]** commit `d86a4c8` 的 message 将静态门控误标为 S4；该 commit 实际只实现静态信任度门控，按项目定义属于 **S3.1**。本轮仅更正 `BLUEPRINT.md`、`HANDOFF.md`、`README.md`、`docs/TRUST_GATING.md` 的编号，不改代码、测试或报告。已用 `rg` 核对 S3.1/S4 语义并执行 `git diff --check`；纯文档变更不复跑数值测试。S3.1 已完成并验收；真正的 S4 是动态权重漂移，尚未开始。
- **[2026-08-06 · S3.1 信任度门控完成]** 新增层无关门控模块 `src/nestor_delta/trust_gating.py` 和组合预测模块 `src/nestor_delta/trust_gated_prediction.py`。接口提供 `ols` / `trust_gated` 两种并列模式；`ols` 直接委托冻结的 Sprint 3 实现，门控模式使用 train-only Sprint 2 权重，不修改 S0-S3 代码或报告。
- **[2026-08-06 · S3.1 机制决策]** 单纯把每个独立源列乘以非零准入系数仍会被无约束 OLS 抵消，因此门控层先按 `direction * admission` 合成每个 lag 的共享关系信号，再交给 OLS。默认分段线性规则固定为：trust `<=0.15` 时准入 `0`，trust `>=0.50` 时准入 `1`，中间线性插值。`0.15` 仅依据五 seed train-only noise score 上界 `0.147512` 确定，未依据 validation/test 指标调参。
- **[2026-08-06 · S3.1 五 seed 结果]** `scripts/run_trust_gating.py` 已生成 `reports/trust_gating_metrics.csv`、`trust_gating_admissions.csv`、`trust_gating_sensitivity.csv`、`trust_gating_summary.md`。`sprint3_ols` MAE mean `0.422277`、range `0.375342-0.457150`，RMSE mean `0.532636`、range `0.470656-0.589775`；`trust_gated_ols` MAE mean `0.454786`、range `0.415817-0.492024`，RMSE mean `0.568517`、range `0.518068-0.634403`。门控精度低于 S3 OLS：mean MAE 高 `7.70%`、RMSE 高 `6.74%`，按要求诚实报告，不要求门控必胜。
- **[2026-08-06 · S3.1 准入与敏感性]** 五 seed 中 `driver_a` admission 恒为 `1.0`；`driver_b` 保持负方向，mean admission `0.687608`、range `0.384004-0.954034`；`noise` 五次均为 `0.0`。只将弱源 `driver_b` trust 改为 `1.0`、保持 noise 阻断并重新拟合后，S3 OLS mean absolute prediction delta 为 `0.0000000000`，门控模式为 `0.0774200737`、range `0.0081728375-0.1567707161`，证明连续准入比例在新模式中实际生效。
- **[2026-08-06 · S3.1 测试与命令]** 新增 `tests/test_trust_gating.py`，覆盖分段线性边界、五 seed 噪声阻断、弱源方向与折扣准入、同 seed 确定性、门控权重敏感性、S3 独立缩放不变性。已执行 `.venv/bin/python scripts/run_baselines.py`、`.venv/bin/python scripts/run_weights.py`、`.venv/bin/python scripts/run_stage1.py`、两次 `.venv/bin/python scripts/run_trust_gating.py`、`.venv/bin/python -m unittest discover -s tests`（12 tests 通过）、`env PYTHONPYCACHEPREFIX=/private/tmp/nestor-delta-pycache python3 -m compileall src scripts tests`、`git diff --check`。四份门控报告连续两次 SHA-256 完全一致；S0-S3 冻结文件 `git diff --numstat` 为空。
- **[2026-08-06 · S3.1 尝试与问题]** 初始 `ignore_threshold=0.10` 在 seed `37` 的 train-only noise score `0.147512` 上不能阻断噪声，因此改为紧邻 train-only 噪声上界的固定值 `0.15`。曾探查“每 lag 共享信号”和“只用每源最佳 lag 的单一共享信号”；最终选择每 lag 共享信号，因为它与 Sprint 3 的五步历史输入更一致。另做 `0.10-0.40` 阈值诊断但未据 test 误差选默认值；没有阈值调参声明。
- **[2026-08-06 · S3.1 输出格式问题]** 首次暂存检查发现 Python `csv` 默认 CRLF 会被 `git diff --cached --check` 标为 trailing whitespace。未修改冻结的 Sprint 1 writer；仅在新 S3.1 三个 CSV writer 中显式固定 `lineterminator="\n"`，重新生成后检查通过。
- **[2026-08-06 · S3.1 文档]** 新增 `docs/TRUST_GATING.md`，说明接口、门函数、为何必须在 OLS 前合并信号、验证与边界。`BLUEPRINT.md` 已留慢变量痕迹：S3.1 验证静态信任度门控；真正的 S4 动态权重仍是后续独立能力。
- **[2026-08-06 · S2 审查反馈落实]** 作者提交 S1 修订与 S2 审查结论：merge 干净、S1 修订达标、S2 通过且无阻断问题。本轮仅处理非阻断文档改进：`docs/WEIGHTING.md` 已明确 Sprint 2 的 `weight` 是边际 pairwise correlation，不是 OLS partial coefficient / 净效应；并记录多 lag 取最大绝对相关会抬高 noise floor，未来 S5 忽略阈值必须高于观测噪声地板。`docs/STAGE1.md` 已补充 Stage 1 只把 relation weights 用于选源与特征缩放，不把它解释为因果或最终回归系数。
- **[2026-08-06 · Sprint 3 完成]** 已实现 Stage 1 三变量预测工作流：`src/nestor_delta/stage1_prediction.py`。一键入口：`scripts/run_stage1.py`。方法：每个 seed 只用 train rows 计算 Sprint 2 relation weights，选择 `target` 的 top-2 non-target sources，再用 lagged `target` + 两个加权 source histories 训练标准库 OLS。未修改 Sprint 2 权重机制，未实现动态权重或忽略值。
- **[2026-08-06 · Sprint 3 结果]** 已按 M0 锁定协议运行 5 个 seed，结果保存在 `reports/stage1_metrics.csv`、`reports/stage1_selected_sources.csv`、`reports/stage1_summary.md`。test 指标：stage1_weighted_three_variable MAE mean `0.422277`、range `0.375342-0.457150`；RMSE mean `0.532636`、range `0.470656-0.589775`。对比：persistence MAE mean `0.566021` / RMSE mean `0.703043`；linear_regression MAE mean `0.428163` / RMSE mean `0.540204`。Stage 1 mean MAE 比 persistence 低 `25.40%`，比 Sprint 1 linear regression 低 `1.37%`；mean RMSE 分别低 `24.24%` 和 `1.40%`。
- **[2026-08-06 · Sprint 3 命令记录]** 已执行：`.venv/bin/python scripts/run_stage1.py`、`.venv/bin/python -m unittest discover -s tests`、`.venv/bin/python scripts/run_baselines.py`、`.venv/bin/python scripts/run_weights.py`。完整测试目前为 7 tests 通过。baseline 与 weight 验证数字保持稳定。
- **[2026-08-06 · Sprint 3 问题与处理]** 初始探针尝试“只用每个 source 的最佳 lag”能优于 persistence，但均值略弱于 Sprint 1 full linear regression；因此在 Sprint 3 范围内调整为“target + top-2 sources 的 5-step lagged features，并用 signed relation weight 缩放 source features”。这是组合已有 S1/S2 模块，不新增动态/忽略逻辑。seed `53` 上 Stage 1 RMSE 略高于 linear regression，但 5 seed mean MAE/RMSE 均优于 linear regression，报告按均值提升诚实表述。
- **[2026-08-06 · 并行审查记录]** 作者明确说明会并行审查 Sprint 2，随后可能给修改建议。本轮先推进 Sprint 3；若收到 S2 修改建议，应优先判断是否影响 Stage 1 结果，并更新 HANDOFF 和报告。
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

1. 作者准备第一份真实案例 CSV：统一频率、数值列、无缺失；同时写 `case.json` 指定 target、candidate_signals、train/test 边界。
2. 用 `python scripts/run_real_case.py cases/<case_name>/case.json` 跑出 S6 五份报告，再人工制图和判断故事是否成立。
3. 不启动 API 抓取、用户上传、dashboard 或自动清洗；抓数脚本如果要做，应作为 S6 之后的 helper，不绑死分析框架。

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
- **Sprint 2 / 审查反馈：完成。** 已补充 marginal correlation vs partial OLS coefficient、multiple-lag noise floor 两项解释，不改代码。
- **Sprint 3 / 三变量预测：完成。** `src/nestor_delta/stage1_prediction.py` 已组合 Sprint 2 权重和 Sprint 1 OLS，在 locked test split 上预测 `target`。
- **Sprint 3 / 指标报告：完成。** `reports/stage1_metrics.csv`、`reports/stage1_selected_sources.csv`、`reports/stage1_summary.md` 已保存 5 seed 指标、选源记录、均值和 min-max。
- **Sprint 3 / 验证：完成。** `.venv/bin/python -m unittest discover -s tests` 通过 7 tests；Stage 1 mean MAE/RMSE 均优于 persistence 和 Sprint 1 linear regression。
- **S3.1 / 独立门控模块：完成并验收。** `trust_gating.py` 提供可配置分段线性准入与共享信号合成；冻结的 S0-S3 实现未修改。
- **S3.1 / 可切换预测：完成并验收。** `fit_prediction_mode` 支持 `ols` 与 `trust_gated`；一键脚本同时运行并对照两种模式。
- **S3.1 / 正确性与确定性：完成并验收。** 12 tests 通过；noise 五 seed 全阻断，弱 driver 保留负方向与非零折扣准入，同 seed 复跑一致。
- **S3.1 / 数值生效证明：完成并验收。** `driver_b` unit-trust 反事实下 OLS delta 为 `0.0000000000`，门控 delta mean `0.0774200737`、range `0.0081728375-0.1567707161`，且 noise 始终阻断。
- **S3.1 / 报告与文档：完成并验收。** 四份 tracked report 与 `docs/TRUST_GATING.md` 已生成；MAE/RMSE 均报告五 seed mean 与 min-max。
- **Sprint 4 / 动态权重漂移：完成并验收。** 作者已独立复核防泄漏、五 seed 漂移追踪和 120 行窗口冻结；动态 mean MAE/RMSE 分别比静态低 `7.52%/6.38%`。
- **Sprint 5 / 忽略值与资源自适应：实现及工程验收完成。** 双轨验收已跑通；高维 stress 轨轻度压缩 downstream proxy 下降 `41.56%`、MAE loss `4.11%`，更高压力展示完整 tradeoff；待作者验收与提交。
- **Sprint 6 / 真实数据案例 Runner：框架实现完成。** 可读取作者准备的本地 CSV + config，自动输出 ranking、预测、资源 tradeoff 和 summary；等待真实案例数据输入。

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
| C6 | Sprint 3 使用 train-only top-2 source selection + weighted lagged OLS | 已决 | 组合 S1/S2，不修改权重机制；mean MAE/RMSE 小幅优于 S1 linear baseline |
| C7 | Sprint 2 `weight` 解释为 marginal signed correlation | 已决 | 不等同于 OLS partial coefficient；多 lag 取最大会产生非零 noise floor |
| C8 | S3.1 使用 OLS 前静态信任度门控 | 已决 | trust 与方向分离；`0.15/0.50` 分段线性准入；源先合成为共享关系信号，确保 OLS 不能抵消相对准入 |
| C9 | S4 使用 120 行因果滑窗重复调用 Sprint 2 静态权重 | 已决 | 新漂移数据独立冻结；train-only 选源/拟合；测试按 `t-1` 截止 prequential 更新；不含 S5 忽略逻辑 |
| C10 | S5 使用双轨验收与 downstream-only 资源 proxy | 已决 | S4 冻结数据只做 correctness regression；新增高维 stress fixture 验证资源曲线；当前仍先算全量关系，因此只声明 downstream compute/memory proxy reduction |
| C11 | S6 只做本地真实案例 runner | 已决 | 作者准备 CSV 和 config；runner 自动 ranking/selection 并输出 CSV 报告；不做 API、dashboard、上传、自动清洗或因果声明 |

---

## 给下一棒的话

> S6 框架已实现：现在可以把作者准备好的真实 CSV + config 丢给 `scripts/run_real_case.py`，输出五份报告供手动画图。下一步是准备第一份真实案例数据；不要把 S6 扩成 API 接入、用户上传或 dashboard。
