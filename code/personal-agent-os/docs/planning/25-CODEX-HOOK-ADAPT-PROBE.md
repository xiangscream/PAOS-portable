# Codex Hook 适配探针（25）

> 状态：**待 Codex Desktop 在自己的会话里执行**；DS-H 侧已把已知事实与最小子实验准备好。
> 上游：`24`（Codex Heartbeat 已 L4 通过）、DS-H 原生 hook 已实证“hook 能造回合”。

---

## 0. 为什么现在问 Codex hook

- DS-H 侧：一个 ~50 行原生插件（`@dsh-external/dsh-turn-hook`）已经实测——`agent/status == idle` 时调用 `agent.followup()`，成功自造了一个非人类消息的新回合（回报 `TURN_HOOK_OK`）。
- Codex 侧：Heartbeat 已 L4 通过（`24` §6）。
- 现在要回答用户的问题：**Codex 自己的 hook 能不能做同样的事（在“回合停止”这个事件上续一个回合），从而替代或补充 Heartbeat？**

---

## 1. 已复核的 Codex Hook 事实（DS-H 侧源码，供 Codex 对照）

DS-H 的 `@deepseek-ai/dsh-hooks-codex` 桥实现了 Codex hook 协议的**子集**（源码 `packages/hooks/hooks-codex/README.md`）：

- 5 / 10 事件：`PreToolUse`、`PostToolUse`、`SessionStart`、`UserPromptSubmit`、`Stop`。
- 关键映射（README “Hook points → typed Decisions”）：
  - `Stop` → `agent/turn-stopping`：“a blocking Stop hook feeds its reason through `steer()`, **forcing another step**”。→ **Codex 的 Stop hook 在回合要停时，可以强制续一步 = 造回合。**
- 已知局限（原文照抄类）：
  - `Stop` blocking 会续步，但 `stop_hook_active` 恒为 `false`、`last_assistant_message` 恒 `null`、`{"continue": false}` 未 enforce；**无条件 blocking 会让它每一步都续命**（`TODO(stop-loop-guard)`）。
  - 只有 sync `command` hook 会运行；非 command / async 会被跳过。
- 结论先行：**Codex 的 hook 大概率能“在停止边界续回合”，但不能冷启动**；冷启动仍要 Heartbeat（或人工第一句）。优雅组合 = `Heartbeat`（唤醒）+ `Stop`/`PostToolUse`（护栏/收尾）。

---

## 2. 让 Codex 自己在 Desktop 里做的最小探针（硬一次性，防续命）

请把本文件交给目标 Codex 会话，让它**只读/只做下面的最小子实验**：

### Probe 1 — 确认 hook 支持与事件面

- 检查本机是否有 `~/.codex/hooks.json`；若没有，用当前 Codex 会话可见的方式查询“hooks 配置如何写、支持哪些 events、`Stop` 的 decision 语义”。
- 记录：事件面是否 ≥ 5（尤其 `Stop`）；`Stop` 是否支持 block/continue；是否允许 `{"continue": false}`；有没有 loop-guard（如 `stop_hook_active` 是否真的会置位）。

### Probe 2 — 一次性 Stop-hook 续回合（有观察窗、一次即撤）

设计一个**只触发一次**的 `Stop` hook：

- hook 外部命令先检查一个一次性 marker（例如 `%TEMP%\codex-stop-hook-once.txt`）：
  - 不存在 → 不 block（让回合正常停）。
  - 存在 → 删除 marker，然后按 Codex hook 协议返回“block + continue 文本”（或等价 continue decision）。
- 放好 marker → 让当前回合自然完成/停止 → 观察是否**在同一 Thread** 被 hook 强制续出新的一步。
- 记录：是否续步、是否同一 Thread、是否只续一次、有没有 `stop_hook_active` 保护。

### Probe 3 — 结论回填

回报三点即可：

1. Codex hook 能“造/续”回合吗？（预期：Stop-blocking 可续步；冷启动不可）
2. 有 loop-guard 吗？（决定它能不能代替 Heartbeat 做安全轮询）
3. 优雅组合是否成立：`Heartbeat（唤醒） + Stop/PostToolUse hook（护栏/收尾）`？

---

## 3. Codex 开源状态（只作背景，勿当 hook 结论）

- **Codex CLI / 核心**：开源，仓库 `openai/codex`，Apache-2.0。
- **Codex Desktop（GUI）**：是闭源壳，但它把本地工具协议、`hooks.json`、`automation` API 暴露给本地会话使用——所以“能不能 hook”“Stop 什么语义”以**本机工具 schema + 官方 hook reference**（`learn.chatgpt.com/docs/hooks`）为准，别照抄 DS-H 的实现细节。

---

## 4. 探针结果（已回填，2026-08-24，隔离 CLI 实测）

> 由 Codex 在隔离环境回填；临时 hook / marker / 日志已清理，PAOS 仓库无残留。

实测：

```text
第一次回复：FIRST_REPLY
Stop hook：decision=block
第二次回复：SECOND_REPLY
```

- 两次 `Stop` 来自同一 Session：`session_id: 01a03333-d909-7e03-abb0-b47b2c00ff2d`。
- 第一次 `stop_hook_active: false`；第二次 `stop_hook_active: true`。
- 一次性 marker 消费后未继续无限续命。

官方语义：`Stop` 返回 `{"decision":"block","reason":"继续执行一次"}` 会让 Codex 自动继续生成下一次回复（[Codex Hooks 官方文档](https://learn.chatgpt.com/docs/hooks)）。

**确认的结论：**
- ✅ `Stop` hook 能继续当前执行流，并自动生成 continuation prompt。
- ✅ 有防续命信号：第二次 hook 能看到 `stop_hook_active=true`。
- ✅ 一次性 marker 方案可防止无限续命。
- ⚠️ 这是“同一执行流中的新回复”，**不等于**创建新的顶层 GUI Thread。
- ✅（收口后）Desktop 可见 GUI Thread 的同 Thread hook 唤醒已实测通过，见 `26` §5。

**对 PAOS 的定论：**
- `Heartbeat / Automation`：负责冷启动 + 定时唤醒。
- `Stop hook`：负责当前 Session 的收尾、补一次检查、护栏。
- 不建议用 `Stop hook` 单独承担周期唤醒；不建议无条件 `block`；实现时**同时检查 `stop_hook_active` 和业务 marker**。

**矩阵影响：** `22` §2.2 的 Codex 停止/护栏层可增加“`Stop` hook 收尾”，但唤醒仍是 Heartbeat；Codex-hook 证据等级 =「CLI same-flow 已证 + **Desktop GUI same-thread 已证**（`26`）」。