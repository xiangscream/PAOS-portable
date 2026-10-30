# -*- coding: utf-8 -*-
"""LRC101 用户侧功能结构图 v3 —— 自上而下树；三个关键二级展开到下一层。
配色/字号按 feishu-cli skill 的莫兰迪规范（viewBox 1600-2000 区间）。"""

import re

MODULES = [
    ("公共能力", "三种使用方式共用", "#FAF6EE", "#B59B6B", "#5C4F2E", [
        ("item", "准备与连接"),
        ("item", "指定目标"),
        ("item", "基本拍摄控制"),
        ("item", "状态反馈"),
        ("item", "切换使用方式"),
        ("item", "取回与整理素材"),
    ]),
    ("Follow", "跟着我拍 · Automatic", "#F2F6FA", "#7A95B5", "#2C3340", [
        ("item", "选定跟随对象"),
        ("item", "设定跟拍关系"),
        ("item", "设定取景景别"),
        ("item", "保持连续跟随"),
        ("item", "调整机位"),
        ("group", "编排镜头 Shot", [
            ("Orbit", "环绕主体"),
            ("Approach · Push", "靠近"),
            ("Pull", "由近退远"),
            ("Pass-by", "侧方掠过"),
            ("Jump · 动作", "轮足"),
        ]),
        ("item", "中断与安全恢复"),
    ]),
    ("B-Cam", "布置好再拍 · Assisted", "#F4F2F8", "#9890B0", "#2C3340", [
        ("item", "布置机位"),
        ("item", "试跑确认"),
        ("item", "执行与重拍"),
        ("group", "预设路线", [
            ("直线移动", "模板"),
            ("弧线移动", "模板"),
            ("环绕移动", "模板"),
            ("平行移动", "模板"),
            ("自定义路线", "走一遍保存"),
        ]),
        ("item", "偏差与安全处理"),
    ]),
    ("FPV", "我来开 · Manual", "#F2F7F3", "#7A9D85", "#2C3340", [
        ("item", "操控方式"),
        ("item", "身体与视线解耦"),
        ("item", "安全档位"),
        ("item", "驾驶中录制与标记"),
        ("group", "互动", [
            ("实时声音", "听现场"),
            ("双向语音", "现场听到我"),
            ("身体动作", "点头·歪头"),
        ]),
    ]),
]

W = 1800
MARGIN = 55
COL_W = 381
COL_GAP = (W - 2 * MARGIN - 4 * COL_W) / 3.0

L1_Y, L1_H = 232, 76
CONTENT_Y = L1_Y + L1_H + 36

L2_INDENT, L2_W, L2_H = 40, 341, 56
L2_GAP = 14
GRP_HEAD_GAP = 16          # 展开组的组长 → 子项
L3_INDENT, L3_W, L3_H = 70, 311, 52
L3_PITCH = 62

FS_TITLE, FS_SUB = 38, 22
FS_L1, FS_L1S = 34, 22
FS_L2 = 29
FS_L3, FS_L3G = 26, 20
FS_NOTE = 20
ROOT_W, ROOT_H, ROOT_Y = 420, 64, 118
TRUNK_Y = 214

C_LINE = "#B0B7C2"
C_NODE_BORDER = "#D0D5DC"
C_TEXT = "#2C3340"
C_MUTED = "#6B7280"
C_GLOSS = "#9CA3AF"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cw(ch, fs):
    o = ord(ch)
    if o > 0x2E80:
        return fs
    if ch == " ":
        return fs * 0.32
    if ch == "·":
        return fs
    return fs * 0.55


def tw(s, fs):
    return sum(cw(c, fs) for c in s)


def fits(name, gloss, w):
    """子节点一行放下「名称 + 说明」吗"""
    need = tw(name, FS_L3) + (tw(gloss, FS_L3G) + 22 if gloss else 0)
    return need <= w - 28


col_x0 = [MARGIN + i * (COL_W + COL_GAP) for i in range(4)]

# ---------- 布局：算出每个一级列的内容块 ----------
layout = []
for m in MODULES:
    blocks = []
    y = CONTENT_Y
    for it in m[5]:
        if it[0] == "item":
            blocks.append(("item", it[1], y, L2_H))
            y += L2_H + L2_GAP
        else:
            kids = []
            hy = y
            ky = hy + L2_H + GRP_HEAD_GAP
            for kn, kg in it[2]:
                kids.append((kn, kg, ky))
                ky += L3_H + (L3_PITCH - L3_H)
            y = ky - (L3_PITCH - L3_H) + L2_GAP
            blocks.append(("group", it[1], hy, kids, ky - (L3_PITCH - L3_H) + L3_H))
    layout.append((blocks, y - L2_GAP))

H = int(max(b for _, b in layout) + 120)

P = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H),
     '<rect x="0" y="0" width="%d" height="%d" fill="#FFFFFF"/>' % (W, H),
     '<text x="%d" y="56" font-size="%d" font-weight="bold" fill="%s">LRC101 用户侧功能结构图</text>' % (MARGIN, FS_TITLE, C_TEXT),
     '<text x="%d" y="92" font-size="%d" fill="%s">一级 = 功能归属　｜　二级 = 功能模块（同层粒度一致）　｜　「编排镜头 Shot」「预设路线」「互动」三项展开到下一层</text>' % (MARGIN, FS_SUB, C_MUTED)]

