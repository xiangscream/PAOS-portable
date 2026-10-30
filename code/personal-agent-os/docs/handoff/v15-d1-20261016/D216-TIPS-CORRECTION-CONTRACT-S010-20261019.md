# D2.16 Tips 修正与不可变版本链

状态：产品合同已裁定，可直接实施；代码、测试、合并和安装尚未完成。

Owner：3002-s032；独审：3002-s029；产品裁定、接受及发布：3002-s010；正常安装采用：Rooter。

Source 基线：`a111c80967c7d3817b0c7fb38dff94768a0a8a05`，tree `6675d24969d0ef5995dcef31be63fb4f8b2d1eac`。Library 基线：`64badee756e7bbfe4379390db84db64b1cceab7b`，接口参考 v2，短工作循环 v41。

## 1. 目标与范围

修正 Tip 的正常路径是：读到准确原件 → 提交带前置条件的完整修正版 → 取得新稳定 ID → 查看新旧版本 → 后续检索能区分历史与当前版本。

本合同选择**追加不可变版本、单条线性链、不允许分叉、默认搜索保留所有版本**。当前版本仅表示该链最后一次成功修正，不表示经验已验证、成果已接受或规则已晋升。

唯一存储来源仍是 Core 当前解析的 Tips Inbox。不得新增 `Materials/TIPS.md`、第二个 Tips 根、独立版本数据库、head 文件、操作 receipt 账或后台消费者。不实施晋升、Project 经验入口、删除、原地覆盖、自动合并或自动去重。D215 不重做。

## 2. 原件与版本身份

- 每个版本是当前 Inbox 下一个独立的 `tip-*.md` 普通文件，使用既有 `tip-[A-Za-z0-9_-]{1,120}` ID；稳定引用仍为 `tips-inbox:<id>`。
- 已有文件不改正文、frontmatter、换行或时间；按旧 ID 读取仍返回该文件原始 Markdown 与其原字节 SHA-256，不自动跳到最新版。
- 无版本字段的合法旧 Tip 是独立链的首版。不批量补字段或迁移文件。
- 修正版保留既有必需 frontmatter 与 `# Tip` 正文格式，额外持久化以下五项。其余链信息从文件推导，不另存权威：

```yaml
version_schema: "paos-tip-version/v1"
previous_tip_id: "tip-example-original"
previous_source_sha256: "<前版原字节的64位小写SHA-256>"
correction_reason: "说明为何修正"
correction_actor: "worker"
```

五项必须完整。未知 `version_schema`、缺字段或仅出现部分版本字段按畸形版本拒绝，不静默当旧格式。`previous_tip_id` 只能是当前 Inbox 的合法 Tip ID，不接受路径、URL、跨安装引用或客户端指定根目录。正文中的普通外部证据链接不受此机器引用规则影响。

新版本的 `title` 是完整替换后的正文，`project` 是该版本完整的项目自由文本；两者沿用现有 trim、长度和 NUL 校验。原始捕获时间与 source 从前版继承，用于保留捕获出处；`savedAt` 为本次服务端保存时间。时间不是 revision。`status` 仍为 `inbox`，不暗示验证、接受或晋升。

## 3. 写入口、写者与输入

新增唯一正式动作 `tips.correct`：`POST /api/tips/corrections`。本裁定**明确允许**当前本机安装内的 `human / coordinator / worker` 角色追加修正版；Reviewer 沿既有 worker 角色，不增加新角色或身份制度。此授权不包含修改旧文件、晋升或其它治理动作，不从旧 create 的权限推导。

沿用本机单用户、loopback、Origin 和 JSON 写入边界。请求显式给出既有 actor；actor 是现有调用角色声明，不是新认证凭据，不宣称已验证某个自然人或 Agent 本体。Authority Manifest、Matrix 与处理函数必须同版表达此动作、合法角色、请求 schema 和真实文件副作用；拒绝缺失或非法角色。既有创建动作及其兼容返回保持，不附加新身份门槛。

