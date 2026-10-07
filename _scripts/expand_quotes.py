#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把太短、沒有上下文的引文往前後延伸。

「師乃引頸就刃神色儼然。」只有十一個字，單獨看不知道在講什麼。
做法：在原典檔裡找到那一段，**往前後擴到完整的句子**，直到夠長為止。
擴出來的仍然是原典的連續原文，一個字都沒有加——只是多引了幾句。

擴完一律回頭過 verify，對不上就不寫入。

用法： python3 expand_quotes.py [--min 34] [--dry]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CANON = os.path.join(ROOT, "_data", "原典")
目標 = ["祖師.json", "祖師檔案.json"]

PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t\r"
bare = lambda s: "".join(c for c in (s or "") if c not in PUNCT)
_c = {}


def canon(經號, 卷):
    k = "%s_j%02d" % (經號, 卷)
    if k not in _c:
        p = os.path.join(CANON, k + ".txt")
        _c[k] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    return _c[k]


def 擴(quote, 經號, 卷, 最短):
    """在原典裡找到 quote，往前後補完整句子直到長度達標。"""
    t = canon(經號, 卷)
    if not t:
        return quote
    # 原典檔有換行，先做一個「去標點位置對照」好定位
    flat, idx = [], []
    for i, ch in enumerate(t):
        if ch not in PUNCT:
            flat.append(ch); idx.append(i)
    flat = "".join(flat)
    need = bare(quote)
    at = flat.find(need)
    if at < 0 or flat.find(need, at + 1) >= 0:
        return quote            # 找不到、或出現多次無法確定是哪一處，不動
    s, e = idx[at], idx[at + len(need) - 1] + 1

    def 句首(p):
        j = t.rfind("。", 0, p)
        k = t.rfind("\n", 0, p)
        return max(j + 1, k + 1, 0)

    def 句尾(p):
        j = t.find("。", p)
        k = t.find("\n", p)
        cands = [x for x in (j, k) if x >= 0]
        return (min(cands) + 1) if cands else len(t)

    s, e = 句首(s), 句尾(e - 1)
    guard = 0
    while len(t[s:e].strip()) < 最短 and guard < 8:
        guard += 1
        ns = 句首(s - 1) if s > 0 else s
        ne = 句尾(e) if e < len(t) else e
        # 優先往後補（後文通常才是結果），不夠再往前
        if ne > e and len(t[s:ne].strip()) >= 最短:
            e = ne; break
        if ne > e:
            e = ne
        elif ns < s:
            s = ns
        else:
            break
        if len(t[s:e].strip()) >= 最短:
            break
    out = t[s:e].strip().replace("\n", "")
    # 景德傳燈錄的正文裡混著宋代編者的考訂語（「當作…」「當云…」「舊本…」），
    # 大正藏把它們排進正文，CBETA 的夾註標記抓不到。擴寫時不要擴進那種句子——
    # 那是校訂者在考年代，不是祖師的事跡。
    編者語 = ("當作", "當云", "舊本", "本作", "未詳孰是", "恐誤", "蓋誤", "此處有誤",
              "依廣燈", "依寶林", "正宗記", "今止可云", "已上", "右件")
    if any(w in out and w not in quote for w in 編者語):
        return quote
    return out if need in bare(out) and len(out) >= len(quote) else quote


def main():
    最短 = 34
    dry = "--dry" in sys.argv
    if "--min" in sys.argv:
        最短 = int(sys.argv[sys.argv.index("--min") + 1])
    改 = 0
    for fn in 目標:
        p = os.path.join(ROOT, "_data", fn)
        d = json.load(open(p, encoding="utf-8"))
        群 = d["祖師"] if fn == "祖師.json" else None
        def walk(條):
            nonlocal 改
            q = 條.get("原文") or ""
            if not q or len(q) >= 最短:
                return
            src = 條.get("出處") or {}
            new = 擴(q, src.get("經號"), src.get("卷") or 0, 最短)
            if new != q and len(new) > len(q):
                print("  %2d→%2d  %s\n          ⇒ %s" % (len(q), len(new), q, new))
                改 += 1
                if not dry:
                    條["原文"] = new
        if 群 is not None:
            for pp in 群:
                for s in pp.get("站", []):
                    walk(s)
        else:
            for 名, prof in d["祖師檔案"].items():
                for k, rows in prof.items():
                    for e in rows:
                        walk(e)
        if not dry:
            json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n共擴寫 %d 條%s" % (改, "（試跑，未寫入）" if dry else ""))


if __name__ == "__main__":
    main()
