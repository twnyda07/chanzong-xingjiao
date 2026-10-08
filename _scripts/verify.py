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


# 「遇到的人」要合世情：本人與父母不算「遇到」。
# 出生本來就會遇到母親，把父母列進去等於把「他出生了」寫成「他遇到了一個人」。
# 姓氏（「萊州狄氏子」的狄氏）更不是人，那是家世。
# （2026-10-08 使用者定的判準）
親屬詞 = {"父", "母", "父母", "嚴父", "慈母", "老母", "先父", "先母", "亡父", "亡母",
          "妻", "兄", "弟", "姊", "妹", "祖父", "祖母"}


def 不算遇到的人(w):
    """回傳擋下來的理由；是正常人物就回 None。"""
    if w in 親屬詞:
        return "父母親屬不算「遇到的人」"
    if re.fullmatch(r".*(嚴父|慈母|老母|父|母)", w):
        return "父母親屬不算「遇到的人」"
    if re.fullmatch(r"[一-鿿]氏", w):
        return "「%s」是姓氏不是人，那是家世" % w
    return None



# 「遇到的人」只能列**從這一站的引文看得出有參與**的人（2026-10-09 使用者指出：
# 臨濟義玄第3站列了首座，但那段引文只有師與黃蘗，首座是第1站那一幕的人）。
# 名字直接出現、或引文裡有簡稱即可；只靠稱謂（帝／祖／光／秀／尼）認定的，
# 每一條都要在下表登記理由——沒登記就不給過，不可以靠記憶或印象放行。
稱謂認定 = {
    ("達摩", "梁武帝"): ("帝", "引文作「帝問曰。朕即位已來」"),
    ("達摩", "神光"): ("光", "引文作「光堅立不動」"),
    ("達摩", "慧可"): ("光", "引文作「光曰。我心未寧」——此時尚名神光，同一人"),
    ("道信", "唐太宗"): ("帝", "引文作「帝彌加歎慕」"),
    ("道信", "弘忍"): ("答曰", "引文是問姓的對答，答者即後來的弘忍"),
    ("僧璨", "道信"): ("願和尚", "引文是求解脫法門的對答，問者即道信"),
    ("弘忍", "慧能"): ("曰", "引文是弘忍與來參者的對答，來者即慧能"),
    ("惠能", "五祖"): ("祖", "引文作「祖言」「祖以杖擊碓三下」"),
    ("惠能", "神秀"): ("秀", "引文作「秀書偈了」"),
    ("惠能", "無盡藏"): ("尼", "引文作「尼乃執卷問字」"),
    ("南院慧顒", "風穴延沼"): ("師", "這一站在南院慧顒名下，引文的「師」即來參的風穴延沼"),
    ("首山省念", "風穴延沼"): ("穴", "引文作「穴乃垂涕告之曰」"),
    ("風穴延沼", "南院慧顒"): ("院", "引文作「院曰」"),
    ("風穴延沼", "華嚴和尚"): ("嚴", "引文作「嚴問」"),
    ("興化存獎", "臨濟義玄"): ("化", "這一站在興化存獎名下，引文的對話者即其師臨濟義玄"),
}


def 引文看得出來(祖, 名, 文):
    """回傳認定方式；看不出來回 None。"""
    b, t = bare(名), bare(文)
    if b in t:
        return "名字直接出現"
    for k in range(len(b), 1, -1):
        if b[:k] in t:
            return "簡稱「%s」" % b[:k]
        if b[-k:] in t:
            return "簡稱「%s」" % b[-k:]
    k = 稱謂認定.get((祖, 名))
    if k and bare(k[0]) in t:
        return "稱謂「%s」：%s" % k
    return None

def 別名(p):
    """這一位在各書裡的寫法，加上四字法號拆出來的兩截。

    景德作「慧能」、壇經作「惠能」、續高僧傳作「僧可」；臨濟義玄也會被寫成「臨濟」或「義玄」。
    只比對介面名會讓換個字的自我指涉溜過去。
    """
    s = {p["介面名"]}
    for v in p.get("各書異寫") or []:
        s.add(re.sub(r"（.*?）", "", v).strip())
    n = p["介面名"]
    if len(n) == 4:
        s.update({n[:2], n[2:]})
    return {a for a in s if a}


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
        自己 = 別名(p)
        for idx, st in enumerate(p.get("站", []), 1):
            where = "%s 第%d站（%s）" % (p["介面名"], idx, st.get("地", "?"))

            # 「遇到的人」不可以是他自己（2026-10-08 使用者抓到：惠能第10站遇到惠能）。
            # **要完全同名才算**——「惠能嚴父」是他父親，是另一個人，不可以一起擋掉。
            # 事實欄位不可以夾括號註解。「居士（後名僧璨）」那個括號是我加的話，
            # 不是原典的字——第零條說畫面上只能有原典原文與事實標註，沒有轉述的位置。
            for 欄, 值 in [("地", st.get("地")), ("年", st.get("年"))] + \
                          [("人", w) for w in (st.get("人") or [])]:
                if 值 and re.search(r"[（(][^）)]*[）)]", 值):
                    errors.append("%s：%s 欄「%s」夾了括號註解，那是轉述不是原典的字"
                                  % (where, 欄, 值))

            for who in st.get("人") or []:
                if who in 自己:
                    errors.append("%s：遇到的人寫了「%s」，那是他自己" % (where, who))
                    continue
                # 父母、姓氏都不算「遇到的人」。先擋這兩種，才輪得到下面的同名警告，
                # 否則「惠能嚴父」會被當成可疑的同名而只出警告。
                why = 不算遇到的人(who)
                if why:
                    errors.append("%s：遇到的人寫了「%s」——%s" % (where, who, why))
                elif not 引文看得出來(p["介面名"], who, st["原文"]):
                    errors.append("%s：遇到的人寫了「%s」，但這一站的引文看不出他有參與"
                                  "——名字沒出現、也沒有登記過的稱謂" % (where, who))
                elif any(who.startswith(a) and who != a for a in 自己):
                    warns.append("%s：遇到的人「%s」以他自己的名號開頭，確認是別人才留"
                                 % (where, who))
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
                    # 原典常是第一次寫全名、之後只寫簡稱（「依棲黃蘗山中」→「却回黃蘗」）。
                    # 這一句只有簡稱，但**同一卷別處有全名**，就認——那不是我推的，
                    # 是同一本書自己寫過的字。全卷都找不到全名才是編出來的，要擋。
                    if not (bare(place) in cache[key] and
                            any(_subseq(bare(place)[:k], bare(ev))
                                for k in range(len(bare(place)), 1, -1))):
                        errors.append("%s：地點「%s」在它自己的依據裡拼不出來，"
                                      "全卷也沒有全名" % (where, place))
                    else:
                        warns.append("%s：地點「%s」這一句只寫簡稱，依同卷別處的全名認定"
                                     % (where, place))

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
    print("進度：%d／%d 位祖師已建站" % (done, len(data["祖師"])))


if __name__ == "__main__":
    main()
