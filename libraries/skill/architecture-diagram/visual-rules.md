# 架构图视觉规则 · 6 条铁律自检手册

每次出图后必须像素级 review 这 6 项，任何一项不达标即视为不合格。

---

## L1 · 线段与文字不得交叉

### 规则
任何 `<line>` / `<path>` 的几何路径**禁止穿过**任何 `<text>` 或带文字的 `<rect>`。

### 常见违规与修复

#### 违规 A · `text-anchor="middle"` 标签骑在主线上
```svg
<!-- ❌ 主线 x=920，标签中心 x 也在 920，穿透 -->
<line x1="920" y1="280" x2="920" y2="380" stroke="#1664FF"/>
<text x="920" y="320" text-anchor="middle" font-size="13">D+1 入主账户</text>
```

修复：把标签整体右移，并改成 `text-anchor="start"`：
```svg
<!-- ✅ 标签右移到主线右侧 18px 处 -->
<line x1="920" y1="280" x2="920" y2="380" stroke="#1664FF"/>
<rect x="938" y="312" width="120" height="24" rx="3" fill="#0E42B5"/>
<text x="998" y="329" text-anchor="middle" fill="#fff">D+1 入主账户</text>
```

注意：rect 的 x=938 而不是 920，避开主线；rect 内部的 text 用 middle 居中没问题（参照系是 rect 内部）。

#### 违规 B · 横跨主线的提示框
```svg
<!-- ❌ 黄色提示框 x=820~1060 跨越主线 x=920 -->
<rect x="820" y="582" width="240" height="24" fill="#FEF3D6"/>
```

修复：把提示框整体推到主线一侧：
```svg
<!-- ✅ 推到主线右侧，左边沿 x=1000 > 主线 920 -->
<rect x="1000" y="582" width="240" height="24" fill="#FEF3D6"/>
```

### 自检方法
1. 列出所有 `<line>` 的 `(x1,y1,x2,y2)` 坐标范围
2. 列出所有 `<text>` 的 bounding box（中心 x ± 文字宽度/2，中心 y ± 文字高度/2）
3. 列出所有 `<rect>` 的 `(x, y, x+width, y+height)`
4. 对每条 line 与每个 text/rect，检查是否相交——线段几何穿过即违规

---

## L2 · 箭头 marker 必须为容器留位（不越界扎入框内）

### 几何原理
SVG `<marker>` 的三角形是画在线身**末端之外**的：
- `y2`（或 `x2`）= 线身末端坐标
- 实际箭头尖端 ≈ `y2 + marker 长度`（默认 `markerHeight=7-8px`）

### 规则
要让"箭头尖端"恰好停在容器边沿（如虚线框上沿 y=388），必须：
```
y2 = 容器边沿 - markerHeight ≈ 容器边沿 - 7px
```

直接写 `y2 = 容器边沿` 会让箭头扎进框内 7-8px，视觉上"越位、没规矩"。

### 错误案例
```svg
<!-- ❌ 虚线框 y=378，箭头扎进框内 7px -->
<rect x="220" y="378" width="1400" height="280" stroke-dasharray="6 4"/>
<line x1="920" y1="280" x2="920" y2="378" marker-end="url(#ah-blue)"/>
```

### 正确写法
```svg
<!-- ✅ y2=370，箭头尖端恰好停在 y=378 处 -->
<rect x="220" y="378" width="1400" height="280" stroke-dasharray="6 4"/>
<line x1="920" y1="280" x2="920" y2="370" marker-end="url(#ah-blue)"/>
```

### 适用范围
- 终点是虚线容器框：留 7px
- 终点是实线节点 rect：留 7px
- 终点是徽章/标签矩形：留 7px
- 终点是其他 line（连接两条干线）：可以恰好对接，不留位

### 自检方法
逐条检查每个箭头的尖端 y 坐标：
- 落在容器**边沿外侧 1-3px**（合格）
- 贴边（合格）
- 扎进框内 ≥ 4px（不合格，必须修复）

---

## L3 · 居中标签让位主线

