#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把需要的原典卷次抓到本機，存成乾淨純文字。

來源＝CBETA API 的 DILA 鏡像（需要 Referer）。
清洗規則照 buddhist-archives MCP 的做法：行號、頁碼、影像連結都不是經文，一律去掉。

用法： python3 fetch_cbeta.py
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

MIRROR = "https://cbdata.dila.edu.tw/stable"
REFERER = "https://cbetaonline.dila.edu.tw/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_data", "原典")

# (經號, 卷次, 說明)
WANTED = [
    ("T2076", 3, "景德傳燈錄卷三 達摩‧慧可‧僧璨‧道信‧弘忍"),
    ("T2076", 5, "景德傳燈錄卷五 惠能及其法嗣"),
    ("T2008", 1, "六祖大師法寶壇經 宗寶本"),
    ("T2007", 1, "壇經 敦煌本"),
    ("T2060", 16, "續高僧傳卷十六 菩提達摩‧僧可"),
    ("T2061", 8, "宋高僧傳卷八 惠能"),
    ("T2092", 1, "洛陽伽藍記卷一 永寧寺"),
    ("T2837", 1, "楞伽師資記 東山法門系譜（敦煌）"),
    ("T2838", 1, "傳法寶紀 北宗系譜（敦煌）"),
    ("T2075", 1, "歷代法寶記 傳衣說"),
    ("X1598", 1, "曹溪大師別傳 惠能別傳"),
    ("B0144", 2, "祖堂集卷二 達摩至惠能"),
    ("T2076", 1, "景德傳燈錄卷一 序與西天祖師"),
    # ── 臨濟宗（2026-10-08 使用者核可的五部新來源）──
    ("T1985", 1, "鎮州臨濟慧照禪師語錄 臨濟義玄本人語錄"),
    ("T2076", 12, "景德傳燈錄卷十二 臨濟義玄及同世"),
    ("X1565", 11, "五燈會元卷十一 臨濟下一世至四世"),
    ("X1565", 12, "五燈會元卷十二 臨濟下五世至七世"),
    ("X1571", 21, "五燈全書卷二十一 臨濟義玄與法嗣"),
    ("X1571", 22, "五燈全書卷二十二 臨濟下二世"),
    ("X1571", 23, "五燈全書卷二十三 臨濟下三世"),
    ("T2077", 1, "續傳燈錄卷一"),
    ("X1578", 14, "指月錄卷十四 臨濟"),
]


def fetch(work, juan):
    qs = urllib.parse.urlencode({"work": work, "juan": juan})
    req = urllib.request.Request(
        "%s/juans?%s" % (MIRROR, qs), headers={"Referer": REFERER}
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def strip_html(html, keep_notes=False):
    """keep_notes=False 回傳純經文；True 回傳把夾註標成〔校註：…〕的版本。

    ⚠️ CBETA 把校勘夾註放在 <small class='inline-note …'> 裡，前面還有一個
    <a class="noteAnchor">。若不剔除，註文會混進經文中間——例如
    「姓盧名慧能。自『舊本誤作鄿字』州來參謁師」，實際經文是「自新州來參謁師」。
    那是校訂者的話，不是原典的字，絕不可以當引文呈現。
    """
    html = re.sub(r"<head.*?</head>", "", html, flags=re.S | re.I)
    # 行號、頁碼、影像連結不是經文
    html = re.sub(r'<span[^>]*class="(?:lb|pb)"[^>]*>.*?</span>', "", html, flags=re.S)
    html = re.sub(r'<a[^>]*class="facsimile"[^>]*>.*?</a>', "", html, flags=re.S)
    # CBETA 把卷末附錄整包放在 <div id='back'>，從那裡切掉最乾淨
    html = re.split(r"<div[^>]*id=['\"]back['\"]", html)[0]
    # 卷末校勘條目與缺字字表：都不是經文，整塊拿掉
    html = re.sub(r"<div[^>]*class=['\"]footnote['\"][^>]*>.*?</div>", "", html, flags=re.S)
    html = re.sub(r"<span[^>]*class=\"gaijiInfo\"[^>]*>.*?</span>", "", html, flags=re.S)
    # 校勘夾註
    html = re.sub(r'<a[^>]*class="noteAnchor[^"]*"[^>]*>.*?</a>', "", html, flags=re.S)
    if keep_notes:
        html = re.sub(r"<small[^>]*inline-note[^>]*>(.*?)</small>",
                      lambda m: "〔校註：" + re.sub(r"<[^>]+>", "", m.group(1)) + "〕",
                      html, flags=re.S)
    else:
        html = re.sub(r"<small[^>]*inline-note[^>]*>.*?</small>", "", html, flags=re.S)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|h\d)>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", html)
    text = (text.replace("&lt;", "<").replace("&gt;", ">")
                .replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"'))
    text = re.sub(r"[A-Z]{1,2}\d+n[0-9A-Za-z]+_p\d+[a-z]\d+", "", text)
    lines = [" ".join(l.split()) for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def split_apparatus(text):
    """切掉卷末的校勘表與版本資訊。

    那一段長得像「爾【大】，邇【明】」「〔名曰…耳〕四十四－【明】」，是版本異文表，
    同樣不是經文。不切掉的話，比對程式會以為那些字也可以拿來當引文。
    回傳 (經文, 卷末附錄)。
    """
    lines = text.split("\n")
    cut = None
    for i, l in enumerate(lines):
        if i < len(lines) * 0.5:
            continue
        if ("【經文資訊】" in l or "【版本記錄】" in l
                or re.search(r"【(大|明|宋|元|甲|CB)】", l)):
            cut = i
            break
    if cut is None:
        return text, ""
    return "\n".join(lines[:cut]), "\n".join(lines[cut:])


def main():
    os.makedirs(OUT, exist_ok=True)
    for work, juan, note in WANTED:
        name = "%s_j%02d.txt" % (work, juan)
        path = os.path.join(OUT, name)
        if os.path.exists(path) and os.path.getsize(path) > 200:
            print("跳過（已存在）%s　%s" % (name, note))
            continue
        try:
            data = fetch(work, juan)
        except Exception as e:  # noqa: BLE001
            print("失敗　%s 卷%s　%s" % (work, juan, e), file=sys.stderr)
            continue
        results = data.get("results") or []
        if not results:
            print("無內容　%s 卷%s" % (work, juan), file=sys.stderr)
            continue
        text, apparatus = split_apparatus(strip_html(results[0]))
        with open(path, "w", encoding="utf-8") as f:
            f.write("# %s　%s 卷%s\n# 來源 CBETA %s\n"
                    "# 純經文：校勘夾註與卷末校勘表皆已剔除（那些是校訂者的話，不是原典）\n"
                    "# 引文只能從這個檔取字\n\n" % (note, work, juan, MIRROR))
            f.write(text)
        # 另存含註本與校勘表，供查核用，不作引文來源
        annotated = strip_html(results[0], keep_notes=True)
        with open(path.replace(".txt", "_含校註.txt"), "w", encoding="utf-8") as f:
            f.write("# %s　%s 卷%s（含校勘夾註，標為〔校註：…〕，另附卷末校勘表）\n"
                    "# 僅供查核，不可當引文來源\n\n" % (note, work, juan))
            f.write(annotated)
        print("已存　%s　經文 %6d 字（剔除校勘 %5d 字）　%s"
              % (name, len(text), len(apparatus), note))
        time.sleep(1.2)


if __name__ == "__main__":
    main()
