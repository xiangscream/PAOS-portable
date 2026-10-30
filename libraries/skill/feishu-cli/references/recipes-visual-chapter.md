# 分册③：画板 / 搬章 / 重编号配方（whiteboard / SVG / 结构重排）

来源：WorkBuddy feishu-cli 单体无损收录。

收录区间：
> - 原文行 143–416
> - 原文行 1068–1087

---

## 插入 SVG 画板（whiteboard）

把自定义图表以原生画板形式插入文档，可编辑、可导出 PNG 审查。

```bash
# 1. 准备内容文件（ASCII 文件名，不含中文路径），内容格式：
# <whiteboard type="svg"><svg xmlns="...">...</svg></whiteboard>
# 2. 取目标锚点 block-id：docs +fetch --scope outline --detail with-ids
# 3. 在锚点之后插入画板
cd /mnt/c/Users/remo/Downloads
lark-cli docs +update --doc "<doc_id>" --command block_insert_after \
  --block-id "<anchor_block_id>" --content @./diagram-whiteboard.md --format json

# 4. 从返回 JSON 拿到 new_blocks[].block_token
# 5. 导出 PNG 审查渲染效果
lark-cli whiteboard +query --whiteboard-token "<board_token>" \
  --output_as image --output ./preview.png --as user
```

**画板 SVG 约束（飞书画板解析器不支持以下特性）**：
- 禁用：`<radialGradient>` / `<filter>` / `<pattern>` / `<clipPath>` / `<mask>`
- 文字必须用 `<text>`，不要用 `<path>` 文字
- 形状用 `<rect>/<circle>/<ellipse>/<polygon>`，连线用 `<line>/<polyline>/<path>` 正交折线
- 节点设计推荐：rect rx=10 + 标题 16px bold + 副标题 13px normal

**字号规范（2026-09-08 调整 · 飞书 web 显示优化）**：

飞书 web 把 SVG 按容器宽度（约 800px）等比缩放，viewBox 1600 宽的画板缩放比约 0.5——SVG 里 18px 实际只显示约 9px，看不清。**字号至少要 × 1.7，节点高度至少 × 1.25，画布高度相应增加**，才能在飞书 web 端清晰可读。

| 元素 | viewBox 1600 内字号 | 实际飞书显示 | 旧版问题 |
|------|-------------------|------------|---------|
| 画布主标题 | 30-34px | 15-17px | OK（清晰可读） |
| 画布副标题 | 20-22px | 10-11px | OK |
| 强权重节点主文 | 30-32px | 15-16px | OK |
| 强权重节点副文 | 20-22px | 10-11px | OK |
| 普通节点主文 | 26-30px | 13-15px | OK |
| 普通节点副文 | 19-20px | 9-10px | 偏小但可读 |
| 图例/小注 | 17-19px | 8-9px | 偏小 |
| 节点高度 | 60-155px | 30-78px | OK（容纳字号） |
| 画布总高度 | 1150-1400 | - | 内容不挤 |

**严禁**用旧版字号（17/12/11px）——飞书 web 显示会糊成蚊子字，用户看着累。**画板"字号规范"和"分色规范"是同等重要**的两条铁律。

**分色语义（莫兰迪降饱和度版本 · 推荐用于立项报告 / 设计稿 / 商务文档）**：

V5 立项报告主文档（以及后续任何"专业文档"场景）使用降饱和度配色——鲜色块 + 白字虽然醒目，但对长篇报告过于刺眼。改用"浅色背景 + 主色边 + 深文字"组合，主色仅用于标识语义边界，不抢戏。

| 语义 | 节点背景 fill | 节点边框 stroke | 文字 | 用法 |
|------|---------------|-----------------|------|------|
| 输入 / 感知 / 物理 | `#F2F6FA` | `#7A95B5`（淡蓝灰） | `#2C3340` | Follow / 输入层 / 感知 |
| 计算 / 决策 / 规划 | `#F4F2F8` | `#9890B0`（淡紫灰） | `#2C3340` | Shot / 规划层 / 摄影目标 |
| 安全 / 用户接管 | `#FAF2F2` | `#B57878`（淡红棕） | `#2C3340` | B-Cam / 主摄云台 / EIS |
| 执行 / 驱动 / 稳定 | `#F2F7F3` | `#7A9D85`（淡绿灰） | `#2C3340` | FPV / 底盘 / 路径 |
| 交互 / 开放 / 调用 | `#FAF6EE` | `#B59B6B`（淡琥珀） | `#5C4F2E` | 开放能力 / 贯穿底座（虚线边框） |
| 结果 / 输出 | `#FAF2F2` | `#A8916B`（淡棕） | `#5C4F2E` | 影像与素材 |
| **强调节点**（强权重） | `#4E5A6B`（深石板灰） | - | `#FFFFFF` | 根节点 / LRC101 主机（唯一可全图 1-2 个） |
| **强调节点**（次强） | `#6B6480`（暗紫） | - | `#FFFFFF` | 中枢节点 / 摄影系统 |
| **强调节点**（终态） | `#A8916B`（暖棕） | - | `#FFFFFF` | 输出节点 / 影像与素材 |
| **辅助元素** | - | - | `#B0B7C2`（连线）/ `#9CA3AF`（注释）/ `#4B5563`（文字强调） | - |