# ---------- 根 ----------
root_cx = W / 2.0
P.append('<rect x="%.1f" y="%d" width="%d" height="%d" rx="12" fill="#4E5A6B"/>' % (root_cx - ROOT_W / 2.0, ROOT_Y, ROOT_W, ROOT_H))
P.append('<text x="%.1f" y="%d" font-size="32" font-weight="bold" fill="#FFFFFF" text-anchor="middle">LRC101 用户侧功能</text>' % (root_cx, ROOT_Y + 41))

P.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>' % (root_cx, ROOT_Y + ROOT_H, root_cx, TRUNK_Y, C_LINE))
P.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>' % (col_x0[0] + COL_W / 2, TRUNK_Y, col_x0[3] + COL_W / 2, TRUNK_Y, C_LINE))
for x0 in col_x0:
    P.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>' % (x0 + COL_W / 2, TRUNK_Y, x0 + COL_W / 2, L1_Y, C_LINE))

# ---------- 一级 + 主干 ----------
for i, (name, sub, fill, stroke, tx, _items) in enumerate(MODULES):
    x0 = col_x0[i]
    blocks, bottom = layout[i]
    spine = x0 + 22
    P.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>'
             % (x0 + COL_W / 2, L1_Y + L1_H, spine, L1_Y + L1_H, C_LINE))
    P.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>'
             % (spine, L1_Y + L1_H, spine, bottom - L2_H / 2.0, C_LINE))

    P.append('<rect x="%.1f" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="%s" stroke-width="2"/>' % (x0, L1_Y, COL_W, L1_H, fill, stroke))
    P.append('<text x="%.1f" y="%d" font-size="%d" font-weight="bold" fill="%s" text-anchor="middle">%s</text>' % (x0 + COL_W / 2, L1_Y + 32, FS_L1, tx, esc(name)))
    P.append('<text x="%.1f" y="%d" font-size="%d" fill="%s" text-anchor="middle">%s</text>' % (x0 + COL_W / 2, L1_Y + 60, FS_L1S, C_MUTED, esc(sub)))

    bx = x0 + L2_INDENT
    c_spine = x0 + 56
    for blk in blocks:
        if blk[0] == "item":
            _, n2, by, hh = blk
            P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (spine, by + hh / 2.0, bx, by + hh / 2.0, C_LINE))
            P.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="#FFFFFF" stroke="%s" stroke-width="1"/>' % (bx, by, L2_W, hh, C_NODE_BORDER))
            P.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="middle">%s</text>' % (bx + L2_W / 2, by + hh / 2.0 + 10, FS_L2, C_TEXT, esc(n2)))
        else:
            _, n2, hy, kids, gb = blk
            P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (spine, hy + L2_H / 2.0, bx, hy + L2_H / 2.0, C_LINE))
            P.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="%s" stroke="%s" stroke-width="2"/>' % (bx, hy, L2_W, L2_H, fill, stroke))
            P.append('<text x="%.1f" y="%.1f" font-size="%d" font-weight="bold" fill="%s" text-anchor="middle">%s</text>' % (bx + L2_W / 2, hy + L2_H / 2.0 + 10, FS_L2, C_TEXT, esc(n2)))
            # 子层主干 + 子节点
            P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (c_spine, hy + L2_H, c_spine, kids[-1][2] + L3_H / 2.0, C_LINE))
            for kn, kg, ky in kids:
                P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (c_spine, ky + L3_H / 2.0, x0 + L3_INDENT, ky + L3_H / 2.0, C_LINE))
                P.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="#FFFFFF" stroke="%s" stroke-width="1"/>' % (x0 + L3_INDENT, ky, L3_W, L3_H, C_NODE_BORDER))
                if kg and fits(kn, kg, L3_W):
                    P.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s">%s</text>' % (x0 + L3_INDENT + 16, ky + L3_H / 2.0 + 9, FS_L3, C_TEXT, esc(kn)))
                    P.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="end">%s</text>' % (x0 + L3_INDENT + L3_W - 16, ky + L3_H / 2.0 + 9, FS_L3G, C_GLOSS, esc(kg)))
                else:
                    P.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="middle">%s</text>' % (x0 + L3_INDENT + L3_W / 2, ky + L3_H / 2.0 + 9, FS_L3, C_TEXT, esc(kn if not kg else kn + "　" + kg)))

P.append('<text x="%d" y="%d" font-size="%d" fill="%s">注：公共能力不区分使用方式，各方式内不再重复出现；异常与安全处理作为功能保留，不与执行类功能并列。</text>'
         % (MARGIN, H - 40, FS_NOTE, C_MUTED))
P.append("</svg>")

svg = "\n".join(P)
open("fg-tree3.svg", "w", encoding="utf-8").write(svg)
print("ok:", len(svg), "bytes | W =", W, "| H =", H)
