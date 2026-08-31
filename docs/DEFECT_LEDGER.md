# Nestor Delta — 缺陷台账 (Defect Ledger)

**本文件的用途。** 登记每一次被发现的真实缺陷，以及为它留下的**机械防线**。

**G-1 已关闭（2026-08-30）。** T11 完成登记、核验并推送后，治理与量具地基关闭。
从此同时生效三条收敛规则：
1. **在制品限制 = 1：** 同时只有一条轨道在跑。
2. **B 类只登记不派工：** 直到 M5 完成，不做逐条例外判断。
3. **每轮结束回答一句：** 本轮让 `docs/DEMO_MILESTONES_V1.md` §0 Demo DoD 三条中的
   哪一条更接近了？答“没有”即说明本轮属 B 类。

**唯一的纪律（不可协商）：** 每一条缺陷必须留下一个此后每次都会自动运行的检查。
只写"下次注意"不算关闭——注意力不会被继承，断言会。

本纪律不是新发明，它在项目里已经自发发生过两次（14% 高报事故 → Q6 口径测试；`n=12` → Q8）。
本文件把它命名为机制，从此显式执行。

**与其他文档的关系。** 本文件只登记缺陷与防线。历史验收记录仍在
`docs/DEMO_MILESTONES_V1.md` 各附录，修复里程碑仍在 `docs/REMEDIATION_Q_V1.md`，
边界仍在 `BLUEPRINT.md` 与 `HANDOFF.md`。本文件**不复述**它们，只引用。

**发现分级协议（T9 起，三方共用）。** 每个新发现必须同时标注处置级别与收敛分类：
- **P — 直接通过：** 明显无问题、无隐患。
- **W — 登记后通过：** 可能有问题，但几乎无隐患；写入台账后放行，并事后告知负责人。
- **H — 卡住不通过：** 可能有问题且可能导致后续故障；写入台账并立即告知，不得自行放行。
- **A：** `docs/DEMO_MILESTONES_V1.md` §0 Demo DoD 三条的必要条件。
- **B：** 其他一切，无论多正确。**B 类只登记，不派发工作，直到 M5 完成**；不做逐条例外判断。
- **H 级不得归入 B 类。** 要么降级为 W，并写明为何在 M5 前不会造成运行时故障；
  要么提升为 A，并给出明确解冻时刻。

**编号约定。**
- T0 / T1 / T2 = M4-A 准入条件（工作树、测试收集、`REPRODUCIBILITY.md` 修正）。
- T3 = M4-B 的一项提前完成（Report narrative 措辞），避免 M4-B 重复做同一件事。
- T5 / T6 / T7 / T8 / T9 / T10 / T11 = G-1：治理与量具地基，独立于 M 系列与 Q 系列，
  排在后续实现轨道之前，不计入 M4-A 的 DoD。

**M4-A accepted（2026-08-30）。** 负责人正式确认：P0 顺序为运行状态 → 是否通过 gate →
selected/rejected → 方向/lag/强度 → gate reasons；`ok` 沿用 T3 已落地的 candidate/evidence-gate
措辞；`baseline_only` 是分析成功且 baseline retained；configuration、snapshot provenance 和版本
元数据默认 P2，但 `pipeline_version` 提升为 P1 context bar；10 个 view id 是记录范围，M3 四状态
仍是主验收范围，二者不得互相删减。M4-B 自本确认起成为唯一在制轨道。

**T9 停止记录与 T10 处置 — W-5 保持 H / A。** 2026-08-30 通过正常上传流程实测连续月度 CSV：
`lag_window=3`、12 期数据先通过 audit（HTTP 200，`ok_to_analyze`），随后 analyze
穿透到 Q8 的空 trajectory 分支并返回 HTTP 422、`validation_error`、
`error.code=invalid_input`、`trajectory must contain at least one point`；13 期对照组 audit
与 analyze 均为 HTTP 200，分析结果为 `baseline_only`。这证明 Q8 对陌生人短 CSV 是真实可达路径，
不是由现有样本量验证提前拦截。**影响：** Demo DoD 第 3 条的上传边界可能把内部 rolling
失效暴露成输入错误，不能按 W 放行。**负责人裁决：** 不破例修 Q8；Q8 保持登记未做。
H / A 的当时处置是由 M4-B/M4-C 建立用户可读的输入边界，并把短样本纳入 CSV 人工验收。
**T13 已取代该实施路线：** 不再拒绝短样本，而是修正滚动进入条件并显式警告 stability 未评估；
下文 T13 记录为当前裁决。

**历史归属。** 附录 B.4 已命名过一类缺陷：**「读起来像权威、实际上没接线」**
（`effect.score` / `pipeline_version` / `noise_floor` / `ledger.durable`）。
下面的 D1–D7 是同一类的第二批，出现在 M4-A 核对与 G-1 阶段。

---

## 缺陷索引

| ID | 一句话 | 类别 | 级别 | A/B | 防线 | 状态 |
|---|---|---|---|---|---|---|
| D1 | 测试全绿可能意味着关键测试根本没被收集 | 量具失效 | H | A | G1 | 已关闭；G1 正、负控制通过 |
| D2 | 文档把未提交、未经审核的能力当作既成事实 | 文档失真 | W | B | G2 | 部分关闭；残余仅为 review 可能漏掉散文声称，无运行时故障 |
| D3 | 上屏文案在后端且在版本哈希内，被误判为前端小改 | 归因失效 | H | A | G3 | 已关闭；G3 正、负控制通过 |
| D4 | 同一句文案存在于四处，改动只准备改一处 | 同步失效 | W | A | G4 | 部分关闭；仓库内实现、mock 与 W0 示例已钉合，外部契约副本仍依赖 push 后人工同步 |
| D5 | 验收指令的形状让未跟踪文件和无关测试静默混入结论 | 验收盲区 | W | B | G5 | 部分关闭；无自动断言，由指令模板承载 |
| D6 | 防线只验正控制，未验负控制；G2 扩范围后实测假阳性 35/35 | 量具校准失效 | H | A | G6 | 已关闭；G1–G4 与 G8 均有正、负控制记录 |
| D7 | 仓库无 CI；防线与 ground-truth 只在人工运行时执行 | 执行盲区 | W | B | G7 | 已登记；M5 后实施 |

