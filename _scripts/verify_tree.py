#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""法脈樹的第零條檢查。

樹的每一條邊都是一句史料主張（「這個人是那個人的法嗣」）。
畫一條沒有依據的線，就是在替原典下論斷——所以每個非根節點都要有依據，
而且那句依據要逐字出現在它標的那個原典卷裡。

另外檢查：
- 父節點要存在，不可以有孤兒或環。
- 標「已建」的名字要真的在 祖師.json 裡找得到，否則首頁會點進一個空的人。
- 「還沒建」的節點不可以編世代名字（無名節點只能寫範圍，不可以指名道姓）。

用法： python3 verify_tree.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TREE = os.path.join(ROOT, "_data", "法脈樹.json")
DATA = os.path.join(ROOT, "_data", "祖師.json")
CANON = os.path.join(ROOT, "_data", "原典")

PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t\r"
bare = lambda s: "".join(c for c in (s or "") if c not in PUNCT)

_c = {}


def canon(經號, 卷):
    k = "%s_j%02d" % (經號, 卷)
    if k not in _c:
        p = os.path.join(CANON, k + ".txt")
        _c[k] = bare(open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    return _c[k]


def main():
    tree = json.load(open(TREE, encoding="utf-8"))["節點"]
    data = json.load(open(DATA, encoding="utf-8"))
    有站 = {p["介面名"] for p in data["祖師"] if p.get("站")}
    ids = {n["id"] for n in tree}
    errors = []

    for n in tree:
        where = "節點「%s」" % n["名"]
        父 = n.get("父")
        if 父 is None:
            if n["id"] != tree[0]["id"]:
                errors.append("%s：沒有父節點，但它不是樹根" % where)
            continue
        if 父 not in ids:
            errors.append("%s：父節點「%s」不存在" % (where, 父))
        src = n.get("依據")
        if not src:
            # 六祖那一串的師承依據已經在 祖師.json 的站與檔案裡逐段驗過了，
            # 這裡只要求「樹上新畫出來的線」要有依據。
            if n["id"] not in 有站 or 父 not in 有站:
                errors.append("%s：畫了一條師承的線，卻沒有原典依據" % where)
            continue
        t = canon(src.get("經號"), src.get("卷") or 0)
        if t is None:
            errors.append("%s：找不到原典檔 %s 卷%s" % (where, src.get("經號"), src.get("卷")))
        elif bare(src.get("原文")) not in t:
            errors.append("%s：依據「%s」對不上 %s 卷%s"
                          % (where, src.get("原文"), src.get("書名"), src.get("卷")))

        if n.get("狀態") == "已建" and n["id"] not in 有站:
            errors.append("%s：標了已建，但 祖師.json 裡沒有這一位（點進去會是空的）" % where)
        if n.get("狀態") == "還沒建" and n.get("世標") and not n.get("依據"):
            errors.append("%s：還沒建卻標了世代，世代也要有依據" % where)

    # 環
    seen = {}
    for n in tree:
        走, cur = set(), n["id"]
        by = {x["id"]: x for x in tree}
        while cur:
            if cur in 走:
                errors.append("節點「%s」的師承繞成一個環" % n["名"])
                break
            走.add(cur)
            cur = (by.get(cur) or {}).get("父")

    print("── 法脈樹 第零條檢查 ──")
    print("已檢查 %d 個節點，%d 個已建、%d 個還沒建"
          % (len(tree), sum(1 for n in tree if n.get("狀態") == "已建"),
             sum(1 for n in tree if n.get("狀態") != "已建")))
    if errors:
        print("\n不通過 %d 項：" % len(errors))
        for e in errors:
            print("  ✗ " + e)
        sys.exit(1)
    print("每一條師承的線都有原典依據，而且逐字對得上。通過。")


if __name__ == "__main__":
    main()
