# drawio XML 速查表（v2）

> 本速查表来自智能体自进化平台架构图案例（2026-06-08）的实战经验。

## 1. 文件骨架

```xml
<mxfile host="app.diagrams.net" agent="diagrams.net" version="24.0.0">
  <diagram name="MyDiagram" id="diagram-1">
    <mxGraphModel dx="2000" dy="1400" grid="1" gridSize="10" guides="1" tooltips="1"
                  connect="1" arrows="1" fold="1" page="1" pageScale="1"
                  pageWidth="1700" pageHeight="1240" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 所有节点和边都 parent="1" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

`pageWidth` / `pageHeight` 决定可视区域，常用 1700×1240（横版 16:9 略宽）。

## 2. 节点（mxCell vertex="1"）

### 标准卡片节点

```xml
<mxCell id="my-node" vertex="1" parent="1"
  style="rounded=1;fillColor=#FFE6CC;strokeColor=#D79B00;strokeWidth=1.6;fontSize=14;whiteSpace=wrap;html=1;verticalAlign=middle;"
  value="&lt;b&gt;节点标题&lt;/b&gt;&lt;br&gt;&lt;span style='font-size:11px;color:#4E5969'&gt;副标题&lt;/span&gt;">
  <mxGeometry x="200" y="240" width="200" height="120" as="geometry"/>
</mxCell>
```

要点：
- `id` 必须唯一且语义化（user / session / ctrl ...）便于后续 source / target 引用
- `value` 用 HTML 实体编码（`&lt;` `&gt;` `&amp;`），支持 `<b>` / `<br>` / `<span>` 等标签
- `style` 半角分号分隔，**fillColor 必须带 # 号**
- `<mxGeometry>` 的 `as="geometry"` 不能漏

### 常用 style 模式

| 用途 | style |
|------|-------|
| 入口节点（白底灰边） | `rounded=1;fillColor=#FFFFFF;strokeColor=#E5E6EB;` |
| 主流程节点（橙色） | `rounded=1;fillColor=#FFE6CC;strokeColor=#D79B00;strokeWidth=1.6;` |
| 控制器节点（粉色加粗） | `rounded=1;fillColor=#F8CECC;strokeColor=#B85450;strokeWidth=1.8;` |
| 数据节点（白底橙边） | `rounded=1;fillColor=#FFFFFF;strokeColor=#F59E0B;strokeWidth=1.4;` |
| 中枢节点（紫底紫边） | `rounded=1;fillColor=#F1ECFE;strokeColor=#8B5CF6;strokeWidth=1.8;` |
| 体系容器（虚线大框） | `rounded=1;fillColor=#E8F0FF;strokeColor=#1664FF;dashed=1;align=left;verticalAlign=top;spacingLeft=14;spacingTop=10;` |
| pill 标签（实色圆角） | `rounded=1;fillColor=#1664FF;strokeColor=none;fontColor=#FFFFFF;fontSize=12;fontStyle=1;` |

## 3. 边（mxCell edge="1"）

### 简单行内右向箭头

```xml
<mxCell edge="1" parent="1" source="A" target="B"
  style="endArrow=classic;exitX=1;exitY=0.5;entryX=0;entryY=0.5;strokeColor=#1664FF;strokeWidth=2.4;">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

`exitX/Y` 是源节点出口锚点（0=左/上，1=右/下，0.5=中），`entryX/Y` 是目标入口锚点。

### 带文字的边

```xml
<mxCell edge="1" parent="1" source="A" target="B"
  style="endArrow=classic;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#1664FF;strokeWidth=2.4;fontColor=#0E42B5;fontSize=12;fontStyle=1;"
  value="①">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

`value` 直接挂在边上，drawio 自动放在中点。不要再加独立的 text mxCell。

### 折线（走指定轨道）

要让箭头走特定的水平/垂直轨道，加 `edgeStyle=orthogonalEdgeStyle` + `<Array as="points">`：

```xml
<!-- 会话 → 用户使用数据：走 y=388 水平轨道 -->
<mxCell edge="1" parent="1" source="session" target="data-user"
  style="endArrow=classic;exitX=0.5;exitY=1;entryX=0.5;entryY=0;
         strokeColor=#F59E0B;strokeWidth=2.2;
         edgeStyle=orthogonalEdgeStyle;"
  value="会话埋点">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="300" y="388"/>
      <mxPoint x="1020" y="388"/>
    </Array>
  </mxGeometry>
</mxCell>
```

points 是边的中间转折点。drawio 会用直角线把 source → 第 1 个 point → 第 2 个 point → ... → target 串起来。

### 干线-枝线模式（4 cell）

汇入多个 → 单点的标准实现：

