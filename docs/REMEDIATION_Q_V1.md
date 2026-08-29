# Nestor Delta — Q 系列修复里程碑 (v1)

本文件登记一次外部审计发现的缺陷，并按**修复难度与预计时间**切成编号里程碑。

**与 M 系列的关系：** M 系列是「把还没做的功能做出来」；Q 系列是「把已经声明过、但事实上不成立的
东西修正」。两者独立编号，可并行，但 **Q3 与 Q4 必须在 M5 冻结之前关闭**——它们影响的是对外
可信度，而不是完成度。

**验收纪律沿用 `BLUEPRINT.md` §6：** 每一条 Q 的 DoD 必须写成一条可执行的命令或一次可复核的观察，
并记录 before/after。「看起来修好了」不构成验收。

---

## 总览

| 编号 | 名称 | 预计时间 | 类型 | 状态 |
|------|------|----------|------|------|
| **Q1** | 测试依赖声明修复 | ~15 分钟 | 事实性错误 | ✅ 已完成 |
| **Q2** | 措辞边界：关系可靠性 ≠ 信息真实性 | ~30 分钟 | 对外表述风险 | ✅ 已完成 |
| **Q3** | `capabilities` 陈旧响应诊断 | 半天 ~ 1 天（下界不明） | 可信度缺陷 | ✅ 已确诊；部署脚本修复待实施 |
| **Q4** | `ledger.durable` 信号名实不符 | 半天 | 可信度缺陷 | ✅ 已完成 |
| **Q5** | 邀请码轻量访问 gate | 半天（规模必须守住） | 新能力 | 未开始 |
| **Q6** | rolling-window 边界 fixture 缺失 | 1 ~ 2 天 | 验证盲区 | ✅ 已完成 |
| **Q7** | live intake 的冻结快照路径 | 独立阶段，M5 之后 | 新方向 | 未开始 |

排序依据是**预计时间升序**，不是重要性。若按「不修的后果」排，顺序是 Q3 > Q6 > Q1 > Q4 > Q2。

---

## Q1 — 测试依赖声明修复 ✅

**问题。** `README.md` 与 `REPRODUCIBILITY.md` 都写着：`pip install -e '.[dev]'` 后运行
`python -m pytest -q`，得到 179 passed。在一台干净机器上照做，**测试根本跑不起来**。

`pyproject.toml` 的 `[dev]` extra 此前只声明了 `pytest` 一个包，而完整测试实际还需要五个：

| 缺失的包 | 谁需要它 | 失败形态 |
|---|---|---|
| `jsonschema` | `tests/test_api_boundary.py` 模块级 import | collection 阶段 `ModuleNotFoundError` |
| `fastapi` | 同上 | 同上 |
| `httpx` | starlette `TestClient` 导入时要求 | collection 阶段 `RuntimeError` |
| `numpy` | `tests/ground_truth/generate_ground_truth.py` | `test_sgt2b_false_positive_rate_across_seeds` 失败 |
| `pandas` | 同上 | 同上 |

**为什么此前没人发现。** 后两个是隐蔽的：`streamlit` 会把 `numpy` 和 `pandas` 传递性地装进环境。
凡是装过 `[web]` extra 的机器，完整测试都能通过——**它靠的是环境里的意外，而不是任何一处声明。**
只装 `[dev]` 的干净机器则会看到 178 passed / 1 failed，且失败的恰好是跨种子假阳性率这条负控制。

**为什么这条最该先修。** 本项目的全部说服力建立在「可验证、可复现」上，文档里甚至专门论证过
「文档会漂移，测试不会」。而这条被反复书写的复现命令，本身在干净环境下不成立。它同时未能通过
`BLUEPRINT.md` §6.4 与 HANDOFF 提出的那条验收标准——「什么情况会让这条声明变成假的？」
答案是：**什么都不用变，它当时就是假的。**

**DoD（已达成，Q1.1 后为当前形态）。** 在一个全新的 venv 中，按文档命令升级 pip、
安装 dev extra 并运行完整套件，不设任何 `PYTHONPATH`：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