## T9–T11 分级登记

| ID | 内容 | 级别 | A/B | 影响 | 解冻时刻 |
|---|---|---|---|---|---|
| W-1 | M4-A 第 2 条为追认：`ok` 措辞已在 T3 落地，确认发生在实施之后 | W | A | 决策与实施顺序倒置，可能诱发重复实施，但现有措辞正确 | 登记即放行；M4-B 将 T3 标为提前完成，不回滚、不重复 |
| W-2 | 状态库存 10 vs 4 并存：10 是记录范围，4 是 M3 验收范围，二者不得互相删减 | W | A | 把任一清单误当全集会缩窄现有错误处理或扩大 M3 验收口径 | M4-C 同时保留 10 状态记录与 4 状态验收口径 |
| W-3 | 项目副本曾与仓库 narrative 分叉 | W | A | 外部阅读副本曾传播旧叙事 | **已关闭（2026-08-30）**：两份契约副本已同步，过期 mock 项目副本已删除 |
| W-4 | Q3 部署竞态未修 | W | A | 旧代码可能顶着新 commit 号对外服务 | Q3.1 修复前，每次部署必须执行 `HANDOFF.md` Deploy sequence 的四步人工门槛；漏一次即升 H |
| W-5 | Q8 短 CSV 路径真实可达；T13 将最小滚动进入条件提为 A 类 | H | A | audit 放行后 analyze 曾返回内部 422，阻断陌生人上传路径 | **已关闭（2026-08-31）**：夹缝退回合法非滚动结果并发布 `stability_not_evaluated` warning；其余 Q8 仍为 B 类 |
| W-6 | I.1 过差分与 I.3 lag profile 必须进入 M5 已知限制；Eurostat 对应表述为“尚未被公平测试”，不是“无关” | W | A | 错误表述会把方法限制升级成数据结论 | M5 已知限制清单逐项收录并审阅措辞 |
| W-7 | D7：无 CI，四条防线与 26 条 ground-truth 只在有人手动运行时执行 | W | B | 自动防线没有自动执行载体 | M5 完成后实施 G7；此前 B 类不派发 |
| H-1 | 公开 URL 仍运行旧叙事版本，API `c6afbb5` / web `01a9e6c` 尚未部署 T3 措辞 | H | A | 当前公开页面继续过度声称 relation reliability | 两层部署并按完整 Deploy sequence 验证前不得外发 URL |
| H-6 | audit 与 analyze 接受集曾不一致：12 期为 `200 ok_to_analyze` 后又返回 `422 invalid_input` | H | A | audit 的“可分析”结论失去意义 | **已关闭（2026-08-31）**：G8 覆盖两组 lag 的夹缝与边界，audit 放行后 analyze 不再返回 422 |
| H-7 | 422 文案 `trajectory must contain at least one point` 曾暴露内部实现细节 | H | A | 陌生人无法据此知道应修改样本长度 | **已关闭（2026-08-31）**：对应合法短样本不再产生该 422；Report 改为可读稳定性未评估 warning |
| W-12 | H-5 Analyst table 的列结构已修正，但关闭时没有留下守卫 | W | A | `sample support` 或 diagnostic 排序可静默回退 | **已关闭**：生产表格 helper 与双控制钉住 `sample support`，且 `noise floor (diagnostic)` 必须最右 |
| W-13 | G2 豁免标记只在被引用路径之后生效 | W | B | 把 `(historical)` 写在引用之前不会豁免，若约定不明会造成误用 | 规则写入 G2 覆盖范围；机械扩展 M5 后解冻 |
| W-14 | lifecycle 算法改动的 S-GT before/after 只报 selection 状态，未报数值 | W | A | 状态相同仍可能掩盖数值漂移，算法验收归因不完整 | **已关闭（2026-08-31）**：T13 补报 S-GT-1 `effect.score` 与双方 `selected_count` 数值，并扩充 G6 规则 |
| W-15 | `baseline_only` 可能混淆“没有关系通过门槛”与“样本太短、未评估 stability” | W | A | 用户可能把未执行的稳定性检查误读为完整证据拒绝 | **部分关闭**：Report warning 显式说明 stability 未评估；M4-C CSV 验收检查完整区分与视觉层级 |
| W-16 | 冻结 Q6 `n=11` 负控制的 Report 新增 `stability_not_evaluated` warning | W | A | selection 未变，但冻结控制的可见输出发生加法变化 | **已登记并接受（2026-08-31）**：Q6 原断言仍钉住 `baseline_only`、零选择、无 effective window/trajectory；G8 `L=3,n=11` 另行钉住新增 warning |
| H.4 lifecycle | 证据不足时仍输出 `birth`，且现有测试把该行为钉住 | H | A | “新生、有希望”强于现有 stability 证据，构成可见的过度声称 | **已关闭**：Report 新增 `insufficient_evidence`，算法级正、负控制与 selection before/after 通过 |
| H-8 | `n_min(3)=13` 与冻结 Q6 前滚动负控制 `n=11` 冲突 | H | A | 把公式用作输入拒绝会破坏已接受的合法非滚动区间 | **已关闭（2026-08-31）**：公式改作滚动进入条件；`n=11/12` 均合法非滚动，fixture 未修改 |

