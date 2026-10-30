---
name: pptx-animation-injector
schema: paos-skill/v1
id: pptx-animation-injector
title: PPTX Animation Injector
description: "为 python-pptx 生成的 PPTX 注入 PowerPoint 原生入场动画（淡入/飞入/擦除/缩放），彻底规避手写 p:timing 动画 XML 导致文件损坏（PowerPoint 报\"文件或目录损坏\" 0x80070570）的陷阱。当用户用 python-pptx 做 PPT 并需要加动画、让角色/图文逐条出现、制作无生微课或精品课动画 PPT 时使用。内置 PowerShell COM 注入脚本、Python 动画清单录制助手、动画清单 JSON 格式参考。"
tags: pptx, animation, python-pptx
status: active
version: 1
---

# PPTX 动画注入器（PowerPoint 原生）

## 用途

用 python-pptx 排版/插图后，给形状加上**标准、可被 PowerPoint 正常打开**的入场动画。核心思路：**绝不手写 `<p:timing>` XML**——那一定会因结构偏差被 PowerPoint 判为损坏。改为两段式：

1. python-pptx 只负责版式与图片，同时把"哪个形状、用什么动画、怎么触发"登记成一份 JSON 清单；
2. 用 **PowerPoint COM (`MainSequence.AddEffect`)** 读清单注入标准动画，保存后文件 100% 可打开。

## 触发

用户出现以下意图时调用：给 python-pptx 的 PPT 加动画 / 让小智或图文逐条出现 / 做无生微课或精品课动画 PPT / 之前手写的动画 XML 导致 PPT 打不开。

## 关键原则（踩坑经验，务必遵守）

1. **禁止手写 `<p:timing>`**：任何手写的 `p:cTn/p:animEffect/p:set` 结构，只要缺 `presetID/presetClass/presetSubtype/nodeType` 等属性就会被 PowerPoint 拒读。一律走 COM 注入。
2. **本机 PowerPoint 禁止隐藏窗口**：`$ppt.Visible = 0` 会抛 *"Hiding the application window is not allowed"*。必须 `$ppt.Visible = -1`（会闪一下窗口，正常）。
3. **`Slide.Export` 在本无头环境会卡死**：不要用它批量导出预览图。改用 python-pptx 读取成品，核对能打开、zip/包完整、每页含真实 `<p:timing>`，且文字/图片数量与注入前一致。
4. **python-pptx 隔离环境**：依赖 `python-pptx`，装在隔离 venv；不要污染用户全局环境。
5. **PowerShell 脚本必须带 UTF-8 BOM**：无 BOM 的 UTF-8 中文 `.ps1` 在 PowerShell 5.1 会按 ANSI(GBK) 解码，解析器会报「字符串缺少终止符 / 语句块缺少 } 」等**级联假错误**（实测 4 个）。写入或修改 `add_animations.ps1` 后，务必用 `utf-8-sig` 编码落盘（`open(p,'wb').write(b'\xef\xbb\xbf'+data)`）。校验命令：
   ```powershell
   $e=$null;$t=$null
   [System.Management.Automation.Language.Parser]::ParseFile("<脚本路径>",[ref]$t,[ref]$e)
   $e.Count   # 必须为 0
   ```
   > 注意：此规则只针对 `.ps1`；bash/`.sh` 脚本千万不要加 BOM，反而会破坏执行。

## 工作流

### 第一步：Python 端登记动画清单

在 python-pptx 项目里用 `scripts/anim_recorder.py` 的 `AnimRecorder`。每建好一个形状并决定它的动画，立即调用：

```python
from anim_recorder import AnimRecorder
rec = AnimRecorder()
# slide_idx：该页在演示文稿中的 1-based 序号
# shape：python-pptx 的 shape 对象（用 shape.shape_id 取 spid）
# preset：'fade' | 'fly' | 'wipe' | 'zoom' | 'appear' | 'peek'
# first=True  -> 单击触发(onclick)；first=False -> 上一动画后自动(afterPrev)
rec.add(slide_idx, shape, preset='fade', first=True)
# ...
rec.save('anim_manifest.json')   # 与最终 pptx 同目录
# 最后 prs.save(OUT)
```

清单格式见 `references/manifest_format.md`。

### 第二步：PowerShell COM 注入动画

确保已生成无动画的 pptx 与 `anim_manifest.json`（同目录或显式传路径），运行：

```powershell
& powershell -ExecutionPolicy Bypass -NoProfile -File "<skill>/scripts/add_animations.ps1" `
  -PptxPath "最终.pptx" -ManifestPath "anim_manifest.json"
```

脚本会打开文件、按清单 `AddEffect`、保存、退出。打印每页动画数量便于核对。

> 若只需给已含动画的文件重新打开/另存（不再注入），可只传 `-PptxPath`，脚本会跳过注入步骤。

## 交付物校验

注入后用 python-pptx 校验：文件能打开、zip 完整、每页含真实 `<p:timing>`、文字/图片齐全。结构校验不等于 PowerPoint 渲染通过；实际播放需在有 PowerPoint 的 Windows 上手工确认。

## 参考文件

- `scripts/add_animations.ps1`：标准动画注入脚本（含 effectId / trigger 映射）。
- `scripts/anim_recorder.py`：Python 端动画清单录制助手。
- `references/manifest_format.md`：JSON 清单 schema 与枚举值。