```xml
<!-- 1) 横向干线（无箭头） -->
<mxCell id="trunk" edge="1" parent="1"
  style="endArrow=none;strokeColor=#F59E0B;strokeWidth=2.2;">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="1020" y="595" as="sourcePoint"/>
    <mxPoint x="1500" y="595" as="targetPoint"/>
  </mxGeometry>
</mxCell>

<!-- 2) 第一条枝线（无箭头）从节点底部到干线 -->
<mxCell edge="1" parent="1" source="data-user"
  style="endArrow=none;exitX=0.5;exitY=1;strokeColor=#F59E0B;strokeWidth=2.2;">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="1020" y="595" as="targetPoint"/>
  </mxGeometry>
</mxCell>

<!-- 3) 第二条枝线 -->
<mxCell edge="1" parent="1" source="data-trans"
  style="endArrow=none;exitX=0.5;exitY=1;strokeColor=#F59E0B;strokeWidth=2.2;">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="1500" y="595" as="targetPoint"/>
  </mxGeometry>
</mxCell>

<!-- 4) 中央枝线 = 主干线（带箭头）从干线中点进目标 -->
<mxCell edge="1" parent="1" target="eval-set"
  style="endArrow=classic;entryX=0.5;entryY=0;strokeColor=#F59E0B;strokeWidth=2.6;"
  value="汇入">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="1260" y="595" as="sourcePoint"/>
  </mxGeometry>
</mxCell>
```

视觉效果：三条枝线无箭头汇入水平干线，干线中点出一根带箭头主线进目标。

## 4. 锚点（exitX / entryX）速查

```
节点矩形：
            (0.5, 0)
              ┃
   (0, 0.5)──┼──(1, 0.5)
              ┃
            (0.5, 1)
```

| 走向 | 源 exit | 目 entry |
|------|---------|----------|
| 行内右（→） | x=1 y=0.5 | x=0 y=0.5 |
| 行内左（←） | x=0 y=0.5 | x=1 y=0.5 |
| 竖直下（↓） | x=0.5 y=1 | x=0.5 y=0 |
| 竖直上（↑） | x=0.5 y=0 | x=0.5 y=1 |

非中点锚（如要从节点 21% 处出来）：用 `exitX=0.21`。

## 5. CLI 渲染

```bash
# macOS 安装
brew install drawio

# 导出 PNG（默认 96dpi，加 --scale 2 提高分辨率）
/opt/homebrew/bin/drawio --no-sandbox -x -f png -o out.png input.drawio

# 导出 PDF（矢量）
/opt/homebrew/bin/drawio --no-sandbox -x -f pdf -o out.pdf input.drawio

# 导出 SVG（可被网页直接嵌入）
/opt/homebrew/bin/drawio --no-sandbox -x -f svg -o out.svg input.drawio
```

⚠️ CLI 在 sandbox 下会报：

```
ERROR:net/disk_cache/disk_cache.cc:284] Unable to create cache
ERROR:gpu/ipc/host/gpu_disk_cache.cc:737] Gpu Cache Creation failed: -2
```

**这些错误不影响输出**，文件仍然会生成。看到这些错就跳过，看 stdout 最后一行 `xxx.drawio -> xxx.png` 就是成功。

## 6. 校验脚本

```bash
# 检查 XML 合法性
python3 -c "import xml.etree.ElementTree as ET; ET.parse('out.drawio'); print('OK')"

# 列出所有节点和边
python3 -c "
import xml.etree.ElementTree as ET
root = ET.parse('out.drawio').getroot()
for c in root.findall('.//mxCell'):
    if c.get('vertex') == '1':
        g = c.find('mxGeometry')
        print(f'V {c.get(\"id\"):20} ({g.get(\"x\")},{g.get(\"y\")}) {(c.get(\"value\") or \"\")[:30]}')
    elif c.get('edge') == '1':
        print(f'E {c.get(\"source\")} -> {c.get(\"target\")} {c.get(\"value\") or \"\"}')
"
```

## 7. 常见错误 & 修复

| 现象 | 原因 | 修复 |
|------|------|------|
| 箭头没显示 | 漏写 `endArrow=classic` | 加上 |
| 箭头从节点外面绕一圈 | exit/entry 锚点不对 | 检查源 exit + 目 entry |
| 文字显示 `&lt;b&gt;` 字面 | value 里没用 HTML 实体编码 | `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;` |
| 颜色不生效 | 用了 `var(--xxx)` 或不带 # | drawio 必须 `#1664FF` 这种格式 |
| 节点重叠 | x/y/width/height 算错 | 列对齐：x = 列中线 - width/2 |
| 折线乱 | 没加 `edgeStyle=orthogonalEdgeStyle` | 加上 + points 数组 |
| 边没连上 | source/target id 写错 | 检查节点 id 拼写 |
