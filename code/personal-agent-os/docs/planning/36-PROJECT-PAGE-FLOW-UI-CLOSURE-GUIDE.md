# PAOS Project 页面流程与 UI 收口开发指导书

状态：待实施  
目标版本：v0.6.1 UI closure  
实施对象：DSH  
范围：只改 PAOS Project 页面前端与聚焦测试，不改后端接口、Project/Work/Session 数据模型和写入语义。

## 1. 结论

当前页面已经装入新版功能，但没有形成一条完整、紧凑的用户流程。它仍按“对象栏目”排版：先展示 Agent 列表和 Start Agent，再展示 Work 列表和 Create Work。用户看到的是两套并列管理面，而不是“Work 正由哪些 Agent 推进”的项目运行图。

本轮不要继续修补现有两列高度。应把页面收敛成：

```text
项目当前事实
→ Work ↔ Agent 关系板（主工作面）
→ Needs Me / Coordinator（人类控制点）
→ 点击节点查看详情或继续工作
→ 创建 Work、启动 Agent 只在需要时弹出
→ Evidence / History / Admin 默认折叠
```

完成后，用户进入 Project 页的第一屏应能回答三件事：

1. 现在最该处理什么；
2. 哪些 Work 正由哪些 Agent 推进；
3. 我需要继续现有 Agent、新开 Agent，还是创建新 Work。

## 2. 实测问题

审查对象：`project.html?id=3002`，1280 × 720 桌面视口，真实 Project 3002 数据。

### 2.1 阻塞问题：关系板渲染失败

页面显示错误：

```text
setHtml 只接受 html`` 产物，收到普通字符串
```

`GET /api/projects/3002/relations` 实际返回了完整数据，其中包含 9 条当前 active 关系；空白关系板不是后端没数据。

根因位于 `project-relations-ui.mjs`：

```js
model.works.map(...).join("")
model.agents.map(...).join("")
```

`.join("")` 把受信任的 `html`` 片段降成普通字符串，随后 `setHtml()` 按合同拒绝。`renderCards()` 抛错后，`drawEdges()` 没有机会获得节点，所以 SVG 中 path 数量为 0。

现有测试只检查关系板占位元素存在，并只测 `buildRelationBoardModel()`；它没有执行真实卡片渲染，因此结构存在、测试通过、页面仍为空。

### 2.2 主流程错列

当前桌面布局实际是：

```text
参与 Agent 列表（左） | Start Agent 长表单（右）
Create Work 折叠面板（左） | Work 列表（右）
Suggestion 列表（左） | 纠错面板（右）
```

因此 Agent 和 Work 仍然分属上下两行。用户必须先阅读一份 Agent 清单，再向下寻找另一份 Work 清单，靠记忆拼接关系。上方空白的 `WORK ↔ AGENTS` 并没有替代这两份清单。

### 2.3 折叠的 Create Work 仍占半栏

`#create-work-panel` 初始 `open=false`，但它是两列 Grid 中的一个 item。Grid 默认 `align-items: stretch`，同排 Work 列表高度为 651px，于是关闭的 Create Work 外框仍被拉成 651px，形成整块空白。

顶部 `+ Work` 只执行 `scrollIntoView()`，不会把 `<details>` 打开。真实流程变成：

```text
点击 + Work
→ 页面滚到一个关闭且占据半栏的空面板
→ 用户再点击 summary
→ 才能填写
```

这是操作路径错误，不应只用 `align-self:start` 掩盖。

### 2.4 Start Agent 永久占据 725px 高度

Start Agent 是低频动作，却作为常驻主栏展示 Work、Role、Continue、Mission、Done When、Materials 和 Advanced Settings。它和 Agent 列表互相撑高，使主页面变成表单页。

“继续这个 Work”“继续 Agent”和顶部 `+ Agent` 都只是滚到同一个长表单，用户要重新确认上下文，页面没有形成“从所选 Work/Agent 进入操作”的局部流程。

### 2.5 列表内部滚动掩盖关系

- Agent 容器高 480px，真实内容高约 5430px；
- Work 容器高 544px，真实内容高约 7224px；
- Suggestion 容器高 544px，真实内容高约 1422px。

三个独立滚动区让用户在不同坐标系中寻找对象。即使恢复 SVG，关系板上方一套节点、下方两套列表仍会造成重复信息和定位分裂。

### 2.6 页面优先级仍不正确

项目页总高约 5122px。状态长文、空白关系板、Needs Me、Coordinator、维护折叠区、Agent/Work/Suggestion、文件、随后事项、Office 依次堆叠。新版模块已经出现，但旧对象管理页没有真正退出主视线。

## 3. 目标页面结构

### 3.1 默认桌面结构

