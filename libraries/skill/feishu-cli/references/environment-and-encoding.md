# 分册④：环境与编码故障（v1.0.70 双装 / PATH / UTF-16 / 中文 argv / WSL NAT）

来源：WorkBuddy feishu-cli 单体无损收录。
对应条目对照："★ 本机内联命令的四个必踩坑"（原行 786–796）与"Git Bash PATH 缺 /usr / 中文 argv 截断"（原行 1184–1191、1412–1421 中的 argv 条）物理位于分册②（因其处在 29–73 与 81–98 两段连续主线内），语义属本册——按任务检索两类问题都在这里先查。

收录区间：
> - 原文行 53–73
> - 原文行 127–141
> - 原文行 552–558
> - 原文行 1109–1126

---

## 环境（2026-09-08 实测修正）

- WSL 内 `lark-cli 1.0.70`，二进制路径：`/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli`（必须是这个绝对路径，**不要**调 PATH 默认的 `lark-cli` —— 它指向 v1.0.87 Windows .exe wrapper，找不到 config）
- 区分两份安装：
  - **v1.0.70**（Linux ELF，`/home/remo/.nvm/.../lib/.../@larksuite/cli/bin/lark-cli`）→ 能读 `/home/remo/.lark-cli/config.json`，OK
  - **v1.0.87**（Windows .exe，`/mnt/c/Users/remo/.workbuddy/binaries/node/cli-connector-packages/...`）→ 默认在 PATH 中优先被解析，找不到 config 报 `not_configured: identity=bot`，**不能用**
- user 与 bot 身份均 ready；编辑私人文档默认 user 身份（用户：张瑞翔）
- 每次会话先验证：

```bash
wsl.exe --exec bash -lc '/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli --version; /home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli config show'
```

成功标准：v1.0.70 出现 + `appId: cli_aad212b4b6789bcf` + `users: 张瑞翔 (ou_...)` + `workspace: local`。忽略 `.profile: line 28: n#: command not found` 警告和 WSL 代理提示。

**WSL 网络断流**：lark-cli 调用报 `Client.Timeout exceeded` / `connect: network is unreachable`（`authen/v2/oauth/token` 那一步最容易先挂）。常见于长时间会话后，NAT 出网会丢；DNS 解析通常还 OK（能解析域名但 TCP 不通）。

> **⛔ 不要自己重启 WSL。** 技能这里原先写的是「`wsl.exe --shutdown` 重启 WSL 实例即可」，2026-09-18 我照做，被用户明确禁止：「禁止你不经许可重启 WSL 实例」。
> 重启 WSL 会打断用户机器上所有 WSL 会话与其他正在跑的 Agent，属于越界动作。
> **正确做法：停下来，把「lark-cli 报 timeout 疑似 WSL NAT 出网丢失」告诉用户，由用户决定是否重启。**
> 如果只是想继续推进，可以先用 `wsl.exe --exec bash -lc '...'` 跑一条只读命令确认是不是真的断流，再把结论报上去。

## 常见故障速查

| 现象 | 处理 |
|---|---|
| `invalid file path` | @file 用了绝对路径 → 先 cd 再用 `@./文件名` |
| node: command not found | PowerShell 破坏 $PATH → 不要用 `lark-cli`（PATH 指向 v1.0.87 wrapper），改用 v1.0.70 绝对路径 |
| `not_configured identity=bot` | 调到了 v1.0.87 → 改用 v1.0.70 绝对路径（`/home/remo/.nvm/.../lib/.../@larksuite/cli/bin/lark-cli`）|
| `Client.Timeout exceeded` / `network is unreachable` | WSL NAT 出网断了（DNS 仍 OK）→ `wsl --shutdown` 重启 WSL 实例 |
| JSON 被截断 | 改 outline/section/keyword 局部读取，或 WSL 内解析后只输出摘要 |
| 中文乱码 | 终端解码问题，云端正文实际正确，不要据此改写云端 |
| 写入成功但 revision 没变 | 无效锚点或 no-op → 重新 fetch 换有效 block ID |
| 标题被替换成残句 | 富文本 span 局部匹配 → 取 block ID 用 block_replace 重建整块 |
| Wiki URL 无法 Drive 操作 | 先 `lark-cli drive +inspect --url "<wiki-url>"` 取底层 token |
| 回读看不到 callout/th 的颜色属性（`background-color`/`border-color`） | 用了默认 `--detail simple`，它会剥离样式属性（emoji 保留、颜色被剥）→ 改用 `--detail full` 回读，颜色会以 rgb/rgba 出现。验证样式必须 `full` |
| `Whiteboard clone failed. Retry later` | 画板 token 引用插入时服务端抖动 → 立即重试一次即可；落地 `block_token` ≠ 源 `board_token`（飞书给副本重分配），这是预期 |

