#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""祖師檔案（生平／參學／開悟因緣／教學風格／歷史定位／交集人物）的第零條檢查。

每一條的原文都要逐字出現在它自己標的那個原典檔裡。對不上就丟掉，不是警告。
另外擋「標題」寫成評語——標題只能是事實語，不可以出現形容詞。

用法： python3 verify_profiles.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PROF = os.path.join(ROOT, "_data", "祖師檔案.json")
DATA = os.path.join(ROOT, "_data", "祖師.json")
CANON = os.path.join(ROOT, "_data", "原典")

PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t\r"
bare = lambda s: "".join(c for c in (s or "") if c not in PUNCT)

# 標題只能是事實語。這些字一出現就是在下評語或抒情，擋掉。
評語字 = ["虔誠", "安詳", "慈悲", "偉大", "殊勝", "精進不懈", "令人", "可見",
          "深刻", "重要", "崇高", "卓越", "感人", "震撼", "啟發", "智慧的",
          "開創", "奠定", "影響深遠", "不朽", "典範"]

_c = {}


def canon(經號, 卷):
    k = "%s_j%02d" % (經號, 卷)
    if k not in _c:
        p = os.path.join(CANON, k + ".txt")
        _c[k] = bare(open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    return _c[k]


def check(條, where, errors):
    src = 條.get("出處") or {}
    t = canon(src.get("經號"), src.get("卷") or 0)
    if t is None:
        errors.append("%s：找不到原典檔 %s 卷%s" % (where, src.get("經號"), src.get("卷")))
        return False
    q = 條.get("原文") or ""
    if not q.strip():
        errors.append("%s：原文空白" % where)
        return False
    if bare(q) not in t:
        errors.append("%s：原文對不上 %s 卷%s ——「%s」"
                      % (where, src.get("書名"), src.get("卷"), q[:28]))
        return False
    lab = 條.get("標題") or 條.get("姓名") or ""
    for w in 評語字:
        if w in lab:
            errors.append("%s：標題「%s」含評語字「%s」，標題只能是事實語" % (where, lab, w))
            return False
    for f in 條:
        if f not in ("標題", "姓名", "身分", "年", "原文", "出處"):
            errors.append("%s：未定義欄位「%s」——不得新增可放轉述的欄位" % (where, f))
            return False
    return True


def main():
    if not os.path.exists(PROF):
        print("還沒有 祖師檔案.json", file=sys.stderr)
        sys.exit(1)
    data = json.load(open(PROF, encoding="utf-8"))
    errors, n = [], 0
    # 各書異寫要從 祖師.json 拿，不然「慧能」這種換字的自我指涉會溜過去
    別 = {}
    try:
        for x in json.load(open(DATA, encoding="utf-8"))["祖師"]:
            s = {x["介面名"]}
            for v in x.get("各書異寫") or []:
                s.add(re.sub(r"（.*?）", "", v).strip())
            if len(x["介面名"]) == 4:
                s.update({x["介面名"][:2], x["介面名"][2:]})
            別[x["介面名"]] = {a for a in s if a}
    except Exception:  # noqa: BLE001
        pass

    for 名, p in data.get("祖師檔案", {}).items():
        for 節 in ("生平", "參學歷程", "開悟因緣", "教學風格", "歷史定位", "交集人物"):
            for i, 條 in enumerate(p.get(節, []), 1):
                n += 1
                check(條, "%s．%s 第%d條" % (名, 節, i), errors)
                # 交集人物不可以是他自己（比照 verify.py 的「遇到的人」那條）
                if 節 == "交集人物" and 條.get("姓名") in 別.get(名, set()):
                    errors.append("%s．交集人物 第%d條：姓名寫了「%s」，那是他自己"
                                  % (名, i, 條.get("姓名")))

    print("── 祖師檔案 第零條檢查 ──")
    print("已檢查 %d 條，涵蓋 %d 個原典卷次" % (n, len(_c)))
    if errors:
        print("\n不通過 %d 項：" % len(errors))
        for e in errors[:40]:
            print("  ✗ " + e)
        sys.exit(1)
    print("全部逐字對上原典。通過。")


if __name__ == "__main__":
    main()