请求恰为以下字段，不接受额外的写路径、savedAt、source、capturedAt 或权限参数：

```json
{
  "schema": "paos-tip-correction/v1",
  "id": "tip-example-correction-001",
  "base_tip_id": "tip-example-original",
  "base_source_sha256": "<按ID读取所得64位小写原字节SHA-256>",
  "title": "完整修正后正文，不是差分补丁",
  "project": "原有项目自由文本，可明确改正或清空",
  "reason": "补充证据后修正适用条件",
  "actor": "worker"
}
```

字段均必需。新旧 ID 必须不同；SHA 必须符合 64 位小写十六进制；`reason` trim 后 1–1000 字符且无 NUL。`title` 与 `project` 复用现有校验；空 project 合法。请求 `id` 同时是幂等身份，不另加 operation-id。

## 4. 并发、幂等与原子性

同一 Core/Inbox 的正式创建及修正发布使用同一个互斥边界，覆盖校验与提交。CLI 只调用 Core，不直接写文件。具体锁与临时文件实现由原作者选择，使用标准库和既有机制，不为此新增服务或外部依赖。

锁内执行顺序：

1. 校验请求并读取当前 Inbox 的合法文件与版本关系。所有版本只指向该 Inbox 的既有前版，父 SHA 与父文件原字节一致；检测缺失前驱、分叉、循环和非法关系，不按 mtime、文件名或最后写者猜链。
2. 先核新 `id` 是否已有**同一修正请求**：其 schema、前版 ID/SHA、规范化正文、project、reason、actor 均一致时，返回该已保存版本，`created=false / replayed=true`，不写文件。即使它后来已有后继，也不因旧 base 已非 head 而拒绝这个合法重放。已有 ID 对应旧 create、不同修正或不同内容时返回冲突。
3. 新 ID 尚不存在时，核 base 存在、原字节 SHA 与请求一致，并且 base 仍是该链唯一 head。不同请求同时修正同一 base，只能一份成功，另一份返回明确前置冲突和当前 head 引用，不能自动重基线或生成分叉。
4. 先在同目录完成并 flush 修正版，再以独占、原子发布方式让最终文件可见；不覆盖既有 ID。前版及其它版本不变。既有 create 也不得把半写文件暴露给新读面，行为和幂等语义保持。

发布前失败不留下可被扫描为版本的半份 `tip-*.md`；本次可清理自己未发布的临时文件，不清理别人的文件。发布后响应丢失，新文件本身就是 durable 幂等依据；同 ID 同请求可安全恢复，不增加第二份操作账。服务重启后从文件恢复关系，不依赖内存 head。

已存版本被人工改写、坏链或读来源失败必须如实拒绝；本片不设计自动修复工具。外部手工写入不属于正式并发写合同；安装继续遵守单 Core writer，不支持为多 Core 并跑另建协调平台。

## 5. 返回与错误

成功响应使用 `schema=paos-tip-correction-receipt/v1`，含 `ok=true`、`created`、`replayed`、本次版本 `item`、`source_ref`、`source_locator`、新原字节 `source_sha256`、`previous_tip_id`、`previous_source_sha256` 和只读派生的 `head_tip_id`。首次创建 HTTP 201，合法重放 HTTP 200。重放返回同一持久版本/原字节；派生 head 可以反映后来合法产生的后继，不冒称整份响应字节不变。