**配色铁律**：
- 主色仅用于**边框 + 强权重节点底色**——不用于大面积块状填色
- 子节点/普通节点统一用 `#FFFFFF` 底 + `#D0D5DC` 1px 边 + `#2C3340` 文字
- 灰阶文字层级：标题 `#2C3340` / 副标题 `#6B7280` / 注释 `#9CA3AF`
- 连线 `#B0B7C2` 1.5px / 虚线 5,4 间距
- 整套色板统一 L=50-58%（HSL 调色），避免任何色相"过亮"

**对比旧版（弃用 · 仍保留作为高饱和度场景的备选）**：
- 蓝 `#2E75B6` / 紫 `#7B68EE` / 红 `#C00000` / 绿 `#00A86B` / 琥珀 `#B8860B` / 橙 `#993C1D` 等高饱和纯色
- 仅适用于"重要 banner / 营销视觉"等需要抢眼的场景
- 用于专业文档 = 视觉噪音，请改用莫兰迪版本

**更新已有画板（重构内容）**：`docs +update` 只能新增画板，不能改已有画板内容；改内容用 `whiteboard +update`，且 `--source @file` 的文件是**纯 `<svg>`**（不带 `<whiteboard type="svg">` 包裹），与上面插画板相反：

```bash
lark-cli whiteboard +update --whiteboard-token "<board_token>" \
  --input_format svg --source @./diagram.svg --overwrite --as user
```

**创建全新画板**（lark-cli v1.0.70 没有 standalone create 命令，必须走"占位 + 写内容"两步）：

```bash
# 1. 在目标锚点后插入 <whiteboard type="svg"> 占位（极简空 svg），拿到新 token
echo '<whiteboard type="svg"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100" height="100"></svg></whiteboard>' \
  | lark-cli docs +update --doc "<doc_id>" --command block_insert_after \
    --block-id "<anchor>" --content -

# 2. 用 whiteboard +update 把真实 SVG 写进去（source 是纯 <svg>，不带 <whiteboard> 包裹）
lark-cli whiteboard +update --whiteboard-token "<new_token>" \
  --input_format svg --source @./diagram.svg --overwrite
```

插入占位返回的 `block_token` ≠ 后续写内容的 `whiteboard-token`：前者是文档里的 block 副本 id，后者是云端画板本身的 token——这是预期的，不是 bug。

**⚠️ 重插画板必须用「原始源画板 token」，不能用上一版的 doc block_token**：

`<whiteboard token="X"/>` 是**克隆语义**——飞书从云端画板 X 复制一份新副本嵌进文档。如果 X 本身是从更早的 doc block_token 拿的（"副本的副本"），连续 clone 会失败：

```
result: "partial_success"
warnings: ["degrade_code=2105,msg=Whiteboard clone failed. Retry later"]
```

重试也无效。**解法：用最初的源画板 token**（用户最初复制/创建时那个），而不是任何一版 doc block 的 `block_token`。

维护一份"源画板 token 表"，每次 overwrite 后重插都用它：

```bash
# ✅ 正确：源画板 token（稳定不变）
echo '<whiteboard token="<源画板token>"/>' | lark-cli docs +update --doc "<doc>" \
  --command block_insert_after --block-id "<anchor>" --content -

# ❌ 错误：上一版 doc block 的 block_token（副本的副本，clone 必失败）
```

判定方法：`whiteboard +query --whiteboard-token "X"` 能成功返回 SVG/PNG 的，才是有效源 token；doc block 里的 `block_token` 只在那一版文档生命周期内有效。