**before：** `1 failed, 178 passed`（补齐 `jsonschema`/`fastapi`/`httpx` 之前更早：collection 直接中断）
**after：** `179 passed, 34 subtests passed`

### Q1.1 — 补记：缺 `[build-system]` 与 pip 版本下限

Q1 首次推送后，在作者本人的 macOS 机器上执行同一条命令仍然失败：

```
ERROR: File "setup.py" or "setup.cfg" not found. Directory cannot be installed
in editable mode: ...  (A "pyproject.toml" file was found, but editable mode
currently requires a setuptools-based build.)
```

两个叠加原因：

1. `pyproject.toml` **没有 `[build-system]` 表**。缺了它，pip 会退回到旧的 setuptools 路径。
   云端 pip 24.0 能隐式兜住，旧 pip 兜不住——所以这个缺陷在现代环境里完全不可见。
2. pyproject-only 项目的 editable 安装依赖 PEP 660，**pip 21.3 才支持**。
   macOS 自带 Python 3.9 的 pip 是 **21.2.4**，正好差一个版本。

值得记下来的是报错信息本身在误导：它说「找不到 setup.py」，让人以为该去补 `setup.py`，
而真正的原因是构建后端未声明 + pip 太旧。

**修复：** 显式声明 `[build-system]`（`setuptools>=64` + `setuptools.build_meta`）与
`[tool.setuptools.packages.find] where = ["src"]`（不依赖自动发现），
并在 `README.md` 与 `REPRODUCIBILITY.md` 写明 pip 版本下限与升级命令。

**验收：** 全新 venv 中 `179 passed`，且 `nestor_delta` / `nestor_delta_service` /
`nestor_delta_web` 三个包均可导入。

**教训（与 Q1 同源）：** 「在我的机器上能跑」这次是反过来的——**云端环境太新，把缺陷盖住了。**
一条复现命令要在文档里出现，就得在**文档所声明的最低环境**下验证过，而不是只在最顺手的那台机器上。

**变更范围：** 仅 `pyproject.toml`（`[dev]` extra、`[build-system]`、包发现）与三份文档的安装说明。
未触碰任何算法、阈值、fixture 或输出，因此 `pipeline_version` 不变。

---

## Q2 — 措辞边界：关系可靠性 ≠ 信息真实性 ✅

**问题。** 新方向允许 Delta 后期拉取实时数据。围绕这件事出现过一种表述：
「抓取实时信息并预测，已验证其真实性」。这句话有歧义，且歧义指向一个 Delta **并不具备**的能力：

- Delta 实际做的：判断**变量之间的关系**是否可信——这个相关性是真信号还是噪声。
- 这句话容易被听成：判断**这条信息本身**是真是假（事实核查 / 假新闻识别）。

**后果。** 在 HR demo 或简历语境中，听者极可能取后一种理解。一旦被追问「你如何判断信息真实性」，
而实际并无该能力，前面所有关于诚实与严谨的建设会被一次性反噬。这属于
`BLUEPRINT.md` §9.5「诚实措辞」与 §6.4「禁止选择性诚实」共同约束的范围。

**DoD（已达成）。** 在 `BLUEPRINT.md` 与 `README.md` 各写入一条不可绕过的措辞约束，明确：
Delta 验证的是关系的可靠性与证据充分性，**不验证任何输入信息的真实性**；实时数据的来源可信度
是输入侧的前提，不是 Delta 的产出。

---

## Q3 — `capabilities` 陈旧响应诊断

**状态：** ✅ 已确诊，部署脚本修复待实施。D5 部署窗口没有复现陈旧成功响应；随后受控变量实验确认：
`railway variables --set` 创建的 prior-source redeploy 会接管公开流量。哨兵 redeploy 服务了 48 次成功
请求、约 74 秒，恢复后 50 次成功响应稳定。证据见
`docs/evidence/Q3_VARIABLE_REDEPLOY_2026-08-29.md` 与相邻原始 JSONL。