**G8（已实现）。** `tests/test_audit_analyze_consistency.py` 断言
`audit == ok_to_analyze` 蕴含 `analyze != 422`。正控制：在内存中恢复旧谓词
`n > L+8`，`L=3,n=12` 复现 audit 200 / analyze 422，G8 拒绝，命中 1/1。
负控制：未破坏实现下覆盖 `L=3,n=11/12/13/14` 与 `L=6,n=16/19`，六例均为
audit 200 / analyze 200，假阳性 0/6；非滚动三例携带 `stability_not_evaluated`，
滚动三例不携带该 warning。

### T11 负责人裁决

1. **H.4 / lifecycle 采纳路径 A。** 后端新增 `insufficient_evidence` 状态，不在前端根据
   stability 与 gate 阈值推导或抑制 lifecycle。实施归 M4-B，属于算法层改动，必须独立提交、
   独立移动 `pipeline_version`，并按 M0 规则记录 S-GT-1 与 S-GT-2 的 before/after 同向验证。
2. **W-5 / H-6 / H-7 采纳机制边界** `n_min(L) = max(L+9, 2L+7)`，其中 `L` 为
   `lag_window`。边界在 audit 的 `_audit_blocks()` 判定，使 audit 通过必然意味着 analyze
   不会因该短样本路径返回 422；实施、可读文案和 G8 均归 M4-B，CSV 人工验收归 M4-C。
   **本条已被 T13 裁决取代，不再作为实施路线。**

### T13 负责人裁决与关闭记录

负责人裁决不新增输入下限：同一公式改作滚动 lifecycle 的进入条件，且 Q8 最小修复仅限
该条件。设 `n` 为训练观测数、`L` 为 `lag_window`：`n <= L+8` 保持既有非滚动行为；
`L+8 < n < 2L+7` 是原空 trajectory 夹缝，也退回非滚动；仅
`n >= max(L+9, 2L+7)` 进入滚动。两段非滚动区间返回合法 Report，并携带
`stability_not_evaluated` warning；不改窗口公式、门控阈值或 fixture 数据。

算法级 before/after 数值：S-GT-1 `effect.score` 为
`0.5844220533473201 -> 0.5844220533473201`，`selected_count` 为 `1 -> 1`；
S-GT-2 `selected_count` 为 `0 -> 0`（其 top relation `effect.score` 同为
`0.11987106578827578 -> 0.11987106578827578`）。selection 无变化。
`pipeline_version` 单次移动：`s10.sha256.ab759b2231a4 -> s10.sha256.7fed154a44bf`，
实现提交 `70e858f`。

### M4-B accepted（2026-08-31）

T14 逐项对照 M4-B 启动指令后接受本阶段：批次 0 的计数 SHA、W-3、H/B 规则与三项重分类、
Evidence Gate 配置守卫、W0 narrative parity 均闭合；原“最小样本输入拒绝”版本移动由 T13
滚动进入条件方案正式取代；lifecycle 路径 A 独立完成；P0 顺序、13 词 gate 解释、
`baseline_only` 正面陈述、P1 `pipeline_version` context bar 与 W-12 守卫均完成。
W-16 记录 Q6 冻结控制新增 warning 的加法变化，原 selection/branch 断言仍有效，新增 warning
由 G8 单独钉住。接受基线为 214 tests、`pipeline_version=s10.sha256.7fed154a44bf`。

### H.4 / lifecycle 事实补记

审核方在独立 clone 核实：`tests/test_s9_lifecycle.py:41` 的
`test_insufficient_evidence_keeps_s9_fields_null` 在同时断言 `stability`、`uncertainty`、
`selected` 均为 `None` 时，又断言 `lifecycle.state == "birth"`。因此过度声称不只是实现现状；
一个名为“证据不足”的测试正在固定“新生、有希望”的标签。该断言必须在 M4-B 路径 A 中
随新状态一起改写，不得把现状测试当成产品定义。

**M4-B lifecycle 关闭记录（2026-08-31）。** 路径 A 已在后端 Report 语义实施：`stability` 为 null
或低于有效 `min_stability` 时，lifecycle 为 `insufficient_evidence`；该状态不属于 `ALIVE`。
正控制：点数不足与 stability=0.40 两例均变为新状态。负控制：S-GT-5 五个构造 profile
逐一命中新的严格预期，假阳性 0/5；完整套件 200/200 通过。M0 双控制 selection before/after：
S-GT-1 均为 `ok`、selected_count=1、`true_driver`；S-GT-2 均为 `baseline_only`、
selected_count=0。`pipeline_version` 为 `s10.sha256.fbcf60d3506d` →
`s10.sha256.ab759b2231a4`；未改动 Evidence Gate 阈值。

---

## D1 — 绿色的测试结果不能证明测试跑过

**现象。** `pyproject.toml` 的 `[tool.pytest.ini_options]` 中
`pythonpath = ["src", "tests/ground_truth"]` 与 `testpaths = ["tests"]` 两行，
决定 bare `pytest` 收集 189 条还是漏掉 26 条 ground-truth 测试。
这两行被修改后，测试**不会报错，只会变少**。

