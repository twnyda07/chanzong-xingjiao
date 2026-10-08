#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 locate.py 查到的座標與今日省市，填進 祖師.json 還沒有座標的站。

**只碰沒有座標的站**，已經人工覆核過的既有資料一概不動。
多筆命中只在「所有命中都指同一個點」時才自動採用；指到不同地方的一律跳過、留白，
由人去判——那正是 CHGIS 第一個坑（查「洛州」第一筆是陝西上洛不是洛陽）。

今日省市走 CHGIS **詳目**端點（搜尋端點沒有這個欄位）：
  https://chgis.hudci.org/tgaz/placename?id=<編號>&fmt=json
  → spatial.present_location[0].text
⚠ 那份 JSON 夾著控制字元，要先濾掉才解析得了。

用法： python3 apply_geo.py          # 先看會改什麼
       python3 apply_geo.py --寫入
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "_data", "祖師.json")
LOC = os.path.join(HERE, "..", "_data", "地名定位.json")
API = "https://chgis.hudci.org/tgaz/placename"

# 簡轉繁：明列對照，不用自動轉換（自動轉換會把「臺」「台」「濛」這類字轉錯）
簡繁 = {"广": "廣", "东": "東", "省": "省", "市": "市", "河": "河", "南": "南",
        "北": "北", "江": "江", "苏": "蘇", "浙": "浙", "安": "安", "徽": "徽",
        "湖": "湖", "山": "山", "西": "西", "陕": "陝", "甘": "甘", "肃": "肅",
        "四": "四", "川": "川", "贵": "貴", "州": "州", "云": "雲", "福": "福",
        "建": "建", "辽": "遼", "宁": "寧", "吉": "吉", "林": "林", "黑": "黑",
        "龙": "龍", "内": "內", "蒙": "蒙", "古": "古", "青": "青", "海": "海",
        "新": "新", "疆": "疆", "西": "西", "藏": "藏", "天": "天", "津": "津",
        "重": "重", "庆": "慶", "上": "上", "县": "縣", "区": "區", "自": "自",
        "治": "治", "回": "回", "族": "族", "维": "維", "吾": "吾", "尔": "爾",
        "壮": "壯", "朝": "朝", "鲜": "鮮", "门": "門", "港": "港", "澳": "澳"}
繁 = lambda s: "".join(簡繁.get(c, c) for c in s)

# CHGIS 的 present_location 是自由書寫，體例不一：有的帶「今」字，有的寫到區、到
# 「驻地東北旧府城」。規格說**今地給到省・市，區級不寫**，所以逐條人工整過再寫進成品。
# key＝CHGIS 回來的原文（照抄，連簡體字一起），value＝成品要顯示的字。
# 原文一律另存在「今地來源.來源全文」裡，查得回去。
今地整理 = {
    "江西南昌市": "江西省南昌市",
    "江西高安縣": "江西省高安縣",
    "湖南长沙市城區": "湖南省長沙市",
    "今浙江杭州市": "浙江省杭州市",
    "今湖北襄樊市汉水南襄城區": "湖北省襄樊市",
    "今河北大名縣驻地東北旧府城": "河北省大名縣",
    "今湖北省钟祥縣": "湖北省鍾祥縣",
}


def 整過的今地(raw):
    """沒整理過的就不寫——寧可空著，也不要把半簡半繁、帶區帶村的字丟上畫面。"""
    if not raw:
        return None, "CHGIS 沒給今地"
    if raw in 今地整理:
        return 今地整理[raw], ""
    return None, "今地「%s」還沒整理成省・市，先留白" % raw


def 含年(起訖, 年):
    """「744 ~ 959」這種範圍字串含不含這一年。看不懂的一律當成不含，寧可留白。"""
    try:
        a, b = [int(x.strip()) for x in 起訖.split("~")]
    except Exception:  # noqa: BLE001
        return False
    return a <= 年 <= b


def 跨幾年(起訖):
    try:
        a, b = [int(x.strip()) for x in 起訖.split("~")]
        return b - a
    except Exception:  # noqa: BLE001
        return 0


def 最遠(命中):
    """一組命中裡最遠的兩點相距幾公里。"""
    import math
    d = 0.0
    for i, a in enumerate(命中):
        for b in 命中[i + 1:]:
            dx = (a["經度"] - b["經度"]) * math.cos(math.radians(a["緯度"])) * 111.0
            dy = (a["緯度"] - b["緯度"]) * 111.0
            d = max(d, math.hypot(dx, dy))
    return d