```text
┌ Project Header ──────────────────────────────────────────┐
│ Personal Agent OS  /  当前阶段  /  Updated               │
│ [创建 Work] [启动 Agent] [···]                            │
└──────────────────────────────────────────────────────────┘

┌ NOW ─────────────────────────┬ NEEDS ME / COORDINATOR ───┐
│ 当前 Work、状态、下一动作      │ 只显示真正需要人的事项      │
└──────────────────────────────┴───────────────────────────┘

┌ WORK ↔ AGENTS ───────────────────────────────────────────┐
│ Work cards             SVG relations          Agent cards │
│ [w032 UI closure] ─────────────────────────── [agent3]    │
│ [w031 domain work] ────────────────────────── [agent2]    │
│ [w030 quality] ────────────────────────────── [agent1]    │
│                                                           │
│ Unassigned current work: 3              [查看全部]         │
└───────────────────────────────────────────────────────────┘

┌ Suggestions（有内容才显示，默认紧凑）────────────────────┐
└───────────────────────────────────────────────────────────┘

▸ Evidence & History
▸ Advanced / Admin
```

默认页面不再常驻展示完整 Agent 列表、完整 Work 列表、Create Work 表单和 Start Agent 表单。

### 3.2 关系板是唯一主工作面

关系板只默认展示当前关系：

- active edge；
- planned edge；
- 有 current 状态但没有关系的 Work，进入 `Unassigned current work`；
- historical edge 只在用户明确打开 History 时展示。

卡片使用紧凑高度，不重复完整 objective、note 和 Session 技术字段：

```text
Work：标题 / 状态 / active-planned 数 / 最近变化
Agent：名称 / runtime / 当前 Work / last active
```

点击 Work 卡打开 Work 详情对话框；点击 Agent 卡打开 Agent 详情对话框。详情对话框复用现有信息和操作，不重新定义领域状态。

关系排序需尽量减少交叉：

1. Work 按 active → planned → last activity 排序；
2. Agent 先按其第一个关联 Work 的顺序排列，再按 last activity；
3. 多 Agent 共同推进一个 Work 时相邻排列；
4. 窗口 resize 后重画 SVG；
5. 移动端隐藏 SVG，但卡片内必须保留关系摘要。

### 3.3 创建 Work 改为对话框

顶部 `[创建 Work]`、NOW 的无 Work 状态、Suggestion 的 `[创建 Work]` 都打开同一个原生 `<dialog>`：

```text
名称
目标
Done When
[创建 Work]
```

Suggestion 进入时预填同一对话框。创建成功后：

1. 关闭创建对话框；
2. 刷新项目和关系板；
3. 打开新 Work 的详情；
4. 在详情中突出 `[为此 Work 启动 Agent]`。

不要创建第二套表单组件，也不要把表单留在主页面占位。

### 3.4 Start Agent 改为上下文对话框

启动 Agent 使用现有原生 `<dialog>` 模式。入口包括：

- 顶部 `[启动 Agent]`：先选择 Work；
- Work 卡 `[启动 Agent]`：Work 已预选；
- Work 卡 `[继续]`：若只有一个 active Agent，直接进入该 Agent 的继续流程；
- Agent 卡 `[继续 Agent]`：Agent 与当前 Work 已预选；
- Coordination Request：Request 和目标 Work 已预填。

对话框首屏只保留：

```text
Work
New Agent / Continue existing Agent
Role
Mission（可空）
[复制并启动]
```

Done When、Materials、Runtime、Model、Context Level 全部放入一个 `Advanced` 折叠区。不要让低频字段决定主页面高度。

### 3.5 完整清单进入“查看全部”

现有 `#session-list` 和 `#work-item-list` 的渲染逻辑可以复用，但移入一个“查看全部 Work / Agent”的管理对话框或折叠区，默认不挂在主页面。

该区域用于查找和纠错，不承担默认理解路径。内部滚动可以保留，因为用户已经明确进入管理语境。

## 4. 视觉方向

本轮同时建立最小视觉基线，不另起一套 Design System 工程：

- 暗色底，低饱和青绿色作为唯一主强调色；
- 细边框、直角或 2–4px 小圆角；
- 高信息密度但增加组间留白；
- 标题可用窄体/粗体视觉，正文优先清晰中文字体；
- 状态主要靠文字、边框和小面积色块，不使用大面积高饱和填充；
- 连线颜色低于卡片文字，hover/focus 时只提升关联线和相邻节点；
- 不增加渐变、玻璃拟态、大阴影或装饰插画。

颜色饱和度应低于用户提供的 Brutalism 参考图。先用 CSS variables 收口现有颜色，不引入 UI 框架。

## 5. 实施顺序

### UI-01：恢复关系板正常渲染

范围：