**后果。** 那 26 条是唯一检查「检测器到底检不检测得出来」的测试（见 A.2 与 K.3-1）。
它们缺席时，套件仍然全绿。本项目最贵的一次事故正是在「132 条全绿」的状态下发生的。
若批量实验装置建立在这样一棵树上，一千次实验结果全部无效，且没有任何信号提示这一点。

**根因（修正一个直觉）。** 不是算法自查不严谨——ground-truth fixture 体系是这个项目
最强的部分。**缺的是"自查是否运行过"的自查。** 量具很好，但没有东西检查量具在不在。

**G1 防线 — 套件完整性自检。** 新增 `tests/test_suite_integrity.py`：
1. 断言 `pyproject.toml` 文本中同时存在 `pythonpath` 的两个条目与 `testpaths = ["tests"]`
   （直接读文件文本，不引入 toml 依赖，兼容 py3.9）。
2. 断言至少一个已知 ground-truth 测试函数可被导入（例如
   `test_sgt2b_false_positive_rate_across_seeds`），缺席即失败。
3. 断言收集总数不低于登记下限（下限值写在本文件末尾的"计数基线"一节，唯一来源）。

**关闭条件。** 手工把 `pythonpath` 改坏一次，确认 G1 变红；改回，确认变绿。
**没有做过这次翻转验证，D1 不算关闭**（沿用 Q4 的验收纪律）。

**控制记录。** 正控制：临时移除 `tests/ground_truth` 后，G1 变红。负控制：
2026-08-30 在未破坏配置的工作树上运行 `tests/test_suite_integrity.py`，3/3 通过，
假阳性 0/3。

---

## D2 — 文档把未提交、未经审核的能力当作既成事实

**现象。** 一份未提交的 `REPRODUCIBILITY.md` 改动新增了 algorithm experiment runner 的说明。
M4-A 收尾复核时发现，本地确实存在四个相关文件，但它们全是未跟踪、未经审核的 G0 工作。
原始路径为：`docs/ALGORITHM_EXPERIMENTS.md` (historical)、
`docs/algorithm_seed_sets_v1.json` (historical)、
`scripts/run_algorithm_experiment.py` (historical)、
`tests/test_algorithm_experiment_log.py` (historical)。
`stat -f "%Sm  %N" -t "%F %T"` 显示四者时间戳均为 `2026-08-29 18:04:11`，早于本轮
T5 执行；它们不是 T5 新建的，但也不是已提交仓库事实。
证据副本保存在 `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/README.md`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/ALGORITHM_EXPERIMENTS.md`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/algorithm_seed_sets_v1.json`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/run_algorithm_experiment.py`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/test_algorithm_experiment_log.py`。

**后果。** `REPRODUCIBILITY.md` 的全部价值就是"里面写的命令能跑"。
一旦提交，权威文档承诺了一个未进入版本控制、未被本阶段接受的能力，而 CI 只能验 schema，验不了散文。
三周后文档就是唯一的记忆。这是 K.2 的复发：**首次出现在治理文档而非代码里的装饰性严谨。**

**根因。** 一段描述未跟踪本地工作之物的文字，读起来和描述已提交能力的文字完全一样。
只审 diff 永远发现不了——必须做一次跨文件核对（文档说的东西，是否已经进入受审版本控制）。
另一个助推因素：该改动被总结为一句"增加 runner 说明"，**听起来是进展**，因此不会被质疑。

**写作规则（对所有向本仓库写 md 的人与 AI）。**
1. **能力陈述必须是已成立的事实。** 现在时描述 = 承诺它此刻存在且可用。
2. **计划必须显式标注**：段落标题或首句含 `Planned — not yet implemented (<里程碑>)`，
   且**段内不得出现可执行命令、脚本路径或文件名**。
3. **文档中出现的每一条命令，必须已在文档自己声明的最低环境下跑通过**（Q1 教训）。
4. 用专业陈述替代承诺式表述：写"在这些冻结条件下 X 成立"，不写"X 已被证明/已验证/已保证"。

**G2 防线 — 文档引用体检。** 新增 `tests/test_docs_claims.py`：
扫描 `.md`，提取反引号中含 `/` 的路径形引用，扩展名限 `.py` / `.md` / `.json` / `.sh` /
`.jsonl`，断言每一个都在磁盘上存在。标注了 `Planned` 的段落跳过检查。
最终豁免规则：不整本豁免任何能力文档或台账；豁免按**单条引用**生效，不按整行生效。
只有匹配项闭合反引号后 40 个字符内、同一行且下一条路径引用之前显式出现 `(historical)` 或
`(quarantined)`，才跳过该引用，因为这些标记记录的是原始路径或隔离状态，而非当前能力路径。
证据目录豁免钉死为四个文件名：
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/ALGORITHM_EXPERIMENTS.md`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/algorithm_seed_sets_v1.json`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/run_algorithm_experiment.py`、
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/test_algorithm_experiment_log.py`。
它们是未经改写的证据文件，T6 明确要求保持原样。

**覆盖范围。** G2 检查含 `/` 的路径形引用，扩展名为 `.py` / `.md` / `.json` / `.sh` /
`.jsonl`。G2 不检查：裸文件名引用（无 `/`）、含 `*` 的通配模式、非 ASCII 文件名、
代码块内未被反引号包裹的示例路径。裸文件名不检查是有意设计：本仓库文档中绝大多数裸文件名是
"提及"而非"引用"，T7 实测纳入后 35/35 均为假阳性。豁免标记的语法约定是**先引用、
后标记**：扫描窗口从匹配项的闭合反引号之后开始，因此把 `(historical)` 写在
`docs/DEFECT_LEDGER.md` 之前不会豁免该引用；应把标记写在引用之后。