| 条件 | HTTP / error_code | 结果 |
| --- | --- | --- |
| 非 application/json | 415 / `tips_correction_content_type_invalid` | 无写入 |
| 非法 JSON、schema、字段、ID/SHA、正文、reason、自引用 | 400 或 422 / `tips_correction_invalid` | 无写入 |
| 角色缺失/非法或不符合写入口边界 | 403 / `tips_correction_forbidden` | 无写入 |
| 合法 base ID 不存在 | 404 / `tips_base_not_found` | 无写入 |
| 新 ID 已被其它内容或动作占用 | 409 / `tips_correction_id_conflict` | 不覆盖 |
| base 原字节已变化 | 409 / `tips_base_changed` | 返回准确 base/current hash，供重新读取，不自动重试 |
| base 已有后继 | 409 / `tips_base_not_head` | 返回当前 head 引用，不自动重基线 |
| 既有版本关系非法、缺前驱、分叉、循环或前驱 SHA 不符 | 422 / `tips_chain_invalid` | 不返回部分成功 |
| 既有条目格式损坏 | 422 / `tips_entry_malformed` | 沿现有来源错误边界 |
| 当前 Inbox 不可解析/枚举/读取 | 503 / `tips_source_unavailable` | 不是空 Inbox |
| 本次持久化失败 | 500 / `tips_correction_write_failed` | 原件保持；发布后的未知结果按新 ID 核查 |

错误正文不得回显完整 Tip、凭据或任意第三方错误正文。ID、准确错误原因和必要的 head/hash 可见。以上状态码与机器码在 HTTP/CLI/UI 保持一致；校验优先级导致同一坏请求先报一个明确错误即可。

## 6. 读取、历史与搜索兼容

`GET /api/tips/<id>` 与 `paos tips read <id>` 保持现有合同：只读取请求原件，返回完整原始 Markdown、准确 SHA 与定位；不为取得 head 扩大为全 Inbox 读取，也不被无关坏链阻断。语法合法但缺失与 ID 本身非法仍分开。

新增显式 `GET /api/tips/<id>/history` 与 `paos tips history <id>`。这是从唯一当前 Inbox 扫描、校验并派生所选完整链的只读操作，不存历史索引。响应 `paos-tip-history/v1` 含来源/观察时点、`requested_id`、`root_tip_id`、`head_tip_id` 及 root→head 顺序的 `items`。每项含 ID、逻辑引用/定位、原字节 SHA、前驱 ID/SHA、保存时间和修正原因/角色；旧首版的前驱和修正信息为 null。不返回每版完整正文；准确正文继续按 ID 读取。

搜索仍默认返回**所有命中的版本**，现有 schema、全部候选先验证、匹配字段/权重/顺序/limit 与自由文本 project 的 `strip().casefold()` 整值比较保持。版本关系校验也在过滤、排序和截断之前完成，不能把坏链藏在不匹配 project 或 limit 外。新增每结果的只读 `version` 摘要：`root_tip_id / previous_tip_id / head_tip_id / is_head / version_number`。版本序号由链顺序计算，首版为 1；不是 Project revision 或接受等级。

历史版本独有的词仍可命中该历史版本；不要用新版正文替换旧匹配，也不自动只搜最新。UI 必须标出“历史版本/当前版本”及 head 入口。本片不添加 latest-only 参数。既有 `GET /api/tips` 仍是捕获列表，不升级成版本权威或另一个检索根。

history/search 在需要扫描校验时遇到来源、条目或链错误明确失败；合法零匹配不等于来源为空。单次读取的字节用于解析与 SHA；多文件读取不是跨文件全局原子快照，不伪造全局 revision。

## 7. 必需 CLI / UI / 文档

- CLI 新增 `paos tips correct --body @<request.json>` 和 `paos tips history <id>`；复用现有 JSON/stdin 载荷入口。ID/SHA/请求形状在发 HTTP 前做既有风格的局部校验，不在 CLI 重建版本链或猜 Inbox 路径。
- 沿现有 Project 工作台 Tips 面板提供历史入口、打开当前版本、完整正文/project/reason 的修正表单和一次明确提交。只在该面板小改，不重做前端、Figma、Project 工作台或新建页面。历史版不直接修正，用户先明确打开 head；表单保留读到的 base ID/SHA。
- 提交时只生成一次新 ID，禁重复点击；失败保留草稿和同一 ID。网络结果未知时先按该 ID 核查；允许用户明确同 ID 同载荷恢复，不自动生成另一个 ID 或自动覆盖并发结果。成功显示新 ID/引用，旧版仍可打开。
- Source 正式合同与 Authority/Matrix 和实现同版；Library 只在接口参考的 Tips 节补准确完整合同及命令，撤下“修正/版本链未做”的失效部分。晋升、Project 经验未做的声明保持，短循环 v41 不再堆接口细节。改 Library 后正常重建 Catalog。

