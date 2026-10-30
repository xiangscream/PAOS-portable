---
name: architecture-diagram
schema: paos-skill/v1
id: architecture-diagram
title: Architecture Diagram
description: "画\"分层节点 + 多类型箭头流转 + 颜色独占轨道 + 步骤编号\"风格的高保真架构图、 资金流图、研发框架图、系统拓扑图。支持双格式输出：(1) HTML/SVG（用于 Smart Page / 网页报告 / PDF 嵌入）；(2) drawio XML（用于 draw.io / VSCode 插件继续编辑、PNG/PDF 导出）。 区别于 sequence-diagram（时间轴交互），本技能处理空间布局上的\"分层 → 节点 → 干线 → 扇出 → 闭环回灌\"模式。视觉风格：腾讯系商务蓝（#1664FF）/ 微信绿（#22C55E）双主色 + 苹方简体 + 严格的\"线-文不交叉 / 箭头不越框 / 同色独占轨道\"自检约束。内置\"HTML 预览 → 老板像素级 review → 迭代修复 → 一键转 drawio\"工作流，避免在不可视化的 XML 上盲调坐标。"
tags: diagram, architecture, visualization
status: active
version: 1
---

# Architecture Diagram · 高保真分层架构图（v2 · HTML 预览 + drawio 双输出）

## 何时触发

只要用户输入命中以下任一信号，就用本 Skill：

- 直接说"画架构图 / 资金流图 / 产品研发框架图 / 系统拓扑图 / 数据流向图"
- **想优化已有的 drawio 文件**（"读取这个 drawio 文件，用我们的技能优化"）
- 描述一个**有上下分层关系的多节点系统**（如"用户 → 收单层 → 主账户层 → 分账层 → 对公户"）
- 需要把"多个客户 / 多个商户号 / 多个银行 / 多个对公户"按列布局，再用箭头串起流转关系
- 在汇报 / 方案建议书 / Smart Page 里嵌一张"X × Y × Z 体系图"
- 用户给出"参与方 + 资金/数据流向描述"，要求空间布局而非时间序

⚠️ **不要用本 Skill 处理**：

| 场景 | 应该用 |
|------|--------|
| 多角色按时间顺序请求/返回 | `sequence-diagram` 时序图技能 |
| 文本描述的 mermaid/plantuml | 直接写文本，不走 HTML |
| 单纯的流程图（无明显层级，纯线性步骤） | 用普通卡片+箭头即可，不必上 SVG |
| PPT 内置形状能搞定的简单 5 节点图 | pptx skill |

## 双输出能力（v2 新增）

| 输出格式 | 何时用 | 工具链 |
|----------|--------|--------|
| **HTML/SVG**（默认） | 嵌入网页、Smart Page、报告内联预览 | 直接写 SVG，浏览器打开 |
| **drawio XML**（v2 新增） | 用户要求"二次编辑"、"上传到 draw.io"、"导出 PNG/PDF" | 写 `.drawio` 文件，用 `drawio` CLI 导出 |

**关键经验**：drawio 是"坐标 + 样式都不可视化"的 XML 格式，盲改容易翻车。**永远先用 HTML 预览迭代到老板满意，再 1:1 翻译成 drawio**。详见 Step 4。

## 核心范式：分层叙事 + 颜色独占轨道 + 干线-枝线

观察成功交付案例（腾讯出行二期资金流图、微企付建议书架构图、智能体自进化平台架构图），高质量架构图遵循三个核心原则：

### 原则 A · 分层叙事（4-6 层）

```
┌─────────────────────────────────────────────────────┐
│ Layer 1 · 入口层（用户 / 评审团 / 客户）   ← 多列分散
├─────────────────────────────────────────────────────┤
│ Layer 2 · 生产/承载层（核心业务节点一行排开）
├─────────────────────────────────────────────────────┤
│ Layer 3 · 能力/数据层（依赖能力 + 数据采集）
├─────────────────────────────────────────────────────┤
│ Layer 4 · 中枢层（评测/规则引擎/分账中枢）
├─────────────────────────────────────────────────────┤
│ Layer 5 · 出口/闭环层（CI回灌 / 对公账户）
└─────────────────────────────────────────────────────┘
```