**量化边界。** 审核方在独立 `origin/main` clone 上实测：反引号内且会被 G2 检查的路径形引用
约 55 条；路径形但落在视野外的约 39 条（约 41%），主要是 `reports/`、`cases/`、`data/`
等未纳入前缀，以及未加反引号的写法。将来若扩大范围，必须显式排除运行时产物路径；例如
`data/relationship_ledger.json` 被三处文档提及，但干净 clone 中不存在，因为它是运行时生成输出。
不先区分仓库事实与运行时产物，扩大范围会立即制造新一批假阳性。

**G0 文件处置。** 上述四个未跟踪 G0 文件已从临时目录移入
`docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/`，仅作为参考材料和缺陷证据保留，不作为 G0 交付。
其中 `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/algorithm_seed_sets_v1.json` 作为 holdout 种子集已作废：它缺少生成 provenance，
无法证明从未参与调参；G0 正式立项时必须重新生成，并在实验日志第一行记录生成参数、时间、
当时的 `pipeline_version`、以及生成前尚未运行任何实验的声明。

**残余风险。** G2 只能发现"路径不存在"。如果散文写成"Delta ships an experiment runner"但不写路径，
或者路径指向未跟踪文件，G2 不会失败。因此 D2 只能标为**部分关闭**：路径引用这一半已有机械检查；
能力陈述与未跟踪工作被当作事实这一半仍靠写作规则和 review。

**关闭条件。** 在任意 md 中写入一个不存在的脚本路径，确认 G2 变红。

**控制记录。** 正控制：临时写入缺失脚本路径后，G2 变红。负控制：
2026-08-30 在未破坏引用的工作树上运行 `tests/test_docs_claims.py`，1/1 通过；
实际检查路径形引用 100 条，假阳性 0/100。

**T10 作用域控制。** 正控制：在同一行先放未标记的缺失路径，再放带 `(historical)` 的第二条
路径；G2 只报告第一条，证明第二条的豁免没有向前覆盖整行。删除探针后负控制 1/1 通过；
当前工作树实际检查 105 条路径形引用，假阳性 0/105。

---

## D3 — 上屏文案在后端，且在版本哈希内

**现象。** 页面 headline 的真实来源是
`src/nestor_delta_service/adapter.py::_narrative()`（`:1022` / `:1032`）。
`src/nestor_delta_web/render_logic.py:130` 的同义字符串是 fallback，
在后端提供 narrative 时**永不执行**。初次核对只 grep 到后者，据此判为"前端文案微调"。

**后果两层。**
1. **措辞**：`reliable relation selected` 直接断言可靠性，强于产品实际主张
   （BLUEPRINT §6.1 / Q2：只主张"在这些冻结条件下通过了证据门控"）。
   页面最显眼的一行声称得比证据强，是本产品唯一不能犯的方向。
2. **归因**：`adapter.py` 在 `pipeline_version` 哈希内，改它必然移动版本号。
   若与算法改动混入同一次提交，版本号移动了一格却说不清是文案还是算法造成的——
   而版本号存在的唯一理由就是归因（K.3-3）。

**根因。** 两条：
- 搜字符串找到的是"这句话出现在哪"，不是"这句话从哪来"。判定文案归属必须追数据流。
- **同一句面向用户的文案在两层各存一份**，本身就是漂移的充分条件。

**G3 防线 — 三件，缺一不可。**
1. **哈希范围显式化。** 新增 `tests/test_version_scope.py`，断言
   `versioning.pipeline_version()` 实际遍历的路径集合等于一份提交在测试中的字面清单。
   任何文件进出哈希范围都必须是一次自觉的、被 review 的改动，而不是 glob 的副作用。
2. **一次提交只允许一个版本移动原因。** 任何触碰哈希内文件的提交，
   message 必须包含 `pipeline_version: <before> -> <after>` 与一句移动原因。
   文案改动与算法改动不得合并提交。
3. **消除并行文案。** 前端 fallback 不得复述后端措辞。
   改为中性占位（或在 narrative 缺失时按 `malformed` 处理），使"哪一层拥有文案"只有一个答案。

**关闭条件。** G3-1 变红一次（临时增删 `src/nestor_delta/` 下一个 .py 文件验证）；
前端 fallback 已不含任何产品主张性措辞。

**控制记录。** 正控制：临时新增 `src/nestor_delta/_version_scope_probe.py` (historical) 后，G3 变红。
负控制：2026-08-30 在未改变哈希范围的工作树上运行 `tests/test_version_scope.py`，1/1 通过，
假阳性 0/1。

---

## D4 — 同一事实存在于四处，改动只准备改一处

**现象。** `"reliable relation"` 出现在：
`adapter.py:1022,1032`（实现）、`docs/mock_reports_v1.json:202,321`（四状态验收 fixture）、
`docs/WEBSITE_CONTRACT_W0.md:147`（契约示例）。
后两个文件另有项目文档副本，按 K.1 必须与仓库副本逐字节一致。
核对时该改动被判定为"两行"。

**附带证据：漂移已经发生。** `WEBSITE_CONTRACT_W0.md:147` 用全角破折号 `—`，
实现与 fixture 用半角 `-`。无人改动过它——这是上一次同类改动留下的残留。
**这不是假想风险，是已经在场的不一致。**

M4-A 复核又发现更严重的副本漂移：外部项目文档副本 `claude/mock_reports_v1.json`
曾保留 `"1 reliable relation · Delta active."`，而仓库 mock 当时是
`"1 reliable relation selected."`。这说明 K.1 要求的逐字节同步至少对
`mock_reports_v1.json` 没有实际运行过。