**问题。** 已观察到：直接访问 `/api/v1/capabilities` 返回了一个已被取代的 `pipeline_version`，
且 `ledger` 块缺失；同一端点带 cache-busting 参数访问，几秒之内返回的是当前值。确诊机制是部署竞态：
脚本设置新 `NESTOR_BUILD_SHA` 会先触发此前 source 的 redeploy，该进程能服务公开请求；新 source 随后的
上传才会替换它。因此旧代码可暂时携带新 revision，cache-busting 也无法避免命中它。

**为什么这条后果最重。** 该端点是文档要求消费者「不要硬编码、来这里发现」的唯一发现面，并且它
携带 `pipeline_version`——那个专门用来证明「现在跑的到底是哪一版」的字段。

> 一个用来证明诚实的字段，本身返回了过期值，而且**从外部无法分辨它是不是过期的**。

对 HR demo 的具体影响：访客浏览器若拿到陈旧响应，你当场展示的「可复现 / 有版本溯源」就是错的，
而你不会知道。

**DoD。** 三者缺一不可：
1. 机制被确诊并写下来（是什么在返回旧值，在链路的哪一段）。
2. 不带 cache-busting 参数的连续 10 次访问，全部返回当前 `pipeline_version` 且 `ledger` 块存在。
3. HANDOFF 与 `docs/API_BOUNDARY_V1.md` §2.8 的 "Open — response freshness" 一并关闭，
   或改写为已确诊的、有边界的限制。

部署脚本的 revision 验证继续带 cache-busting 参数；普通发现请求使用已声明 `no-store` 的 canonical URL。

---

## Q4 — `ledger.durable` 信号名实不符

**状态：** ✅ 已完成。`ledger.durable` 不再镜像环境变量，而是要求非默认路径已配置且最近一次真实探测
通过；`/health` 与 `/api/v1/capabilities` 都能看到同一份 ledger 状态。外部复审发现初版在每次请求中
探测并完整数行，与 capabilities 的 "cheap" 契约冲突；现改为 60 秒有界探测缓存、首次数行和真实 append
增量更新。缓存命中请求不产生磁盘 I/O，过期后的首次请求只执行固定大小探针，不再扫描完整 ledger。
`ledger.observed_at` 暴露该缓存观测的 UTC 时间；命中缓存时保持不变，真实 append 或探针刷新时更新。

**问题。** `capabilities.ledger.durable` 目前只表示「配置了一个非默认路径」。它**不检查该路径是否
可写、是否真的持久**。而 ledger 写入是 fail-soft 的（写失败只记日志，不让请求失败）。

三者叠加的后果：**ledger 已经坏了，接口却报告健康，同时在丢失一种事后无法重建的记录。**

**DoD。**
1. `durable` 变成一次真实探测（按需：写入 → 读回 → 清理），而不是一次配置读取。
2. 探测失败时 `durable: false`，且 `/health` 能看出来。
3. 人为把路径指向不可写位置，验证 `durable` 确实翻转为 `false`——**没有做过这次翻转验证，
   这条不算关闭**（否则只是把一个装饰字段换成了另一个）。

**完成边界。** 这证明的是当前进程对当前路径的写入健康，不证明平台卷跨重启持久。跨重启持久性仍由
Railway volume、环境变量路径和部署后文件检查证明。

**热路径边界。** 未鉴权的 `/health` 与 `/api/v1/capabilities` 不得因 ledger 增长而线性变慢。探针
结果最多缓存 60 秒；行数只在首次观察新路径或路径恢复可写时完整读取一次，之后由当前单写进程按成功追加
数量递增。测试必须证明重复请求既不再次探针，也不重新读取 ledger。

**已知限制。** `lines` 是单进程增量估计，外部追加、截断或替换文件会使它在重启/恢复前漂移；这不影响
Q3 部署采样，因为 Q3 依据 revision、响应头和 ledger 块存在性，不依据行数。崩溃或强制终止也可能留下
`.probe-*` 文件；它不计入 ledger，但可能累积。两项均在本轮部署后再评估，避免冻结前继续扩大改动。

---

## Q5 — 邀请码轻量访问 gate

