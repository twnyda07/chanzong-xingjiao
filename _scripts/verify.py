#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第零條的機器檢查：資料檔裡每一句「原文」都必須逐字出現在原典檔裡。

對不上就離開碼 1，正式站的建置流程要卡在這裡，不給過。
順便查規則 11（缺字／擴充區罕用字）與關鍵詞是否真的出自該段原文。

用法： python3 verify.py
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "_data", "祖師.json")
CANON = os.path.join(HERE, "..", "_data", "原典")

# 原典檔裡的標點由 CBETA 加，比對時兩邊都剝掉，比的是「字」
PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t"


def bare(s):
    return "".join(c for c in s if c not in PUNCT)


def _subseq(needle, hay):
    """needle 的每個字依序出現在 hay 裡（原文常夾字，如「舒州之皖公山」）。"""
    i = 0
    for c in hay:
        if i < len(needle) and c == needle[i]:
            i += 1
    return i == len(needle)


def rare_chars(s):
    """擴充區罕用字：播放端常缺字型，會變成方框。"""
    out = []
    for c in s:
        o = ord(c)
        if 0x3400 <= o <= 0x4DBF or o >= 0x20000:
            out.append(c)
    return out


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    cache = {}
    errors, warns, checked = [], [], 0

    for p in data["祖師"]:
        for idx, st in enumerate(p.get("站", []), 1):
            where = "%s 第%d站（%s）" % (p["介面名"], idx, st.get("地", "?"))
            src = st["出處"]
            key = "%s_j%02d" % (src["經號"], src["卷"])
            if key not in cache:
                path = os.path.join(CANON, key + ".txt")
                if not os.path.exists(path):
                    errors.append("%s：找不到原典檔 %s.txt" % (where, key))
                    continue
                cache[key] = bare(open(path, encoding="utf-8").read())
            checked += 1

            quote = st["原文"]
            if not quote.strip():
                errors.append("%s：原文是空的" % where)
                continue
            if bare(quote) not in cache[key]:
                errors.append("%s：原文對不上 %s 卷%s\n      「%s」"
                              % (where, src["書名"], src["卷"], quote[:40]))

            for r in rare_chars(quote):
                warns.append("%s：原文含擴充區罕用字「%s」(U+%04X)，播放端可能變方框"
                             % (where, r, ord(r)))
            if re.search(r"\[[^\]]*[*@/+\-][^\]]*\]", quote):
                errors.append("%s：原文含 CBETA 缺字組字式（如 [示*谷]），不可直接上畫面" % where)

            for kw in st.get("關鍵詞", []):
                if bare(kw) not in bare(quote):
                    errors.append("%s：關鍵詞「%s」不在該段原文裡" % (where, kw))

            # 地點若沒出現在該段原文裡，就是我從上下文推的——要逐一人工確認，
            # 否則就是 dont-invent-facts 那條在講的「推算出來的東西看起來跟真的一樣」
            place, ev = st.get("地"), st.get("地依據")
            if place:
                if not ev:
                    errors.append("%s：有地點「%s」卻沒有地依據" % (where, place))
                elif bare(ev) not in cache[key]:
                    errors.append("%s：地依據對不上 %s 卷%s" % (where, src["書名"], src["卷"]))
                elif not _subseq(bare(place), bare(ev)) and not _subseq(bare(place), bare(quote)):
                    errors.append("%s：地點「%s」在它自己的依據裡拼不出來" % (where, place))

            # 結構檢查：不可以有放轉述的欄位
            for f in st:
                if f not in ("地", "地依據", "今地", "年", "人", "原文", "關鍵詞",
                             "出處", "異文提醒", "行政地名", "地類", "座標", "今地來源"):
                    errors.append("%s：出現未定義欄位「%s」——資料檔不得新增可放轉述的欄位" % (where, f))

    print("── 第零條機器檢查 ──")
    print("已檢查 %d 段原文，涵蓋 %d 個原典卷次" % (checked, len(cache)))
    for w in warns:
        print("  ⚠ " + w)
    if errors:
        print("\n不通過 %d 項：" % len(errors))
        for e in errors:
            print("  ✗ " + e)
        sys.exit(1)
    print("全部逐字對上原典。通過。")
    done = sum(1 for p in data["祖師"] if p.get("站"))
    print("進度：%d／6 位祖師已建站" % done)


if __name__ == "__main__":
    main()