def 詳目(編號):
    qs = urllib.parse.urlencode({"id": 編號, "fmt": "json"})
    with urllib.request.urlopen(API + "?" + qs, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace")
    raw = "".join(c for c in raw if c >= " " or c in "\n\r\t")   # 夾著控制字元會解析失敗
    d = json.loads(raw)
    pl = ((d.get("spatial") or {}).get("present_location") or [])
    return 繁(pl[0].get("text", "")) if pl else None


def main():
    寫入 = "--寫入" in sys.argv
    data = json.load(open(DATA, encoding="utf-8"))
    loc = json.load(open(LOC, encoding="utf-8"))["結果"]

    # 地點名 → 該查詢的命中
    by地 = {}
    for r in loc:
        for 地 in r["用於地點"]:
            by地.setdefault(地, r)

    改, 跳過, 今地快取 = [], [], {}
    for p in data["祖師"]:
        for idx, s in enumerate(p.get("站", []), 1):
            where = "%s 第%d站" % (p["介面名"], idx)
            if not s.get("地") or s.get("座標"):
                continue                        # 沒地名、或已經有座標的都不動
            改註 = ""
            r = by地.get(s["地"])
            if not r or not r["命中"]:
                跳過.append("%s（%s）：%s" % (where, s["地"], r["狀態"] if r else "沒查過"))
                continue
            命中 = r["命中"]
            點 = {(round(c["經度"], 4), round(c["緯度"], 4)) for c in 命中}
            if len(點) > 1:
                # 先用年代範圍篩：那一年根本不存在的記錄不該拿來定位。
                # （魏州有兩筆：744~959 與 906~922。存獎示寂 889，後者那時還沒出現。）
                合年 = [c for c in 命中 if 含年(c["起訖"], r["查詢年"])] or 命中
                點合 = {(round(c["經度"], 4), round(c["緯度"], 4)) for c in 合年}
                散 = 最遠(合年)
                if len(點合) == 1:
                    命中 = 合年
                elif 散 <= 25:
                    # 同一座城，地名資料庫收了兩筆記錄而已（魏州兩筆相距 13 公里，
                    # 兩筆都在魏州治所貴鄉縣旁邊）。這跟「洛州第一筆是陝西上洛」那種
                    # 差三百公里的指錯地方是兩回事。取年代範圍涵蓋查詢年、起訖最長的那筆，
                    # 另一筆的編號也記下來，日後要查得到。
                    命中 = sorted(合年, key=lambda c: -跨幾年(c["起訖"]))
                    改註 = "（同名 %d 筆，最遠相距 %.0f 公里，視為同一座城）" % (len(合年), 散)
                else:
                    跳過.append("%s（%s）：%d 筆命中最遠相距 %.0f 公里，不是同一個地方，"
                                "不自動採用，留給人判"
                                % (where, s["地"], len(合年), 散))
                    continue
            c = 命中[0]
            今 = 今地快取.get(c["編號"], "未查")
            if 今 == "未查":
                try:
                    今 = 詳目(c["編號"])
                except Exception as e:          # noqa: BLE001
                    今 = None
                    print("  今地查詢失敗 %s：%s" % (c["編號"], e))
                今地快取[c["編號"]] = 今
                time.sleep(0.4)
            s["座標"] = {"經度": c["經度"], "緯度": c["緯度"], "查詢名": r["查詢名"],
                         "CHGIS編號": c["編號"], "CHGIS網址": c["網址"],
                         "年代範圍": c["起訖"]}
            顯示, 為何沒有 = 整過的今地(今)
            if 顯示:
                s["今地"] = 顯示
                s["今地來源"] = {"今地": 顯示, "來源全文": 今, "來源": "CHGIS（復旦）"}
            elif 今:
                跳過.append("%s（%s）：座標有了，但%s" % (where, s["地"], 為何沒有))
            if 改註:
                s["座標"]["同名其他筆"] = [x["編號"] for x in 命中[1:]]
            改.append("%s（%s）→ %s　%s%s"
                      % (where, s["地"], c["名"], 今 or "今地查無", 改註))

    print("── 會填上座標的 %d 站 ──" % len(改))
    for x in 改:
        print("  ✓ " + x)
    print("\n── 留白的 %d 站 ──" % len(跳過))
    for x in 跳過:
        print("  － " + x)

    if 寫入:
        json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("\n已寫入 祖師.json")
    else:
        print("\n（這一輪只是預覽，沒有動檔案。確認無誤再加 --寫入）")


if __name__ == "__main__":
    main()
