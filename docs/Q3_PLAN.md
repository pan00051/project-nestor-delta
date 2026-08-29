# Q3 执行规格 — `capabilities` 陈旧响应

**状态：** ✅ 已确诊，部署脚本修复待实施。D1/D2、F1、D5 与变量 redeploy 实验均已完成。
**上位文档：** `docs/REMEDIATION_Q_V1.md` Q3 · `docs/API_BOUNDARY_V1.md` §2.8

---

## 0. 一句话

`/api/v1/capabilities` 曾返回一个更早版本代码产生的完整响应体（旧 `pipeline_version`，且无 `ledger` 块），
而带 cache-busting 参数的同一端点在数秒内返回当前值。机制已复现：部署脚本先设置
`NESTOR_BUILD_SHA`，Railway 因变量变化启动此前上传的 source redeploy；该 redeploy 能接管公开流量，
随后 `railway up` 才上传新 source。

**顺序是硬约束：先取证，后修。** 先加 `Cache-Control` 会让现象消失但原因永远不明；
若真因是 H2，那次修改一行都没修到，只是把缺陷变成了「以为修好了」。

**D5 结果：** 127 条原始记录中 126 条为 HTTP 200、切换期一条 canonical 请求为 502。新版本首次
出现后，canonical 与 cache-busted 共 66 条成功响应全部保持 `c6afbb581ff7`、`no-store`、ledger 与
`ledger_observed_at`，没有旧版本回返。完整证据见
`docs/evidence/Q3_DEPLOYMENT_WINDOW_2026-08-29.md` 与相邻 JSONL。

**变量 redeploy 结果：** 受控实验没有上传新 source，只把 `NESTOR_BUILD_SHA` 临时设为哨兵
`deadbeef3333`。Railway 创建的 redeploy 实际服务了 48 次成功请求、约 74 秒；恢复真实 revision 后
连续 50 次成功响应稳定。证据见 `docs/evidence/Q3_VARIABLE_REDEPLOY_2026-08-29.md` 与相邻 JSONL。

---

## 1. 已确认的代码事实（无需重新排查）

- `boundary.capabilities()` 每次请求现构造字典，**应用层无任何缓存**。
- `PIPELINE_VERSION` / `SOURCE_REVISION` 是模块导入时求值的常量；`relationship_ledger_status()` 每次现算。
- Q3 修复前，路由 `return dict`，走 FastAPI 默认 JSONResponse。
- Q3 修复前，全代码库无任何 `Cache-Control` / `max-age` / `no-store`（已 grep `src/` `scripts/` `Dockerfile` `railway.json`）。
- Q3 F1 后，`/health` 与 `/api/v1/capabilities` 显式返回 `Cache-Control: no-store`。
- 关键线索：`ledger` 块是 M3（`78e2c2f`）才加入 capabilities 的。旧响应缺该块，
  说明它来自**旧代码**，而不是旧代码的新响应被改坏。

结论：应用代码不会自行返回旧值。确诊点在部署链路：变量更新启动 prior-source redeploy，且它能够
服务公开请求。历史请求无法事后绑定 deployment ID，因此“那一条请求正来自该 deployment”是高置信
归因，不伪装成逐请求直接证明。

---

## 2. 假设集

| 编号 | 假设 | 判别特征 |
|---|---|---|
| **H1** | 前置 HTTP 缓存（平台边缘 / CDN / 中间层）存了部署前的响应 | 响应头有痕迹：`Age` / `Cache-Control` / `ETag` / `CF-Cache-Status` / `x-railway-*`；规范 URL 稳定返回旧值，带参数稳定返回新值 |
| **H2** | prior-source redeploy 在新 source 上传前/期间服务 | 变量变化创建 redeploy；公开响应出现受控 revision，证明该 redeploy 接管流量 |
| **H3** | 观测端自身缓存（浏览器 / 本地代理 / web 层复用连接） | 仅在特定客户端复现，换机器或换网络即消失 |

三者覆盖当前最主要的机制，但不能把未公开语义的平台响应头当作穷尽性证明。H2 包括部署切换期间
新旧进程短暂并存这一时限性子类。不得在取证前预设任何一个。

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

**D5 · 下一次 API 部署窗口采样（有时限，部署前必须启动）**

下一次 API 部署是检验 H2 部署切换子类的观测窗口。不得先部署再补采样。先在一个终端启动：

```bash
scripts/sample-q3-deploy-window.py \
  https://api-production-9849.up.railway.app \
  /tmp/nestor-delta-q3-deploy-<UTC> \
  --duration 240 --interval 1
```

工具开始写入 `evidence.jsonl` 后，才在另一终端执行规定的 API 部署脚本。采样同时请求 canonical 与
cache-busted capabilities，保存完整响应头和响应体，并发送 `X-Railway-Debug: 1` 以收集 upstream zone。
每条记录还显式提取 `ledger_observed_at`，用于区分缓存命中时保留的观测时间与部署后新进程取得的观测。
部署切换完成后仍继续采样至少 60 秒。输出先放在 repo 外，避免工作树变脏导致部署脚本拒绝执行；完成后
审查原始内容，再将证据纳入仓库。