- `project-relations-ui.mjs`
- `tests/project-relations.test.mjs`

要求：

- 使用 `joinHtml()` 或保持品牌类型的等价写法，禁止 `.join("")`；
- 对 Work 卡和 Agent 卡的真实 HTML 产物加测试；
- 断言 active edge 能生成对应节点；
- 浏览器只读验收中不再出现 `setHtml` 错误；
- 3002 真实关系接口有 active edges 时，DOM 必须出现 Work/Agent node，SVG 必须出现 path。

完成 UI-01 后单独提交，先让审查 Agent 验收，不要立即进入大布局改造。

### UI-02：重排主流程

范围：

- `project.html`
- `project-view.mjs`
- `project-session-ui.mjs`
- `project-work-ui.mjs`
- `styles.css`
- 对应 Node 测试

要求：

- 关系板升为主工作面；
- Agent/Work 完整列表退出默认页面；
- Create Work 和 Start Agent 改为 dialog；
- 顶部动作一次点击直接打开正确操作层，不再只滚动；
- 创建成功和继续 Agent 都保留原有 API 与 Prompt 合同；
- 不改后端、不新增 schema、不复制业务判断到 DOM 层。

完成 UI-02 后暂停，使用真实 3002 做完整流程验收。

### UI-03：关系交互和视觉收口

范围仍只限前端。

要求：

- 调整节点顺序以降低交叉；
- hover、focus、键盘导航均能突出邻接关系；
- 无 SVG 时仍可理解；
- 实施低饱和暗色 Brutalism 视觉变量；
- 1280px 与常用宽屏均无错列；
- 760px 以下退为单列卡片，隐藏 SVG。

## 6. 验收场景

### 场景 A：进入项目

- 首屏看到 NOW、Needs Me/Coordinator、关系板的开始部分；
- 不先看到长表单；
- 无前端错误提示；
- 页面默认高度不再由完整 Agent/Work 历史决定。

### 场景 B：理解关系

- 3002 当前 active edge 都能在关系板找到；
- Work 和对应 Agent 之间有可见连线；
- hover Work 只突出关联 Agent 和线；
- hover Agent 只突出其 Work 和线；
- unassigned current Work 有明确入口，不伪造 Agent。

### 场景 C：创建 Work

- 任意“创建 Work”入口一次点击打开对话框；
- 不发生先滚动、再展开；
- 创建后新 Work 立即出现在当前页面；
- 用户能直接继续“为此 Work 启动 Agent”。

### 场景 D：启动或继续 Agent

- 从 Work 节点启动时 Work 已预选；
- 从 Agent 节点继续时 Agent 已预选；
- Advanced 默认关闭；
- 复制 Prompt 的既有字段和协议不丢失；
- 不创建真实 Session 也能完成只读表单验收，真实写入另走受控测试 Project。

### 场景 E：历史和管理

- 默认不展示历史 Session、历史 Work、Files、Office 和纠错表单；
- 用户主动展开后仍能找到原功能；
- 管理区收起不会留下等高空白栏。

## 7. 测试要求

必须补的是能守住真实问题的测试，不增加 DOM 快照式大测试：

1. relationship HTML 产物保持 `html`` 品牌类型；
2. active relation 生成两端节点和 SVG path；
3. 顶部创建 Work 动作打开 dialog，而非只滚动；
4. 从 Work/Agent 入口打开 launcher 时预选值正确；
5. 默认主页面不存在常驻的完整 Start Agent/Create Work 表单；
6. 移动端无 SVG 时卡片仍包含关系摘要。

每个实施包执行：

```text
python scripts/verify.py
```

最后用两组数据浏览器验收：

- synthetic：空项目、1 Work/1 Agent、多 Agent 共推 1 Work、unassigned Work；
- 真实只读：3002，验证长数据、当前关系和页面密度，不写 `private-data`。

## 8. 禁止扩修

- 不改 Project/Work/Session schema；
- 不改 Coordinator、Needs Me、关系投影的后端语义；
- 不引入 React、Vue、状态管理库或图可视化库；
- 不为旧 DOM 长期保留两套入口；
- 不用 CSS 隐藏重复内容但继续双份渲染；
- 不通过截断真实关系制造“页面变短”的假象；
- 不顺手清理 3002 历史数据；数据语义清账是另一项工作；
- 不改 CAT。

## 9. 交付方式

三个实施包分别提交，禁止一次大提交：

```text
fix(ui): restore work agent relation rendering
refactor(ui): make relation board the project primary flow
style(ui): apply compact low-saturation project workspace
```

每包提交后报告：文件、用户流程变化、测试数字、真实浏览器观察、仍未处理的问题。UI-01 和 UI-02 后都必须等待审查放行，再进入下一包。
