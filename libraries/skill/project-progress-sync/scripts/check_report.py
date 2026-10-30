#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进度汇报完整性预检。

用法:
    python check_report.py <report.md> [更多文件...]

检查项:
  1. 四段是否齐全（遇到的问题 / 解决方法 / 结果 / 下一步计划）
  2. 必填项是否存在（报的人 / 日期 / 负责人 / 目标日期 / 外部依赖）
  3. 写作风险提示（反面句、自我削弱词、活动式表述）
  4. 是否提到基线（版本 / 零点 / 口径），以便触发对齐检查

退出码: 0 = 无阻塞问题; 1 = 有阻塞问题(缺段或缺必填项)
"""
import re
import sys

SECTIONS = [
    ("遇到的问题", [r"遇到的问题", r"问题"]),
    ("解决方法", [r"解决方法", r"解决办法", r"方法"]),
    ("结果", [r"结果"]),
    ("下一步计划", [r"下一步", r"下步", r"计划"]),
]

REQUIRED = [
    ("报的人", [r"报的人", r"姓名", r"汇报人"]),
    ("日期", [r"日期", r"20\d{2}[-/年]\d{1,2}"]),
    ("负责人/对接人", [r"负责人", r"对接人", r"责任人", r"owner"]),
    ("目标日期/到位时间", [r"目标日期", r"到位时间", r"截止", r"预计.*完", r"待定"]),
    ("外部依赖标注", [r"外部", r"厂家", r"采购", r"供应商", r"等.*提供"]),
]

# 负面/防御性表达（提示改法：改写成正面陈述）
DEFENSIVE = [
    (r"不改变", "是对正面句的反面重复，直接删或改正面"),
    (r"不会", "改为正面陈述，例如说明实际行为"),
    (r"不把.*当作", "改为正面，例如「只对……生效」"),
    (r"不能关闭", "改为正面：「……始终可见」"),
    (r"不表示", "改为正面：「……表示……」"),
]

# 自我削弱（发布会原则禁止）
WEAKENING = [
    r"遗憾的是", r"可惜", r"仅", r"只是", r"效果有限", r"仍明显落后",
    r"未能", r"不够理想", r"比较差", r"退步",
]

# 活动式表述（应写结果）
ACTIVITY = [
    (r"进行了[^。\n]{0,12}(测试|实验|调试)", "写结果：拿到了什么数据、达到什么状态"),
    (r"做了[^。\n]{0,12}(测试|实验|调试|优化)", "写结果：完成到什么程度"),
    (r"在?(做|搞|弄)[^。\n]{0,8}(测试|调试|优化)", "写结果而不是动作"),
]

BASELINE_HINTS = [r"版本", r"编译", r"固件", r"零点", r"标定", r"口径", r"坐标", r"单位", r"接口"]


def check(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("  ❌ 无法读取: %s" % e)
        return False

    print("=" * 66)
    print("检查:", path)
    print("-" * 66)
    blocking = False

    print("[1] 四段完整性")
    for name, pats in SECTIONS:
        ok = any(re.search(p, text) for p in pats)
        print("  %s %s" % ("✅" if ok else "❌", name))
        if not ok:
            blocking = True

    print("[2] 必填项")
    for name, pats in REQUIRED:
        ok = any(re.search(p, text) for p in pats)
        print("  %s %s" % ("✅" if ok else "⚠️ 缺", name))
        if not ok:
            blocking = True

    print("[3] 写作风险（建议改法）")
    hits = 0
    for pat, tip in DEFENSIVE:
        for m in re.finditer(pat, text):
            hits += 1
            print("  ⚠️  反面句「%s」→ %s" % (m.group(0), tip))
    for pat in WEAKENING:
        for m in re.finditer(pat, text):
            hits += 1
            print("  ⚠️  自我削弱「%s」→ 换成事实陈述" % m.group(0))
    for pat, tip in ACTIVITY:
        for m in re.finditer(pat, text):
            hits += 1
            print("  ⚠️  活动式表述「%s」→ %s" % (m.group(0), tip))
    if hits == 0:
        print("  ✅ 未发现明显风险表述")

    print("[4] 基线对齐")
    base = [h for h in BASELINE_HINTS if re.search(h, text)]
    if base:
        print("  ℹ️  提到基线相关词：%s" % "、".join(base))
        print("     → 按 references/alignment-checklist.md 逐条核对是否与他人一致")
    else:
        print("  ℹ️  未提到基线；若有跨人协作，主动确认版本/零点/口径")

    print("-" * 66)
    print("结论:", "❌ 有阻塞项，需回问补全后再整理" if blocking else "✅ 可进入整理流程")
    return not blocking


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ok = all([check(p) for p in sys.argv[1:]])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
