# WSL 侧 Skill 来源（2026-10-02，由 3002-s032 按 w061 获批计划补齐）

WSL 内运行的真实 Skill 入口在三个位置；本页是来源与入口说明，不派生外部记录（依据获批统一计划："不手写不支持的外部记录、不为本轮索引扩产品代码"）。

| 来源根 | 内容 | 性质与消费口径 |
| --- | --- | --- |
| `/home/remo/.agents/skills/` | 27 个 `lark-*` 域技册（lark-doc/drive/im/mail/… 5.1MB） | lark-cli 各域官方入口册（progressive-disclosure：入口轻 + references/ 懒加载）。读操作入径；正文就读对应册 |
| `/home/remo/.config/opencode/skills/` | docx / pdf / xlsx / cpp-pro / daily-work-summary（2.8MB） | OpenCode 装载的通用技能 |
| `/mnt/c/Users/remo/.workbuddy/skills/`（Windows，经 /mnt/c 可达） | 11 个 WorkBuddy 技能（architecture-diagram、feishu-cli、fullstack-dev、grill-me、handoff、paos-cat-collab、playwright-browser-automation、product-function-tree、spec-writing、workbuddy-session-recovery；另有根级收口 JSON） | s014（WorkBuddy Runtime）的真实消费入口；**不整批迁移**，需收口能力时日后逐个按 shared 库规则迁移 |

- **feishu-cli 大单体拆分已完成**：canonical 在共享库 `skill/feishu-cli/`（主入口 + 四分册 references + 原单体《编号索引》附录，1428 行无收编损失）；原《LRC101 附加约定》的唯一现行落点在 Project 2001（`2001-LRC101\Works\Process\LRC101-Feishu-CLI项目约定.md`，导航见其 INDEX.md），3002 的 pending 文件仅作原文交接材料。**junction 切换（原 WorkBuddy 原位改链接）是已获批的入口采用责任，随本轮发布收拢执行；切换前核在途、保留恢复点，s014 实际消费未取得时不宣称已全员采用。**
- 有效自建 canonical 首读共享 [CATALOG.md](../CATALOG.md)；外部大索引已退出当前导航（见 [README](README.md)）。