**预计时间：** 半天。**这条的风险不是做不出来，是做太大。**

**问题。** 新方向允许邀请码访问，但当前 `docs/API_BOUNDARY_V1.md` §2.9 的 auth 依赖是一个
对所有请求放行的空壳。

**规格（不得超出）。** 在**已有的那一个** auth 依赖里校验一个存放于环境变量的共享口令：
对上放行，对不上拒绝。仅此而已。

**明确的非目标——出现任何一项即为越界：**
用户表 · 注册 / 登录流程 · 邀请码的签发与管理后台 · 会话与 refresh token · 组织 / 租户 ·
使用量统计与配额 · 找回口令。

`BLUEPRINT.md` §7 已将「商业 SaaS 能力」整体划入星辰大海；本条是其中唯一被放行的例外，
因此边界必须写死。

**DoD。**
1. 无口令访问受保护端点 → 拒绝；带正确口令 → 与当前行为完全一致。
2. `/health` 与 `/api/v1/capabilities` **保持免鉴权**（文档要求其"unauthenticated and cheap"）。
3. 变更集不包含任何数据库迁移、任何新表、任何新的持久化实体。
4. 口令仅来自环境变量，**不得进入 Git**，不得出现在任何报告体或日志中。

---

## Q6 — rolling-window 边界 fixture 缺失

**状态：** ✅ 已完成。新增 `s_gt_6_pre_rolling_negative.csv` 与
`s_gt_6_rolling_positive.csv`，并在 ground-truth 契约测试中固定滚动窗口边界、
正/负控制结果和 `effect.score` 口径。

**预计时间：** 1 ~ 2 天。

**问题。** 全部 ground-truth fixture 都是 n=216，因此**滚动窗口分支从未被任何已知答案的用例覆盖**。

**为什么这条比它看起来重要。** 本项目历史上最严重的一次缺陷正是滚动窗口相关：`effect.score`
被从 36 个月滚动窗口读取，却按全样本 effect 对外呈现，把头条数字往高报了 14%，而当时 132 个
测试全绿。抓住它的不是测试套件，是一个**答案由构造方式已知**的 fixture。

现在滚动窗口分支恰好又处于「没有这类 fixture」的状态。这不是「还差一点覆盖率」，
而是同一类事故的复发条件仍然存在。

**DoD。**
1. 新增至少两个 n 落在滚动窗口切换边界两侧的 ground-truth fixture（一正控制一负控制）。
2. 正控制仍须选出真实关系并还原 lag 与符号；负控制仍须返回 `baseline_only` 且 `selected_count: 0`。
3. 记录边界两侧的 `effect.score`，并说明该值应当从哪个窗口读取——**把口径写下来，
   而不是只让测试通过**。

**第 0 步：滚动窗口分支条件。** 当前源码条件在
`src/nestor_delta_service/adapter.py`：

- `_s9_relation_objects`：第 745 行，`len(train_rows) <= analysis_input.lag_window + 8`
  时跳过 rolling 并返回全训练窗口 ranking；否则进入 rolling（第 747-750 行）。
- `_lifecycle_block`：第 786 行，同一条件下返回 `{"state": "birth", "points": None}`；
  否则进入 rolling lifecycle（第 788-789 行）。
- `_trajectory_block`：第 812 行，同一条件下返回 `None`；否则进入 rolling trajectory
  （第 814-815 行）。
- `_rolling_window_size`：进入 rolling 后窗口为
  `min(36, max(lag_window + 6, len(train_rows) // 3))`（第 903-907 行）。

这个条件此前已由 report configuration 暴露为窗口公式，但没有作为
ground-truth fixture 选择依据写入 `tests/ground_truth/README.md`。Q6 已补记。

**n 值推导。** Q6 沿用 ground-truth 默认 `lag_window = 3`，所以分支边界是
`train_observations <= 11` 跳过 rolling，`train_observations > 11` 进入 rolling。
负控制取 `n = 11`，即边界下方最后一个非 rolling 训练长度。正控制取 `n = 51`：
这是 accepted S-GT-1 种子的最短前缀，既进入 rolling，又按当前
`step_interval = 6` 与 `min_points = 6` 产生 6 个 trajectory points，并在不放宽
Evidence Gate 的情况下选择真实关系。

