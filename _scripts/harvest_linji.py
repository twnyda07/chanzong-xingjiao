#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收割臨濟宗唐段五位（義玄→存獎→慧顒→延沼→省念）的 workflow 產出。

**agent 給的一律不信任。** 每一筆都回本機原典檔逐字比對，對不上的整筆丟掉，
不猜、不修、不補標點。丟掉什麼、為什麼丟，全部印出來。

agent 把經號寫成 "T1985_j01" 這種帶卷次的格式，要先拆成 經號=T1985、卷=1
才對得上原典檔命名（T1985_j01.txt）。拆出來的卷次若與它自己填的「卷」不一致，
視為來源可疑，整筆丟掉。

用法： python3 harvest_linji.py <workflow 輸出檔.json>
       python3 harvest_linji.py <輸出檔> --寫入     # 確認過才真的寫進資料檔
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "_data", "祖師.json")
PROF = os.path.join(ROOT, "_data", "祖師檔案.json")
CANON = os.path.join(ROOT, "_data", "原典")

PUNCT = "。，、；：？！「」『』（）〔〕《》〈〉…—·　 \n\t\r"
bare = lambda s: "".join(c for c in (s or "") if c not in PUNCT)

# verify_profiles.py 那份評語字表，收割時就先擋掉，不要等建置才爆
評語字 = ["虔誠", "安詳", "慈悲", "偉大", "殊勝", "精進不懈", "令人", "可見",
          "深刻", "重要", "崇高", "卓越", "感人", "震撼", "啟發", "智慧的",
          "開創", "奠定", "影響深遠", "不朽", "典範"]

# 臨濟唐段五位的識別色。比照已定案的六祖那組：彩度 25–49%、明度 35–47%，
# 都落在六祖原本的 25–61% / 36–50% 區間內，色相彼此至少隔 25 度，也避開六祖已占的色相。
# **這五色是我配的，還沒給使用者看過**，他要換隨時改這裡就好。
配色 = {
    "臨濟義玄": "#2f7f8b",   # 青碧　色相 188
    "興化存獎": "#7a7c35",   # 苔綠　色相 62
    "南院慧顒": "#9c5584",   # 藕紫　色相 320
    "風穴延沼": "#4f5f9e",   # 黛藍　色相 228
    "首山省念": "#4f8450",   # 竹綠　色相 121
}

_cache = {}