### 环境与编码

4. **`wsl.exe` 输出重定向到 Windows 文件会变成 UTF-16LE**，grep/正则解析全部失败。解法：脚本内把日志写到 Windows 可访问路径的 utf-8 文本文件，再用 Read 工具读；不要在 bash 管道里解析。
5. **node 版本目录会被升级改名**（`22.22.2` → `22.22.2-2`），硬编码版本号的 node 路径会静默失效。`~/.workbuddy/binaries/node/versions/` 下有 `current` 文件存当前目录名，**动态读它拼路径或先 `ls versions/`**。
6. **从 Windows 侧调 lark-cli 的可行姿势**：写 `.bat` 用绝对路径调 `node.exe <cli>/node_modules/@larksuite/cli/scripts/run.js`，用 PowerShell 执行 .bat，输出重定向到文件后读。**直接 PowerShell 调 node.exe 拿不到任何输出**（exit 0 但无 stdout）；`lark-cli.cmd` 从 PowerShell 直调也不出结果。
7. **`config not_configured` 是独立问题**，修 node 路径不一定能解决。根因可能是会话 WSL 的 `HOME=/c/Users/remo`（Windows-style），读不到 Linux 视图下的 `/home/remo/.lark-cli/config.json`。修法：在能跑通 lark-cli 的 **WSL native shell**（不是 Git Bash 代理出来的）跑 `lark-cli config init --new` 走浏览器授权。
8. **API 变更**：`docs +fetch` 的 `--document-id` 已改为 `--doc`（可传完整 URL 或 token）。**症状：`unknown flag "--doc-id"`**，错误里会提示 `did you mean --doc-format, --doc?`。`--doc-id`、`--document-id` 一律不认，写 `--doc`。写之前先 `--help` 确认一次，别凭记忆拼。

### ★ 日志排查的两个坑（2026-09-17 实测）

1. **查限流不要用宽松数字匹配**。`grep 429` 会大量命中 `rss=429.5MB` 这类**内存数值**——
   本次 93 处 "429" 里**真实限流为 0**，全是我自己正则太松造成的假阳性。
   正确模式：`queue\.waiting|HTTP 429|status[= ]429|429 Too Many|rate.?limit|Prompt refused`。
2. **WorkBuddy 会话卡顿的三类真因，判据不同**（配 `workbuddy-session-recovery` skill 使用）：
   - `[SessionRunStateMachine] ignored invalid transition | event=RUN_PREPARING | current=model_done`
     ＋ `[ACP Agent] RESULT: suppressed by interceptorGate` —— **一一对应成对出现**时，是**内存态状态机死锁**，
     **只有重启客户端能清**，改 DB 无效（DB 里的 status 可能仍是 `working`，别被它误导）。
   - **会话历史 `.jsonl` 过大**：本会话曾到 8.66 MB / 1744 行，单次追加最大 93,979 bytes（大文档粘贴）。
     每轮都要读这份历史 → 越往后越慢。**判据：`~/.workbuddy/projects/<slug>/<sid>.jsonl` 的大小与行数。**
   - **真实 429**：必须用上面那条精确模式确认，别被内存数值骗。
3. **`switch-work` 会把发起 Runtime 的写权限锁死（PAOS 侧问题，非本 skill 范畴，但会撞上）**：
   自发 `session switch-work` 成功后，该 Runtime 对 Session 的 **Ack / Update / artifact-add 全部 409**
   （`执行任期已变化：…旧 Runtime 不得把报告写入当前任期`），只剩读。
   因为 switch 创建了新 Cycle，而**新 Cycle 的 Context Pack 不在发起方手上**。
   **遇到这种情况：停止一切写入尝试、不重试、不改 DB、不臆造 context_pack_id，直接上抛给 Coordinator。**