### 规则
任何 `text-anchor="middle"` 的居中标签，其中心 x 坐标**不得正好落在某条竖线轴 x 上**。

### 修复策略
两种处理方式：

#### 方式 1 · 改 anchor + 偏移
```svg
<!-- ❌ 居中标签骑在主线 x=410 上 -->
<text x="410" y="760" text-anchor="middle">分账 → 小马智行</text>
<line x1="410" y1="658" x2="410" y2="772"/>

<!-- ✅ 改成 start anchor + 右移 10px -->
<text x="420" y="760" text-anchor="start">分账 → 小马智行</text>
<line x1="410" y1="658" x2="410" y2="772"/>
```

#### 方式 2 · 整体推开
```svg
<!-- ❌ 步骤标签矩形跨越主线 x=920 -->
<rect x="820" y="582" width="200" height="24"/>

<!-- ✅ 推到主线一侧 -->
<rect x="1000" y="582" width="200" height="24"/>
```

### 自检方法
对每条主线 x，检查是否有 anchor=middle 的 text 中心 x 与之相等。

---

## L4 · 列对齐（同列节点中线 x 必须一致）

### 规则
属于同一列的所有节点（rect），其**中线 x 坐标**必须严格相等。

### 计算公式
```
节点 rect 的 x = 列中线 x - 节点宽度 / 2
```

### 推荐列坐标

#### 3 列布局（间距 560）
- 列 1：中线 x=360（rect 宽 220 → x=250）
- 列 2：中线 x=920（rect 宽 220 → x=810）
- 列 3：中线 x=1480（rect 宽 220 → x=1370）

#### 4 列布局（间距 320）
- 列 1：中线 x=410（rect 宽 220 → x=300）
- 列 2：中线 x=730（rect 宽 220 → x=620）
- 列 3：中线 x=1050（rect 宽 220 → x=940）
- 列 4：中线 x=1370（rect 宽 220 → x=1260）

### 自检方法
对每列，列出该列所有节点的 `(x, x+width)`，确认 `(x+width/2)` 全部相等。

---

## L5 · marker 复用（每色一个 defs marker）

### 规则
每种颜色只在 `<defs>` 中定义**一个** `<marker>`，所有同色箭头共用 `marker-end="url(#xxx)"`。

### 标准命名约定
```svg
<defs>
  <marker id="ah-blue"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#1664FF"/>
  </marker>
  <marker id="ah-teal"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#14B8A6"/>
  </marker>
  <marker id="ah-green"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#22C55E"/>
  </marker>
  <marker id="ah-orange" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#F59E0B"/>
  </marker>
</defs>
```

### 关键参数
- `refX="9"` + `refY="5"`：让线段末端正好对齐三角形底边中点
- `orient="auto-start-reverse"`：自动跟随线段方向旋转
- `markerWidth/markerHeight=7~8`：与 stroke-width 比例 ≈ 3.5:1，视觉协调

### 自检方法
确认 `<defs>` 里每色一个 marker，不出现重复定义；所有 line 通过 `url(#ah-xxx)` 引用，没有 inline marker。

---

## L6 · 图例（legend）必须用 SVG marker，不能用 CSS 三角

### 规则
图例区的箭头**必须**用内联 SVG + marker（与主图风格 1:1 一致），**禁止**用 CSS `border` 三角伪元素。

### 错误写法（已知 bug）
```css
.lg-line::after{
  content:"";position:absolute;right:-1px;top:-5px;
  border:5px solid transparent;border-left-color:#1664FF;
}
```
**问题**：在某些渲染环境（headless Chrome、PDF 导出、特定 zoom 比例）下，`transparent` 边会被错误渲染成实心矩形，箭头看起来像一个蓝色方块——已在历史项目中被用户标红。

### 正确写法
```html
<span class="lg-line">
  <svg viewBox="0 0 38 10">
    <defs>
      <marker id="lg-blue" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="#1664FF"/>
      </marker>
    </defs>
    <line x1="0" y1="5" x2="30" y2="5" stroke="#1664FF" stroke-width="2"
          marker-end="url(#lg-blue)"/>
  </svg>
</span>
```

