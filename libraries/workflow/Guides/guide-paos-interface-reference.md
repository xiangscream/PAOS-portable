---
schema: paos-workflow/v1
id: guide-paos-interface-reference
title: PAOS 接口参考：读面、Project/UI/CLI、Library 与 Tips
description: 按用途读取的接口参考：Home 读面、Project 成果与工作台、Library/Tips 检索与修正、进度 CLI 及共用边界。
tags: paos, interface, reference, api, cli
status: active
version: 22
---

# PAOS 接口参考

本参考只说明已存在的只读/授权接口的用途、边界与读取条件，不新建权限、硬合同或事实源。命令参数以安装 CLI `--help` 为准，日常联系、当前页、Notice、安装与故障命令见 [PAOS 操作指南](guide-paos-cat-operations.md)。

## 用途索引

| 要做什么 | 章节 |
| --- | --- |
| 找回本人或成员责任、按范围读取 | [Home 读面](#home-读面) |
| 查看 Project 成果、历史与接受边界 | [Project 成果与历史](#project-成果与历史) |
| 寻找可复用 Workflow/Skill | [Library 资源检索](#library-资源检索) |
| 查找或读取已有 Tips | [Tips 检索与读取](#tips-检索与读取) |
| 维护 Project 阶段/进展/缺口 | [Project 进度 CLI](#project-进度-cli) |
| 核对一条接受引用的本地原件字节 | [接受引用核验](#接受引用本地字节核验) |
| 查看某条 Tip 被哪些现行方法吸收 | [Tips 吸收去向](#tips-吸收去向只读) |
| 读取本项目经验原件 | [Project 经验](#project-经验只读) |
| 读取本安装 Tool 目录 | [Tool 目录](#tool-目录只读) |
| 盘点全部登记 Home 与联系包 | [安装/Home 覆盖](#安装home-覆盖只读) |
| 定位安装数据根与程序根 | [安装数据根](#安装数据根与程序根) |
| 预览升级差分与退出对象 | [安装计划](#安装计划只读) |
| 重建 Markdown 工作台 | [Markdown 工作台](#markdown-工作台) |
| 外部非成员投递/通知 | [外部调用授权](#外部调用授权a14) |
| 程序回退但保留新业务 | [程序回退](#程序回退a25) |

## 共用边界

- 读取结果保留并核对来源与范围、一致性、`observed_at`、来源指纹与可达性；范围内没有记录只说明本次读面未返回相应事实，不推断全局不存在。
- 摘要样本是**条数**上限，不是总字节或 Token 上界；长字符串与嵌套对象不截断。
- 引用、Artifact 登记、Decision `accepted` 与 Session Close 互不蕴含成果正式接受；缺少证据保持未知，不发明接受状态。
- 错误与合法零匹配必须区分；非法参数、配置损坏、来源缺失、越界都作为明确错误，不退化为空结果。
- Tips 只从当前 Core 解析的唯一 Inbox 根读取；按 ID 读取返回 `raw_markdown` 与原字节 SHA-256；检索先验证全部候选再应用过滤与 limit；`project` 是捕获自由文本，不映射 Project ID。
- Project 进度 CLI 只写四个 `generated` 字段；不据此新造 `next_items`/`key_files` 全局 Human-only 禁令。
- 尚未实现的写合同（Tips 编辑、结构化 Project 经验写 API）继续明确未实现；Tips 修正与版本链按“Tips 修正与不可变版本链”节、吸收去向按“Tips 吸收去向（只读）”节执行（吸收由 Owner 正常文件发布，无新 Core 晋升写接口），不新增平行索引。

## Home 读面

### 按本次工作范围读取

恢复本人责任后，先选择本次工作真正需要的读面，再展开长阅读。全局首页用于跨项目协调、优先级比较和确实需要了解全局的场景；单个 Project 的实施、审阅或交付，优先读取该 Project；只需核对某位成员的 Current、Task、输入与成果时，优先读取该 Project 下准确登记的 Home。

沿现有 /api/home 只读接口按需指定 project_id；确需核对单一成员时，同时指定 home_id。查询范围必须来自当前责任、登记信息或原输入，不按目录猜测身份，不把 Rooter 安装级 Home 当作 Project Session。参数及返回字段以同版接口与实际 --help 为准。

读取结果应保留并核对其 filter_scope、实际包含的 Project/Home、observed_at、来源指纹、可达性和过滤范围。范围内没有记录，只能说明本次读面未返回相应事实；不能推断系统全局不存在。读取失败、成员未登记、来源缺失或语义未知时，应保留具体断点，不把错误转换成空列表或“没有任务”。

局部读面用于减少无关读取，不取代正式恢复顺序、本人 Current、当前原输入和合法所需原件。涉及跨项目优先级、下游责任或项目历史时，再扩展到对应范围并直接读取必要原件；不要为了避免遗漏而默认下载全部项目和历史，也不要仅凭聚合摘要作出接受或完成判断。

全局首页与局部读面都复用既有 ProjectStore、Home resolver、TODO parser、团队联系读面及 Catalog。它们是同一事实源的不同过滤视图，不得维护另一份 Current、任务账本或接受状态。性能是否改善以相同环境、相同数据范围的实际测量为准；代码提供了更窄的读取路径，不等于已经证明端到端延迟或上下文成本下降。

### 单 Home 工作视图

当本次工作只需要核对本人 Current、Task、成果引用和下一步时，优先使用现有 /api/home/work?project_id=<id>&home_id=<id>，而不是请求全局首页或完整 Project/Home 聚合。

该工作视图只读取准确登记的 Project Agent Home 中的 TODO.md，并沿现有 TODO v3 parser 返回 Current、Tasks、计数和来源指纹。它是轻量工作索引，不读取 Notice、Mailbox、Runtime、Rooter Home、其他 Project/Home、Library Catalog 或 Project 历史。

使用前确认 project_id 和 home_id 来自当前责任或正式登记。接口要求两个参数各出现一次且不能为空；参数缺失、空值、身份不符、Home 未登记或原件不可读时，按实际错误处理，不扩大到整个 Project 或全局读取，也不把读取失败解释为没有任务。

读取后核对 home、filter_scope、observed_at、consistency、TODO 原始字节指纹及更新时间。当前语义更新时间缺失时保持未知；文件更新时间仅表示文件系统观察，不代替语义更新时间。若读取期间文件发生变化，或身份校验失败，不将该结果冒称为稳定的当前状态。

本工作视图只帮助快速找回工作责任，不替代正式恢复顺序、本人固定 ENTRY、当前原输入、Notice 已读/处理记录或合法所需成果原件。若需要判断输入是否已收悉、是否仍待处理、提醒是否受理、Runtime 是否可联系、下游是否实际接续或成果是否已接受，返回现有相应读面和原件核实；不得从 TODO 引用存在推断业务已接受或完成。

完整的 Project/Home 读面与全局首页继续保留，用于需要输入恢复、跨项目协调、优先级比较或完整联系状态的场景。轻量视图不创建第二份 Current、任务账本、接受状态或新的事实权威。

性能以相同环境、相同 Home 和相同数据条件下的实际测量为准。新增轻量接口仅表示提供了更窄的读取路径；在本地实测前，不宣称延迟、响应字节或上下文消耗已改善。

#### 紧凑 Home 工作视图

当本次工作只需找回当前目标、下一步、等待和仍在进行的任务时，可使用现有 `GET /api/home/work?project_id=<id>&home_id=<id>&format=compact`。省略 `format` 或指定 `format=full` 仍取得完整工作读面；未知、空白或重复的 `format` 按接口错误处理，不扩大读取范围。`project_id` 和 `home_id` 必须来自当前责任或正式登记，不按目录猜测身份。

成功响应的 JSON 包络为顶层 `ok`、`read_only`、`view` 和 `markdown`；Home、范围、观察时间、一致性及来源信息都位于 `view` 内，`markdown` 是顶层字段，不是 `view.markdown`。以下只展示包络和字段层级，不是完整字段清单：

```json
{
  "ok": true,
  "read_only": true,
  "view": {
    "schema": "paos-home-work-compact/v1",
    "observed_at": "2026-10-19T07:23:25Z",
    "home": { "home_kind": "project_agent", "home_id": "3002-s010", "project_id": "3002" },
    "consistency": "single_file_snapshot",
    "filter_scope": { "kind": "home_work", "project_id": "3002", "home_id": "3002-s010", "read": ["exact Home/TODO.md"] },
    "sources": {
      "todo": {
        "fingerprint_sha256": "以实际响应为准",
        "semantic_updated_at": "2026-10-19T07:20:00Z",
        "semantic_updated_at_basis": "current.updated_at",
        "filesystem_updated_at": "2026-10-19T07:23:24Z",
        "snapshot_basis": "same_bytes_parsed_and_hashed"
      }
    }
  },
  "markdown": "# PAOS Home work · compact (partial read-only view)"
}
```

最小访问示例只说明访问方法，不是完整 schema 合同：

```js
const response = await fetch("/api/home/work?project_id=3002&home_id=3002-s010&format=compact");
const body = await response.json();
if (!response.ok || body?.ok !== true) throw new Error(body?.error || `HTTP ${response.status}`);
if (
  body.read_only !== true ||
  body.view?.schema !== "paos-home-work-compact/v1" ||
  !body.view.home || !body.view.filter_scope ||
  typeof body.view.observed_at !== "string" ||
  typeof body.view.consistency !== "string" ||
  typeof body.view.sources?.todo?.fingerprint_sha256 !== "string" ||
  typeof body.markdown !== "string"
) throw new Error("Home compact 响应结构无效或不完整");
const { home, filter_scope, observed_at, consistency, sources } = body.view;
const markdown = body.markdown;
```

示例中的项目/工位标识只说明字段层级；实际调用必须使用当前责任或正式登记提供的准确标识，来源指纹读取实际响应值，不用示例占位文本。

紧凑视图只是从同一次已读取的准确 Project Agent Home/TODO.md 工作投影派生的展示摘要，不新增文件读取、写入、事实源或状态账。它突出选定的 Current 字段和最多 12 条非终态任务摘要；超出条数、被缩短的字段和未展开的终态任务必须明确标记。任务顺序沿 TODO 原有顺序，不代表优先级；引用只显示计数，不展示完整原始引用。需要准确 `source_refs`、`acceptance_refs`、完整结果或历史细节时，返回 `format=full` 或直接读取合法原件。

使用后核对 `view.home`、`view.filter_scope`、`view.observed_at`、`view.consistency` 与 `view.sources.todo`。`consistency` 只有 `single_file_snapshot` 表示同字节快照；出现 `changed_during_read` 时保留实际观察，不冒称稳定快照。来源更新时间按现行实现：`semantic_updated_at` 取自 TODO `current.updated_at`，缺失时为 `null` 且 `semantic_updated_at_basis` 为 `unknown`；`filesystem_updated_at` 只是文件系统观察时间，不代替语义更新时间。语义时间缺失或未知时保持未知，不用文件时间冒充。紧凑摘要不能证明输入已收悉或处理、Runtime 可联系、成果已接受或任务已完成；引用计数或存在本身不构成接受证据。若需要恢复输入、确认 Notice、联系状态或接受结果，返回现有相应读面和原件，不把紧凑视图当作完整恢复。

读取失败、HTTP 错误、未知 schema 或畸形响应必须作为明确失败处理，不能退化为空列表、空 Home 或成功结果，也不得因失败扩大读取范围。该接口只提供现有只读路径，不修改 ProjectStore、不标读 Notice、不创建任务、不调用模型或 Runtime。

当前实现仅提供更短的 JSON/Markdown 呈现路径；是否减少实际响应字节、延迟或模型上下文，应在相同 Home、相同 TODO 和相同环境下分别测量。字段访问示例或局部测试不等于已采用，不能据此宣称端到端性能改善。

## Project 成果与历史

当需要核对某个 Project 的已登记成果、成果版本关系、正式 Decision 及已有收口结果时，使用现有 ProjectStore 的只读成果读面：

`GET /api/projects/<project_id>/outcomes`

必须从当前责任或正式登记取得准确 `project_id`。读面只针对一个经 ProjectStore 校验的 Project 快照，返回观察时间、Project revision、当前可见的普通 Artifact 登记、Artifact lineage、Ledger 中明确保存的 Artifact 登记快照、当前 Decision 状态、已记录的 `decision.*` Ledger 事件，以及 Session Cycle 中实际保存的 Close 结果历史。它复用现有 Artifact lineage、Decision 和 Session Cycle 合同，不创建第二份成果账、接受状态或历史数据库。

使用后核对 Project ID、revision、`observed_at`、各部分的 `record_basis` 和历史完整性说明。当前 Artifact 仅表示当前 Project 投影中可见的登记成果；`replaces` 关系按现有 lineage 规则展示，分支不按时间、ID 或最近活动自动选胜者。Ledger 中的 Artifact 登记快照仅证明曾有该登记证据；若该 Artifact 当前已不可见，只保留为历史，不得因其历史事件把它复活为当前 head。旧式登记若从未保存历史快照，就明确保留历史缺口，不补造记录。

Decision 当前状态读取 `project.decisions`；事件历史只展示实际存在的 `decision.*` Ledger 事件。没有事件只表示当前读面未发现已记录的相应事件，不证明 Decision 从未被裁决。当前状态与历史事件须分别呈现，不根据标题、推荐、Session 结束或 Artifact 存在推断接受。

Session Close 历史只显示实际记录的 Close 结果及已有的修订历史。Runtime handover、管理方 abandon、普通 Session 结束、成果登记和 Decision accepted 均不等同于 Project 成果被正式接受。只有正式接受原件或当前合同明确记录的接受证据，才可作为接受结论；本读面不读取 Home/TODO 的 `acceptance_refs`，也不将其缺失解释为未接受。

本接口只读，不读取 Mail、Notice、Runtime 原生文件、Home/TODO、Library/Tips 或外部版本提供方；不验证外部 `version_ref` 的可达性，不读取 Artifact 路径对应的文件正文，不调用模型、不写 ProjectStore。需要检查接受引用、实际文件内容、输入处理、当前工位责任或运行状态时，沿对应的现有读面和准确原件核实。未知 Project 或读取/校验失败必须保留为明确错误，不当作空历史或无成果。

### 成果与历史只读 UI

需要查看单个 Project 已登记成果及其历史时，从项目看板打开“成果与历史”只读页面；入口应携带当前责任或正式登记提供的准确 Project ID。页面使用现有 `GET /api/projects/<project_id>/outcomes?view=summary|full`，默认展示每集合最多五条样本的摘要；需要完整记录时显式切换完整记录。不得新增另一份 Project 数据源、接受账或索引。

页面分别呈现当前可见的普通 Artifact 登记、Artifact lineage、Ledger 中明确记录的登记历史快照、当前 Decision 状态、已持久化的 `decision.*` 事件和实际保存的 Session Close 历史。保留 Project revision、观察时间、计数、历史依据和省略数量。摘要样本只限制条数，不限制总字节，也不保证模型 Token 上界；不能将摘要的计数或排序当作完整内容或接受证据。

必须显著显示以下语义边界：Artifact 登记、Decision accepted 与 Session Close 相互独立，不能据此推断 Project 成果已正式接受。当前读面不读取 Home/TODO 的 `acceptance_refs`，不打开登记路径指向的外部文件，也不验证外部 `version_ref`。正式接受结论须沿既有接受原件及合法读面核实；缺少证据时保持未知，不发明接受状态。

只读页面通过文本节点呈现不可信字段，不将 Project、Artifact、Decision、Session 或 Ledger 文本当作 HTML。未知 schema、缺少 Project ID、HTTP 失败或错误响应应显示明确失败状态，不伪装成空成果。切换摘要/完整记录只发起相应 GET；页面不写 ProjectStore、不标读 Notice、不创建任务、不调用模型，也不触发 Runtime 动作。

页面列出的“登记路径”只是来源定位信息，不代表文件已经打开或验证。历史登记快照不得复活为当前 Artifact head；lineage 的多个 head、分支或错误状态应如实呈现，不按时间或 ID 自动选胜者。需要查全 Vault 文件、实际文件内容、Home/TODO 接受引用、输入处理或运行状态时，返回相应现有读面和准确原件核实。

该 UI 是成果与历史的只读浏览入口，不是完整 Project 操作工作台，也不关闭 Tips 正式检索/修正、完整接受引用或 D3 覆盖等剩余事项。只有在对应切片完成原验证链和真实采用后，才能将相应能力标为 DONE/ADOPTED。

### CLI 资源检索与 Project 成果读面

当需要从终端寻找可复用的 Workflow/Skill，或查看单个 Project 的成果与历史时，优先使用现有 CLI 的只读入口：

- `paos library search "<查询词>" --kind all|workflow|skill --limit 20`
- `paos project outcomes <project_id>`
- `paos project outcomes <project_id> --full`

Library 查询复用已登记 Workflow/Skill 根目录和既有确定性匹配合同：不同空白分隔词项全部命中，大小写不敏感，结果保留准确相对路径、来源指纹和命中理由。没有登记根目录或接口返回错误时，应报告实际错误，不退回到仓库、Tips Inbox 或猜测路径。检索结果只代表词项匹配，不能替代打开原件后判断适用性。

Project outcomes CLI 默认请求每个集合最多五条样本的 summary；它保留 Project revision、观察时间、当前 Artifact/lineage/Decision/Close 计数、历史依据、每个集合最多五条样本及明确的省略数量。样本是**条数**上限，不是总大小界：长字符串与嵌套对象**不截断**，不保证总响应字节或 Token 上界。需要完整记录时显式使用 `--full`。原 HTTP 接口未指定 `view` 时继续返回完整读面；CLI 摘要是呈现范围选择，不创建新的事实源或接受状态。

Summary 只缩短响应展示，不隐藏语义限制：Artifact 登记、Decision accepted、Session Close 仍互不蕴含成果接受；历史事件缺失不合成，外部版本引用不视为已验证。摘要计数不证明成果已被完整读取或接受。需要准确来源、旧历史细节或接受证据时使用 full 并读取对应原件。

该入口只连接现有 Library search 与 ProjectStore outcomes HTTP 接口；不直接读写 ProjectStore 文件，不增加模型调用，不改变原生 Runtime、STOP、权限或安装配置。CLI/HTTP 路径可用性与真实安装采用仍按现有验证链分别核实。

### Project 工作台与接受引用只读呈现

当需要围绕一个 Project 继续实施、审阅或交付时，从项目看板进入 `project-workbench.html?id=<project_id>`，使用现有只读读面组合项目目标/当前方向、固定 Home 的成员与 TODO、Needs Me，以及 Project 成果与历史摘要。页面复用现有 `GET /api/projects/<project_id>`、`GET /api/projects/<project_id>/team`、`GET /api/projects/<project_id>/needs-me` 与 `GET /api/projects/<project_id>/outcomes?view=summary`；完整成果/历史继续由独立 outcomes 只读页提供。各读面分别读取，不构成跨文件原子快照，必须显示各自失败和观察时间，不能将一项读取失败折算成项目没有事实。

Home/TODO 的 `source_refs`、`acceptance_refs` 和 `artifact_ref` 只按原样展示为登记引用。页面不打开这些外部路径、不验证外部版本、不推断引用已接受；缺少引用只表示本次 Home 快照没有返回，不代表其它接受原件不存在。Artifact 登记、Decision `accepted` 状态与 Session Close 历史仍相互独立，不据此推断正式成果接受。正式接受必须沿现有接受原件和合法读面核实。

该工作台仅消费当前 ProjectStore、既有 Team/Contact/Home TODO 与 outcomes 投影，不创建新的项目状态、任务账、接受账、Library/Tips 索引或数据源。页面只读，不修改 ProjectStore/TODO、不标读 Notice、不创建任务、不调用模型或 Runtime。项目看板及旧 Project 入口可以导航到该工作台，但不得以工作台显示成功代替作者实施、S029 独审、S010 接受或 Rooter 实际采用。原被动读面（本工作台/outcomes）只展示未核验引用、不自动打开文件；显式本地字节核验见“接受引用本地字节核验”节。完整 Project UI、完整业务接受闭环、Tips 编辑、结构化 Project 经验写 API、Skill/Tool 整体业务与 D3 仍按原主线保持未完成；Tips 修正/版本链见“Tips 修正与不可变版本链”节，吸收去向见“Tips 吸收去向（只读）”节。

### 接受引用本地字节核验

需要核对 `tasks[].acceptance_refs` 中某条新式引用的两份本地登记原件是否与声明字节一致时，使用只读入口：

```text
GET /api/projects/<project_id>/acceptance-ref/verify?home_id=<home_id>&task_id=<task_id>&ref_index=<n>&todo_sha256=<64位小写hex>

paos project acceptance-check <project_id> --home <home_id> --task <task_id> --ref-index <n> --todo-sha256 <sha>
```

新式引用固定 `paos-acceptance:v1?`，必填 `project_id`、`evidence_artifact_id`、`evidence_sha256`、`target_artifact_id`、`target_sha256`；可选 `evidence_event_id`、`target_event_id` 精确选择历史登记事件，以及 `version_provider`/`version_revision`/`version_path` 三字段（同时提供或同时省略，只与目标登记 `version_ref` 整值比对）。未知键、重复字段、空必填值、fragment、坏编码、非法 ID/SHA 或保留前缀下的未知版本均 422；非 `paos-acceptance:` 字符串是旧引用，原样保留为不可核验。

核验只回答“所指本地文件是否与声明相符”，`business_acceptance` 始终为 `not_determined`，`check_status` 只取 `local_bytes_match`、`legacy_unverifiable`、`no_references`。它不判断真实业务接受，不替代接受人，也不完成全部 A16/A21。

- 同一 Project 快照内定位登记：未给事件 ID 时只按准确 ID 取当前 `project.artifacts`；给事件 ID 时只取该 Ledger 事件 `details.artifact_registration_evidence` 且快照 ID 必须相符；不按 ID 搜第一条历史，不选最新 head、不合并分支、不按时间猜版本。
- `todo_sha256` 必须等于本次同一 Home TODO 原字节指纹；不同先返回 409 `acceptance_todo_changed`，不打开成果文件。读取范围只有该 Project Agent Home 的 `TODO.md`，不新建 Session/Work、不要求活动 Cycle 或 ACK；安装级 Rooter Home 返回 400 `acceptance_home_scope_invalid`。
- 文件定位只来自选定 Artifact 登记的 `path`；支持根相对与根内正式绝对路径，拒绝 URI/UNC、drive-relative、`..`、越根、符号链接/junction、设备/非普通文件，以及受管目录（`Workstations/`、`.paos/`、`.obsidian/`、`.workbuddy/`、`.git`、安装 `private-data/`、ProjectStore 根、当前 Tips Inbox 根）。同一句柄流式 SHA，读取中变化返回 503。
- 任一步失败可短路，未执行检查的结果为 null/`not_checked`；成功但外部坐标仅表示本地登记，`external_version_status` 为 `unverified` 或 `not_applicable`，不发网络请求。
- 结果不返回文件正文或异常堆栈；多文件读取不是跨文件原子事务（`multi_file_atomic=false`）。
- 错误码：400 `acceptance_check_query_invalid`/`acceptance_home_scope_invalid`；404 `project_not_found`/`acceptance_home_not_found`/`acceptance_task_not_found`/`acceptance_todo_missing`/`acceptance_ref_not_found`/`acceptance_artifact_not_found`/`acceptance_registration_not_found`/`acceptance_source_missing`；409 `acceptance_todo_changed`/`acceptance_registration_mismatch`/`acceptance_version_coordinate_mismatch`/`acceptance_content_changed`；422 `acceptance_todo_invalid`/`acceptance_ref_invalid`/`acceptance_ref_scope_mismatch`/`acceptance_registration_invalid`/`acceptance_artifact_out_of_scope`/`acceptance_source_out_of_scope`；503 `acceptance_todo_unavailable`/`acceptance_source_unavailable`。

工作台只在用户点击某条引用的“核对原件字节”时调用，携带该行所属 Home 读面的 TODO 指纹；没有可靠指纹时要求刷新，不猜。响应中的 Project/Home/Task/index/TODO 指纹必须与当前选择相符，切换成员、Task、引用、刷新或重新核验后，晚到成功与错误都不得复活旧结果。页面以文本节点显示“本地字节相符，业务接受另核”，不把匹配计数当接受数，不改 Task/Project 完成状态，不在普通页面载入时批量核验。

原被动展示面（Project 工作台/outcomes）仍只展示 `acceptance_refs` 为未核验登记引用，不自动打开文件；本入口是用户显式发起的单条核对。

### Tips 吸收去向（只读）

需要查看某条准确 Tip 版本被哪些现行方法吸收时，使用只读入口：

```text
GET /api/tips/<tip_id>/absorptions?source_sha256=<64位小写hex>

paos tips absorptions <tip_id> --source-sha256 <sha>
```

吸收是**方法正文的正常维护与发布**：Owner 把已验证经验提炼进唯一现行方法，并在同一正文记录来源。没有新的 Core 晋升写事务、状态表、操作账、规则副本或自动方法生成器；Tip 原件与 D216 不可变版本链保持。

方法正文 frontmatter 可选一行 JSON 数组（不引入 YAML 依赖）：

```yaml
absorbed_tips: [{"tip_id":"tip-example","source_sha256":"<64位小写hex>","evidence_ref":"Works/example-review.md"}]
```

每个对象恰含 `tip_id`（`tip-[A-Za-z0-9_-]{1,120}`，精确大小写）、`source_sha256`（`tips read` 的完整原文件字节 SHA）、`evidence_ref`（1–1000 字符、非空、无 NUL；只作定位，不自动打开）。字段缺省保持旧资源兼容；存在时必须是合法非空 JSON 数组，字段/类型/ID/SHA/引用或同一 `tip_id+SHA` 重复均 422 `library_absorbed_tips_invalid`。新式注记要求正文**显式声明 `status`**；只有 `paos-workflow/v1`、准确 ID/title、`Guides/`/`Workflows/` 且 `status: active` 的当前正文才作为现行去向；Templates、候选/退役正文不参与。

读取先按现有 `read_tip_by_id` 取准确原件并核对请求 SHA；再沿本机登记解析 Workflow 根，从正文原字节读取注记（同一字节解析与指纹），不读旧 Catalog、仓库、Project 或提示词。请求 ID/SHA 必填且各一次，未知/重复/坏编码拒绝；来源 SHA 不符 409 `tips_source_changed`，方法对同一 Tip ID 声明不同 SHA 返回 409 `tips_absorption_source_conflict`。Library 未登记/根失效/来源不可读明确 503；越根、链接/junction/reparse 拒绝；读取中变化 503 `library_source_changed_during_read`；资源重复 ID 422 `library_duplicate_id`。

成功包络 `paos-tip-absorptions/v1`：`ok=true`、`read_only=true`、`business_acceptance=not_determined`、`status=matches|no_matches`、Tip 身份/来源定位/SHA、`observed_at`、`multi_file_atomic=false`、`scope` 与 `targets`。每个 target 含 `library_kind=workflow`、ID、title、section、`relative_path`、声明 `version`（缺失为 null，不伪造）、方法正文 `source_sha256` 与本次 `evidence_ref`；同一方法多条命中只返回一次，按 ID/相对路径排序。`no_matches` 只表示本次范围无当前匹配，不表示从未吸收或无价值。方法声明与证据字段不等于程序证明审阅、发布、使用或正式接受。

工作台在已打开的 Tip 原文详情提供“查看吸收去向”，只在点击时请求并携带该详情的准确 ID/SHA；没有可靠 SHA 时提示重新读取，不发猜测请求。新查询、清空、关闭、切换 Tip 后，晚到成功与错误均失效。结果用文本节点显示方法定位/版本/实际 SHA/证据引用及“这是方法正文的来源注记，业务接受另核”；不增加晋升写表单或自动改方法按钮。

本片只覆盖已登记 Workflow Library 的 `Guides/`、`Workflows/`；Skill、Tool Index、Project 经验与自动晋升仍未完成，不借此批量导入或改 Kernel。

### Project 经验（只读）

需要从项目自身积累中找回经验时，使用固定入口：

```text
GET /api/projects/<project_id>/experience

paos project experience <project_id>
```

唯一原件是当前 Project 登记根下的 `Materials/TIPS.md`（名称大小写固定）；不接受请求提供 path/root/URI 或其它候选文件。它是普通 UTF-8 Markdown，由 Project Owner 通过正常文件/Git 维护；本片没有 Core 写 API、CLI 写命令、自动捕获或晋升。无经验不凑条数；已有其它经验文档不自动搬迁或合并，可指向真实原件，Core 不跟随链接。Status/版本链不新增；文件历史仍在 Project Git。

服务只读一次 Project 快照，沿正式 Windows/WSL locator 解析登记根；从固定入口读取同一份原始字节（最多 262144 字节，不截断），严格 UTF-8 解码，BOM/CRLF 不改写，SHA-256 直接按原字节计算。只打开普通文件并确认句柄最终位置在根内；拒绝 symlink/reparse/junction、越根与非普通文件；读取中可观察变化返回 409 `project_experience_source_changed`。路径、SHA、字节数与正文来自同一读取。

成功包络 `paos-project-experience/v1`：`ok=true`、`project_id`、`project_revision`、`observed_at`、`read_only=true`、`business_acceptance=not_determined`、`filter_scope`（`registered_project_root` / `Materials/TIPS.md` / `recursive=false`）与 `document`（相对路径、实际运行路径、原字节 SHA、字节数、文件系统修改时间、完整 `raw_markdown`）。mtime 只是文件系统观察；SHA 相同不等于业务接受或晋升。

错误：400 `project_experience_query_invalid`（不接受任何查询参数）；404 既有 `project_not_found` 或 `project_experience_not_found`（尚未建立，不 mkdir/建空文件）；409 `project_experience_source_changed`；422 `project_experience_invalid`（空/仅空白、非 UTF-8、超限）与 `project_experience_out_of_scope`（跳转/非普通文件/越根）；503 `project_experience_source_unavailable`（root 缺失/权限/IO/句柄无法确认，不降级猜其它路径）。

工作台“Project经验”区域初始不取正文，点击后读取当前准确 Project；显示位置、原字节 SHA/字节数、观察时间与正文（文本节点，不执行 HTML/链接），可关闭并再次读取最新版本。重复读取或关闭后旧成功/失败不得回填，且该区域请求不取消 Tips 原文/历史/head/吸收去向等其它读面。页面没有编辑、创建、接受或晋升按钮。




### Markdown 工作台

`paos workbench build [--home <Home>] [--project <Project>] [--changed-only]` 从现有事实重建四类 Markdown 页，输出到登记 `data_root/workbench/`：安装、Project、精确 Home、资源导航，并生成 `INDEX.md`。

- 页面复用安装计划、Project registry/Home 覆盖、精确 Home 读模型与已登记 Workflow/Skill 目录；显示来源、版本/指纹、观察时间、缺失与过滤范围。Home 页不标读 Notice、不启动 Runtime；Notice 数不冒充任务数。
- 生成页可重建；人工修改按记录 sha 识别为冲突并保留原字节，不覆盖。`--changed-only` 按源签名跳过未变页；缺 Home/未登记 Home 如实报告且不创建。
- 正常安装生成的 Windows/WSL CLI 与 Core 启动器会设置投影开关及安装定位，写者可刷新 `homes/<id>.md`。底层调用未启用或调用方显式关闭 `PAOS_WORKBENCH_PROJECTION` 时不生成投影；失败/冲突以 `projection` 返回。是否本次更新成功看该回执及页面的来源、观察时间，不能把一次 `written` 当作后续所有写入的保证；当前责任仍以正式 Home 读面为准。无 marker 的补扫对已生成 Home 做逐文件元数据比较，并纳入 Project/Catalog 依赖；只重建受影响页，install/Catalog 依赖也参与补扫；INDEX 始终列出全部已生成页，局部刷新不缩减导航；Home 的 metadata 与 marker 同轮去重。冲突位置与投影未完成会显式返回。
- 写后局部刷新：TODO 写成功后，受影响 Home 页用新 TODO 字节立即重建（回归目标 <5 秒）；Notice 区域保留上次来源/指纹并明确标 `stale`，不冒充本次已重读。60 秒补扫由 `paos workbench watch --interval 60` 或 `scan` 作为每主机一个无模型维护入口，只重建受影响页并校正 Notice。
- 完整构建把 TODO/Notice 的观察时间与指纹写入元数据；快速刷新复用（不再 unknown）。依赖签名包含 Source revision、Project registry、Home 存在/状态与 Catalog；Home 签名含 TODO 与每个 Notice 文件字节哈希。
- 5 秒保证已提交的 TODO/任务/Current 真实更新；Notice 写后显示受影响 Notice 行并标其余 stale，由补扫校正。投影失败不回滚业务，但以独立 `projection` 字段暴露失败/冲突；changed-only 的 INDEX 保留未变页导航；依赖签名包含 Source revision 与目录 Catalog。GET 不写盘。
- 不复制 TODO/Mail 正文到 Source 或公开 Git；不改变 Current/治理模型，不引入第二状态源。


### 外部调用授权（A14）

同机受授权的外部调用方可不成为 PAOS 成员，通过准确 Home 的薄入口 `contact.py send|notify` 投递或通知。授权仅覆盖 `send`、`notify`、`remind`；不允许 prepare、代标读、审批、改模型/Thread/工具或读全邮箱。

- 私有授权配置位于安装 `data_root/contact/external-callers.json`（不进 Git/日志）：`grant_id`、稳定 `caller_id`、`token_sha256`、准确 Home `targets`、`actions`、`revoked`、限额。凭据经私有环境/标准输入传入，不进 argv/日志。
- `send` 先持久 Mail/Notice，默认不提醒；显式 `--remind` 且授权含 remind 才发一次既有提醒。`notify` 只引用该调用方在此目标的既有消息。
- 幂等命名空间：`caller_id + target Home + external message_id` 派生 `ext-…` Mail ID；正文指纹不进入派生。同键同文复用 dispatch/Notice，不重复提醒；异文拒绝。
- 默认限额：单目标、64 KiB UTF-8、每 caller 60 秒 10 次新操作；跨进程一致，重放不计数。缺失/损坏/撤销/凭据不符/越目标/越动作在投递前拒绝，零投递。
- 未配置授权时明确不可调用；生产 caller/token/范围/限额由 Human 指定，Rooter 只按授权配置或撤销。
- Core 不可用时复用文件服务与准确登记保存输入；必须 Core 的动作明确未完成，不启动第二 Core、不直写 ProjectStore。


### 程序回退（A25）

`paos install rollback --target-source <已存在绝对路径> [--compatibility-file <json>] [--apply]`。默认只读预览；`--apply` 才切换。

- 只切换安装描述的 `source_root` 到显式目标程序目录；不改/不恢复 `data_root`、Home/TODO/Mail/Notice、Project 事实与成果、Library 正文或私有授权。
- 目标必须已在准备，含 `scripts/paos.py`；不下载、不 pull、不按名字找版本、不整体重置 Source。
- 必须提供显式兼容声明 `paos-program-compatibility/v1`（`data_contract=paos-data-contract/v1`），冻结本次五个执行输入：`current_source`、`current_revision`、`data_root`、`target_source`、`target_revision`；revision 为 40 位 hex。preview 与 apply 使用同一文件校验；与任一值不符、未知合同或目标无来源依据时拒绝，不做版本号/日期/目录相近推断。
- 执行前取得现有内核 writer lease，仅证明该 Core 数据根没有活动 writer；它不代表 Home、CLI、投影或其他常驻消费者已全部停写。Core 写者占用时拒绝；完整停机窗口仍由 Rooter 按真实消费者清单核实。描述写入沿用原子配置写者，并保存唯一 `.before-rollback-<UTC>` 备份；失败不得留下半份定位。
- 切换定位不等于运行进程已加载新代码；服务按正常重载。生产回退/迁移仍需明确 Human 窗口，本命令不杀进程、不改模型/STOP/Contact、不迁移数据。

### 安装计划（只读）

`paos install plan [--target-source <明确路径>] [--retire]` 只读预览本安装的升级差分与退出/退役对象；`--json` 返回 `paos-install-plan/v1`。

结果包含：安装描述、Source/data_root/Library/Rooter 与登记 Home 归属；Source、运行 CLI、Core、Library 的版本与各自来源；受管文件（仅 Source git 跟踪的程序文件）、显式目标 Source 的新增/替换/退出差分；保留对象和未知项。Core 不由 Source 标签推断：plan 不访问 Core，运行版本显式为 `not_observed`。

- 升级目标必须显式给出本机路径；不下载、不 pull、不扫描其它安装。
- 升级差分不包含 `data_root` 与未跟踪用户内容；Home/TODO/Mail/Notice、Project 事实、共享方法、原始输入与采用历史不是退出对象。
- 人工改动按 Git 自身 `diff HEAD` 判定（遵循 autocrlf/换行规则），干净换行检出不算人工；真实编辑标 `manually_modified` 冲突并保留，不计普通替换或退役候选。目标新增路径若本机已有内容（含 ignored），标为冲突而不是无冲突新增。
- 无安装回执/生成正文证据的启动器保持 `owner=unknown`、保留，不凭名称或目录猜安装器所有。
- 退役预览只列有安装依据且本机未被人工修改的程序文件；启动器无回执时保留并标未知。其它宿主、服务、Hook 保持 `not_observed`，不凭目录相似或缺失记录猜可删。
- plan 无副作用：不写 installation/Project/Home/Contact/STOP/模型，不建备份/状态账、不停止或卸载服务、不删除文件、不迁移数据。实际备份、回退与卸载 apply 仍按后续明确范围执行。
- 描述错误、缺 data_root、Source 不可读等按既有错误码返回，不转空成功；非 git 工作树的所有权与差分为 `unknown`。

### 安装/Home 覆盖（只读）

`paos --json install homes [--project <Project> | --home <Home>]` 与 `GET /api/install/homes` 共用同一无副作用文件读服务，盘点本安装登记的全部 Project Agent 与 Rooter。CLI 在 Core 不可用时仍可读已登记本机文件；不启动第二 Core，也不要求 Core 在线。

包络为 `paos-installation-home-coverage/v1`，含 `ok/read_only/business_acceptance/observed_at/scope/summary/homes/issues`。`scope.total` 给出 Project 数、Project Agent 数、Rooter 数、登记身份总数；筛选后另报 `scope.filter`，不回写总数。Project 与 Home 精确筛选互斥；不存在的精确目标返回 404，不把过滤后 0 写成安装无成员。

每行给 `home_kind/home_id/project_id`、Project revision 与登记 lifecycle、Home locator、Home/ENTRY/TODO 存在与可读、TODO schema/身份检查结果（不返回正文）、三份联系包文件逐项状态与 `files_present_count`。联系包状态：`absent`（0 文件）、`partial`（1–2 文件）、`matching`（三文件可读且同当前模板）、`modified`（可读但有差异）、`unavailable`（Home 不可定位、路径冲突或不可读）。文件存在只算物理齐备；差异不判坏、不覆盖。

Contact 只返回白名单：是否登记、Runtime 类别、目标字段完整性、STOP 存在/缺失/未配置、配置来源、支持分类、条件与缺项；不返回 token、pipe、完整 target、原生会话数据库或配置原文。`native_reachability` 恒为 `not_observed`：本读面不探测 Runtime、端口或进程，Contact 存在不等于在线或可唤醒。

支持分类只描述当前代码的显式单次原生提醒条件，独立于文件齐备与当下可达性：

| classification | 判定 |
| --- | --- |
| automatic | 本片恒为 0；自动忙后/恢复须另立合同与实际证据。 |
| conditional | Home 可定位、目标字段完整、Runtime 属当前直接注入实现（Codex/OpenCode/WorkBuddy）；附 Owner 准备、目标可用、STOP 放行等条件。 |
| manual | Home 可定位但未登记原生目标；只能人工进入工作世界。 |
| unsupported | 目标声明的 Runtime 不在当前直接注入实现中；由原 Owner 处理，不换路。 |

无法可靠读取 Home/配置或目标字段残缺时分类为 `null` 并单列 `unclassified`，不是第五种支持类别。STOP 只作独立运行条件，不改写历史/暂停身份。

错误：400 未知/重复/互斥 query 或非法 ID；404 安装未登记、registry 根缺失或精确目标不存在；409 HTTP registry 与安装描述定位不一致；422 安装描述不合约；503 必要来源损坏、无法形成可信分母。单行缺失/修改/冲突保留行级 issue 并令 `complete=false`；一个 Project 源损坏导致分母不可知时全局失败。

本读面不执行 `contact.py`、不递归扫描 Home、不打开 Mail/Notice 正文、不写 Store 或状态文件。重复读取只更新本次 `observed_at`；多文件结果不是全局原子快照。


### 安装数据根与程序根

`source_root` 只定位程序；`data_root` 定位本安装的数据（registry、inbox、日志、plugin registry、环境能力等）。二者都由同一 `paos-installation/v1` 描述登记，沿既有 `--installation-file`／环境／用户默认描述选择，不另建配置或平行回退。

- `paos install show` 与 `status` 公开同一有效 `data_root`。已配置描述缺字段、空值或非法路径时明确报错（`installation_data_root_missing`/`invalid`），不推导 `Source/private-data`、不建空 Store。
- `paos install configure --data-root <绝对路径>` 首次登记或旧描述补字段时必须显式提供；已有值时省略该参数保留原值，显式空值为错误。写入保留 `rooter_home`、`agent_numbers_config`、Library registry 等未提交定位字段。
- Project registry/Home 路由、`install homes`、Core 的 registry/inbox/capabilities/plugin registry/日志、Windows host 日志与备份/恢复都以同一 `data_root` 为根；程序加载仍来自 `source_root`。
- 备份/恢复的 staging 与回滚目录位于数据根父目录；归档格式不变。查询不创建缺失数据根。
- Project Vault、Workstations、Project-local Contact、Rooter Home、共享 Library、工号表、Runtime receiver/STOP/token 不归并入 `data_root`。
- 两个 Source 指向同一 `data_root` 时仍只有一个 writer；D31 的 registry 来源冲突继续 409。数据字节不因定位统一而搬迁。

CLI/HTTP 读面不因新增字段改变业务事实；缺项与不可读保持显式错误。

### Tool 目录（只读）

需要从本安装唯一 Tool Catalog 查找工具的用途、调用入口、环境与限制时，使用：

```text
GET /api/library/tools

paos library tools
```

唯一来源是安装配置 `paos-library-roots/v1` 中可选绝对 locator `tool_catalog`，指向 `PAOS-Libraries/tool-catalog.md`（`paos-tool-catalog/v1`）。登记入口：

```text
paos library roots set --workflow-root <原根> --skill-root <原根> --tool-catalog <原件绝对路径>
paos library roots show
```

- 未提供 `--tool-catalog` 时保留已有 locator；旧 registry 无此字段仍合法，不影响 Workflow/Skill、Session Open 或工位创建。
- 新路径必须是存在、可读、合法 UTF-8、声明 `paos-tool-catalog/v1` 的普通 Markdown 原件；先验证再原子写配置，失败保留原 registry。Windows drive locator 存 `C:/…`，WSL 沿既有路径转换读取。
- Tool 原件仍由原 Owner 通过普通文件/Git 维护；Core 不安装、调用、检测或评价工具，不建第二份工具表，不扫描父目录或猜路径。

读取只接受无查询参数的 GET；CLI 是同一 HTTP 的薄包装，Core 不可达时如实失败。服务读取准确登记的普通文件，同一次原字节（≤256KiB），返回 `paos-tool-catalog-read/v1`：`source_path`（稳定 locator）、`source_sha256`、`byte_count`、`observed_at`、`content`（保留 BOM/换行）。不缓存长期正文；原子替换后下次读取反映新原件，读中来源替换/非普通文件 409 `tool_catalog_conflict`。

错误：未登记 404 `tool_catalog_unregistered`；原件缺失 404 `tool_catalog_missing`；非普通文件/读中替换 409；非 UTF-8/空/schema 不符 422 `tool_catalog_invalid`；超 256KiB 413 `tool_catalog_too_large`；权限/IO 503 `tool_catalog_unreadable`；任意/重复 query 400 `tool_catalog_query_invalid`。配置 JSON/schema 损坏沿原配置错误合同，不当作未登记。

工作台“Tool目录”区域默认不载入，点击后显示原件路径、观察时间、原字节指纹/大小与纯文本正文；不执行或自动打开目录中的命令/链接，不提供安装/运行/升级/登记/ACK 按钮。Skill 发现仍沿现有 Library 搜索与原件。


## Library 资源检索

当当前工作需要寻找可复用的 Guide、Workflow 或 Skill 时，先使用安装当前登记的 Workflow/Skill Library 资源检索读面：

`GET /api/library/search?q=<terms>&kind=all|workflow|skill&limit=20`

`kind` 缺省为 `all`，`limit` 缺省为 20、允许范围为 1–50。查询是 1–200 个字符；以空白分隔的不同词项必须全部命中，匹配采用大小写不敏感的子串规则。它是确定性的字段检索，不是语义搜索。标题、ID、标签、描述、标题行和正文按既定权重排序；结果包含匹配字段、每个词命中的字段、相关标题、可解释的命中理由和稳定排序，不应把分数单独当作适用性或质量结论。

检索范围只包含安装描述所指向的已登记 Workflow Library（`Guides/`、`Workflows/`、`Templates/` 中带合法 `paos-workflow/v1` 元数据的 Markdown）和 Skill Library（`<skill-id>/SKILL.md` 中带合法 `paos-skill/v1` 元数据的 Markdown）。仅 active 资源进入结果；来源引用为登记根目录内的准确相对路径，并附来源 SHA-256，供下一步直接打开原件核实。接口不返回正文摘录，不写文件、不创建任务、不调用模型，也不更新使用事件或 Catalog。

检索前先核查询、`kind`、`limit` 和安装登记状态。未登记 Library 时必须明确报告无法检索，不回退到仓库、Tips Inbox、猜测的 Vault 或其它目录。非法参数、配置损坏、根目录缺失、来源不可读、元数据冲突和路径越界都应作为明确错误处理；错误不等于零结果。只有成功执行且 `match_count=0` 时，才可报告本次登记范围内无匹配项，并同时保留查询词、范围和观察版本。

命中只表示词项与字段匹配，不表示资源适合当前任务、已被采用、已验证或具备当前环境依赖。打开准确相对路径对应的原件，核正文、状态、版本、适用范围和环境条件后再决定使用。不要仅因资源排名靠前就自动执行 Skill 或 Tool；使用结果按既有工作循环和权限执行，只有真实采用后才按现有合同记录使用证据。

此检索只覆盖登记的 Workflow/Skill Library，不是 Tips 搜索，不读取 Project Home/TODO、Notice、Mail、Runtime 或其它未登记目录，也不证明这些范围不存在相关经验。Tips 的只读发现与引用合同已在本页定义（唯一 Inbox 根、按 ID 读取、原字节 SHA-256、明确失败/零匹配）；编辑写接口与 结构化 Project 经验写 API 仍未做（只读原件见“Project 经验（只读）”节）；吸收去向见“Tips 吸收去向（只读）”节（Owner 正常文件发布 + 只读查询）。本页只落实捕获源的只读发现与引用（修正与版本链见“Tips 修正与不可变版本链”节），不新建平行索引。

## Tips 检索与读取

当需要查找或复用已有 Tips 时，使用当前 Core 解析得到的唯一 Tips Inbox 根目录，不自行猜测 `Materials/TIPS.md`、其它 Vault、仓库路径或跨安装路径。旧 `GET /api/tips` 继续承担捕获后的收件箱列表；它不是相关性检索。Workflow/Skill Library 搜索继续只搜索已登记的 Workflow/Skill 根目录，两者不得混用。

通过只读接口检索当前 Inbox：`GET /api/tips/search?q=<查询>&limit=20`；按稳定 ID 读取单条原件：`GET /api/tips/<tip_id>`。CLI 对应入口为 `paos tips search "<查询>" --limit 20` 和 `paos tips read <tip_id>`。CLI 必须在发出 HTTP 请求前按 `tip-[A-Za-z0-9_-]{1,120}` 校验 ID，并使用 URL 编码；包含 `?`、`#`、斜线或把查询串当作 ID 的输入必须明确报错且不发请求。HTTP limit 必须在整数转换前限制长度或安全捕获转换异常；超长数字一律返回参数错误，不能产生未处理的 500。检索仅扫描当前已解析 Inbox 根目录的直接普通文件，不递归，不跟随符号链接，不接受用户提供的路径，也不读取其它目录。无效查询或 limit 必须作为参数错误；可用来源中零匹配返回明确 `no_matches`；根目录不可解析、不可枚举或来源读失败必须作为来源错误；任意条目格式错误必须使整次搜索明确失败（HTTP 422），不得同时返回匹配结果或以 partial 表示部分成功；合法格式的 ID 不存在与 ID 本身无效必须分开返回。

检索采用确定性大小写不敏感子串匹配：空白分隔的不同词项全部命中；字段权重只用于排序，不代表质量或适用性。结果提供稳定 `tip_id`、逻辑引用 `tips-inbox:<tip_id>`、当前原文件字节的 SHA-256、每条结果的来源定位（当前 Inbox 根目录身份与文件名）、单次读取的 observed_at、匹配字段、各词命中字段及命中理由；按 ID 读取必须返回完整 raw_markdown，不得把解析后的 title/content 冒称完整原始 Markdown。时间戳仅是捕获/保存时间，不是 revision，也不用于伪造版本链。相对路径不能作为跨安装 URI 或权威来源身份。

按 ID 读取只从同一个当前 Inbox 根目录解析文件名，返回同样的逻辑引用、来源定位、observed_at、原字节 SHA-256 和完整原始 Markdown（raw_markdown），同时单独返回解析字段。调用方打开或核实内容时，必须确认引用的 Inbox 身份与当前安装一致；不能把 ID 当成任意路径，也不能跨安装自动跟随到其它根目录。SHA-256 证明返回摘要所对应的原始字节，不证明内容已接受、可信或适用。

本节的只读检索与单条读取不改变旧捕获/列表行为，也不编辑、晋升或写使用事件。追加修正与线性版本链见“Tips 修正与不可变版本链”节；吸收去向见“Tips 吸收去向（只读）”节（由 Owner 正常文件发布并记录来源，无 Core 晋升写入口）。编辑与重复/相似合并仍需单独的正式写合同，合同未接受前不新增这些动作。读取错误、零匹配和部分坏条目须保持可区分，禁止将错误折算为空结果。

### Tips 捕获项目文本精确筛选

当前 Tips search 可选 HTTP 参数为 `project`，CLI 参数为 `--project TEXT`。它只按捕获条目既有 `project` 自由文本筛选，不映射 Project ID、不形成项目隔离或权限边界。比较双方的 `strip().casefold()` 结果，要求完整字符串相等；不作子串、别名、内部空白折叠或 Unicode NFKC。字面 `null` 仍是普通文本。project 去首尾空白后长度必须为 1–200 个字符，且不能包含 NUL；重复或非法的 project 在发起请求前按同一错误合同拒绝。

先校验必需 q、limit 与可选 project，再枚举当前 Core 解析 Inbox。每个候选都必须完整按既有 D2.9 规则解析，之后才能应用项目条件和 q；任一候选损坏/不可读仍使整次搜索失败，不得被过滤条件或 limit 隐藏。最终交集沿原 `match_score desc, tip_id asc` 排序，再截取 limit。无筛选时旧搜索语义保持；结果仅增加 `project_filter` 描述对象（未传时为 null），不改原条目、原字节哈希、捕获文件、旧 Inbox 列表或 read 权限。

该片只改 HTTP 与薄 CLI；不改工作台，不新增写权限、索引、来源根或 Project ID 映射。原被动读面不自动核验（显式本地字节核验见“接受引用本地字节核验”节）；完整业务接受闭环、Tips 编辑写合同仍是独立后置事项（修正/版本链见“Tips 修正与不可变版本链”节；吸收去向见“Tips 吸收去向（只读）”节；Project 经验只读见“Project 经验（只读）”节），不阻塞本片。实现、测试与部署状态以本片实际候选、S032 验证、S029 独审、S010 发布和 Rooter 实际采用证据分别为准。

### Project 工作台 Tips 只读入口

Project 工作台（`project-workbench.html`）在既有面板后新增只读 Tips 检索区：直接复用当前 `GET /api/tips/search` 与 `GET /api/tips/<tip_id>` 的实际响应字段（搜索条目用 `content_preview`/`source_locator`/`source_sha256`，读取用 `raw_markdown`/`source_sha256`/`source_locator`）。

- 检索词 q 必填、最长 200 字符、不含 NUL；limit 取 10/20/50（缺省 20）。项目筛选只来自用户手填的自由文本，绝不自动填入当前 Project ID/名称；留空表示不筛项目，非空但非法（空白/超长/NUL）按错误处理，不偷偷变成不筛项目。服务端按既有 `strip().casefold()` 整值相等比较。
- 页面显式区分成功、合法 `no_matches`、HTTP/来源错误与畸形响应：未知 schema/字段、读取失败或不完整条目/来源（缺 ID、来源定位或原字节 SHA）不得变成空成功，也不以默认空数组隐藏错误。按实际 ID 展示逻辑引用、来源定位、原字节 SHA 与完整 `raw_markdown`；不把解析 content 当原文、不把 SHA 当正式接受或 revision。
- 新查询、清空、关闭详情、切换条目后，旧搜索结果、详情与旧错误一并失效，旧搜索/读取响应不得复原已失效结果；取消请求可优化但不替代“响应是否仍属当前操作”的判断，错误响应同样遵守过期规则。
- 结果、来源、错误与 Markdown 均按文本节点呈现，不用 innerHTML 渲染不可信内容。本节（工作台的 Tips 检索与原文读取）只发 GET，不写 Tip 或 Project 治理事实；显式修正仅按上节“Tips 修正与不可变版本链”的追加版本合同执行，不新增后端数据源、索引或来源根，不改模型/权限/绑定。工作台其余面板保持。

### Tips 修正与不可变版本链

修正 Tip 的路径是：按 ID 读取准确原件 → 提交带前置条件的完整修正版 → 取得新稳定 ID → 查看新旧版本 → 检索区分历史与当前版本。存储仍是唯一 Core 解析的 Inbox；追加不可变版本、单条线性链、不允许分叉、默认搜索保留所有版本。不新增第二个根、版本数据库或操作账；不实施晋升、删除、原地覆盖或自动合并。

- 写入口：`POST /api/tips/corrections`（CLI `paos tips correct --body @<request.json>`）。请求恰为 `schema=paos-tip-correction/v1`、`id`、`base_tip_id`、`base_source_sha256`、`title`（完整替换正文）、`project`、`reason`、`actor`。本机允许 `human`/`coordinator`/`worker` 追加；不新增身份制度，也不从旧 create 权限推导。新 ID 是幂等身份，不另加 operation-id。
- 修正版额外持久化 `version_schema=paos-tip-version/v1`、`previous_tip_id`、`previous_source_sha256`、`correction_reason`、`correction_actor`；五项必须完整，否则按畸形版本拒绝。旧文件不改，按旧 ID 读取仍返回原字节与 SHA。无版本字段的合法旧 Tip 是独立链首版。
- 并发与幂等：同一 Core/Inbox 单一互斥边界；同 ID 同请求返回 `created=false/replayed=true` 且不写文件（即使已有后继）；同 ID 异内容 409 `tips_correction_id_conflict`；base 非 head 409 `tips_base_not_head`（带 head 引用）；base SHA 漂移 409 `tips_base_changed`；不自动重基线、不生成分叉。发布前失败不留半文件，发布后按新 ID 核查。
- 读取与历史：`GET /api/tips/<id>`（`paos tips read`）仍只读该原件；新增 `GET /api/tips/<id>/history`（`paos tips history <id>`）返回 `paos-tip-history/v1`（root→head 顺序、每版 ID/SHA/前驱/保存时间/原因/角色，旧首版前驱为 null）。搜索默认返回所有命中版本，每结果附只读 `version`（`root_tip_id`/`previous_tip_id`/`head_tip_id`/`is_head`/`version_number`）；版本关系校验在过滤/排序/截断之前完成。
- 错误码：415 `tips_correction_content_type_invalid`、400/422 `tips_correction_invalid`、403 `tips_correction_forbidden`、404 `tips_base_not_found`、409 见上、422 `tips_chain_invalid`/`tips_entry_malformed`、503 `tips_source_unavailable`、500 `tips_correction_write_failed`。错误不回显完整 Tip 或凭据。
- 工作台 Tips 面板提供历史入口、打开当前版本与完整正文/project/reason 的修正表单；只提交一次新 ID，失败保留草稿与同一 ID；历史版不直接修正，用户先打开 head。

### Tips 尚未实现的写合同

编辑以外的 Project 经验入口仍未做；规则吸收由 Owner 正常文件发布并在正文记录来源注记，只读去向见“Tips 吸收去向（只读）”节；本参考只落实追加修正与只读历史/检索。通用规则再按既有分工进唯一 Workflow/Guide、Skill 或 Tool Index；在该范围落实前不新建平行索引。
## Project 进度 CLI

需要维护 Project 的阶段、进展与结果、最近变化或当前缺口时，可以使用 CLI `paos project progress-update <project_id>`，但这只是现有 `POST /api/agent/project-progress-update` 合同的薄入口，不是 Human 写入口，也不授予任意 Session 权限。调用方必须提供当前有效的 `--session-id` 或 `--handshake-id` 之一、读取时取得的 `--expected-revision`、非空 `--reason`，以及至少一个允许的进度字段：`--stage`、`--progress-and-results`、`--recent-change` 或 `--current-gap`。CLI 只组装现有 `paos-agent-project-progress-update/v1` payload 并提交给 HTTP/ProjectStore；服务端继续匹配当前受管 Session、校验 revision、`update_id` 幂等性、触碰路径冲突及原有 Ledger/receipt 规则。调用方不得自行构造或猜测有效 Session 身份。

该入口（progress-update）不暴露 `human.original_requirement`、`human.current_commitment`、`human.ddl`，也不改 `next_items`、`key_files`、Artifact、Decision、接受状态或 Session 历史。这是本命令的字段范围，不是对整体授权面的全局禁令：`next_items`/`key_files` 由既有受权 Agent 合同 `POST /api/agent/project-list-update`（authority `agent.project.list_update`，roles worker/coordinator）按整表列表更新，不是 Human-only；`human.original_requirement`/`human.current_commitment`/`human.ddl` 没有 Agent CLI 写口，仍走 Human 授权表面。不得据此新造“next_items 全局 Human-only”禁令，也不得把 Coordinator/Agent 的一般工作身份当作 Human 授权。

该 CLI 只扩展已存在的进度写合同，不新建 Project 数据源、任务账或新的写者身份，不调用模型或 Runtime 动作。参数错误应在发请求前明确失败；服务端仍负责最终授权与冲突裁决。验证应覆盖正确受管 Session 成功、未匹配 Session 不写入、缺少进度字段不发请求、revision 冲突不覆盖，以及回执与当前 revision 一致。