每层左侧用固定 120-180px 宽的**专属标签区**（pill + 多行说明）解释合规叙事。

### 原则 B · 颜色独占轨道（v2 强调）

**每种颜色的箭头独占一条水平 / 垂直"轨道"**，避免同色箭头扎堆：

| 颜色 | 业务语义 | 推荐轨道 |
|------|----------|----------|
| 🔵 蓝 #1664FF | 生成主链路 / 控制流 | 沿层中线行内右向 |
| 🟠 橙 #F59E0B | 数据上报 / 采集 | y=388 / y=410（同方向同色错开 22px） |
| 🟣 紫 #8B5CF6 | 评测驱动 / 反向回流 | 底部 y=820 反向轨道 |
| 🟢 绿 #22C55E | CI/CD 回灌 | 行内 + 沿左边缘 x=160 上行 |
| ⚪ 灰虚 #86909C | 人工兜底 / 依赖 | 短距，stroke-dasharray="5 4" |

**关键**：同向多条同色箭头，**绝对不要全压在同一根 y 上**——会糊成一坨。错开 20-30px 分到不同水平轨道。

### 原则 C · 干线-枝线模式（v2 强化）

汇入多个 → 单点：用"枝线 → 干线 → 主线"三段式：

```
节点A ─┐
       ├──── 干线（无箭头）────► 中央节点
节点B ─┤
节点C ─┘
```

实现：
- 三条短**枝线**（`endArrow=none`）从来源节点底部延伸到干线
- 一根**水平干线**（`endArrow=none`）连接所有枝线起点
- 干线中点引出**单根带箭头主线**进入中央节点

效果：视觉上整洁的"漏斗"，远胜三条线挤一坨各自带箭头。

## 七步工作流（v2 升级）

### Step 1 · 解析输入

从用户输入提取六要素（同 v1）。如果是优化已有 drawio 文件：

```bash
# 读取 drawio 并解析节点/边
python3 -c "
import xml.etree.ElementTree as ET
root = ET.parse('source.drawio').getroot()
for c in root.findall('.//mxCell'):
    if c.get('vertex') == '1':
        print('VERTEX', c.get('id'), c.get('value','')[:30])
    elif c.get('edge') == '1':
        print('EDGE', c.get('source'), '->', c.get('target'), c.get('value',''))
"
```

把所有节点 + 流转关系提取成清单，作为后续布局的输入。

### Step 2 · 列对齐 + 行分层（先在脑中布局）

**列中线**（同列节点 x 中心严格相等）：

- 6 列布局：300 / 540 / 780 / 1020 / 1260 / 1500（间距 240，节点宽 200）
- 4 列布局：290 / 520 / 750 / 980（间距 230，节点宽 180）
- 3 列布局：360 / 920 / 1480（间距 560）

**行 y 坐标**（同层节点顶部 y 严格相等）：

| 层 | y 范围 | 高度 | 用途 |
|---|--------|------|------|
| L1 入口 | 70 ~ 150 | 80 | 用户/评审团 |
| L2 生产承载 | 240 ~ 360 | 120 | 主业务节点（横排 6 卡） |
| L3 能力/数据 | 430 ~ 570 | 100~115 | 依赖能力 + 数据卡 |
| L4 中枢 | 655 ~ 780 | 125 | 评测集 + 引擎 |
| L5 闭环 | 880 ~ 950 | 70 | CI/CD 卡片行 |

### Step 3 · 写 HTML/SVG 预览版（必做）

用 `architecture-template.html` 作为骨架，把内容、连线全部用 SVG 写出。这是**给老板像素级 review 的预览版**，不要直接写 drawio。

> 💡 v2 经验：哪怕用户最终要 drawio，也**先写 HTML 预览**。HTML 改一次坐标只要 5 秒，drawio XML 改一次要看 30 秒坐标算半天。预览满意了再转 drawio。

#### 推荐双栏对照页结构

```
┌───────────────────────────────────────┐
│ 左栏：原图 SVG 1:1 复刻               │
│ 右栏：优化版 SVG（边迭代边改）        │
└───────────────────────────────────────┘
```

