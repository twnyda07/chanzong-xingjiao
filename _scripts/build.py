#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 _data/祖師.json 編成單檔遊戲 遊戲.html（雙擊就能開，不需要伺服器）。

建置前先跑 verify.py；原文對不上原典就不給編。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "_data", "祖師.json")
PROF = os.path.join(ROOT, "_data", "祖師檔案.json")
ERAS = os.path.join(ROOT, "_data", "年代對照.json")
PICS = os.path.join(ROOT, "_data", "畫像出處.json")
TREE = os.path.join(ROOT, "_data", "法脈樹.json")
TPL = os.path.join(HERE, "template.html")
OUT = os.path.join(ROOT, "遊戲.html")


def main():
    for v in ("verify.py", "verify_profiles.py", "verify_tree.py"):
        r = subprocess.run([sys.executable, os.path.join(HERE, v)],
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            print("\n建置中止：原文沒有逐字對上原典（%s）。" % v, file=sys.stderr)
            sys.exit(1)

    data = json.load(open(DATA, encoding="utf-8"))
    tpl = open(TPL, encoding="utf-8").read()
    prof = json.load(open(PROF, encoding="utf-8"))
    html = tpl.replace("/*__DATA__*/null",
                       json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__PROFILES__*/null",
                        json.dumps(prof, ensure_ascii=False, separators=(",", ":")))
    eras = json.load(open(ERAS, encoding="utf-8"))
    html = html.replace("/*__ERAS__*/null",
                        json.dumps(eras, ensure_ascii=False, separators=(",", ":")))
    tree = json.load(open(TREE, encoding="utf-8"))
    html = html.replace("/*__TREE__*/null",
                        json.dumps(tree, ensure_ascii=False, separators=(",", ":")))
    pics = json.load(open(PICS, encoding="utf-8"))
    html = html.replace("/*__PICS__*/null",
                        json.dumps(pics, ensure_ascii=False, separators=(",", ":")))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    n = sum(len(p.get("站", [])) for p in data["祖師"])
    print("\n已編出 遊戲.html　%d 站　%d 位祖師"
          % (n, sum(1 for p in data["祖師"] if p.get("站"))))


if __name__ == "__main__":
    main()