## 8. 验证、交付与采用

原作者从上述准确 Source 新建正常代码分支/PR，不操作生产 Tip，不沿网页草稿补造缺文。用隔离、合成 Inbox 做一次完整真实 HTTP 闭环及以下回归；现有 create、D29/D212/D213 读面、CLI/UI 与 Authority 回归一起跑，正式代码候选做正常 verifier 和 diff check。

1. 合法旧首版 → 修正版 → 再修正；每个旧 ID 的 Markdown/SHA 保持，历史顺序、head 和逻辑引用准确。
2. 同 ID 同请求重复及并发只生成一份；已有后继后再重放仍命中原版本。同 ID 不同请求冲突。
3. 两个新 ID 同时修正同一 base 只允许一份提交；SHA 漂移、非 head、非法 ID/路径、未授权角色均零 mutation。
4. 缺失前驱、分叉、循环、前驱 SHA 不符、畸形/不可读来源明确失败；project 不匹配和小 limit 不能隐藏坏链。单 ID 读取不因无关坏链扩大范围或失败。
5. 发布前 IO 故障不暴露半文件；发布后模拟响应丢失，同 ID 恢复不增版本；新服务实例从文件恢复链。
6. 既有 project 自由文本、所有版本搜索、旧正文命中、原始 Markdown/SHA 与创建幂等兼容；CLI 参数错误不发 HTTP；UI 显示历史/当前、冲突、失败及草稿，不能报假成功。
7. 隔离前后 Project revision、Work/Session/Request/Decision/Ledger、真实私 Tip 和模型/Contact/STOP/receiver 均未受本片测试误改。

S032 可自主完成已授权实施及自测，候选直接交 S029 独审并抄 S010；不等逐字段批准。S029 以同一最终 HEAD 核上述不变量和实际闭环，不另开全库普查。S010 接受后正常合并发布，Rooter 采用实际合并版本、必要 Core/前端与 Library；只做与本片相关的运行/read-only 核验，保留其它组件和原生会话。没有真实业务需要时，不为“采用”在生产新增或修正私 Tip。

本 planning 目录保存 `D216-EXECUTABLE-S032-20261019.md`、`D216-INDEPENDENT-REVIEW-S029-20261019.md` 及后续接受/采用原件。Source 代码和正式合同正常入同一 PR；Library 候选另存准确 commit 与 diff。这里的产品裁定是实施输入，实际发布后的 API 正文归 Source 合同，按需入口归唯一 Library 参考，不把本决策记录变成第二份运行手册。

交付保存准确 base/HEAD/PR、完整实现与合同、命令/结果、独审原件和采用读回；不得把本合同裁定、模拟测试、合并或提醒 accepted 任一单独称为 D216 DONE/ADOPTED。下一位从同一 Mail/Contact 接续并实际消费，真实 blocker 回原责任人，不回 Human 逐字段裁决。

## 来源

本地原始交接：`D216-CONTRACT-GAP-20261019-v0/` 的 README、最终回复、可见上下文、消息元数据、Source 只读核查及 PLAN-SECTION8；最终回复 `9fc6b0aa-2862-4e51-825d-6638c8ff4c1d` 只有合同缺口，不是本合同内容来源或已实现声明。暂现草稿未用于裁定。

现有行为已按基线 `attention-dashboard-v1-static/tips.py`、`local_server.py`、`authority_manifest.py`、`project-workbench-tips.mjs`、`scripts/paos.py` 的相关入口核对。当前 create、搜索/读取和 Authority 三角色是实际代码事实；新修正字段、线性链、权限动作与显式历史读面是本裁定，不冒称旧源码已经提供。