可拖拽对比 + 在浏览器里像素级看箭头（v2 新经验：永远不要 iframe + file:// 加载 drawio，会报"未找到确定性文件"，用纯 SVG 还原代替）。

### Step 4 · 老板像素级 Review + 迭代修复（v2 新增 · 关键）

**收到老板反馈不要返工，按"每条线独立修复"原则改**：

#### 4.1 老板用截图 + 红框圈出问题线（推荐让老板这么提反馈）

#### 4.2 对每条红框线，按下面这张表精确修复：

| 病灶 | 诊断 | 解法 |
|------|------|------|
| 长对角虚线斜跨整个层 | 来源节点列 ≠ 目的节点列 | **搬列**：把来源节点搬到目的节点同一列 |
| 多条同色箭头挤在同一 y 轴 | 共用一根水平轨道 | **错列轨道**：分到 y / y+22 两条不同水平线 |
| 多对一汇入，箭头拥挤 | 三条线各自带箭头进同一个目标 | **干线-枝线模式**：枝线无箭头汇入干线，干线单根带箭头进目标 |
| 短斜线（40-60px 偏角） | 来源中心和目的中心不同列 | **共用 x**：把箭头起止点都设在两者重叠的中心 x |
| 长曲线穿越其他卡片 | 走法贪近不绕路 | **走河道/边缘**：跨区箭头走中间留白河道或左/右边缘 |

#### 4.3 修复完截图再 review，往复直到老板说"差不多了"

### Step 5 · 严格自检（v2 扩展到 8 项）

- [ ] **L1 线-文不交叉**：line 不穿过任何 text 或带文字 rect
- [ ] **L2 箭头 marker 让位**：`y2 = 容器边沿 - 7px`，不扎入框内
- [ ] **L3 居中标签让位**：`text-anchor="middle"` 不正落在主线 x 上
- [ ] **L4 列对齐**：同列节点 x 中心严格相等
- [ ] **L5 marker 复用**：每种颜色一个 `<marker>`，所有同色箭头共用
- [ ] **L6 图例与主图一致**：legend 用 SVG marker（不要 CSS 三角）
- [ ] **L7 同色箭头不挤压**（v2 新增）：同向多条同色，必须错开到不同水平/垂直轨道
- [ ] **L8 干线-枝线**（v2 新增）：N→1 汇入必须用干线-枝线模式，不许 N 条独立箭头各自进同一目标

### Step 6 · 转 drawio 文件（仅当用户要求时）

用户说"生成 drawio 文件"、"上传到 draw.io"、"要可编辑文件" 时，把 HTML 预览版翻译成 drawio。

#### 6.1 用 `architecture-template.drawio` 作为骨架

#### 6.2 翻译要点（v2 新经验，避坑必读）

| HTML SVG | drawio mxCell | 注意 |
|----------|---------------|------|
| `<rect x y w h fill stroke>` | `<mxCell vertex="1" style="rounded=1;fillColor=#xxx;strokeColor=#xxx">` + `<mxGeometry x y width height>` | 颜色必须**带 # 号大写十六进制**，不要用 css var |
| `<line x1 y1 x2 y2 stroke>` | `<mxCell edge="1" style="endArrow=classic;strokeColor=#xxx" source target>` + `<mxGeometry relative="1">` | 优先用 source/target 锚定节点 ID，不要写死坐标 |
| 折线（path d="M x1 y1 L x2 y2 L x3 y3..."） | `style="...edgeStyle=orthogonalEdgeStyle"` + `<Array as="points"><mxPoint x y/></Array>` | drawio 用 points 数组指定折点 |
| 带文字的连线 | mxCell 上加 `value="..."` + `fontColor=#xxx;fontSize=11` | 不要再加单独的 text mxCell |
| `<marker>` | `endArrow=classic` 或 `endArrow=open` | drawio 自带，不用定义 marker |
| 干线（无箭头） | `endArrow=none` | 用 4-cell 模式：1 条带箭头主线 + N 条 endArrow=none 辅助 |
| `<g>` 分组 | drawio 没有等价物 | 把 group 拆开成多个独立 cell |