**完成证据（Q6 after）。**

| Fixture | Train n | Rolling window | Outcome | Selected | Key effect evidence |
|---|---:|---:|---|---|---|
| `s_gt_6_pre_rolling_negative` | 11 | `null` | `baseline_only` | `selected_count = 0` | top `noise_1`: `effect.score = 0.6722015107369267`, `trajectory = null` |
| `s_gt_6_rolling_positive` | 51 | 17 | `ok` | `["true_driver"]` | `true_driver`: `effect.score = 0.6230268430213287`, `lag = 2`, `sign = -1`, `stability = 0.522353792707568`, `uncertainty = 0.1337838756106424` |

`s_gt_6_rolling_positive` 的最后一个 rolling trajectory point 是
`score = 0.6323873577775484` at `step = 51`。报告中的 `effect.score` 必须读取
**full training window** 的 transformed correlation（`0.6230268430213287`），不是这个
rolling point；rolling 只供 `stability` / `uncertainty` / `lifecycle` 使用。

**历史控制 before/after。** Q6 没有修改算法、阈值或既有冻结 fixture。Q6 后重新测得：
S-GT-1 仍为 `outcome = ok`、`selected_count = 1`、`selected_sources = ["true_driver"]`、
`effect.score = 0.5844220533473201`、`lag = 2`、`sign = -1`；S-GT-2 仍为
`outcome = baseline_only`、`selected_count = 0`。`pipeline_version` 仍为
`s10.sha256.3665b88553ad`。

---

## Q7 — live intake 的冻结快照路径

**预计时间：** 独立阶段，**M5 冻结之后**再开工。

**问题。** 实时数据与 `docs/API_BOUNDARY_V1.md` P2 直接对冲。P2 是本产品的可信度主张本身：

```
report = f(snapshot_id, analysis_params, pipeline_version)
```

同样三项输入，必须逐字节相同的报告，任何机器、任何时刻。实时数据的定义就是它会变。

**唯一安全的形态（顺序不可颠倒）：**

```
拉取实时数据 → 立即冻结为带 hash 的不可变 snapshot（记录来源、时间、参数、版本）→ 对 snapshot 做分析
```

**绝不允许**对实时数据流直接跑分析。`BLUEPRINT.md` §6.6 与 `HANDOFF.md` 不可协商边界第 5 条
已写入此约束；本条是它的实现里程碑。

**为什么必须排在 M5 之后。** 当前 M4（图表 + CSV 人工验收）是 Demo DoD 里唯一尚未达成的一项。
在它之前插入一个新的数据摄入方向，正是 `BLUEPRINT.md` §5 收敛纪律要防的范围膨胀。

**DoD（届时细化）。** 至少包含：live 结果在成为任何对外证据之前必须已被冻结为 snapshot；
snapshot 的 hash 可独立重算；exploratory live run 与 frozen evidence 在界面与文档语言上
明确区分（§6.3）。

---

## 审计说明

Q1–Q7 由 Claude 在 2026-08-28 的一次外部审计中提出，审计基线为 `f5abd58`。
在该审计基线上，Q1 与 Q2 同批完成并附验收证据，Q3–Q7 当时仅登记、尚未开工；当前状态以上方总览
和各条正文为准。

审计中一并核实、**确认无误**的项（不构成 Q 条目，此处记录以免重复排查）：

- `01a9e6c` 确实修复了此前登记的两条缺陷：relation expander label 现已成对显示 lifecycle 与
  `stability`（`render_logic.relation_expander_label`），`configuration` 现已渲染
  （`streamlit_app.render_configuration`）。HANDOFF 将其从已知缺陷清单中移除属实，非选择性删除。
- 生产 API `/health`（带 cache-buster）返回 `source_revision=01a9e6ca2637`，与 HANDOFF
  所记录的部署版本一致。