def canon(經號, 卷):
    k = "%s_j%02d" % (經號, 卷)
    if k not in _cache:
        p = os.path.join(CANON, k + ".txt")
        _cache[k] = bare(open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    return _cache[k]


def 正規化出處(src):
    """T1985_j01 → (T1985, 1)。拆出來的卷次與它自己填的卷不符就是來源可疑。"""
    if not isinstance(src, dict):
        return None, "出處不是物件"
    經 = (src.get("經號") or "").strip()
    卷 = src.get("卷")
    m = re.match(r"^([A-Z]+\d+)_j(\d+)$", 經)
    if m:
        經, 卷附 = m.group(1), int(m.group(2))
        if 卷 is not None and int(卷) != 卷附:
            return None, "經號寫 %s 但卷填 %s，兩者不符" % (src.get("經號"), 卷)
        卷 = 卷附
    if not 經 or 卷 is None:
        return None, "出處缺經號或卷"
    return {"經號": 經, "書名": src.get("書名") or "", "卷": int(卷)}, ""


def subseq(needle, hay):
    i = 0
    for c in hay:
        if i < len(needle) and c == needle[i]:
            i += 1
    return i == len(needle)


def 查原文(原文, src):
    t = canon(src["經號"], src["卷"])
    if t is None:
        return "找不到原典檔 %s_j%02d.txt" % (src["經號"], src["卷"])
    if not (原文 or "").strip():
        return "原文空白"
    if bare(原文) not in t:
        return "原文對不上 %s 卷%d" % (src["經號"], src["卷"])
    return ""


# 人工覆核過的地點修訂：agent 把原典沒有的字拼進地名，改回原典真的有的那個詞。
# key = (祖師, agent 給的地名)，value = (改成什麼, 憑哪一句原典)。
# **只收「那個詞逐字就在依據裡」的情形**，推論出來的一律不收，寧可留白。
地點修訂 = {
    ("臨濟義玄", "鎮州臨濟院"): (
        "鎮州",
        "原典作「尋抵河北鎮州城東南隅，臨滹沱河側小院住持，其臨濟因地得名」。"
        "「鎮州」是原典的字；「臨濟院」是把「臨濟」與「小院」拼起來的，原典沒有這三個字連用。"),
}
# 兩本書記的年不一樣，**兩說並陳，不調和**（規格第三節：傳說與史傳不一致照演，出處自己會說話）。
# 掛法比照壇經那首偈：「<書名> <經號> 卷<n> 作：」＋該書逐字原文。
# 下面這段文字一樣要通過原典比對才掛得上去，掛不上就整個不掛。
異文 = {
    ("臨濟義玄", "咸通八年"): {
        "認": "咸通八年",                      # 站的原文裡出現這幾個字就掛
        "書名": "景德傳燈錄", "經號": "T2076", "卷": 12,
        "原文": "時唐咸通七年丙戌四月十日。師將示寂上堂云。",
    },
}

# 生平欄也要兩說並陳：agent 只取了語錄塔記那一說，另一說補上去，各掛各的出處。
# 補進來的一樣要過原典比對，對不上就不補。
補檔案條 = {
    ("臨濟義玄", "生平"): [
        {"標題": "示寂", "年": "唐咸通七年丙戌四月十日",
         "原文": "時唐咸通七年丙戌四月十日。師將示寂上堂云。吾滅後不得滅却吾正法眼藏。",
         "出處": {"經號": "T2076", "書名": "景德傳燈錄", "卷": 12}},
    ],
}

# 人工覆核過、確定原典沒有交代地點的，直接留白（會顯示成「原典未載地點」）
地點留白 = {
    ("風穴延沼", "廣慧寺"):
        "原典只作「賜額廣慧」，沒有「寺」字；該寺在哪一州要從「汝州太師宋侯捨宅為寺」"
        "推，那是推論不是原典的字，依「不要自己編事實」留白。",
}


def 收站(st, 祖師名):
    註 = []
    src, why = 正規化出處(st.get("出處"))
    if why:
        return None, why, 註
    why = 查原文(st.get("原文"), src)
    if why:
        return None, why, 註
    # 關鍵詞只是畫面上的色塊標籤，不是經文本身。對不上就**只丟那個詞**，
    # 不要連整段已驗證的原文一起丟掉——但也絕不讓它上畫面（鐵律零：畫面的字只能是原典的字）。
    關鍵詞 = []
    for kw in st.get("關鍵詞") or []:
        if bare(kw) in bare(st["原文"]):
            關鍵詞.append(kw)
        else:
            註.append("丟掉關鍵詞「%s」（不在它自己的原文裡）" % kw)
    ev = st.get("地依據")
    地 = st.get("地")
    if ev and bare(ev) not in canon(src["經號"], src["卷"]):
        return None, "地依據對不上原典", 註
    if 地 and not ev:
        註.append("丟掉地點「%s」（沒有地依據）" % 地)
        地 = None
    if 地 and (祖師名, 地) in 地點留白:
        註.append("地點「%s」留白：%s" % (地, 地點留白[(祖師名, 地)]))
        地, ev = None, None
    elif 地 and (祖師名, 地) in 地點修訂:
        新, 因 = 地點修訂[(祖師名, 地)]
        註.append("地點「%s」→「%s」：%s" % (地, 新, 因))
        地 = 新
    if 地 and not subseq(bare(地), bare(ev)) and not subseq(bare(地), bare(st["原文"])):
        # 原典常在第一次寫全名、之後只寫簡稱（「依棲黃蘗山中」→「却回黃蘗」）。
        # 這一句只寫簡稱，但**同一卷裡別處有全名**，就認；否則丟掉。
        # 這條規則救得回「黃蘗山」，救不回「鎮州臨濟院」「廣慧寺」——那兩個全卷都沒出現過。
        全名在同卷 = bare(地) in canon(src["經號"], src["卷"])
        簡稱在依據 = any(subseq(bare(地)[:k], bare(ev)) and k >= 2
                         for k in range(len(bare(地)), 1, -1))
        if 全名在同卷 and 簡稱在依據:
            註.append("地點「%s」這一句只寫簡稱，同卷別處有全名，照收" % 地)
        else:
            註.append("丟掉地點「%s」（在它自己的依據裡拼不出來，全卷也沒有全名，"
                      "未經人工覆核不自行改寫）" % 地)
            地, ev = None, None
    st = dict(st, 關鍵詞=關鍵詞)
    # 「遇到的人」不可以是他自己。agent 很容易把主角也列進去
    # （2026-10-08 使用者抓到惠能第 10 站遇到惠能，整整 13 站都有）。
    # 完全同名才刪——「惠能嚴父」是他父親，是另一個人。
    自己 = {祖師名}
    if len(祖師名) == 4:
        自己.update({祖師名[:2], 祖師名[2:]})
    人 = []
    for who in st.get("人") or []:
        if who in 自己:
            註.append("丟掉遇到的人「%s」（那是他自己）" % who)
        else:
            人.append(who)
    st = dict(st, 人=人)
    out = {
        "地": 地 or None,
        "地依據": ev or None,
        "今地": None,                       # 等 locate.py 去查，agent 給的不收
        "年": st.get("年") or None,
        "人": [p for p in (st.get("人") or []) if p and p != "—"],
        "原文": st["原文"],
        "關鍵詞": st.get("關鍵詞") or [],
        "出處": src,
    }
    if st.get("行政地名"):
        out["行政地名"] = st["行政地名"]
    for (who, _), v in 異文.items():
        if who == 祖師名 and v["認"] in out["原文"]:
            t = canon(v["經號"], v["卷"])
            if t and bare(v["原文"]) in t:
                out["異文提醒"] = "%s %s 卷%d 作：%s" % (v["書名"], v["經號"], v["卷"], v["原文"])
                註.append("掛上異文：%s 卷%d 作「%s」" % (v["書名"], v["卷"], v["原文"][:16]))
            else:
                註.append("⚠ 異文掛不上去（%s 卷%d 裡找不到那句），整個不掛"
                          % (v["書名"], v["卷"]))
    return out, "", 註


def 收檔案條(c, 是人物):
    src, why = 正規化出處(c.get("出處"))
    if why:
        return None, why
    why = 查原文(c.get("原文"), src)
    if why:
        return None, why
    lab = c.get("姓名") if 是人物 else c.get("標題")
    if not (lab or "").strip():
        return None, "沒有標題／姓名"
    for w in 評語字:
        if w in lab:
            return None, "標題「%s」含評語字「%s」" % (lab, w)
    if 是人物:
        return {"姓名": c["姓名"], "身分": c.get("身分") or "",
                "原文": c["原文"], "出處": src}, ""
    return {"標題": c["標題"], "年": c.get("年") or None,
            "原文": c["原文"], "出處": src}, ""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    got = json.load(open(sys.argv[1], encoding="utf-8"))["result"]
    寫入 = "--寫入" in sys.argv

    新祖師, 新檔案, 報告 = [], {}, []
    總收, 總丟 = 0, 0

    for 名, v in got.items():
        收站們, 丟站, 修正 = [], [], []
        for i, st in enumerate(v.get("站", []), 1):
            ok, why, 註 = 收站(st, 名)
            for n in 註:
                修正.append("第%d站（%s）：%s" % (i, st.get("地") or "未載", n))
            (收站們.append(ok) if ok else 丟站.append("第%d站（%s）：%s"
                                                     % (i, st.get("地") or "未載", why)))
        檔 = {}
        丟條 = []
        for 面向, 條s in (v.get("檔案") or {}).items():
            是人物 = (面向 == "交集人物")
            留 = []
            for j, c in enumerate(條s, 1):
                ok, why = 收檔案條(c, 是人物)
                (留.append(ok) if ok else
                 丟條.append("%s 第%d條（%s）：%s"
                            % (面向, j, c.get("姓名") or c.get("標題") or "?", why)))
            for c in 補檔案條.get((名, 面向), []):
                ok, why = 收檔案條(c, 是人物)
                if ok:
                    留.append(ok)
                    修正.append("%s 補上一條：%s 卷%d「%s」"
                                % (面向, c["出處"]["書名"], c["出處"]["卷"], c["標題"]))
                else:
                    丟條.append("%s 要補的那條補不上去：%s" % (面向, why))
            if 留:
                檔[面向] = 留

        收數 = len(收站們) + sum(len(x) for x in 檔.values())
        丟數 = len(丟站) + len(丟條)
        總收 += 收數
        總丟 += 丟數
        報告.append("── %s　收 %d　整筆丟 %d　局部修正 %d"
                    % (名, 收數, 丟數, len(修正)))
        for x in 丟站 + 丟條:
            報告.append("     ✗ " + x)
        for x in 修正:
            報告.append("     · " + x)

        if not 收站們:
            報告.append("     ⚠ 一站都沒通過，這一位整個不收")
            continue
        新祖師.append({
            "介面名": 名,
            "世代": v.get("世代") or "",
            "師": v.get("師") or "",
            "法嗣": v.get("法嗣") or [],
            "站": 收站們,
        })
        新檔案[名] = 檔

    print("\n".join(報告))
    print("\n── 合計　收 %d 丟 %d ──" % (總收, 總丟))
    for p in 新祖師:
        print("  %s　%d 站　檔案 %d 條"
              % (p["介面名"], len(p["站"]),
                 sum(len(x) for x in 新檔案[p["介面名"]].values())))

    out = os.path.join(ROOT, "_data", "_臨濟唐段收割.json")
    json.dump({"祖師": 新祖師, "祖師檔案": 新檔案},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已存 %s" % os.path.relpath(out, ROOT))
    if not 寫入:
        print("（這一步只做驗證與落地暫存，沒有動 祖師.json。確認無誤再加 --寫入）")
        return

    data = json.load(open(DATA, encoding="utf-8"))
    prof = json.load(open(PROF, encoding="utf-8"))
    既有 = {p["介面名"] for p in data["祖師"]}
    加 = 0
    for p in 新祖師:
        if p["介面名"] in 既有:
            print("  ！%s 已經在資料檔裡，跳過（要改請先手動刪掉舊的）" % p["介面名"])
            continue
        # 世代只留數字。agent 寫「臨濟下第一世（開宗）」，括號裡那三個字是它自己的話，
        # 不是原典的字，依鐵律零不收——欄位只放得下數字，結構上就沒地方放轉述。
        漢數 = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        m = re.search(r"第([一二三四五六七八九十])世", p["世代"] or "")
        data["祖師"].append({
            "序": len(data["祖師"]) + 1,
            "介面名": p["介面名"],
            "各書異寫": [],
            "法脈": {"宗": "臨濟宗", "世": 漢數.get(m.group(1)) if m else None,
                     "師": p["師"], "法嗣": p["法嗣"]},
            "色": 配色.get(p["介面名"], "#6b645b"),
            "站": p["站"],
        })
        prof["祖師檔案"][p["介面名"]] = 新檔案[p["介面名"]]
        加 += 1
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(prof, open(PROF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已寫入 %d 位。接著跑 locate.py 補座標，再跑 build.py。" % 加)


if __name__ == "__main__":
    main()