#### 6.3 关键样式片段（直接复制粘贴）

```xml
<!-- 节点（圆角 + 主色描边） -->
<mxCell vertex="1" parent="1"
  style="rounded=1;fillColor=#FFE6CC;strokeColor=#D79B00;strokeWidth=1.6;fontSize=14;whiteSpace=wrap;html=1;verticalAlign=middle;"
  value="&lt;b&gt;节点标题&lt;/b&gt;&lt;br&gt;&lt;span style='font-size:11px;color:#4E5969'&gt;副标题&lt;/span&gt;">
  <mxGeometry x="200" y="240" width="200" height="120" as="geometry"/>
</mxCell>

<!-- 行内蓝箭头 -->
<mxCell edge="1" parent="1" source="A" target="B"
  style="endArrow=classic;exitX=1;exitY=0.5;entryX=0;entryY=0.5;strokeColor=#1664FF;strokeWidth=2.4;">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>

<!-- 折线（走轨道）：会话→数据卡，走 y=388 水平轨道 -->
<mxCell edge="1" parent="1" source="session" target="data-user"
  style="endArrow=classic;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#F59E0B;strokeWidth=2.2;edgeStyle=orthogonalEdgeStyle;"
  value="会话埋点">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="300" y="388"/>
      <mxPoint x="1020" y="388"/>
    </Array>
  </mxGeometry>
</mxCell>

<!-- 干线-枝线（4 cell 模式） -->
<!-- 1) 横向干线（无箭头） -->
<mxCell edge="1" parent="1" style="endArrow=none;strokeColor=#F59E0B;strokeWidth=2.2;">
  <mxGeometry relative="1"><mxPoint x="1020" y="595" as="sourcePoint"/><mxPoint x="1500" y="595" as="targetPoint"/></mxGeometry>
</mxCell>
<!-- 2/3) 两条枝线（无箭头）从节点底部到干线 -->
<mxCell edge="1" parent="1" source="data-user" style="endArrow=none;exitX=0.5;exitY=1;strokeColor=#F59E0B;strokeWidth=2.2;">
  <mxGeometry relative="1"><mxPoint x="1020" y="595" as="targetPoint"/></mxGeometry>
</mxCell>
<!-- 4) 主线（带箭头）从干线中点进目标 -->
<mxCell edge="1" parent="1" target="eval-set" style="endArrow=classic;entryX=0.5;entryY=0;strokeColor=#F59E0B;strokeWidth=2.6;" value="汇入">
  <mxGeometry relative="1"><mxPoint x="1260" y="595" as="sourcePoint"/></mxGeometry>
</mxCell>
```

#### 6.4 校验 + 渲染

```bash
# XML 合法性校验
python3 -c "import xml.etree.ElementTree as ET; ET.parse('output.drawio'); print('OK')"

# 用 drawio CLI 导出 PNG / PDF（需要本地安装 drawio.app 或 brew install drawio）
/opt/homebrew/bin/drawio --no-sandbox -x -f png -o out.png input.drawio
/opt/homebrew/bin/drawio --no-sandbox -x -f pdf -o out.pdf input.drawio
```

> 💡 v2 经验：drawio CLI 在 sandbox 模式下会有 GPU cache 错误，但**不影响输出文件生成**。看到 `Unable to create cache` 不要慌，文件已经在了。

### Step 7 · 交付三件套

```
output/
├── architecture-vN.drawio    # 可编辑源文件（必）
├── architecture-vN.png       # 渲染图（建议）
└── architecture-vN.pdf       # 矢量备份（建议）
```

用 `deliver_attachments` 一次性交付全部三件套，按重要性排序：drawio 最优先（用户最常用）。

## 视觉规范

### 配色 Token

