# 独立复核 — orient 窄修 PR #115（ca26600：live Work 永先于旧 Request）— s029

- Reviewer：`3002-s029`。Work：`3002-w060`（沿用）。
- 对象：PR #115 branch `narrow/v12-orient-work-priority` @ `ca2660002dcf47c059fb5f41b7378aadeb634eb3`（base=现生产 `819b642`）。
- delta 范围实测：2 文件 / +35−12 → `scripts/paos.py`（`_orient_next_action` 重排）+ 1 个复现测试。

## 1. 判定

### 1.1 只调序、无兜底伪装 — **PASS**
- 重排后逻辑：`request_note` 仅作注记（有 Request 时附加「仅处理与当前 Work 相关项、陈旧/无关记为待收口不篡位」）；
- live Work 存在 → 三分支全在此前置（coherent+next 推进 / 不 coherent「继续当前 Work；TODO 不可用」/ coherent 无 next「继续当前 Work」）——Request 分支仅在**无 live Work** 时保留原「先处理正式 PAOS Request inbox」行为。
- 与 s027 声明一致；无硬编码 ID/未删 Request/未改模型/未动 Store。

### 1.2 复现测试真实 — **PASS**
- `test_orient_live_work_beats_stale_request_when_todo_conflicts`：todo=`3002-w0010`(mismatch)+request=2 → 断言 next **以「继续当前 Work 3002-w001」开头**、含「Request 收件箱（2）」注记、**不以「先处理正式 PAOS Request inbox」开头**——结构性复刻 s010 情形，且同时证明旧 bug 路径不再可达。

### 1.3 本地复跑 — **PASS**
- 在 `ca26600` 本地 clone：`test_paos_intent_read_cli_v12.py` **10/10 OK**（含新测试与既有 8 个 orient 契约消息不变）；`git diff --check` clean。
- Windows 侧 verifier/CI 由正常发布轮出（不在本_report 宣告）。

## 2. 结论

**总判：PR #115（`ca26600`）窄修 — PASS。建议 s010 正常验收合入；Rooter 受影响部分 exact 结果以 CI/发布轮为准。**

---
审查人：3002-s029。证据：remote branch 读回（存在性）、diff 三要素（范围/无硬编码/语义调序）、复现测试、10/10 复跑。未改 Source/生产/模型。
