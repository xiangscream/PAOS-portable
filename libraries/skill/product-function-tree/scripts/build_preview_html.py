# -*- coding: utf-8 -*-
import io, re, sys

# 用法: python build_preview_html.py <tree.svg> <out.html>
SRC = sys.argv[1] if len(sys.argv) > 1 else 'fg-tree3.svg'
DST = sys.argv[2] if len(sys.argv) > 2 else 'fg-tree3.html'

svg = open(SRC, encoding='utf-8').read()
vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
VW, VH = (vb.group(1), vb.group(2)) if vb else ('1600', '1200')
svg_inline = svg.replace('<?xml version="1.0" encoding="UTF-8"?>', '').strip()
# 给 svg 根标签加上自适应宽度
svg_inline = svg_inline.replace('<svg ', '<svg id="tree" preserveAspectRatio="xMinYMin meet" ', 1)

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>LRC101 用户侧功能结构图</title>
<style>
  :root { --line: #E3E6EB; --ink: #2C3340; --muted: #6B7280; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #F6F7F9; color: var(--ink);
         font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; }
  header { position: sticky; top: 0; z-index: 5; background: #fff; border-bottom: 1px solid var(--line);
           padding: 14px 20px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  h1 { font-size: 15px; font-weight: 600; margin: 0; }
  .hint { font-size: 12px; color: var(--muted); }
  .btns { margin-left: auto; display: flex; gap: 8px; }
  button { font: inherit; font-size: 12px; padding: 6px 12px; border-radius: 8px;
           border: 1px solid var(--line); background: #fff; color: var(--ink); cursor: pointer; }
  button.on { background: #EEF2F7; border-color: #C8D2DE; }
  main { padding: 18px 20px 40px; }
  .card { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 10px; overflow: auto; }
  .card.fit svg { width: 100%; height: auto; }
  .card.full svg { width: __VW__px; height: __VH__px; }
</style>
</head>
<body>
<header>
  <h1>LRC101 用户侧功能结构图</h1>
  <span class="hint">一级＝功能归属　二级＝功能模块（同层粒度一致）　「编排镜头 Shot」「预设路线」「互动」展开到下一层</span>
  <div class="btns">
    <button id="bFit" class="on" type="button">适应宽度</button>
    <button id="bFull" type="button">原始大小</button>
  </div>
</header>
<main>
  <div class="card fit" id="card">
__SVG__
  </div>
</main>
<script>
  var card = document.getElementById('card');
  document.getElementById('bFit').onclick = function () {
    card.className = 'card fit'; this.className = 'on'; document.getElementById('bFull').className = '';
  };
  document.getElementById('bFull').onclick = function () {
    card.className = 'card full'; this.className = 'on'; document.getElementById('bFit').className = '';
  };
</script>
</body>
</html>
""".replace('__SVG__', svg_inline).replace('__VW__', VW).replace('__VH__', VH)

open(DST, 'w', encoding='utf-8').write(html)
print('html ok:', len(html), 'bytes')
