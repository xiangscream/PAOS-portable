# 动画清单 JSON 格式（anim_manifest.json）

由 `scripts/anim_recorder.py` 生成，供 `add_animations.ps1` 读取。

## 顶层结构

对象（dict），键为**页序号（1-based 字符串）**，值为该页的动画条目数组：

```json
{
  "1": [
    {"spid": 5, "preset": "fade", "trig": "onclick"},
    {"spid": 7, "preset": "fly",  "trig": "afterPrev"}
  ],
  "2": [
    {"spid": 3, "preset": "wipe", "trig": "afterPrev"}
  ]
}
```

## 字段说明

| 字段    | 类型   | 取值 | 含义 |
|---------|--------|------|------|
| `spid`  | int    | 形状 id | 来自 python-pptx `shape.shape_id`；脚本按 `slide.Shapes.Id` 匹配 |
| `preset`| string | 见下表 | 动画类型（映射到 PowerPoint `msoAnimEffect` 枚举值） |
| `trig`  | string | `onclick` / `afterPrev` / `withPrev` | 触发方式：单击 / 上一动画后 / 与上一动画同时 |

## preset -> msoAnimEffect 枚举值

| preset   | 枚举值 | 备注 |
|----------|--------|------|
| `fade`   | 10     | 淡入（最稳，默认兜底） |
| `fly`    | 2      | 飞入（默认从右侧） |
| `wipe`   | 13     | 擦除 |
| `zoom`   | 19     | 缩放 |
| `appear` | 1      | 出现 |
| `peek`   | 12     | 上浮/探出（常用作"升起"） |
| `dissolve`| 9     | 溶解 |

> 未知 preset 会被脚本自动回退为 `fade`，不会报错。

## 注意事项

- 同一页内多个 `afterPrev` 会按顺序自动接续；第一个动画建议用 `onclick` 作为入场锚点。
- `withPrev` 需配合前一个已存在的动画，单独使用可能表现异常，谨慎使用。
- Python 端务必在**该页 slide 创建后、下页创建前**调用 `rec.add()`，否则 `slide_idx` 错位。
- 注入脚本只对未注入过的文件安全；重复运行同一清单会**叠加**动画，需重新从 python-pptx 生成干净 pptx 再注入。