本次 `pipeline_version` 不变，版本切换只能用 `source_revision` 判断。`Cache-Control: no-store` 的出现
可以证明 F1 代码已开始服务，但无法单独区分“旧进程响应”与“旧响应被重放”。还要同时保存 Railway
部署状态、部署代次和相邻运行日志。`x-hikari-trace` 相同只是路由线索；Railway 没有将它公开定义为
应用副本标识，因此不能据此宣称“只有一个后端实例”。

**取证产出：** 一份原始记录（响应头全文 + 10 次采样表 + 环境说明），提交进 repo，
作为 Q3 关闭的证据。**不得只写结论。**

**D6 · 变量 redeploy 受控验证（已完成）**

在不上传 source 的前提下临时设置有效十六进制 revision 哨兵，确认变量触发的 redeploy 是否出现在
canonical/cache-busted 响应中，再恢复真实 revision 并继续采样。结果成立；完整方法、部署 ID、digest、
时间线和 134 条原始记录见 `docs/evidence/Q3_VARIABLE_REDEPLOY_2026-08-29.md`。

---

## 4. F — 修复

### F1 · 无条件执行（与诊断结果无关）

给 `/api/v1/capabilities` 与 `/health` 显式声明 `Cache-Control: no-store`。

理由不是「因为它是缓存问题」，而是：**承载 provenance 的端点必须自己声明不可缓存，
不该把这件事留给中间层去猜。** 当前它什么都不声明，一个无 `Cache-Control` 的 200 GET
被中间层施加启发式缓存是合规行为，不是谁的 bug。

- 触及文件：`src/nestor_delta_service/app.py`
- 实现选择：逐路由返回带 header 的 `JSONResponse`。理由是影响面小，只覆盖 provenance
  端点，不改变 POST 分析、run store、audit 或 snapshot 的响应路径。
- 契约测试：`tests/test_api_boundary.py` 断言两个端点响应头含 `no-store`。
- **F1 不构成 Q3 的验收。** 若真因是 H2，它一行都没修到。

### F2 · 按诊断结果分支

- **H1 成立**：F1 即正解。追加确认是哪一层在缓存，并写入 `docs/M2_DEPLOYMENT.md`。
- **H2 成立（已确认）**：处理变量更新与 source 上传之间的部署竞态。
  **注意相邻风险**：HANDOFF 明确要求 API 跑 `--workers 1`，因为 `RunStore` 是进程内单例，
  多进程会让 `GET /api/v1/runs/{run_id}` 随机 404。若确有第二进程在服务，
  则**同一根因正在同时破坏 run retention**，只是尚未被观测到。此时 Q3 的范围需相应扩大。
- **H3 成立**：API 侧无缺陷。产出为观测纪律文档，不改代码。

### F3 · 让陈旧可被发现（**已决定不纳入 Q3**）

即便 no-store 生效，消费者仍**无法分辨手中响应是否新鲜**——陈旧响应与正确响应外观完全相同。
候选方向（未择定）：

- 响应携带进程启动时间或每进程唯一标识，使被重放的响应自我暴露；
- 利用现成条件：`/health` 与 `capabilities` 均报 `source_revision`，两者不一致即为信号。

该方向不纳入 Q3。D6 已通过可控 revision 复现部署链路根因；进程身份属于额外的纵深防护，不能替代
部署脚本对 prior-source/new-revision 错配的修复。

---

## 5. 验收（三条缺一不可）

1. 机制被确诊并写下来——**是什么在返回旧值，在链路的哪一段**。「加了 header 就好了」不算确诊。
2. **不带任何 cache-busting 参数**，连续 10 次访问，全部返回当前 `pipeline_version` 且 `ledger` 块存在。
3. 关闭 `docs/API_BOUNDARY_V1.md` §2.8 的 "Open — response freshness"，
   或将其改写为一条已确诊、有边界的限制；同步 HANDOFF「已知缺陷」清单与
   `docs/REMEDIATION_Q_V1.md` Q3 状态。

三项均已完成。诊断关闭不等于部署脚本已修复；脚本风险单独保留到下一次生产 source deploy 之前。

部署脚本的 revision 验证继续携带 cache-busting 参数，作为纵深防护；普通发现请求可使用声明
`Cache-Control: no-store` 的 canonical URL。

---

## 6. 后续

1. 在下一次生产 source deploy 前修复 `scripts/deploy-railway.sh` 的变量触发竞态，并为部署顺序补验收。
2. 修复时优先评估 Railway 的 non-deploying variable update；不得让 prior-source 进程携带新 revision。
3. F3 的进程身份设计不纳入 Q3；当前根因已在部署链路复现。