**根因。** 规模判断一旦下了，就不会再回去验证规模。
"两行改动"这个结论形成后，注意力立刻转向了更有趣的问题（何时提交、如何归因），
而没有人再问一句：**这个事实还存在于别的什么地方？**

**G4 防线。**
1. **钉合断言。** 新增 `tests/test_narrative_parity.py`：断言
   `docs/mock_reports_v1.json` 中每个 headline 等于 `_narrative()` 对相同 outcome 的输出。
   W0 示例现由同一测试钉住；项目契约副本仍按 K.1 在 push 后人工同步。
2. **多处事实登记表**（本文件下一节）。任何在两处以上出现的字面量，
   **要么合并为一处，要么加一条断言把它们钉在一起**，并登记在表中。
3. **项目副本同步是提交清单的一部分**，不是事后想起来的事。
   `mock_reports_v1.json` 的外部项目副本已删除，仓库文件是唯一权威；
   `WEBSITE_CONTRACT_W0.md` / `API_BOUNDARY_V1.md` 项目副本保留，并已在 T11 push 后同步。

**关闭条件。** 手工把 `mock_reports_v1.json` 的一个 headline 改错，确认 G4-1 变红。

**控制记录。** 正控制：临时改错 `docs/mock_reports_v1.json` 中一个 headline 后，G4 变红；
M4-B 批次 0 又以 in-memory 漂移证明 W0 示例守卫变红。负控制：2026-08-30 在未破坏 narrative
的工作树上运行 `tests/test_narrative_parity.py`，实现、mock 与 W0 示例均通过，假阳性 0/3。

---

## 多处事实登记表

同一事实必须出现在多个位置时，在此登记，并注明由哪条断言钉合。

| 事实 | 出现位置 | 钉合机制 | 状态 |
|---|---|---|---|
| Report narrative headline 文案 | `adapter.py::_narrative`；`docs/mock_reports_v1.json`；`docs/WEBSITE_CONTRACT_W0.md` §2 示例；不再存在独立项目 fixture 副本 | G4-1 钉住仓库内实现、mock 与 W0；契约副本按 K.1 人工同步 | 生效中 |
| evidence gate 阈值 | `src/nestor_delta/evidence_gate.py` 默认值；`adapter.py::EVIDENCE_GATE_CONFIG` | `tests/test_evidence_gate_config.py` 逐项比较四个默认值；只读，不改阈值 | 生效中 |
| W0 契约 | `docs/WEBSITE_CONTRACT_W0.md`；项目文档副本 | 人工逐字节同步（K.1）；同步动作必须列入 push 后清单 | 生效中 |
| API 契约 | `docs/API_BOUNDARY_V1.md`；项目文档副本 | 人工逐字节同步（K.1）；同步动作必须列入 push 后清单 | 生效中 |

**Evidence Gate 配置控制记录。** 正控制：向内存副本注入错误的 `min_stability`，一致性守卫拒绝；
负控制：读取当前 core 默认值与 adapter 配置，四项逐一相等，假阳性 0/1。整个控制过程未修改
`src/nestor_delta/evidence_gate.py` 或 `EVIDENCE_GATE_CONFIG` 的任何取值。

---

## 两条纳入验收的常设提问

从此对每一个新字段、新文案、新保证问这两句，答案写进验收记录：

1. **「这个东西如果错了，会有什么变红吗？」** 答案是"不会"，它就是装饰（B.4 / K.5）。
2. **「这个事实还存在于别的什么地方？」** 答案不是"只有这里"，就登记进上表并加钉合断言（D4）。

---

## D5 — 验收指令的形状决定了报告的形状

**现象。** T0 要求"输出三段 `git diff` 原文"，于是报告精确输出了三段 diff；未跟踪文件没有
diff，`??` 行静默缺席。T5 又要求贴出测试结果，于是报告给出 bare `pytest` 总数 `200`，
但其中 5 条来自未跟踪的 G0 文件 `tests/test_algorithm_experiment_log.py` (historical)，不属于 T5。

**后果。** T5 实际新增测试是 6 条，`189 + 6 = 195`。把 200 写成 D1 的新计数基线，会让
G1 依赖未接受的 G0 文件。等 G0 文件被移走或推迟，套件从 200 回到 195，G1 会无理由变红。

**根因。** 验收指令只要求了局部证据：diff 原文而非完整 `git status --short`，总测试数而非
"本任务新增 N 条 + 总数"的可核对算术。报告满足了字面要求，却漏掉了工作树规模和任务归属。

**G5 防线 — 指令形状规则。**
1. 凡要求报告工作树状态，必须写"贴出 `git status --short` 完整原文（含 `??` 行）"。
2. 凡报告测试计数，必须同时给出"本任务新增 N 条"与"总数"，且两者相加可核对。
3. 若工作树中存在不属于当前任务的未跟踪测试，当前任务的计数基线必须排除它们。

**关闭状态。** 本条管的是下一份指令如何写，不新增代码；
**无自动断言，由指令模板承载**。当前先登记为验收纪律，不能和 D1-D4 的机械防线等价看待。

---

## D6 — 防线只验正控制，未验负控制

**现象。** G1-G4 上线时都做了"故意弄坏 → 变红"的翻转验证，但没有同步记录
"未改动的干净树 → 变绿"。T7 把 G2 扩大到裸文件名和更宽路径后，实测出现 35/35 假阳性：
被点名的 35 条引用经独立核查均不是真缺陷。

