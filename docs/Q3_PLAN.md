# Q3 执行规格 — `capabilities` 陈旧响应

**状态：** 规格草案，待 GPT 补充与审查后开工。
**上位文档：** `docs/REMEDIATION_Q_V1.md` Q3 · `docs/API_BOUNDARY_V1.md` §2.8（Open — response freshness）

---

## 0. 一句话

`/api/v1/capabilities` 曾返回一个更早版本代码产生的完整响应体（旧 `pipeline_version`，且无 `ledger` 块），
而带 cache-busting 参数的同一端点在数秒内返回当前值。机制未确诊。

**顺序是硬约束：先取证，后修。** 先加 `Cache-Control` 会让现象消失但原因永远不明；
若真因是 H2，那次修改一行都没修到，只是把缺陷变成了「以为修好了」。

---

## 1. 已确认的代码事实（无需重新排查）

- `boundary.capabilities()` 每次请求现构造字典，**应用层无任何缓存**。
- `PIPELINE_VERSION` / `SOURCE_REVISION` 是模块导入时求值的常量；`relationship_ledger_status()` 每次现算。
- 路由 `return dict`，走 FastAPI 默认 JSONResponse。
- **全代码库无任何 `Cache-Control` / `max-age` / `no-store`**（已 grep `src/` `scripts/` `Dockerfile` `railway.json`）。
- 关键线索：`ledger` 块是 M3（`78e2c2f`）才加入 capabilities 的。旧响应缺该块，
  说明它来自**旧代码**，而不是旧代码的新响应被改坏。

结论：应用代码不会自行返回旧值。原因必在「响应被存下重放」或「旧进程仍在服务」二者之一。

---

## 2. 假设集

| 编号 | 假设 | 判别特征 |
|---|---|---|
| **H1** | 前置 HTTP 缓存（平台边缘 / CDN / 中间层）存了部署前的响应 | 响应头有痕迹：`Age` / `Cache-Control` / `ETag` / `CF-Cache-Status` / `x-railway-*`；规范 URL 稳定返回旧值，带参数稳定返回新值 |
| **H2** | 新旧进程同时在服务（旧部署未排空，或存在第二副本） | 连续请求规范 URL **随机跳变**；cache-busting 参数**不稳定有效** |
| **H3** | 观测端自身缓存（浏览器 / 本地代理 / web 层复用连接） | 仅在特定客户端复现，换机器或换网络即消失 |

三者互斥且穷尽当前证据。不得在取证前预设任何一个。

---

## 3. D — 诊断步骤（不改任何代码）

**D1 · 响应头对比**
规范 URL 与带随机参数 URL 各请求一次，记录**完整响应头**。
这是区分 H1 与 H2 最便宜的一刀。

**D2 · 重复采样**
连续请求规范 URL ≥ 10 次，记录每次的 `pipeline_version` 与 `ledger` 是否存在。
- 稳定旧值 → 指向 H1
- 新旧跳变 → 指向 H2

**D3 · 换网络复测**
从另一台机器 / 另一个网络重复 D1、D2。差异消失 → 指向 H3。

**D4 · 部署侧核对**（仅当 D2 出现跳变时执行）
确认当前实际在跑的实例数与部署代次；核对 API 是否仍为 `--workers 1`。

**取证产出：** 一份原始记录（响应头全文 + 10 次采样表 + 环境说明），提交进 repo，
作为 Q3 关闭的证据。**不得只写结论。**

---

## 4. F — 修复

### F1 · 无条件执行（与诊断结果无关）

给 `/api/v1/capabilities` 与 `/health` 显式声明 `Cache-Control: no-store`。

理由不是「因为它是缓存问题」，而是：**承载 provenance 的端点必须自己声明不可缓存，
不该把这件事留给中间层去猜。** 当前它什么都不声明，一个无 `Cache-Control` 的 200 GET
被中间层施加启发式缓存是合规行为，不是谁的 bug。

- 触及文件：`src/nestor_delta_service/app.py`
- 实现选择（**待 GPT 定夺**）：逐路由返回带 header 的 `JSONResponse`，
  还是加一个中间件统一处理 GET 响应。前者显式、影响面小；后者不易漏但会覆盖到未来新增端点。
- 必须新增契约测试：`tests/test_api_boundary.py` 断言两个端点响应头含 `no-store`。
- **F1 不构成 Q3 的验收。** 若真因是 H2，它一行都没修到。

### F2 · 按诊断结果分支

- **H1 成立**：F1 即正解。追加确认是哪一层在缓存，并写入 `docs/M2_DEPLOYMENT.md`。
- **H2 成立**：处理部署排空 / 副本策略。
  **注意相邻风险**：HANDOFF 明确要求 API 跑 `--workers 1`，因为 `RunStore` 是进程内单例，
  多进程会让 `GET /api/v1/runs/{run_id}` 随机 404。若确有第二进程在服务，
  则**同一根因正在同时破坏 run retention**，只是尚未被观测到。此时 Q3 的范围需相应扩大。
- **H3 成立**：API 侧无缺陷。产出为观测纪律文档，不改代码。

### F3 · 让陈旧可被发现（**设计问题，待 GPT 评审是否纳入 Q3**）

即便 no-store 生效，消费者仍**无法分辨手中响应是否新鲜**——陈旧响应与正确响应外观完全相同。
候选方向（未择定）：

- 响应携带进程启动时间或每进程唯一标识，使被重放的响应自我暴露；
- 利用现成条件：`/health` 与 `capabilities` 均报 `source_revision`，两者不一致即为信号。

**开放问题：** 这属于 Q3 的范围，还是应另立条目？纳入会扩大 Q3；不纳入则 §2.8 只是被关闭，
而「无法判断新鲜度」这个结构性弱点仍然存在。

---

## 5. 验收（三条缺一不可）

1. 机制被确诊并写下来——**是什么在返回旧值，在链路的哪一段**。「加了 header 就好了」不算确诊。
2. **不带任何 cache-busting 参数**，连续 10 次访问，全部返回当前 `pipeline_version` 且 `ledger` 块存在。
3. 关闭 `docs/API_BOUNDARY_V1.md` §2.8 的 "Open — response freshness"，
   或将其改写为一条已确诊、有边界的限制；同步 HANDOFF「已知缺陷」清单与
   `docs/REMEDIATION_Q_V1.md` Q3 状态。

**在 Q3 关闭前**：所有验证性访问必须携带 cache-busting 参数。此规则保留。

---

## 6. 交给 GPT 的待办

1. 审查 §2 假设集是否穷尽——有无第四种机制被漏掉。
2. 定夺 F1 的实现形式（逐路由 vs 中间件），并说明取舍。
3. 评审 F3 是否纳入 Q3。
4. 补充 D1–D4 在 Railway 上的具体操作细节（本规格刻意不写平台特定步骤，以免预设 H1）。
5. 核对 F2/H2 分支对 `--workers 1` 与 run retention 的影响判断是否成立。