**⚠️ 更正（2026-09-18 实测）：`+query` 成功 ≠ 可以 clone。** 想从另一篇文档里「搬」一个画板过来时，
把 `docs +fetch` 回读到的 `<whiteboard token="X"/>` 拿来插到新文档，**`+query` 能正常导出 PNG/SVG，但插入一律报**：

```
result: "partial_success"  warnings: ["degrade_code=2105,msg=Whiteboard clone failed. Retry later"]
```
隔 8 秒、15 秒各重试三轮，**每次都是 2105**——这是「副本的副本」，不是限流，重试无用。
（回读 XML 里的 `token` 是**那一篇文档里的 block 副本 token**，不是云端源画板 token。）

**可靠的替代路径：导出 SVG 再作为新画板插入。** 视觉完全一致，且不依赖 clone：

```bash
# 1) 把源画板导出为 SVG（这一步 +query 是通的）
lark-cli whiteboard +query --whiteboard-token "<源文档里的 token>" --output_as svg --output ./wb.svg
# 2) 检查兼容性（飞书画板解析器不支持这些）
grep -c -E 'radialGradient|<filter|<pattern|clipPath|<mask' wb.svg    # 应为 0
# 3) 用 SVG 内容作为新画板插入（注意是 type="svg"，不是 token=）
#    payload = '<whiteboard type="svg">' + SVG全文 + '</whiteboard>'，走 --content -
```
本次实测：三张画板全部 `result: success`，形状/文字/连线/箭头都保住了。

**如果 clone 失败但 token 有效 → 是服务端限流，不要连续重试**：

```
result: "partial_success"
warnings: ["degrade_code=2105,msg=Whiteboard clone failed. Retry later"]
```

先用 `whiteboard +query` 确认 token 有效（能返回 SVG 就说明 token 没问题）。确认有效后**不要立刻重试同一块**——连撞限流会一直失败。正确做法：**先去插其他画板，把这一块留到最后再回来重试**，通常第 2-3 次就成功。

批量重插 4 块画板时，如果某块失败：跳过它 → 插完其余 → 回头重试失败的那块。

**画板 web 缓存问题（"我已经更新了但飞书还是显示旧图"）**：

`whiteboard +update --overwrite` 确实会更新云端画板的 SVG 节点（`docs +history-list` 能看到 revision 变化，`whiteboard +query --output_as image` 导出的 PNG 也是新版本）——但**飞书 web 端的画板快照缓存**（特别在 `openbrd=1` 这种"白板编辑"模式 URL 下）经常不实时读云端 SVG，而是用打开时的本地缓存。验证方法：先 `whiteboard +query --output_as image` 导出 PNG 给你看，与飞书 web 截图对比，如果 PNG 是新但 web 是旧——**100% 是缓存问题**。

根治方案（**重建画板**——让 doc block 也换新，飞书 web 任何缓存都失效）：

```bash
# 1. 删旧 doc block（revision_id 自增）
lark-cli docs +update --doc "<doc_id>" --command block_delete \
  --block-id "<old_whiteboard_block_id>"

# 2. 在原位置插入新占位 block（拿到全新 block_id + block_token）
echo '<whiteboard type="svg"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100" height="100"></svg></whiteboard>' \
  | lark-cli docs +update --doc "<doc_id>" --command block_insert_after \
    --block-id "<anchor_block_id>" --content -
# 响应里的 block_id 和 block_token 都是新的

# 3. 用新 token 上传 SVG
lark-cli whiteboard +update --whiteboard-token "<new_block_token>" \
  --input_format svg --source @./diagram.svg --overwrite
```

**画板节点 ID 池变化**是判断"是否真重建"的可靠指标：旧画板节点 id 前缀通常是 `o1:NN`，新画板会变成 `o2:NN` 或 `o1:更高数字`，并且**没有任何重叠**。如果 id 仍然有重叠或前缀没变——说明云端画板被覆写了但 doc block 没换新，飞书 web 可能仍显示缓存。

## markdown 引用块降级（区域块颜色太鲜艳的解法）

飞书把 markdown `>` 渲染成 `<blockquote>`，但 `<blockquote>` 不支持 `background-color` 属性，只能用默认主题色块——视觉上对专业文档太刺眼。降级方法：把 `> xxx` 全部改成浅灰 callout（markdown 与 XML 混用合法，lark-doc-md.md 确认）：

```bash
# 用 python 批量转换 md 源稿
python3 quote-to-callout.py   # 把 > xxx 改成 <callout emoji="📌" background-color="light-gray" border-color="gray"><p>xxx</p></callout>
```