**后果。** 一个总是乱红的检查器比没有检查器更糟：人会学会忽略它，等真正缺陷出现时也会被忽略。
这和分析算法里防止假阳性的原则相同：只证明敏感性不够，还必须证明特异性。

**根因。** 验收只要求了正控制，缺少负控制记录。于是防线可以在"能抓坏例子"的同时，
对正常文档大量误报，仍被登记为关闭。

**G6 规则 — 每条防线必须双控制关闭。** 从 G-1 起，任何新防线只有同时通过两类控制才算关闭：
1. 正控制：故意弄坏 → 变红。
2. 负控制：未改动的干净树 → 变绿，且假阳性数为 0。

两个结果都必须写入台账；负控制必须写明"假阳性 0/N"。
算法层改动的 before/after 还必须给出可比较的数值，不得只报告 outcome、selection 状态或
“未变化”；至少记录任务指定的 score/count，并明确写出前后两个值。

**控制记录。** 2026-08-30 补跑 G1-G4 负控制：G1 假阳性 0/3；G2 假阳性 0/100；
G3 假阳性 0/1；G4 假阳性 0/2。对应正控制已在 D1-D4 条目登记。
2026-08-31 G8 正控制命中 1/1，负控制假阳性 0/6；详见 T13 记录。

**关闭条件。** D1-D4 均已补齐正控制和负控制记录；未来新增防线若缺任一控制，不得标为关闭。

---

## D7 — 防线没有自动执行载体

**现象。** 仓库没有 `.github/` 或其他 CI workflow；G1-G4 与 26 条 ground-truth 测试只在
有人主动运行完整 pytest 套件时执行。

**影响。** 机械断言已经存在，但没有远端自动触发机制。漏跑测试时，它们无法阻止错误进入后续提交。

**G7（Planned — not yet implemented, M5 后）。** 为完整测试套件建立自动执行载体，并按 G6
补正、负控制。本项为 W / B；依照收敛规则，在 M5 完成前只登记，不派发、不实现。

**解冻时刻。** M5 完成后立项 G7。

---

## G-1 关闭时未决项清单

下表是进入 M4-B 前的完整交接库存。“解冻”表示允许开始实施，不表示自动接受；B 类统一在
M5 完成后解冻。相同根因的缺陷、防线和处置项合并在一行时，ID 全部保留。

### A 类：Demo DoD 必要条件

| 项目 | 级别 | A/B | 未决内容 | 归属里程碑 | 解冻时刻 |
|---|---|---|---|---|---|
| W-2 | W | A | 10 状态记录范围与 4 状态 M3 验收范围必须并存 | M4-C | M4-B 完成后进入 M4-C 时 |
| W-4 | W | A | Q3 部署竞态仍需人工 Deploy sequence 门槛 | 每次部署验收 | Q3.1 实施前持续生效 |
| W-6 | W | A | I.1 / I.3 限制必须进入对外已知限制，不能升级成数据结论 | M5 | M5 已知限制整理时 |
| H-1 | H | A | 线上两层仍是旧叙事，公开 URL 禁发 | M4-B 后部署验收 | M4-B 两次版本移动完成后；须完整部署验证 |
| W-15 | W | A | warning 已区分 stability 未评估，但短 CSV 的完整文案与视觉层级尚未人工验收 | M4-C | M4-C CSV 八项验收时 |

### B 类：统一冻结

| 项目 | 级别 | A/B | 未决内容 | 归属里程碑 | 解冻时刻 |
|---|---|---|---|---|---|
| D2 / G2 残余 | W | B | 散文能力声明与“未跟踪但存在”的路径仍只能靠 review 识别；无运行时故障 | 治理 backlog | M5 完成后 |
| D5 / G5 | W | B | 指令形状规则没有自动断言 | 治理 backlog | M5 完成后 |
| D7 / G7 / W-7 | W | B | 仓库没有 CI 自动执行载体 | G7 | M5 完成后 |
| W-13 | W | B | G2 的“标记必须在引用之后”仅有文档约定 | G2 backlog | M5 完成后 |
| G0 | W | B | 验证地基及隔离草稿的重新设计/验收 | G0 | M5 完成后；作废种子不得复用 |
| 参数化生成器 | W | B | 机制参数化的数据生成能力尚未立项 | 后置 backlog | M5 完成后 |
| C1 | W | B | 算法实现轨道冻结 | C1 | M5 完成后 |
| C2 | W | B | 算法实现轨道冻结 | C2 | M5 完成后 |
| C3 | W | B | 算法实现轨道冻结 | C3 | M5 完成后 |
| V1 | W | B | V1 验证轨道冻结 | V1-core | M5 完成后 |
| Q3.1 | W | B | deploy-script 竞态修复；当前由 W-4 人工门槛托底 | Q3.1 | M5 完成后 |
| Q5 | W | B | 轻量 invite gate | Q5 | M5 完成后 |
| Q7 | W | B | live intake 的冻结快照路径 | Q7 | M5 完成后 |
| Q8（剩余范围） | W | B | T13 只完成滚动进入条件这一项最小 A 类修复；Q8 其余算法改造不展开 | Q8 | M5 完成后 |
| I.1 | W | B | 过差分诊断实现；M5 前只保留 W-6 的诚实限制声明 | 后置算法 backlog | M5 完成后 |
| I.3 | W | B | lag profile 第三轴实现；M5 前只保留 W-6 的诚实限制声明 | 后置算法 backlog | M5 完成后 |

**阻碍核验。** 当前不存在 H 级且无归属的事项。M4-A 与 M4-B 已 accepted；T13 已关闭 H-8、W-5、
H-6、H-7 与 G8。剩余 A 类事项均有明确归属；Q8 除本次单一进入
条件外的范围继续按 B 类冻结。fixture 未修改，也没有新增输入拒绝或豁免。

