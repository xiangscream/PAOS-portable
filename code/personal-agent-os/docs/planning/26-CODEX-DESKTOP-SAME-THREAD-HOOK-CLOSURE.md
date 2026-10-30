# Codex Desktop 可见 GUI Thread 同 Thread hook 唤醒收口（26）

> 状态：**待 Codex Desktop 里执行（Page GUI 现场最小实测）**；这是 `25` §4 里唯一还挂「未验证」的一项。
> 目标：证明 **Codex Desktop 的 `Stop` hook 在可见 GUI Thread 内 block 续步时，续出的回复仍属于同一个 Thread**，而不是开新 standalone 任务/线程。
> 性质：临时、可回滚、一次性；不落 Desktop 全局配置。

---

## 0. 先回答上一个问题（结论句）

是——Codex 的 hook 可以用在“进入自动化交换模式之后”：

- **继续**：`Stop` hook 返回 `decision:block` → 同一执行流里强制再生成一次回复（已在隔离 CLI 实测）。
- **收尾**：同一机制可在收尾时“再走一步”，做最后一次检查 / 写回 / Close。
- 但**不能**用 `Stop` hook 做冷启动或周期性唤醒；那仍是 `Heartbeat/Automation` 的职责。
- 唯一定悬：这个“继续/收尾”是否发生在 **Desktop 的同一个可见 GUI Thread**。本文档就是收这一口。

---

## 1. 前置

1. 用户正在 Codex Desktop GUI 里、打开一个目标 Thread。
2. **不修改全局配置**：用临时 hooks 配置或“备份→改→还原”流程；实测后恢复原状。
3. 记录两条基线：
   - 当前可见 Thread 的原生 ID（从当前 session / rollout 路径或 app 暴露的信息取）。
   - hooks 配置当前路径（`~/.codex/hooks.json` 是否存在、原内容哈希/备份）。

---

## 2. 一次性 Stop hook（硬一次性 + 防续命）

用 25 里已验证的 marker 方案，改放到 Desktop：

- hook 外部命令（sync command hook）逻辑：
  1. 检查一次性 marker（例如 `%TEMP%\codex-desktop-stop-once.txt`）：
     - 不存在 → 放行（不 block，让回合正常停）。
     - 存在 → **先删除 marker**，随后按 Codex hook 协议返回：
       ```json
       { "decision": "block", "reason": "继续执行一次" }
       ```
- 实现时同时检查 `stop_hook_active`（第二次应为 `true`）再决定是否 block；**绝不做无条件 block**。

---

## 3. 实测步骤

1. 起好临时 hook；确保 marker **不存在**。
2. 在 Desktop 当前可见 Thread 发一条普通消息（让一个正常回合发生）→ 预期第一次回复出现，回合正常停（hook 未 block）。
3. 放好 marker（一次性）。
4. 再次让一个回合停止（可再发一条消息，或让刚才的回合自然收尾）→ 预期第一次回复后，`Stop` hook block → **第二个回复自动出现**。
5. 观察并记录第二个回复：
   - 是否仍在**同一个可见 GUI Thread**（Thread ID 未变、GUI 里就是这条 Thread，没有新跳/新卡片）。
   - 两次 `stop_hook_active`：第一次 `false`、第二次 `true`。
   - marker 是否已被消费，且没有第三次无限续命。
6. 清理：删除临时 hook 配置、marker、临时日志；恢复原 hooks.json（或删除临时文件）。

---

## 4. 证据与验收（L4 口径限定 Codex Desktop GUI 同 Thread）

通过 = 以下全真：

- [ ] 第二次回复仍在同一个可见 GUI Thread（原生 Thread ID 未变）
- [ ] 未新建 Thread / standalone job / 新卡片
- [ ] `stop_hook_active`：false → true
- [ ] 一次性 marker 消费后不再续命
- [ ] 临时 hook/marker/日志已清理，全局配置已还原

未通过/存疑 = 若第二次回复落在新 Thread、或需要新任务、或出现无限续命 → 如实记 `unverified`，并回退。

---

## 5. 实测结果（已通过，2026-08-24）

```text
第一次回复：DESKTOP_HOOK_INITIAL
        ↓
Stop hook 注入 continuation prompt
        ↓
第二次回复：DESKTOP_HOOK_CONTINUED
```

- `session_id: 019fa820-4cd7-77c2-9e0d-50600edc2300`（与 `24` Heartbeat L4 同一个 Thread）
- 第一次 `stop_hook_active: false`；第二次 `stop_hook_active: true`；第三次：无
- 同一个可见 Thread；没有新建 Thread 或新卡片
- marker 已消费；无无限续命；临时配置 / 脚本 / 日志已清理

**Desktop L4 通过 ✅**：`Stop` hook 在 Codex Desktop 可见 GUI Thread 内 block 续步，续出的第二次回复仍属同一 Thread（`019fa820…`）。

回填完成：`25` §4「仍未验证」项已转为已验证；`22` §2.2 的 Codex hook 证据等级 =「CLI same-flow + Desktop GUI same-thread」。