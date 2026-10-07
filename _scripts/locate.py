#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""古地名定位：走哈佛・復旦中國歷史地理資訊系統（CHGIS）。

規則（使用者定的，見 定案規格_不可違.md）：
- 只採 CHGIS／中研院 CCTS／中研院歷史地名三家，佛學人地名規範不可當依據。
- **查詢一定要帶年份**，否則同名地名會回一堆不同朝代的記錄。
- 今地給到**省・市**，區級不寫。

查詢用的年份是「該祖師在世的大致年代」，只是用來把同名地名篩到對的朝代，
**它本身不會被當成事實寫進成品**。

結果寫到 _data/地名定位.json，給人工覆核後才會進 祖師.json。
查不到的照實記 null，不自己推。

用法： python3 locate.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "_data", "祖師.json")
OUT = os.path.join(HERE, "..", "_data", "地名定位.json")
API = "https://chgis.hudci.org/tgaz/placename"

# 查詢用年份：用來把同名地名篩到對的朝代，不是成品裡的事實
查詢年 = {"達摩": 527, "慧可": 550, "僧璨": 600, "道信": 620, "弘忍": 650, "惠能": 700}

# 個別地點改用「事件當年」查，比用祖師在世中點準
地點查詢年 = {"吉州": 617, "蘄春破頭山": 617, "鄴都": 550, "筦城縣匡救寺": 600}

# 人工指定的查詢名。agent 給的候選有些查不到（複合名），有些會撈到同名的別處：
# 「洛州」在 CHGIS 第一筆是陝西上洛（109.93, 33.87），不是洛陽——會把達摩放到錯的省。
查詢名覆寫 = {
    "洛州": "洛陽縣",
    "蘄州黃梅縣": "黃梅縣",
    "廣州四會縣": "四會縣",
    "河內郡": "河內縣",
    # 第二輪補的：原本查無，是因為查詢年用「祖師在世中點」而不是事件當年，
    # 或因為該地在那個年份叫別的名字。候選由我提出，認定仍由 CHGIS 做。
    "吉州": "廬陵郡",        # 道信抵吉州在大業十三載(617)，當時已改廬陵郡，座標同點
    "鄴都": "鄴縣",
    "蘄州": "蘄春郡",
    "蘄春破頭山": "蘄春郡",
    "相州": "鄴縣",          # 相州治所在鄴
}


def query(name, year):
    qs = urllib.parse.urlencode({"n": name, "yr": year, "fmt": "json"})
    with urllib.request.urlopen(API + "?" + qs, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    jobs = {}
    for p in data["祖師"]:
        for s in p.get("站", []):
            if s.get("地"):
                # 優先用 agent 給的「當時行政地名」候選；查歷史地理庫只認行政地名，
                # 「嵩山少林寺」「碓坊」這種寺院山名查不到。
                q = s.get("行政地名") or s["地"]
                yr0 = 地點查詢年.get(s["地"], 查詢年.get(p["介面名"], 600))
                q = 查詢名覆寫.get(q, q)
                jobs.setdefault(q, (yr0, set()))
                jobs[q][1].add(s["地"])

    out = []
    for name, (yr, 用於) in sorted(jobs.items()):
        rec = {"查詢名": name, "用於地點": sorted(用於), "查詢年": yr,
               "命中": [], "今地": None, "狀態": ""}
        try:
            r = query(name, yr)
        except Exception as e:  # noqa: BLE001
            rec["狀態"] = "查詢失敗：%s" % e
            out.append(rec)
            print("✗ %-12s %s" % (name, e))
            continue
        hits = r.get("placenames") or []
        # CHGIS 有少數記錄經度是 0.00000（吉州、蘄州都有），那是壞資料，丟掉
        def _xy(h):
            try:
                a, b = (h.get("xy coordinates") or "").split(",")
                return float(a), float(b)
            except Exception:
                return None, None
        hits = [h for h in hits if (_xy(h)[0] or 0) > 1]
        # 年代範圍涵蓋查詢年的優先
        def _fit(h):
            try:
                a, b = (h.get("years") or "").split("~")
                return int(a.strip()) <= yr <= int(b.strip())
            except Exception:
                return False
        hits.sort(key=lambda h: (not _fit(h),))
        for h in hits[:5]:
            xy = (h.get("xy coordinates") or "").split(",")
            rec["命中"].append({
                "名": h.get("name"), "編號": h.get("sys_id"),
                "類型": h.get("feature type"), "起訖": h.get("years"),
                "朝代": h.get("parent name"), "網址": h.get("uri"),
                "經度": float(xy[0]) if len(xy) == 2 else None,
                "緯度": float(xy[1]) if len(xy) == 2 else None,
            })
        if not hits:
            rec["狀態"] = "查無——可能是寺院、山名等非行政地名，需另尋來源或留白"
            print("－ %-12s 查無" % name)
        elif len(hits) == 1:
            rec["狀態"] = "單一命中，待人工覆核今地"
            print("○ %-12s 1 筆　%s" % (name, hits[0].get("name")))
        else:
            rec["狀態"] = "多筆命中，待人工判讀"
            print("△ %-12s %d 筆　%s" % (name, len(hits),
                  "／".join(h.get("name", "") for h in hits[:3])))
        out.append(rec)
        time.sleep(0.8)

    json.dump({
        "說明": "CHGIS 查詢結果，待人工覆核。今地欄要人工填到省・市，不自動寫入祖師.json。",
        "來源": "哈佛・復旦 中國歷史地理資訊系統（CHGIS）TGAZ",
        "查詢年說明": "只用來把同名地名篩到對的朝代，不是成品裡的事實",
        "結果": out,
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    ok = sum(1 for r in out if r["命中"])
    print("\n共 %d 個地名，%d 個有命中，%d 個查無。結果寫入 _data/地名定位.json"
          % (len(out), ok, len(out) - ok))


if __name__ == "__main__":
    main()
