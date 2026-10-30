"""动画清单录制助手：供 python-pptx 项目调用，记录 形状->动画 映射。

用法（在 build 脚本里）：
    from anim_recorder import AnimRecorder
    rec = AnimRecorder()
    # 每建好一个形状并决定动画，立即登记（务必在该页 slide 创建后、新页创建前）
    rec.add(slide_idx, shape, preset='fade', first=True)
    ...
    rec.save('anim_manifest.json')   # 与最终 pptx 放同目录
    prs.save(OUT)

slide_idx 为该页在演示文稿中的 1-based 序号；shape 为 python-pptx shape 对象，
内部用 shape.shape_id 取 spid。preset/trig 取值见 manifest_format.md。
"""
from collections import OrderedDict


class AnimRecorder:
    def __init__(self):
        self.data = OrderedDict()

    def add(self, slide_idx, shape, preset="fade", first=True):
        """登记一个形状的动画。
        slide_idx: int 1-based 页序号
        shape:     python-pptx shape（需 shape.shape_id）
        preset:    'fade'|'fly'|'wipe'|'zoom'|'appear'|'peek'
        first:     True=单击触发(onclick)；False=上一动画后自动(afterPrev)
        """
        key = str(int(slide_idx))
        trig = "onclick" if first else "afterPrev"
        self.data.setdefault(key, []).append(
            {"spid": int(shape.shape_id), "preset": preset, "trig": trig}
        )

    def save(self, path):
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