### 注意
- 图例的 marker id 要与主图 marker id 区分（如 `lg-blue` vs `ah-blue`），避免 SVG 内 id 冲突
- 图例 SVG 是独立的（不在主图 viewBox 内），所以不用担心坐标系冲突

---

## L7 · 绘制顺序：卡片 → 连接线 → 步骤标签（v3 新增，源头预防叠层遮挡）

### 规则
SVG 按文档顺序叠层渲染，后画的元素会覆盖先画的。**必须严格分三段绘制**：
1. 第一段：所有实体卡片（表头 pill、入口节点、容器框、中枢节点、出口节点等所有 `<rect>`+`<text>` 组合）
2. 第二段：所有连接线（干线、枝线、箭头）
3. 第三段：所有步骤标签（编号矩形 + 圆形数字徽章）

### 反面案例
如果按"画节点A → 画A到B的线和标签 → 画节点B → 画B到C的线和标签"交替顺序绘制，后画的节点 B 会把前面画的"A→B 步骤标签"压住一角（尤其当标签位置离节点边缘较近时）。

```svg
<!-- ❌ 交替绘制：标签在节点之前画，会被之后画的节点盖住 -->
<rect x="100" y="100" width="200" height="80" fill="#fff"/> <!-- 节点A -->
<rect x="480" y="255" width="130" height="26" fill="#1664FF"/> <!-- 步骤①标签 -->
<rect x="600" y="160" width="380" height="170" fill="#E7F8EF"/> <!-- 节点B，可能压住步骤①标签的一角 -->
```

```svg
<!-- ✅ 三段式：先画完所有卡片，再画所有线，最后画所有标签 -->
<!-- 第一段：卡片 -->
<rect x="100" y="100" width="200" height="80" fill="#fff"/> <!-- 节点A -->
<rect x="600" y="160" width="380" height="170" fill="#E7F8EF"/> <!-- 节点B -->
<!-- 第二段：连接线 -->
<line x1="300" y1="140" x2="600" y2="140" stroke="#1664FF" marker-end="url(#ah-blue)"/>
<!-- 第三段：步骤标签（永远在最上层，不会被任何卡片压住） -->
<rect x="420" y="120" width="130" height="26" fill="#1664FF"/>
<text x="485" y="137" text-anchor="middle" fill="#fff">① 步骤名</text>
```

### 标签坐标选取原则
步骤标签必须落在**纯留白区**（不与任何容器/卡片的矩形范围重叠），优先选择：
- 两个同色系连接线之间的空白带
- 容器边缘外侧、下一个容器边缘内侧之间的间隙
- 若空白区域太窄（如两个表头之间的窄缝），宁可把标签挪到旁边更宽的留白区，也不要硬塞——挤在窄缝里即使不被遮挡，也会造成"看不清顺序"的阅读问题

### 自检方法
1. 检查 SVG 源码中 `<rect>`+`<text>` 的组合顺序，凡是步骤标签（带序号圆圈的那种），必须出现在所有实体卡片的 `<g>` 块之后
2. 用坐标计算法逐一验证每个标签矩形的 `(x, x+width, y, y+height)` 范围，与所有卡片的范围做矩形碰撞检测，确认零重叠
3. 截图放大标签周边 150px 范围，人工确认无遮挡、无窄缝挤压感

---

## 自检流程总表

完成后逐项打勾：

| # | 检查项 | 工具 |
|---|--------|------|
| L1 | 线-文不交叉 | 截图 + 像素 review |
| L2 | 箭头不越框 | 检查每条 line 的 y2/x2 |
| L3 | 居中标签让位 | 搜 `text-anchor="middle"` |
| L4 | 列对齐 | 列出同列节点 x+width/2 |
| L5 | marker 复用 | 检查 defs 区 |
| L6 | 图例 SVG | 搜 `.lg-line::after` 应为空 |
| L7 | 绘制顺序（卡片→线→标签），标签零遮挡 | 检查绘制顺序 + 矩形碰撞检测 |

任何一项不达标 → 修复 → 重新截图 review，循环直到 7 项全过。