飞书支持的语义化颜色（lark-doc-xml.md）：
- **基础色**：`gray` / `blue` / `green` / `yellow` / `red` / `purple` / `orange` / `pink` / `indigo` / `teal` / `lime` / `cyan`
- **前缀**：`light-{色}`（浅）/ `medium-{色}`（中）/ `dark-{色}`（深）
- **额外**：`medium-gray`
- 完整文档：`lark-cli skills read lark-doc references/lark-doc-xml.md`

注意事项：
- callout 子块仅支持文本/标题/列表/待办/引用——加粗 `<b>` 算文本 OK
- 浅灰推荐：`background-color="light-gray"` + `border-color="gray"`
- 改完源稿后用 overwrite 整篇重写 + 重插所有画板（overwrite 会清空 doc block，云端 token 保留）

### ★★ 结构重排：搬整章 + 全篇重编号（2026-09-20 实测，Camera Intelligence Stack v07）

**场景**：用户说「以我们的四层架构为骨架，先总体介绍，各层讲清楚后，外层参照再出现」——
即把某一章（外部参照）从前面搬到架构章之后。**做法是在本地 md 上一次性完成，再整篇 overwrite**，
不要在飞书上用 `block_move_after` 搬几十个块（搬块会换 id、要逐轮 re-fetch、失败点极多）。

**① 章节标题的正则必须带「尾点」，小节不带——用一条正则必然只改到一半。**

| 形式 | 样子 | 匹配写法 |
|---|---|---|
| 章标题 | `# 3. 总体架构` | `^(#{1,2}) (\d+)\. (.*)$` |
| 小节标题 | `## 2.1 ROS 2 / Nav2：…` | `^(#{1,2}) (\d+)\.(\d+)\.? (.*)$` |

我曾写成 `^(#{1,4}) (\d+)((?:\.\d+)*) (.*)$`，以为一条通吃：`(\d+)` 吃掉 `3`，
但下一个字符是 `.` 而不是空格，`((?:\.\d+)*)` 匹配空串后 ` ` 失配 → **章标题全部没匹配上**，
只改了 33 个小节。结果章写「# 4. 第一层」、节写「## 3.1 定义」——比不改更糟。
**症状识别**：脚本报告「改了 N 个标题」，但打印出来的章标题编号纹丝不动。

**② 重编号必须「一趟映射函数」，绝不要顺序 replace。**

```python
CHAP = {2: 10, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9}
def fix(m):
    return f"{m.group(1)} {CHAP.get(int(m.group(2)), int(m.group(2)))}{m.group(3)} {m.group(4)}"
md = PAT.sub(fix, md)     # ✅ 一趟
```
顺序 `replace("3.","2.")` 再 `replace("2.","10.")` 会把**新产生的 2 又变成 10**。

**③ 把「预期改动数」写成断言——它会抓到你自己算错。**
本次我断言 `章 8 个`，实际 9 个（2→10、3→2…10→9 共 9 章改号），断言当场拦下。
**别把断言值当形式，它真的拦过。**

**④ 插入点的 `rfind` 会多留一个换行。**
```python
sep = "\n---\n"
q = md.rfind(sep, 0, p)          # p = 目标章标题位置
md = md[:q].rstrip("\n") + "\n\n---\n\n" + block + "\n\n---\n\n" + md[q+len(sep):].lstrip("\n")
```
`q` 落在 `"\n\n---\n"` 里的**第二个** `\n` 上，所以 `md[:q]` **末尾还留着一个换行**；
不 `rstrip("\n")` 就会插出 `\n\n\n`（连续空行）。**收尾统一 `re.sub(r"\n{3,}", "\n\n", md)` 兜底**，
并顺手把源稿里的同类问题一并清掉。

**⑤ 动手前先做「引用清单扫描」，把改号范围钉死。** 扫这四类：
`见 (\d+)\.(\d+)`、`（(\d+)\.(\d+)）`（映射表自我标注）、`第 \d+ 章`、以及裸的 `\d+\.\d+`。
**必须排除的假阳性**（本次实测）：`v2.1.0_8`、`《LRC101 产品 PRD》第五章`（指外部文档的第五章）、
arXiv 号 `2609.01281`、`10 Hz` / `200 Hz`、`0.95` / `86.20%` / `0.61 m/s³`（指标数字）、
以及「本文主要追求前两层」这种**层**引用（层号与章号是两套编号，别一起改）。
合并引用 `（见 1.3 / 2.6）` 里的第二个号没有 `见` 前缀，一般正则抓不到，
**要单列一条特例**，否则它会残留。