---

## 计数基线（G1-3 的唯一来源）

| 日期 | commit | bare `pytest` 收集数 | 备注 |
|---|---|---|---|
| 2026-08-29 | `1ff9863` | 189 | Q6 rolling negative control 之后 |
| 2026-08-30 | `6eb4c3f` | 195 | T11 G-1 closure；正式基线，工作树无未跟踪测试 |
| 2026-08-30 | `84ca1b5` | 199 | M4-B 批次 0；新增 Evidence Gate 配置与 W0 narrative 正、负控制 |
| 2026-08-31 | `f6e6681` | 200 | M4-B lifecycle 路径 A；新增低稳定度严格控制，selection 双控制不变 |
| 2026-08-31 | `e200a82` | 206 | M4-B 呈现层；新增 P0/P1 层级与 Analyst table 双控制 |
| 2026-08-31 | `70e858f` | 214 | T13 滚动进入条件与 warning；新增 G8 7 条及结构化 warning 渲染 1 条 |
| 2026-08-31 | `3076df0` | 214 | T14 M4-B accepted；W-16 登记，无新增测试 |

新增测试时同步更新本表；**G1-3 只读本表，不在测试里硬编码第二份数字。**

---

## 变更记录

- 2026-08-29 建档。登记 D1–D4，均在 M4-A 核对阶段发现，防线 G1–G4 待实现。
- 2026-08-30 T5 复核修正：四个 G0 文件确认为早已存在的未跟踪文件，D2 改为"未提交能力被当作既成事实"并降为部分关闭；四个 G0 文件移出工作树，仅作为参考材料保留，holdout 种子集作废；T5 计数基线在移出 G0 文件后正式修正为 195；G4-1 仅钉住仓库内实现与 mock，W0 示例和项目副本同步仍为人工，状态为部分生效；新增 D5，并标注无自动断言。
- 2026-08-30 版本记录：提交 `0f02df6` 在哈希内 `adapter.py` 同时完成 Report narrative
  措辞变更与 `_narrative()` 哈希范围说明注释，记录为 `s10.sha256.3665b88553ad` →
  `s10.sha256.fbcf60d3506d`。中间态未形成提交，不进入提交记录。哈希内文件任何字节改动都会
  移动版本号，注释也算。
- 2026-08-30 T8 修正：撤回 T7 的 G2 扩范围，G2 收窄为含 `/` 的路径形引用并跳过通配模式；新增 D6/G6，要求每条防线同时记录正控制与负控制；补齐 G1-G4 负控制，均为零假阳性。
- 2026-08-30 T9 可达性实测：12 期上传通过 audit 后穿透到 Q8 并在 analyze 返回 422；
  W-5 升级为 H / A，触发 T9 停止条件，未执行本轮其余修复或提交。
- 2026-08-30 T10 裁决：T9 停止仅适用于触发项，恢复第一部分；Q8 保持登记不修，W-5、H-6、
  H-7 归 M4-B/M4-C 的输入边界与 CSV 人工验收；建立 P/W/H 与 A/B 分级协议。
- 2026-08-30 T11 收官：登记 W-12、W-13 与 H.4 lifecycle 测试固定事实；负责人裁决 lifecycle
  路径 A 和 `n_min(L) = max(L+9, 2L+7)`；收敛 D1–D6 状态、正式冻结 195 计数基线并建立
  完整未决库存。G-1 关闭；本轮没有直接推进 Demo DoD 三条，因此按收敛规则属于 B 类治理工作。
- 2026-08-30 M4-A accepted / M4-B 批次 0：负责人确认五条产品口径；关闭 W-3；新增 H 不得归 B
  的规则；D2 残余降为 W/B；以只读断言钉住 Evidence Gate 四项配置与 W0 narrative 示例。
  最小样本量预检发现冻结 Q6 `s_gt_6_pre_rolling_negative` 为 `n=11`，低于
  `n_min(3)=13`，登记 H-8 并按部分停止条件暂停该实现。
- 2026-08-31 M4-B lifecycle 路径 A：新增 `insufficient_evidence` Report 状态并完成契约、mock、
  前端与 ground-truth 扇出；S-GT-1/S-GT-2 selection 不变，版本由
  `s10.sha256.fbcf60d3506d` 移至 `s10.sha256.ab759b2231a4`，H.4 关闭。
- 2026-08-31 M4-B 呈现层：按已确认顺序落实运行状态、gate 结果、selected/rejected、
  方向/lag/强度与 gate reasons；headline 下的 gate 解释为 13 词；`baseline_only` 明示为预期行为；
  `pipeline_version` 与 case/as-of/snapshot hash 同列 P1 context bar。W-12 正控制用内存列漂移触发，
  负控制在当前表格上通过、假阳性 0/1；桌面与 390px 窄屏均完成视觉检查。
- 2026-08-31 T13：负责人撤回输入边界拒绝路线，将 `max(L+9, 2L+7)` 改作唯一滚动
  lifecycle 进入条件；关闭 H-8、W-5、H-6、H-7 与 G8，新增稳定性未评估 warning、W-14
  数值验收规则和 W-15 表述风险。S-GT-1/2 selection 与指定数值均不变；提交 `70e858f`
  将 `pipeline_version` 单次移动到 `s10.sha256.7fed154a44bf`，完整套件 214/214 通过。
- 2026-08-31 T14 M4-B 结项自查：启动指令第 0–4 部分逐项闭合，登记 W-16；M4-B accepted。
