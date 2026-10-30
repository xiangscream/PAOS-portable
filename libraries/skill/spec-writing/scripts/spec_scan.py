# -*- coding: utf-8 -*-
"""规格语气自查：找出「说明而非规格」的候选句。

判据：删掉后研发行为不变、用户可见结果不变 -> 说明，应删或改成事实陈述。

用法: python spec_scan.py <markdown文件>

注意：本脚本只做候选筛选，命中不等于必删。
      「触发 -> 系统动作」型的句子会被 PATTERNS 命中，但那是规格，必须人工判为误报保留。
"""
import re
import sys

PATTERNS = [
    # (正则, 病灶类型)
    (r'不必先', '替用户辩解'),
    (r'不需要先', '替用户辩解'),
    (r'无需(了解|知道)', '替用户辩解'),
    (r'用户不用知道', '替用户辩解'),
    (r'避免', '防误读声明'),
    (r'两者分开', '防误读声明'),
    (r'以免', '防误读声明'),
    (r'共同实现', '实现手段'),
    (r'由[^，。]{2,20}(共同)?实现', '实现手段'),
    (r'内部(由|通过)', '内部实现'),
    (r'通过[^，。]{2,15}完成', '实现手段'),
    (r'[，。]?(否则|若不|不足时)[^。]*[，。]', '条件-兜底句式'),
    (r'不应(出现|表现为)', '设计意图声明'),
    (r'应表现为', '设计意图声明'),
    (r'产品目标(是|为)', '意图声明'),
    (r'受到[^，。]{0,12}(约束|限制)', '能力免责式'),
    (r'受限于', '能力免责式'),
    (r'优先(保留|利用|选择)', '内部策略'),
    (r'并让用户知道', '结果描述模糊'),
    (r'同时呈现', '实现手段'),
]

# 这些词一旦出现在句子里，说明该句规定了「禁止行为」，是规格，抑制报错
SPEC_MARKERS = [r'不能', r'不得', r'不出现', r'不返回', r'不超过', r'不改变', r'禁止']


def scan(path):
    t = open(path, encoding='utf-8').read()
    hits = []
    for line in t.split('\n'):
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('|') or s.startswith('```'):
            continue
        for sent in re.split(r'(?<=[。；])', s):
            sent = sent.strip()
            if not sent:
                continue
            # 含「禁止规范标记」的整句不报（多为规格）
            if any(re.search(p, sent) for p in SPEC_MARKERS):
                continue
            for pat, kind in PATTERNS:
                m = re.search(pat, sent)
                if m:
                    hits.append((kind, m.group(0), sent[:100]))
                    break
    return hits


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else 'follow_sample.md'
    hs = scan(p)
    print('候选 %d 处（命中不等于必删，请逐条人工判定）\n' % len(hs))
    for kind, kw, sent in hs:
        print('[%s] 《%s》' % (kind, kw))
        print('   %s\n' % sent)


if __name__ == '__main__':
    main()