```css
/* CSS / SVG 用 */
--blue:#1664FF;  --blue-soft:#E8F0FF;  --blue-deep:#0E42B5;   /* 收单/控制 */
--teal:#14B8A6;  --teal-soft:#E6F8F5;  --teal-deep:#0E8A7C;   /* 中枢/合规 */
--green:#22C55E; --green-soft:#E8F8EE; --green-deep:#15803D;  /* 出口/分账 */
--orange:#F59E0B; --orange-soft:#FEF3D6;                       /* 警示/数据 */
--purple:#8B5CF6; --purple-soft:#F1ECFE; --purple-deep:#6D28D9; /* 评测/AI */
--red:#EF4444;   --red-soft:#FDECEC;                           /* 风险/断点 */
```

drawio 用相同的十六进制值（带 # 号），不能用 var。

### 字体

- 中文：`-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei"` 优先苹方简体
- 数字 / 英文：Menlo / Consolas
- **不用腾讯体**——架构图常出现在移动端预览，腾讯体在小尺寸下视觉过重

### 节点风格

| 节点类型 | 样式 |
|----------|------|
| 入口节点（用户/客户） | 白底 + 灰边 (#E5E6EB) + 圆角 8 + soft 阴影 |
| 中央枢纽节点 | soft 色底 + 主色边 (1.6~1.8 stroke-width) + 加粗 |
| 出口节点 | soft 色底 + 主色边 + 内嵌"作用"标注 |
| 体系容器（虚线框） | soft 色底 + 主色边 + `stroke-dasharray="6 4"` |
| 体系标签（pill） | 主色实底 + 白字 + 圆角 14-17 |

### 箭头规范

- SVG marker：`<marker viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="主色"/></marker>`
- drawio：`endArrow=classic` 即可
- 干线 stroke-width=2.4-2.6，枝线=2-2.2，资金流加粗到 3
- 箭头尖端规则：`y2 = 容器目标 y - 7-8px`，避免扎入容器

### 步骤编号

- 彩色矩形标签（fill=主色，文字白色，圆角 3）+ 紧邻的圆形数字徽章（fill=deep 色）
- 用阿拉伯数字 `1`/`2`/`3`，不用 ①②③（小尺寸下圆圈数字易糊）

### 响应式（仅 HTML）

- 桌面优先（max-width: 1620px）
- 移动端（≤ 980px）：canvas `overflow-x:auto`，svg `min-width:1480px`
- **不做窄屏压缩**——架构图压缩后所有对齐都崩，宁可横向滚动也不破坏几何

## 详细规则参考

- `visual-rules.md` — 6 条自检铁律的几何细节、坐标计算、错误案例
- `layout-patterns.md` — 分层叙事结构、干线-枝线模式、典型布局尺寸
- `drawio-cheatsheet.md` — **v2 新增**：drawio XML 速查表（节点/边/折点/分组）
- `iteration-playbook.md` — **v2 新增**：基于老板红框的 5 类病灶诊断+修复手册
- `architecture-template.html` — HTML/SVG 模板
- `architecture-template.drawio` — **v2 新增**：drawio XML 模板（5 层 / 18 节点 / 4 色轨道）

## 反面教材（历史踩坑实录）

这些坑在前期项目（腾讯出行二期资金流、微企付建议书、智能体自进化平台）中被用户**逐一纠正过**，不要再犯：

### v1 经典坑

1. ❌ `text-anchor="middle"` 步骤标签 cx 落在主线 x 上 → ✅ 必须左/右移开
2. ❌ 箭头 `y2=378`（容器上沿） → ✅ marker 三角扎入框内 7px，必须 `y2=370`
3. ❌ 三家乘客的支付线带拐弯 → ✅ 三列已对齐，竖直直达即可
4. ❌ 用 CSS `border:transparent` 画图例箭头 → ✅ 渲染成方块 bug，必须 SVG marker
5. ❌ 干线穿过中央节点的文字标签 → ✅ 主线必须从节点上沿/下沿出入
6. ❌ 信息流和资金流画两张图 → ✅ 用箭头颜色区分
7. ❌ 列宽不一致 → ✅ 同列节点中线 x 严格相等
8. ❌ 窄屏压缩 SVG → ✅ `overflow-x:auto` 横向滚动
9. ❌ 节点用渐变填充 → ✅ 商务图克制：白底 + 1px 边 + soft 阴影
10. ❌ 黑话写进图（"三入三出转一出"）→ ✅ 改成业务可读文案

### v2 新坑（智能体自进化平台案例）

11. ❌ **viewer.diagrams.net iframe + file://** 加载本地 drawio → ✅ 报"未找到确定性文件"，必须用纯 SVG 还原代替
12. ❌ **上下分层**导致箭头穿越无关模块 → ✅ 同行内能解决的就同行（如评审团搬到腾讯会议正上方），不要硬塞分层
13. ❌ **左右双区 + 中间河道**仍然乱 → ✅ 河道只够走 1-2 条线，超过就要改用"颜色独占轨道"
14. ❌ **三条同色箭头共用 y=395 一根轨道** → ✅ 错开到 y=388 / y=410 两条
15. ❌ **N 对 1 汇入用 N 个独立箭头** → ✅ 用干线-枝线（枝线 endArrow=none，干线 1 个箭头）
16. ❌ **Skill→Git 用 40px 短斜线** → ✅ 共用同一个 x 坐标，竖直直下
17. ❌ **直接写 drawio 盲调坐标** → ✅ 永远先 HTML 预览迭代到老板满意，再 1:1 翻译到 drawio
18. ❌ **drawio CLI sandbox 报错就放弃** → ✅ 看到 `Unable to create cache` 不要慌，文件已经生成

### v2 新坑（教育收支分离扣款案例 · 截图自检）

19. ❌ **用 `agent-browser screenshot ".selector"` 截 `overflow-x:auto` 容器内的 SVG** → 截出纯白图。✅ 改用 `set viewport <w> <h>` 设足够高视口 + `window.scrollTo(0, el.top+scrollY-20)` 把目标滚进视口顶部 + 视口截图，最稳定
20. ❌ **"收支分离"这类一进多出的枢纽**，资金流和信息流从同一节点底部两个不同 x 引出折线 → ✅ 资金流走左侧 x、信息流走右侧 x，各自竖直下行再水平拐向目标，两条折线全程不交叉；中间放主色 pill 标注"收支分离"点题
21. ❌ **双轨语义图**资金流和信息流同色难分 → ✅ 资金流用绿实线(#07C160)，信息流用蓝虚线(#1664FF stroke-dasharray="6 4")，图例同步区分

### v3 新坑（业务模式结构图案例 · 用户红框反馈）

22. ❌ **按"画节点A→画A到B的步骤标签→画节点B"的交替顺序绘制** → 后画的节点 B 会把前面画的步骤标签压住一角（老板截图红框圈出"标签被图层压住"）。✅ 严格三段式绘制：第一段画完所有实体卡片，第二段画完所有连接线，第三段统一画所有步骤标签（标签永远在最上层）。详见 `visual-rules.md` L7。
23. ❌ **步骤标签硬塞进两个容器表头之间的窄缝**（如"③生态分发"卡在中列表头和右列表头之间几十像素的间隙里）→ 视觉上像挤牙膏，容易让人误读步骤顺序。✅ 找更宽的留白区重新安放标签，哪怕离连接线稍远一点，也比挤在窄缝里可读性好。
24. ❌ **步骤标签起点 x 与连接线 x 不对齐**（标签矩形左边缘比连接线起点更靠左）→ 视觉上标签像是"溢出"了连接线范围。✅ 标签矩形的左边缘、右边缘都应完全落在连接线经过的空白区间内，不贴边、不超界。

## 上传到市场的注意事项

本 Skill 已设置 `agent_created: true` 和 `version: 2.0.0`，可以通过 `SkillManage` 上传：

1. 检查 `_user_meta.json` 中 source 标记是否合理
2. SKILL.md 顶部 frontmatter 必须有 `name` / `description` / `agent_created: true` / `license` / `version`
3. 不要在技能包里打包腾讯字体（版权），用户机器自取
4. 不要在示例里嵌入内部敏感信息（项目代号、客户名）

后续维护建议：
- 每完成一个新案例，回到本 SKILL.md 的"反面教材"部分追加新坑（v3 / v4 …）
- 模板文件按 v 大版本分文件归档（architecture-template-v2.html, v3.drawio ...）