**⑥ 搬完要改一句衔接语。** 被搬走的章原本承接前文，落到新位置后开头的「这套架构并非凭空发明」
会显得突兀。最小改动是把它改成「前面几章描述的四层主栈与三环主线，每个部分都能…」——
**只动这一句，不要重写整章**。

**⑦ 改号映射表必须「从实际扫描结果建」，不能只写你打算改的那几个号。**
本次要把 `见 10.5` 改成 `见 11`、`10.6/10.7/10.8` 各降一号，我就只写了 `{5:…,6:…,7:…,8:…}`。
跑起来 `KeyError: 1` —— 因为 `见 10.1`…`见 10.4` 也存在（ch21 前 7 条参照，指向未改动的节）。
**这是我第二次在同一处栽跟头**：第一次数错改号章数（8 vs 9），这次漏了恒等项。
**规矩：映射表写成 `{…全部实际出现的号…}`，含恒等项，再加 `assert n_hit == <扫描得到的总数>`。**

**⑧ 小节与章之间的「合并」有方向，选错就是白干。** 本次要合并一个 `## 10.5` 小节与一个 `# 11` 整章，
两个方向都可行，判断依据是**容器本身的节奏是否被破坏**：

| 方向 | 结果 | 判断 |
|---|---|---|
| 章 → 并入小节 | 「参照清单」章里出现一条比邻条长 4 倍的节 | ❌ 该章 8 条原本等长，节奏被打破 |
| 小节 → 并入章 | 该章成为这条路线唯一的完整讨论；参照章回到 7 条等长 | ✅ 且 **12 章以后编号一个都不用动** |

被合并章里的**11 行对比表**是要保留的强资产——**别把它降级到小节里**，那等于把最可引用的东西埋掉。

**⑨ 合并必带去重，去重要选「哪一处的位置更好」。** 两个待合并块各有一句结论说的是同一件事
（A 处是结构图、B 处是引语）。保留位置更好的那一处，删掉另一处——**不要两处都留**，
否则合并完读者会看到同一结论说两遍，比合并前更糟。
本次保留了结构图（信息量更大、且被周围文字引用），删掉章末引语，让对比表直接流向收尾句。

**⑩ 合并后重新排「阅读顺序」，不是简单首尾相接。** 本次把小节内容接到章首后，出现
「论述 → 参考 URL → 引导句 → 对比表」，**引导句和它的表被 10 行 URL 隔开**。
正确顺序是 **论述 → 对比 → 结论 → 出处**：把 `参考：` 列表挪到章末。
**排版级的错序，字符数对账和双向比对都发现不了**——它们只验「在不在」，不验「顺不顺」。
合并完必须自己从头读一遍新章。

**★ 用飞书当 SVG 渲染器（2026-09-18 实测）**：本机 **cairosvg 装不上**（缺 `libcairo`，`cannot load library 'libcairo-2.dll'`），
所以「画板画完了要给人看渲染效果」只能走飞书。做法：

```
1) docs +create --parent-position my_library --content -   # 建一个临时预览文档，正文里直接放 <whiteboard type="svg">…</whiteboard>
   → 返回 data.document.document_id，以及 new_blocks[].block_token（每个画板一条）
2) whiteboard +query --whiteboard-token <block_token> --output_as image --output ./p1.png --overwrite
3) 用 PIL 的 ImageChops.difference 求 bbox 裁掉四周留白后再给人看
```

- **`--output` 已存在会直接失败**：`file already exists: ./p1.png (use --overwrite to overwrite)`。**加 `--overwrite`**，
  别以为画板没更新——我第一次就误判成"更新没生效"。
- **导出 PNG 是 2560×2560 的方形画布**（导出器统一尺寸，内容贴左上），**这不是画板被拉方**。
  画板真实尺寸用 `--output_as svg` 看根元素的 `width/height` 确认（例：1600×470 的画板导出后是 1640×510，含 ±20 边距）。
- 临时文档审完可删，**不要让预览文档进入交付链路**。

**★ 从视频抽帧做并排对照图**：`imageio-ffmpeg` 自带 ffmpeg 二进制（`imageio_ffmpeg.get_ffmpeg_exe()`），
`ffmpeg -y -ss <t> -i in.mp4 -frames:v 1 -q:v 2 out.jpg`。抽帧前先 `ffmpeg -i` 读 **Duration 与分辨率**——
本次差点把 1278×720 与 406×720（竖幅）两段拼在一起，并排会一高一矮；**配对前先对齐宽高比**。

