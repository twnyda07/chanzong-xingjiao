#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收割 workflow 的結果，逐字驗證後才併進 祖師.json。

agent 給的東西一律不信任：每一段原文都回本機原典檔逐字比對，對不上的整筆丟掉。
地依據的合併還多一道：站數與原文必須與原資料檔完全相同，否則整位祖師不併。

用法： python3 harvest.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "_data", "祖師.json")
PICK = os.path.join(ROOT, "_data", "_workflow收割.json")
CANON = os.path.join(ROOT, "_data", "原典")

PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t\r"
bare = lambda s: "".join(c for c in (s or "") if c not in PUNCT)

_cache = {}


def canon(經號, 卷):
    k = "%s_j%02d" % (經號, 卷)
    if k not in _cache:
        p = os.path.join(CANON, k + ".txt")
        _cache[k] = bare(open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    return _cache[k]


def ok(st):
    """原文是否逐字出現在該出處的原典檔裡。"""
    src = st.get("出處") or {}
    t = canon(src.get("經號"), src.get("卷") or 0)
    if not t:
        return False, "找不到原典檔"
    if not st.get("原文"):
        return False, "原文空白"
    if bare(st["原文"]) not in t:
        return False, "原文對不上原典"
    for kw in st.get("關鍵詞") or []:
        if bare(kw) not in bare(st["原文"]):
            return False, "關鍵詞「%s」不在原文裡" % kw
    ev = st.get("地依據")
    if ev and bare(ev) not in t:
        return False, "地依據對不上原典"
    if st.get("地") and not ev:
        return False, "有地點卻沒有地依據"
    if st.get("地"):
        # 地名的每個字要依序出現在依據裡。原文常是「舒州之皖公山」「却返蘄春住破頭山」，
        # 中間夾字很正常；但像「破頭山碓坊」這種把兩個地方拼起來的名字就該被擋下來。
        if not subseq(bare(st["地"]), bare(ev)) and not subseq(bare(st["地"]), bare(st["原文"])):
            return False, "地點「%s」在它自己的依據裡拼不出來" % st["地"]
    return True, ""


def subseq(needle, hay):
    """needle 的每個字依序出現在 hay 裡。"""
    i = 0
    for c in hay:
        if i < len(needle) and c == needle[i]:
            i += 1
    return i == len(needle)


def clean(st):
    """只留下允許的欄位。沒有可以放轉述的地方。"""
    out = {
        "地": st.get("地") or None,
        "地依據": st.get("地依據") or None,
        "今地": None,
        "年": st.get("年") or None,
        "人": [p for p in (st.get("人") or []) if p and p != "—"],
        "原文": st["原文"],
        "關鍵詞": st.get("關鍵詞") or [],
        "出處": st["出處"],
    }
    if st.get("行政地名"):
        out["行政地名"] = st["行政地名"]
    if st.get("地類"):
        out["地類"] = st["地類"]
    if st.get("異文提醒"):
        out["異文提醒"] = st["異文提醒"]
    return out


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    got = json.load(open(PICK, encoding="utf-8"))
    by名 = {p["介面名"]: p for p in data["祖師"]}
    報告 = []

    # ── 一、五祖的地點依據：站數與原文必須完全吻合才併 ──
    for blk in got.get("地依據", []):
        名 = blk["祖師"]
        舊 = by名[名]["站"]
        新 = blk.get("站", [])
        if len(新) != len(舊):
            報告.append("✗ %s：agent 回 %d 站，原本 %d 站，數目不符 → 整位不併"
                        % (名, len(新), len(舊)))
            continue
        壞 = []
        for i, (a, b) in enumerate(zip(舊, 新), 1):
            if bare(a["原文"]) != bare(b.get("原文", "")):
                壞.append("第%d站原文被改動" % i)
            else:
                good, why = ok(b)
                if not good:
                    壞.append("第%d站 %s" % (i, why))
        if 壞:
            報告.append("✗ %s：%s → 整位不併" % (名, "；".join(壞[:3])))
            continue
        合併 = []
        for a, b in zip(舊, 新):
            c = clean(b)
            c["原文"] = a["原文"]            # 原文一律用原本已驗證過的
            c["關鍵詞"] = a.get("關鍵詞", [])  # 關鍵詞也維持原本的
            c["今地"] = a.get("今地")
            if a.get("異文提醒"):
                c["異文提醒"] = a["異文提醒"]
            合併.append(c)
        掉地 = sum(1 for a, c in zip(舊, 合併) if a.get("地") and not c.get("地"))
        by名[名]["站"] = 合併
        報告.append("✓ %s：%d 站已補地依據%s"
                    % (名, len(合併), ("，其中 %d 站地點查無依據已改為未載" % 掉地) if 掉地 else ""))

    # ── 二、惠能：以宗寶本為主（使用者第六題的決定） ──
    主 = next((b for b in got.get("惠能", []) if b["來源"] == "六祖大師法寶壇經"), None)
    if 主:
        收, 丟 = [], []
        for i, st in enumerate(主["站"], 1):
            good, why = ok(st)
            (收 if good else 丟).append(clean(st) if good else "第%d站 %s" % (i, why))
        # 那首偈掛上敦煌本異文
        異 = got.get("壇經異文", [])
        for st in 收:
            if "菩提本無樹" in st["原文"]:
                m = next((x for x in 異 if "菩提本無樹" in (x.get("宗寶本") or "")), None)
                if m and m.get("敦煌本"):
                    t = canon("T2007", 1)
                    if t and bare(m["敦煌本"]) in t:
                        st["異文提醒"] = "敦煌本 T2007 作：" + m["敦煌本"]
        by名["惠能"]["站"] = 收
        by名["惠能"].pop("待辦", None)
        報告.append("✓ 惠能：宗寶本 %d 站通過%s"
                    % (len(收), ("，丟掉 %d 站（%s）" % (len(丟), 丟[0])) if 丟 else ""))

    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("── 收割結果 ──")
    for r in 報告:
        print("  " + r)
    n = sum(len(p.get("站", [])) for p in data["祖師"])
    print("\n現在共 %d 站，%d 位祖師" % (n, sum(1 for p in data["祖師"] if p.get("站"))))

    # 其他來源與古畫另存，供人工挑選，不自動併入
    other = [b for b in got.get("惠能", []) if b["來源"] != "六祖大師法寶壇經"]
    json.dump({"未採用的惠能來源": other, "壇經異文": got.get("壇經異文", []),
               "古畫候選": got.get("古畫", [])},
              open(os.path.join(ROOT, "_data", "_待挑選.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("另存 _data/_待挑選.json（其他惠能來源、異文、古畫候選）")


if __name__ == "__main__":
    main()
