"""
日本萬豪 (Marriott Bonvoy) 全 109 家飯店整月房價總覽與最多五館每日比較系統
============================================================================
功能：
1. 讀取 marriott_japan_cache.json（若不存在則自動呼叫 fetch_marriott_japan.py 抓取）
2. 產出完整的 Markdown 報告：日本萬豪全飯店_整月房價與五館比較報告.md
3. 產出互動式 HTML 網頁：日本萬豪全飯店_整月房價與五館比較.html
   - 支援任意月份切換 (2026-10 ~ 2027-09，預設 2027-02)
   - 支援從全 109 家日本萬豪飯店中自由勾選最多 5 家進行「逐日現金價 & 點數並排比較」
   - 內建多館每日價格走勢折線圖、當日最低價自動皇冠標記、地區篩選與一鍵匯出自訂 Markdown 報告
"""

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import statistics
import sys
import webbrowser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WEEKDAY_ZH = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

# 日本主要國定假日 (2026-10 ~ 2027-09)
JP_HOLIDAYS: dict[str, str] = {
    "2026-10-12": "🇯🇵 運動之日",
    "2026-11-03": "🇯🇵 文化之日",
    "2026-11-23": "🇯🇵 勤勞感謝之日",
    "2027-01-01": "🇯🇵 元旦",
    "2027-01-11": "🇯🇵 成人之日",
    "2027-02-11": "🇯🇵 建國紀念日",
    "2027-02-14": "💝 情人節",
    "2027-02-23": "🇯🇵 天皇誕生日",
    "2027-03-21": "🇯🇵 春分之日",
    "2027-03-22": "🇯🇵 補假",
    "2027-04-29": "🇯🇵 昭和之日",
    "2027-05-03": "🇯🇵 憲法紀念日",
    "2027-05-04": "🇯🇵 綠之日",
    "2027-05-05": "🇯🇵 兒童之日",
    "2027-07-19": "🇯🇵 海之日",
    "2027-08-11": "🇯🇵 山之日",
    "2027-09-20": "🇯🇵 敬老之日",
    "2027-09-23": "🇯🇵 秋分之日",
}

# 常見飯店中文譯名補充與地區分類輔助
HOTEL_ZH_MAP: dict[str, str] = {
    "OSAKB": "神戶灣喜來登大飯店",
    "UKBXF": "神戶三宮福朋快選喜來登酒店",
    "OSAYS": "大阪喜來登都酒店",
    "OSACO": "大阪本町萬怡酒店",
    "OSACY": "新大阪站萬怡酒店",
    "OSAMC": "大阪萬豪都酒店",
    "OSAWI": "大阪威斯汀酒店",
    "OSARZ": "大阪麗思卡爾頓酒店",
    "OSAXR": "大阪瑞吉酒店",
    "OSAOW": "大阪 W 酒店",
    "OSAAL": "大阪堂島雅樂軒酒店",
    "OSAOX": "大阪本町 Moxy 酒店",
    "OSAOO": "大阪新梅田 Moxy 酒店",
    "OSAFN": "大阪難波萬楓酒店",
    "OSAAK": "大阪傲途格精選酒店 (Osaka Station Hotel)",
    "OSAUU": "大阪梅田福朋快選喜來登酒店",
    "OSAHU": "大阪心齋橋福朋快選喜來登酒店",
    "OSAKU": "大阪北濱福朋快選喜來登酒店",
    "OSASU": "新大阪福朋快選喜來登酒店",
    "UKYWI": "京都威斯汀都酒店",
    "UKYRZ": "京都麗思卡爾頓酒店",
    "OSALC": "京都三井豪華精選酒店 (HOTEL THE MITSUI)",
    "UKYLC": "京都翠嵐豪華精選酒店",
    "UKYAK": "京都寶池皇家王子傲途格精選酒店",
    "UKYOX": "京都二條 Moxy 酒店",
    "OSAKT": "京都日和 Chapter 臻品之選酒店",
    "OSAYU": "京都烏丸御池福朋快選喜來登酒店",
    "OSAJW": "奈良 JW 萬豪酒店",
    "OSANL": "奈良紫翠豪華精選酒店",
    "OSALB": "琵琶湖萬豪酒店",
    "OSANA": "南紀白濱萬豪酒店",
    "TYOAR": "東京銀座 AC 酒店",
    "TYOAL": "東京銀座雅樂軒酒店",
    "TYOCY": "東京銀座萬怡酒店",
    "TYOGZ": "東京站萬怡酒店",
    "TYOMC": "東京萬豪酒店",
    "TYOWI": "東京威斯汀酒店",
    "TYORZ": "東京麗思卡爾頓酒店",
    "TYOLC": "東京紀尾井町王子畫廊豪華精選酒店",
    "TYOAM": "東京竹芝 Mesm 傲途格精選酒店",
    "TYOAK": "東京高輪皇家王子大飯店櫻花塔",
    "TYOEB": "東京銀座艾迪遜酒店 (EDITION)",
    "TYOET": "東京虎之門艾迪遜酒店 (EDITION)",
    "TYOBT": "東京寶格麗酒店 (Bulgari)",
    "TYOOX": "東京錦糸町 Moxy 酒店",
    "TYOMY": "東京喜來登都酒店",
    "TYOSI": "東京灣喜來登大飯店",
    "TYOYS": "橫濱灣喜來登大飯店",
    "TYOWY": "橫濱威斯汀酒店",
    "TYOYU": "橫濱福朋快選喜來登酒店",
    "TYONZ": "日光麗思卡爾頓酒店",
    "CTSCY": "札幌萬怡酒店",
    "CTSFI": "札幌萬楓酒店",
    "CTSWI": "留壽都威斯汀度假酒店",
    "CTSRZ": "二世谷東山麗思卡爾頓隱世酒店",
    "HKDXF": "函館站福朋快選喜來登酒店",
    "SDJWI": "仙台威斯汀酒店",
    "NGODT": "名古屋萬豪酒店",
    "NGOCY": "名古屋萬怡酒店",
    "NGOAK": "名古屋 TIAD 傲途格精選酒店",
    "NGOFP": "名古屋中部國際機場福朋喜來登酒店",
    "NGOXF": "名古屋站福朋快選喜來登酒店",
    "FUKRZ": "福岡麗思卡爾頓酒店",
    "FUKHS": "福岡博多福朋快選喜來登酒店",
    "HIJSI": "廣島喜來登大飯店",
    "NGSMC": "長崎萬豪酒店",
    "KOJSI": "鹿兒島喜來登酒店",
    "OKASI": "沖繩聖瑪莉娜喜來登度假酒店",
    "OKARN": "沖繩萬麗度假酒店",
    "OKARZ": "沖繩麗思卡爾頓酒店",
    "OKALC": "沖繩宮古島伊良部翠豪華精選酒店",
    # 🇹🇼 台灣萬豪集團全 26 家飯店中文名稱
    "TPETM": "台北萬豪酒店",
    "TPEWH": "台北 W 飯店",
    "TPEDM": "台北寒舍艾美酒店",
    "TPEST": "台北喜來登大飯店",
    "TPESH": "台北士林萬麗酒店",
    "TPECY": "台北六福萬怡酒店",
    "TPECD": "台北國泰萬怡酒店",
    "TPEDS": "台北賦樂旅居 (Hotel Proverbs Taipei)",
    "TPESC": "台北慕軒飯店 (Tribute Portfolio)",
    "TPEAL": "台北中山雅樂軒酒店",
    "TPEBE": "台北北投雅樂軒酒店",
    "TPEFT": "新北八里福朋喜來登酒店",
    "TPELF": "林口亞昕福朋喜來登酒店",
    "TPESY": "桃園喜來登酒店",
    "TPETW": "桃園大溪笠復威斯汀度假酒店",
    "TPEHS": "新竹豐邑喜來登大飯店",
    "RMQMD": "台中李方艾美酒店",
    "RMQFI": "台中萬楓酒店",
    "RMQOX": "台中豐邑 Moxy 酒店",
    "TNNAL": "台南安平雅樂軒酒店",
    "KHHMC": "高雄萬豪酒店",
    "TPEYR": "宜蘭力麗威斯汀度假酒店",
    "TPEPJ": "宜蘭礁溪福朋喜來登酒店",
    "HUNMD": "花蓮潔西艾美渡假酒店",
    "TTTSI": "台東桂田喜來登酒店",
    "MZGFP": "澎湖福朋喜來登酒店",
}

TW_CODES = {
    "TPETM", "TPEWH", "TPEDM", "TPEST", "TPESH", "TPECY", "TPECD", "TPEDS",
    "TPESC", "TPEAL", "TPEBE", "TPEFT", "TPELF", "TPESY", "TPETW", "TPEHS",
    "RMQMD", "RMQFI", "RMQOX", "TNNAL", "KHHMC", "TPEYR", "TPEPJ", "HUNMD",
    "TTTSI", "MZGFP",
}


def is_taiwan_hotel(code: str, hotel: dict | None = None) -> bool:
    if hotel and hotel.get("country") == "TW":
        return True
    return code in TW_CODES


def get_currency_symbol(code: str, hotel: dict | None = None) -> str:
    if is_taiwan_hotel(code, hotel) or (hotel and hotel.get("currency") == "TWD"):
        return "NT$"
    return "¥"


def detect_region(code: str, name: str, country: str = "") -> str:
    """根據飯店代碼與英文名稱歸類日本與台灣地區。"""
    n_low = name.lower()
    if country == "TW" or code in TW_CODES:
        if code in {"TPEYR", "TPEPJ", "HUNMD", "TTTSI", "MZGFP"} or any(
            k in n_low for k in ["yilan", "hualien", "taitung", "penghu"]
        ):
            return "🇹🇼 台灣 (宜蘭/花東/澎湖)"
        if code in {"RMQMD", "RMQFI", "RMQOX", "TNNAL", "KHHMC"} or any(
            k in n_low for k in ["taichung", "tainan", "kaohsiung"]
        ):
            return "🇹🇼 台灣 (台中/台南/高雄)"
        return "🇹🇼 台灣 (雙北/桃園/新竹)"
    if any(k in n_low for k in ["okinawa", "miyako"]):
        return "🇯🇵 沖繩 (Okinawa)"
    if any(
        k in n_low
        for k in ["hokkaido", "sapporo", "niseko", "rusutsu", "hakodate", "sendai", "morioka"]
    ) or code.startswith(("CTS", "HKD", "SDJ", "HNA")):
        return "🇯🇵 北海道・東北"
    if any(
        k in n_low
        for k in [
            "tokyo",
            "yokohama",
            "nikko",
            "tochigi",
            "utsunomiya",
            "motegi",
            "karuizawa",
        ]
    ) or code.startswith(("TYO", "IBR")):
        return "🇯🇵 關東 (東京/橫濱/關東)"
    if any(
        k in n_low
        for k in [
            "osaka",
            "kyoto",
            "kobe",
            "nara",
            "hyogo",
            "wakayama",
            "shirahama",
            "biwa",
        ]
    ) or code.startswith(("OSA", "UKB", "UKY")):
        return "🇯🇵 關西 (大阪/京都/神戶/奈良)"
    if any(
        k in n_low
        for k in [
            "nagoya",
            "gifu",
            "mie",
            "fukui",
            "kanazawa",
            "hakuba",
            "fuji",
            "izu",
        ]
    ) or code.startswith(("NGO", "KMQ", "MMJ", "FSZ")):
        return "🇯🇵 中部・北陸・東海"
    return "🇯🇵 中國・四國・九州"


def translate_fallback_name(name: str, code: str) -> str:
    """若未在字典中，提供易讀的中文輔助名稱。"""
    if code in HOTEL_ZH_MAP:
        return HOTEL_ZH_MAP[code]
    if name.startswith("Fairfield by Marriott "):
        place = name.replace("Fairfield by Marriott ", "").replace(" Japan", "")
        return f"萬楓酒店 ({place})"
    if "Four Points Express by Sheraton" in name:
        place = name.replace("Four Points Express by Sheraton ", "")
        return f"福朋快選喜來登 ({place})"
    return name


def build_booking_url(code: str, checkin_str: str) -> str:
    """根據飯店代碼與入住日 (YYYY-MM-DD) 組合萬豪官網預訂連結。"""
    dt = date.fromisoformat(checkin_str)
    next_dt = date.fromordinal(dt.toordinal() + 1)
    from_str = dt.strftime("%m/%d/%Y")
    to_str = next_dt.strftime("%m/%d/%Y")
    return (
        "https://www.marriott.com/reservation/availabilitySearch.mi?"
        f"isSearch=false&propertyCode={code}&isRateCalendar=false&costView=AVG"
        "&numberOfRooms=1&numberOfAdults=2&numberOfChildren=0"
        f"&useRewardsPoints=true&clusterCode=none&fromDate={from_str}&toDate={to_str}"
    )


def get_dates_in_range(all_data: dict, start_date: str, end_date: str) -> list[str]:
    """取得在指定開始日期與結束日期 (YYYY-MM-DD, 含首尾) 之間的所有日期清單。"""
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    dates_set: set[str] = set()
    for h in all_data.values():
        for d in h.get("days", {}).keys():
            if start_date <= d <= end_date:
                dates_set.add(d)
    return sorted(dates_set)


def get_all_available_dates(all_data: dict) -> list[str]:
    """取得快取資料中涵蓋的所有日期 (YYYY-MM-DD)。"""
    dates_set: set[str] = set()
    for h in all_data.values():
        for d in h.get("days", {}).keys():
            if len(d) == 10:
                dates_set.add(d)
    return sorted(dates_set)


def get_available_months(all_data: dict) -> list[str]:
    """取得快取資料中涵蓋的所有月份 (YYYY-MM)。"""
    months: set[str] = set()
    for h in all_data.values():
        for d in h.get("days", {}).keys():
            if len(d) >= 7:
                months.add(d[:7])
    return sorted(months)


def compute_hotel_range_summary(hotel: dict, range_dates: list[str]) -> dict:
    """計算單一飯店在指定日期區間的統計摘要（含區間總價）。"""
    days_map = hotel.get("days", {})
    cash_vals = []
    pts_vals = []
    for d in range_dates:
        pair = days_map.get(d)
        if pair:
            c, p = pair[0], pair[1]
            if c and c > 0:
                cash_vals.append(c)
            if p and p > 0:
                pts_vals.append(p)

    return {
        "min_cash": min(cash_vals) if cash_vals else None,
        "max_cash": max(cash_vals) if cash_vals else None,
        "avg_cash": round(statistics.mean(cash_vals)) if cash_vals else None,
        "total_cash": sum(cash_vals) if cash_vals else None,
        "avail_days": len(cash_vals),
        "min_pts": min(pts_vals) if pts_vals else None,
        "total_pts": sum(pts_vals) if pts_vals else None,
        "pts_days": len(pts_vals),
    }


def generate_markdown_report(
    all_data: dict,
    selected_codes: list[str],
    start_date: str,
    end_date: str,
    output_path: Path,
) -> None:
    """產生包含『所選最多五家飯店每日比較』與『全日本萬豪各旅館區間價格總覽』的 Markdown 報告。"""
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    range_dates = get_dates_in_range(all_data, start_date, end_date)
    range_label = f"{start_date} ～ {end_date}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    selected_codes = [c for c in selected_codes if c in all_data][:5]

    selected_names_str = ", ".join(
        f"**{translate_fallback_name(all_data[c]['name'], c)} (`{c}`)**"
        for c in selected_codes
    )

    lines = [
        f"# 🇯🇵 日本萬豪 (Marriott Bonvoy) 全旅館價格與最多五館每日比較報告 ({range_label})",
        "",
        "- **資料來源**：[USTATZ 日本萬豪酒店查詢](https://www.ustatz.com/hotelGroups/Japan)",
        f"- **查詢日期區間**：`{start_date}` 至 `{end_date}`（共 **{len(range_dates)}** 晚）",
        f"- **收錄飯店總數**：全日本共 **{len(all_data)}** 家萬豪集團飯店",
        f"- **目前每日比較飯店（最多 5 家）**：{selected_names_str}",
        f"- **報表生成時間**：{now_str}",
        "",
        "> 💡 **提示**：你可以打開同目錄下的互動式網頁 `日本萬豪全飯店_整月房價與五館比較.html`，在瀏覽器中自由選擇任意**開始日期**與**結束日期**、從 109 家飯店自由勾選最多 5 家飯店進行每日價格曲線與表格對比，並一鍵匯出新的 Markdown 報告！",
        "",
        "---",
        "",
        f"## 🏆 第一部分：精選 {len(selected_codes)} 家飯店區間統計對比 ({range_label})",
        "",
        "| 飯店代碼 | 飯店名稱 | 地區 | 區間最低價 | 區間平均價 | 區間最高價 | 區間總房價 (有房日合計) | 可訂天數 | 最低點數兌換 |",
        "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for code in selected_codes:
        h = all_data[code]
        sym = get_currency_symbol(code, h)
        zh_name = translate_fallback_name(h["name"], code)
        region = detect_region(code, h["name"], h.get("country", ""))
        s = compute_hotel_range_summary(h, range_dates)
        min_c = f"**{sym}{s['min_cash']:,}**" if s["min_cash"] else "無空房"
        avg_c = f"{sym}{s['avg_cash']:,}" if s["avg_cash"] else "-"
        max_c = f"{sym}{s['max_cash']:,}" if s["max_cash"] else "-"
        tot_c = f"{sym}{s['total_cash']:,}" if s["total_cash"] else "-"
        min_p = f"{s['min_pts']:,} pts ({s['pts_days']}天)" if s["min_pts"] else "未開放"
        lines.append(
            f"| `{code}` | **{zh_name}**<br><small>{h['name']}</small> | {region} | {min_c} | {avg_c} | {max_c} | {tot_c} | {s['avail_days']}/{len(range_dates)}晚 | {min_p} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            f"## 📅 第二部分：所選 {len(selected_codes)} 家飯店每日房價並排比較表 ({range_label})",
            "",
        ]
    )

    header_cols = ["日期", "星期", "節日/備註"]
    for code in selected_codes:
        zh_name = translate_fallback_name(all_data[code]["name"], code)
        header_cols.append(f"{zh_name}<br>(`{code}`)")
    header_cols.append("👑 當日最低價推薦")

    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join([":---:"] * len(header_cols)) + " |")

    for d_str in range_dates:
        dt = date.fromisoformat(d_str)
        w_idx = dt.weekday()
        w_zh = WEEKDAY_ZH[w_idx]
        holiday = JP_HOLIDAYS.get(d_str, "🔥 週六" if w_idx == 5 else "-")

        day_prices: list[tuple[int, str]] = []
        cell_strs: list[str] = []

        for code in selected_codes:
            pair = all_data[code].get("days", {}).get(d_str, [-1, -1])
            c_val, _ = pair[0], pair[1]
            if c_val and c_val > 0:
                day_prices.append((c_val, code))

        min_day_price = min((p[0] for p in day_prices), default=None)

        for code in selected_codes:
            h = all_data[code]
            sym = get_currency_symbol(code, h)
            pair = h.get("days", {}).get(d_str, [-1, -1])
            c_val, p_val = pair[0], pair[1]
            if c_val and c_val > 0:
                is_cheapest = min_day_price is not None and c_val == min_day_price
                price_txt = f"🟢 **{sym}{c_val:,}**" if is_cheapest else f"{sym}{c_val:,}"
                if p_val and p_val > 0:
                    price_txt += f"<br><small>({p_val // 1000}k pts)</small>"
                cell_strs.append(price_txt)
            else:
                cell_strs.append("無房")

        if min_day_price is not None:
            winners = [
                translate_fallback_name(all_data[c]["name"], c)
                for val, c in day_prices
                if val == min_day_price
            ]
            win_sym = get_currency_symbol(day_prices[0][1], all_data[day_prices[0][1]])
            best_str = f"**{win_sym}{min_day_price:,}** ({', '.join(winners)})"
        else:
            best_str = "全滿"

        row_cols = [f"`{d_str}`", w_zh, holiday] + cell_strs + [best_str]
        lines.append("| " + " | ".join(row_cols) + " |")

    lines.extend(
        [
            "",
            "---",
            "",
            f"## 🗾 第三部分：日本＆台灣萬豪全 {len(all_data)} 家飯店區間房價總覽 ({range_label})",
            "",
            "| 地區 | 代碼 | 飯店名稱 (中/英) | 區間最低價 | 區間均價 | 區間最高價 | 可訂天數 | 最低點數 (Points) |",
            "| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    overview_rows = []
    for code, h in all_data.items():
        zh_name = translate_fallback_name(h["name"], code)
        region = detect_region(code, h["name"], h.get("country", ""))
        sym = get_currency_symbol(code, h)
        s = compute_hotel_range_summary(h, range_dates)
        overview_rows.append((region, s["min_cash"] or 99999999, code, zh_name, h["name"], sym, s))

    overview_rows.sort(key=lambda x: (x[0], x[1], x[2]))

    for region, _, code, zh_name, en_name, sym, s in overview_rows:
        min_c = f"**{sym}{s['min_cash']:,}**" if s["min_cash"] else "無空房"
        avg_c = f"{sym}{s['avg_cash']:,}" if s["avg_cash"] else "-"
        max_c = f"{sym}{s['max_cash']:,}" if s["max_cash"] else "-"
        min_p = f"{s['min_pts']:,} pts" if s["min_pts"] else "-"
        lines.append(
            f"| {region} | `{code}` | **{zh_name}**<br><small>{en_name}</small> | {min_c} | {avg_c} | {max_c} | {s['avail_days']}晚 | {min_p} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_html_comparator(
    all_data: dict,
    default_selected: list[str],
    default_start_date: str,
    default_end_date: str,
    output_path: Path,
) -> None:
    """產生內嵌日本 109 家 + 台灣 26 家（共 135 家）萬豪飯店完整資料的互動式比較 HTML 網頁。"""
    compact_hotels = []
    for code, h in all_data.items():
        zh_name = translate_fallback_name(h["name"], code)
        country = "TW" if is_taiwan_hotel(code, h) else "JP"
        region = detect_region(code, h["name"], country)
        sym = get_currency_symbol(code, h)
        compact_hotels.append(
            {
                "code": code,
                "name": h["name"],
                "zh": zh_name,
                "country": country,
                "sym": sym,
                "region": region,
                "days": h.get("days", {}),
            }
        )

    compact_hotels.sort(key=lambda x: (x["region"], x["zh"]))
    all_dates = get_all_available_dates(all_data)
    months_list = get_available_months(all_data)
    min_avail_date = all_dates[0] if all_dates else "2026-10-22"
    max_avail_date = all_dates[-1] if all_dates else "2027-10-15"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    embedded_json = json.dumps(
        {
            "updatedAt": now_str,
            "defaultStartDate": default_start_date,
            "defaultEndDate": default_end_date,
            "minDate": min_avail_date,
            "maxDate": max_avail_date,
            "defaultSelected": default_selected[:5],
            "months": months_list,
            "holidays": JP_HOLIDAYS,
            "hotels": compact_hotels,
        },
        ensure_ascii=False,
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇯🇵 日本萬豪全飯店整月房價總覽 ＆ 最多五館每日比較儀表板</title>
    <style>
        :root {{
            --bg: #0b1120;
            --panel: #151f32;
            --panel-alt: #1e293b;
            --text: #f8fafc;
            --muted: #94a3b8;
            --border: #26354d;
            --accent: #38bdf8;
            --green: #10b981;
            --amber: #f59e0b;
            --rose: #f43f5e;
            --purple: #a855f7;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Segoe UI", "Microsoft JhengHei", system-ui, sans-serif;
            background: radial-gradient(circle at top right, #1e293b 0%, var(--bg) 55%);
            color: var(--text);
            padding: 1.75rem 1.25rem 4rem;
            line-height: 1.5;
        }}
        .container {{ max-width: 1340px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1rem;
            padding-bottom: 1.25rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .brand-pill {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.14);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.35);
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            margin-bottom: 0.45rem;
        }}
        h1 {{ font-size: 1.75rem; font-weight: 800; }}
        .sub {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }}
        .sub a {{ color: var(--accent); text-decoration: none; }}

        /* 控制列 */
        .toolbar {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.15rem 1.4rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.22);
        }}
        .control-group {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }}
        label.ctrl-label {{ font-size: 0.88rem; color: var(--muted); font-weight: 600; }}
        select, input[type="text"], input[type="date"] {{
            background: #0f172a;
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.5rem 0.85rem;
            border-radius: 10px;
            font-size: 0.92rem;
            outline: none;
            color-scheme: dark;
        }}
        select:focus, input[type="text"]:focus, input[type="date"]:focus {{ border-color: var(--accent); }}
        .nights-badge {{
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            font-size: 0.84rem;
            font-weight: 700;
        }}
        .preset-btn, .action-btn {{
            background: #0f172a;
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.45rem 0.85rem;
            border-radius: 999px;
            font-size: 0.83rem;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .preset-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
        .action-btn.primary {{
            background: linear-gradient(135deg, #0ea5e9, #6366f1);
            border: none;
            color: #fff;
            font-weight: 700;
            padding: 0.55rem 1.1rem;
        }}
        .action-btn.primary:hover {{ opacity: 0.92; transform: translateY(-1px); }}

        /* 五館選擇槽 */
        .slots-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .slot-card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            position: relative;
            box-shadow: 0 6px 18px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 136px;
        }}
        .slot-card.empty {{
            border-style: dashed;
            align-items: center;
            justify-content: center;
            color: var(--muted);
            cursor: pointer;
            text-align: center;
        }}
        .slot-card.empty:hover {{ border-color: var(--accent); color: var(--accent); }}
        .slot-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }}
        .slot-code {{
            font-family: Consolas, monospace;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
        }}
        .remove-btn {{
            background: rgba(244, 63, 94, 0.15);
            color: #fda4af;
            border: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 0.85rem;
            line-height: 1;
        }}
        .remove-btn:hover {{ background: var(--rose); color: #fff; }}
        .slot-title {{ font-weight: 700; font-size: 1rem; margin-top: 0.35rem; }}
        .slot-en {{ font-size: 0.76rem; color: var(--muted); margin-bottom: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .slot-stats {{
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
            border-top: 1px solid var(--border);
            padding-top: 0.55rem;
            color: var(--muted);
        }}
        .slot-stats strong {{ color: var(--text); font-size: 0.95rem; }}

        /* 區塊卡片 */
        .panel-box {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.4rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.22);
        }}
        .panel-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.8rem;
            margin-bottom: 1.1rem;
        }}
        .panel-head h2 {{ font-size: 1.2rem; font-weight: 700; }}

        /* 折線圖 SVG 容器 */
        .chart-wrap {{
            width: 100%;
            overflow-x: auto;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
        }}
        .chart-legend {{
            display: flex;
            gap: 1.25rem;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
            font-size: 0.85rem;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 0.45rem; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}

        /* 表格通用 */
        .table-scroll {{ overflow-x: auto; max-height: 680px; overflow-y: auto; border-radius: 12px; border: 1px solid var(--border); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 0.75rem 0.95rem; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{
            background: #0f172a;
            color: var(--muted);
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 5;
        }}
        tr:hover td {{ background: rgba(30, 41, 59, 0.6); }}
        .mono {{ font-family: Consolas, monospace; }}
        .price-val {{ font-weight: 700; font-size: 0.98rem; font-variant-numeric: tabular-nums; }}
        .cheapest-cell {{
            background: rgba(16, 185, 129, 0.13) !important;
            border-left: 3px solid var(--green);
        }}
        .crown-badge {{
            display: inline-block;
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.1rem 0.45rem;
            border-radius: 999px;
            margin-left: 0.35rem;
        }}
        .pts-sub {{ display: block; font-size: 0.75rem; color: var(--amber); }}
        .price-link {{ color: inherit; text-decoration: none; display: block; }}
        .price-link:hover {{ text-decoration: underline; color: var(--accent); }}
        .sat-row {{ background: rgba(244, 63, 94, 0.04); }}
        .sat-badge {{ color: #fda4af; font-weight: 700; }}

        .pick-btn {{
            background: #0f172a;
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .pick-btn.selected {{
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border-color: var(--green);
        }}
        .pick-btn:hover {{ border-color: var(--accent); }}
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            border: 1px solid var(--accent);
            color: var(--text);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            display: none;
            z-index: 999;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <span class="brand-pill">Marriott Bonvoy · 日本 109 家 ＋ 台灣 26 家（共 135 家）動態比較系統</span>
                <h1>🇯🇵 日本 ＆ 🇹🇼 台灣萬豪各旅館房價總覽與最多五館每日比較</h1>
                <div class="sub">
                    資料來源：<a href="https://www.ustatz.com/hotelGroups/Japan" target="_blank">USTATZ 日本</a> ＆ <a href="https://www.ustatz.com/hotelGroups/Taiwan" target="_blank">台灣酒店查詢</a> ｜
                    可自由選擇開始與結束日期、從下方 135 家日台萬豪飯店勾選最多 5 家進行逐日房價與點數比較
                </div>
            </div>
            <div class="sub" style="text-align:right;">
                資料快取時間：{now_str}<br>
                點擊表格內任一價格可直接前往萬豪官網預訂
            </div>
        </header>

        <!-- 頂部控制列 -->
        <section class="toolbar">
            <div class="control-group">
                <label class="ctrl-label" for="startDate">📅 開始日期：</label>
                <input type="date" id="startDate" onchange="onDateRangeChange('start')">
                <label class="ctrl-label" for="endDate">結束日期：</label>
                <input type="date" id="endDate" onchange="onDateRangeChange('end')">
                <span class="nights-badge" id="nightsBadge">共 28 晚</span>

                <button class="preset-btn" onclick="setQuickDays(3)" title="從開始日期往後算 3 晚">3晚</button>
                <button class="preset-btn" onclick="setQuickDays(5)" title="從開始日期往後算 5 晚">5晚</button>
                <button class="preset-btn" onclick="setQuickDays(7)" title="從開始日期往後算 7 晚">7晚</button>
                <select id="quickMonthSelect" onchange="onQuickMonthSelect(this.value)" title="快速帶入整月日期區間">
                    <option value="">⚡ 快速帶入整月...</option>
                </select>
            </div>
            <div class="control-group" style="width:100%; padding-top:0.65rem; border-top:1px solid var(--border); justify-content:space-between;">
                <div class="control-group">
                    <span class="ctrl-label">🏨 快速套用五館：</span>
                    <button class="preset-btn" onclick="applyPreset(['TPETM','TPEWH','TPEST','TPECY','TPETW'])">🇹🇼 台北/北台灣 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['KHHMC','RMQMD','TNNAL','TPEYR','HUNMD'])">🇹🇼 中南部/宜花渡假 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['OSAKB','OSACO','OSAYS','OSAUU','OSAAL'])">🏯 關西神戶/大阪 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['OSALC','UKYRZ','UKYLC','UKYWI','UKYOX'])">⛩️ 京都精選 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['TYOCY','TYOAL','TYOMC','TYOWI','TYOSI'])">🗼 東京熱門 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['CTSCY','CTSFI','CTSWI','HKDXF','SDJWI'])">❄️ 北海道/東北 5 館</button>
                    <button class="preset-btn" onclick="applyPreset(['OKASI','OKARN','OKARZ','OKALC','FUKRZ'])">🌺 沖繩/九州 5 館</button>
                </div>
                <button class="action-btn primary" onclick="exportMarkdownReport()">📥 匯出所選日期區間＆五館比較 Markdown (.md)</button>
            </div>
        </section>

        <!-- 目前選中的最多 5 家飯店卡片槽 -->
        <section class="slots-grid" id="selectedSlots"></section>

        <!-- 每日價格走勢比較折線圖 -->
        <section class="panel-box">
            <div class="panel-head">
                <h2 id="chartTitle">📈 所選飯店每日現金房價走勢比較</h2>
                <div class="sub">滑鼠移至圖表圓點可檢視日期與房價；週六以粉紅底色標示</div>
            </div>
            <div class="chart-wrap">
                <div class="chart-legend" id="chartLegend"></div>
                <div id="svgChartContainer"></div>
            </div>
        </section>

        <!-- 所選最多 5 家飯店每日並排比較表 -->
        <section class="panel-box">
            <div class="panel-head">
                <h2 id="dailyTableTitle">📅 每日房價＆點數並排比較表（最多 5 家）</h2>
                <div class="control-group">
                    <label class="ctrl-label">顯示模式：</label>
                    <select id="WeekendFilter" onchange="renderDailyComparison()">
                        <option value="all">顯示區間內全部日期</option>
                        <option value="weekend">只看週五 / 週六 / 國定假日</option>
                        <option value="weekday">只看平日 (週日~週四)</option>
                    </select>
                </div>
            </div>
            <div class="table-scroll">
                <table id="dailyCompTable">
                    <thead id="dailyCompThead"></thead>
                    <tbody id="dailyCompTbody"></tbody>
                </table>
            </div>
        </section>

        <!-- 全日本 109 家 + 台灣 26 家萬豪飯店區間價格總覽與挑選器 -->
        <section class="panel-box" id="allHotelsSection">
            <div class="panel-head">
                <h2 id="overviewTitle">🗾 日本＆台灣萬豪全 135 家飯店區間房價總覽（點擊按鈕可加入上方每日比較，最多 5 家）</h2>
                <div class="control-group">
                    <select id="regionFilter" onchange="renderAllHotelsTable()">
                        <option value="ALL">🌏 全部日本＋台灣 (135 家)</option>
                        <option value="COUNTRY_TW">🇹🇼 全部台灣萬豪 (26 家)</option>
                        <option value="COUNTRY_JP">🇯🇵 全部日本萬豪 (109 家)</option>
                        <option value="🇹🇼 台灣 (雙北/桃園/新竹)">🇹🇼 台灣 (雙北/桃園/新竹)</option>
                        <option value="🇹🇼 台灣 (台中/台南/高雄)">🇹🇼 台灣 (台中/台南/高雄)</option>
                        <option value="🇹🇼 台灣 (宜蘭/花東/澎湖)">🇹🇼 台灣 (宜蘭/花東/澎湖)</option>
                        <option value="🇯🇵 關西 (大阪/京都/神戶/奈良)">🇯🇵 關西 (大阪/京都/神戶/奈良)</option>
                        <option value="🇯🇵 關東 (東京/橫濱/關東)">🇯🇵 關東 (東京/橫濱/關東)</option>
                        <option value="🇯🇵 中部・北陸・東海">🇯🇵 中部・北陸・東海</option>
                        <option value="🇯🇵 北海道・東北">🇯🇵 北海道・東北</option>
                        <option value="🇯🇵 中國・四國・九州">🇯🇵 中國・四國・九州</option>
                        <option value="🇯🇵 沖繩 (Okinawa)">🇯🇵 沖繩 (Okinawa)</option>
                    </select>
                    <input type="text" id="hotelSearch" placeholder="🔍 搜尋飯店中英文、城市或代碼 (如 台北, 高雄, 神戶, TPETM, OSAKB)..." oninput="renderAllHotelsTable()" style="min-width:280px;">
                    <select id="sortSelect" onchange="renderAllHotelsTable()">
                        <option value="min_asc">排序：區間最低價 (由低至高)</option>
                        <option value="avg_asc">排序：區間平均價 (由低至高)</option>
                        <option value="total_asc">排序：區間總房價 (由低至高)</option>
                        <option value="min_desc">排序：區間最低價 (由高至低)</option>
                        <option value="pts_asc">排序：最低點數 (由低至高)</option>
                        <option value="region">排序：依地區與名稱</option>
                    </select>
                </div>
            </div>
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th style="width:110px;">比較選擇</th>
                            <th>地區</th>
                            <th>代碼</th>
                            <th>飯店名稱 (中文 / 英文)</th>
                            <th>區間最低價</th>
                            <th>區間平均價</th>
                            <th>區間最高價</th>
                            <th>區間總房價</th>
                            <th>可訂天數</th>
                            <th>最低點數兌換</th>
                        </tr>
                    </thead>
                    <tbody id="allHotelsTbody"></tbody>
                </table>
            </div>
        </section>
    </div>

    <div class="toast" id="toastMsg"></div>

    <script>
        const APP_DATA = {embedded_json};
        const PALETTE = ["#38bdf8", "#10b981", "#f59e0b", "#f43f5e", "#a855f7"];
        const WEEKDAYS_ZH = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];

        let startDate = APP_DATA.defaultStartDate;
        let endDate = APP_DATA.defaultEndDate;
        let selectedCodes = [...APP_DATA.defaultSelected];

        const hotelMap = {{}};
        APP_DATA.hotels.forEach(h => {{ hotelMap[h.code] = h; }});

        function showToast(msg) {{
            const el = document.getElementById("toastMsg");
            el.textContent = msg;
            el.style.display = "block";
            clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => {{ el.style.display = "none"; }}, 2600);
        }}

        function getDatesForRange(sDate, eDate) {{
            const s = new Set();
            APP_DATA.hotels.forEach(h => {{
                Object.keys(h.days).forEach(d => {{
                    if (d >= sDate && d <= eDate) s.add(d);
                }});
            }});
            return Array.from(s).sort();
        }}

        function getDatesForMonth(monthStr) {{
            const s = new Set();
            APP_DATA.hotels.forEach(h => {{
                Object.keys(h.days).forEach(d => {{
                    if (d.startsWith(monthStr)) s.add(d);
                }});
            }});
            return Array.from(s).sort();
        }}

        function computeSummary(hotel, dates) {{
            const cashList = [];
            const ptsList = [];
            dates.forEach(d => {{
                const pair = hotel.days[d];
                if (pair) {{
                    if (pair[0] > 0) cashList.push(pair[0]);
                    if (pair[1] > 0) ptsList.push(pair[1]);
                }}
            }});
            const minCash = cashList.length ? Math.min(...cashList) : null;
            const maxCash = cashList.length ? Math.max(...cashList) : null;
            const totalCash = cashList.length ? cashList.reduce((a,b)=>a+b,0) : null;
            const avgCash = cashList.length ? Math.round(totalCash / cashList.length) : null;
            const minPts = ptsList.length ? Math.min(...ptsList) : null;
            return {{ minCash, maxCash, avgCash, totalCash, availDays: cashList.length, minPts, ptsDays: ptsList.length }};
        }}

        function makeBookingUrl(code, dateStr) {{
            const [y, m, d] = dateStr.split("-").map(Number);
            const dt = new Date(Date.UTC(y, m - 1, d));
            const nextDt = new Date(dt.getTime() + 86400000);
            const fmt = (x) => String(x.getUTCMonth()+1).padStart(2,'0') + "/" + String(x.getUTCDate()).padStart(2,'0') + "/" + x.getUTCFullYear();
            return `https://www.marriott.com/reservation/availabilitySearch.mi?isSearch=false&propertyCode=${{code}}&isRateCalendar=false&costView=AVG&numberOfRooms=1&numberOfAdults=2&numberOfChildren=0&useRewardsPoints=true&clusterCode=none&fromDate=${{fmt(dt)}}&toDate=${{fmt(nextDt)}}`;
        }}

        function initApp() {{
            const sInput = document.getElementById("startDate");
            const eInput = document.getElementById("endDate");
            sInput.min = APP_DATA.minDate;
            sInput.max = APP_DATA.maxDate;
            eInput.min = APP_DATA.minDate;
            eInput.max = APP_DATA.maxDate;
            sInput.value = startDate;
            eInput.value = endDate;

            const qSel = document.getElementById("quickMonthSelect");
            qSel.innerHTML = `<option value="">⚡ 快速帶入整月...</option>` +
                APP_DATA.months.map(m => `<option value="${{m}}">${{m}} 整月</option>`).join("");
            renderAll();
        }}

        function onDateRangeChange(changedField) {{
            const sInput = document.getElementById("startDate");
            const eInput = document.getElementById("endDate");
            let sVal = sInput.value || APP_DATA.defaultStartDate;
            let eVal = eInput.value || APP_DATA.defaultEndDate;

            if (sVal > eVal) {{
                if (changedField === 'start') {{
                    eVal = sVal;
                    eInput.value = eVal;
                }} else {{
                    sVal = eVal;
                    sInput.value = sVal;
                }}
            }}
            startDate = sVal;
            endDate = eVal;
            document.getElementById("quickMonthSelect").value = "";
            renderAll();
        }}

        function setQuickDays(numNights) {{
            const eInput = document.getElementById("endDate");
            const [y, m, d] = startDate.split("-").map(Number);
            const dt = new Date(Date.UTC(y, m - 1, d));
            const endDt = new Date(dt.getTime() + (numNights - 1) * 86400000);
            let eStr = endDt.toISOString().slice(0, 10);
            if (eStr > APP_DATA.maxDate) eStr = APP_DATA.maxDate;
            endDate = eStr;
            eInput.value = endDate;
            document.getElementById("quickMonthSelect").value = "";
            renderAll();
            showToast(`已設定為自 ${{startDate}} 起共 ${{numNights}} 晚入住區間！`);
        }}

        function onQuickMonthSelect(monthStr) {{
            if (!monthStr) return;
            const mDates = getDatesForMonth(monthStr);
            if (mDates.length) {{
                startDate = mDates[0];
                endDate = mDates[mDates.length - 1];
                document.getElementById("startDate").value = startDate;
                document.getElementById("endDate").value = endDate;
                renderAll();
                showToast(`已帶入 ${{monthStr}} 整月 (${{startDate}} ~ ${{endDate}})！`);
            }}
        }}

        function applyPreset(codes) {{
            selectedCodes = codes.filter(c => hotelMap[c]).slice(0, 5);
            renderAll();
            showToast(`已套用 ${{selectedCodes.length}} 家飯店比較組合！`);
        }}

        function toggleHotelSelection(code) {{
            const idx = selectedCodes.indexOf(code);
            if (idx >= 0) {{
                if (selectedCodes.length <= 1) {{
                    showToast("⚠️ 請至少保留 1 家飯店進行比較！");
                    return;
                }}
                selectedCodes.splice(idx, 1);
            }} else {{
                if (selectedCodes.length >= 5) {{
                    showToast("⚠️ 最多只能同時選擇 5 家飯店！請先移除上方任一飯店再加入。");
                    return;
                }}
                selectedCodes.push(code);
            }}
            renderAll();
        }}

        function scrollToAllHotels() {{
            document.getElementById("allHotelsSection").scrollIntoView({{ behavior: "smooth" }});
            document.getElementById("hotelSearch").focus();
        }}

        function renderSlots(dates) {{
            const container = document.getElementById("selectedSlots");
            const cards = [];
            for (let i = 0; i < 5; i++) {{
                const code = selectedCodes[i];
                const color = PALETTE[i % PALETTE.length];
                if (code && hotelMap[code]) {{
                    const h = hotelMap[code];
                    const sym = h.sym || "¥";
                    const s = computeSummary(h, dates);
                    cards.push(`
                    <div class="slot-card" style="border-top: 4px solid ${{color}};">
                        <div>
                            <div class="slot-top">
                                <span class="slot-code" style="background:${{color}}22; color:${{color}};">#${{i+1}} · ${{h.code}}</span>
                                <button class="remove-btn" onclick="toggleHotelSelection('${{h.code}}')" title="移除此飯店">✕</button>
                            </div>
                            <div class="slot-title">${{h.zh}}</div>
                            <div class="slot-en" title="${{h.name}}">${{h.name}}</div>
                        </div>
                        <div class="slot-stats">
                            <div>最低 <strong style="color:${{color}}">${{s.minCash ? sym+s.minCash.toLocaleString() : '無房'}}</strong></div>
                            <div>均價 <strong>${{s.avgCash ? sym+s.avgCash.toLocaleString() : '-'}}</strong></div>
                            <div>區間總計 <strong>${{s.totalCash ? sym+s.totalCash.toLocaleString() : '-'}}</strong></div>
                        </div>
                    </div>`);
                }} else {{
                    cards.push(`
                    <div class="slot-card empty" onclick="scrollToAllHotels()">
                        <div style="font-size:1.5rem; margin-bottom:0.25rem;">➕</div>
                        <div style="font-weight:600; font-size:0.9rem;">點擊從下方清單加入第 ${{i+1}} 家飯店</div>
                        <div style="font-size:0.78rem; margin-top:0.2rem;">(最多可選 5 家同時比較)</div>
                    </div>`);
                }}
            }}
            container.innerHTML = cards.join("");
        }}

        function renderChart(dates) {{
            const rangeText = `${{startDate}} ～ ${{endDate}}`;
            document.getElementById("chartTitle").textContent = `📈 所選 ${{selectedCodes.length}} 家飯店每日現金房價走勢比較 (${{rangeText}})`;
            const legendEl = document.getElementById("chartLegend");
            legendEl.innerHTML = selectedCodes.map((c, idx) => {{
                const h = hotelMap[c];
                const color = PALETTE[idx % PALETTE.length];
                return `<div class="legend-item"><span class="legend-color" style="background:${{color}}"></span><strong>${{h.zh}}</strong> <span style="color:var(--muted)">(${{c}})</span></div>`;
            }}).join("");

            const svgWrap = document.getElementById("svgChartContainer");
            if (!dates.length || !selectedCodes.length) {{
                svgWrap.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--muted);">所選日期區間 (${{rangeText}}) 暫無房價資料</div>`;
                return;
            }}

            let maxVal = 0;
            let minVal = Infinity;
            selectedCodes.forEach(c => {{
                dates.forEach(d => {{
                    const pair = hotelMap[c].days[d];
                    if (pair && pair[0] > 0) {{
                        if (pair[0] > maxVal) maxVal = pair[0];
                        if (pair[0] < minVal) minVal = pair[0];
                    }}
                }});
            }});
            if (maxVal === 0) {{
                svgWrap.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--muted);">所選飯店在此日期區間皆無空房</div>`;
                return;
            }}
            minVal = Math.max(0, Math.floor(minVal * 0.85 / 1000) * 1000);
            maxVal = Math.ceil(maxVal * 1.08 / 1000) * 1000;
            const range = Math.max(1000, maxVal - minVal);
            const firstSym = (hotelMap[selectedCodes[0]] && hotelMap[selectedCodes[0]].sym) || "¥";

            const W = Math.max(960, dates.length * 42 + 90);
            const H = 295;
            const padL = 68, padR = 24, padT = 22, padB = 50;
            const plotW = W - padL - padR;
            const plotH = H - padT - padB;

            const xOf = (i) => padL + (dates.length > 1 ? (i / (dates.length - 1)) * plotW : plotW / 2);
            const yOf = (v) => padT + plotH - ((v - minVal) / range) * plotH;

            let gridSvg = "";
            for (let g = 0; g <= 4; g++) {{
                const val = Math.round(minVal + (range * g) / 4);
                const y = yOf(val);
                gridSvg += `<line x1="${{padL}}" y1="${{y}}" x2="${{W - padR}}" y2="${{y}}" stroke="#1e293b" stroke-width="1" />`;
                gridSvg += `<text x="${{padL - 8}}" y="${{y + 4}}" fill="#94a3b8" font-size="11" text-anchor="end">${{firstSym}}${{(val/1000).toFixed(0)}}k</text>`;
            }}

            let xLabelsSvg = "";
            dates.forEach((d, i) => {{
                const x = xOf(i);
                const dt = new Date(d + "T00:00:00");
                const wDay = dt.getDay();
                const isSat = wDay === 6;
                if (isSat) {{
                    gridSvg += `<rect x="${{x - 14}}" y="${{padT}}" width="28" height="${{plotH}}" fill="rgba(244,63,94,0.08)" />`;
                }}
                const shortMd = Number(d.slice(5,7)) + "/" + Number(d.slice(8,10));
                const wTxt = WEEKDAYS_ZH[wDay].slice(1);
                xLabelsSvg += `<text x="${{x}}" y="${{H - 24}}" fill="${{isSat ? '#fda4af' : '#94a3b8'}}" font-size="10.5" font-weight="${{isSat ? '700' : '400'}}" text-anchor="middle">${{shortMd}}</text>`;
                xLabelsSvg += `<text x="${{x}}" y="${{H - 9}}" fill="${{isSat ? '#fda4af' : '#64748b'}}" font-size="10" text-anchor="middle">${{wTxt}}</text>`;
            }});

            let linesSvg = "";
            selectedCodes.forEach((c, idx) => {{
                const color = PALETTE[idx % PALETTE.length];
                const h = hotelMap[c];
                const sym = h.sym || "¥";
                const pts = [];
                dates.forEach((d, i) => {{
                    const pair = h.days[d];
                    if (pair && pair[0] > 0) {{
                        pts.push({{ x: xOf(i), y: yOf(pair[0]), val: pair[0], date: d }});
                    }}
                }});
                if (pts.length > 1) {{
                    const poly = pts.map(p => `${{p.x.toFixed(1)}},${{p.y.toFixed(1)}}`).join(" ");
                    linesSvg += `<polyline fill="none" stroke="${{color}}" stroke-width="2.5" points="${{poly}}" />`;
                }}
                pts.forEach(p => {{
                    linesSvg += `<circle cx="${{p.x.toFixed(1)}}" cy="${{p.y.toFixed(1)}}" r="4" fill="${{color}}" stroke="#0b1120" stroke-width="1.5"><title>${{p.date}} · ${{h.zh}}: ${{sym}}${{p.val.toLocaleString()}}</title></circle>`;
                }});
            }});

            svgWrap.innerHTML = `<svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}">${{gridSvg}}${{xLabelsSvg}}${{linesSvg}}</svg>`;
        }}

        function renderDailyComparison() {{
            const dates = getDatesForRange(startDate, endDate);
            const filterMode = document.getElementById("WeekendFilter").value;
            document.getElementById("dailyTableTitle").textContent = `📅 所選 ${{selectedCodes.length}} 家飯店每日房價＆點數並排比較表 (${{startDate}} ～ ${{endDate}}，共 ${{dates.length}} 晚)`;

            const thead = document.getElementById("dailyCompThead");
            let headHtml = `<tr><th style="width:110px;">日期</th><th style="width:70px;">星期</th><th style="width:120px;">節日 / 備註</th>`;
            selectedCodes.forEach((c, idx) => {{
                const h = hotelMap[c];
                const color = PALETTE[idx % PALETTE.length];
                headHtml += `<th style="border-top: 3px solid ${{color}};">${{h.zh}}<br><small class="mono" style="color:${{color}}">${{h.code}}</small></th>`;
            }});
            headHtml += `<th>👑 當日最划算推薦</th></tr>`;
            thead.innerHTML = headHtml;

            const tbody = document.getElementById("dailyCompTbody");
            const rowsHtml = [];

            dates.forEach(d => {{
                const dt = new Date(d + "T00:00:00");
                const wDay = dt.getDay();
                const isFriOrSat = (wDay === 5 || wDay === 6);
                const holiday = APP_DATA.holidays[d] || "";

                if (filterMode === "weekend" && !isFriOrSat && !holiday) return;
                if (filterMode === "weekday" && (isFriOrSat || holiday)) return;

                let minPrice = Infinity;
                let minSym = "¥";
                selectedCodes.forEach(c => {{
                    const pair = hotelMap[c].days[d];
                    if (pair && pair[0] > 0 && pair[0] < minPrice) {{
                        minPrice = pair[0];
                        minSym = hotelMap[c].sym || "¥";
                    }}
                }});

                const cells = [];
                const winners = [];
                selectedCodes.forEach((c, idx) => {{
                    const h = hotelMap[c];
                    const sym = h.sym || "¥";
                    const pair = h.days[d] || [-1, -1];
                    const cash = pair[0];
                    const pts = pair[1];
                    const isCheapest = (cash > 0 && cash === minPrice);
                    if (isCheapest) winners.push(h.zh);

                    const bUrl = makeBookingUrl(c, d);
                    if (cash > 0) {{
                        const crown = isCheapest ? `<span class="crown-badge">👑 最低</span>` : "";
                        const ptsHtml = pts > 0 ? `<span class="pts-sub">✨ ${{pts.toLocaleString()}} 點</span>` : `<span style="display:block;font-size:0.72rem;color:#64748b;">點數未開放</span>`;
                        cells.push(`
                        <td class="${{isCheapest ? 'cheapest-cell' : ''}}">
                            <a class="price-link" href="${{bUrl}}" target="_blank" title="前往萬豪官網預訂 ${{h.zh}} (${{d}})">
                                <span class="price-val" style="color:${{isCheapest ? '#34d399' : '#f8fafc'}}">${{sym}}${{cash.toLocaleString()}}</span>${{crown}}
                                ${{ptsHtml}}
                            </a>
                        </td>`);
                    }} else {{
                        const ptsHtml = pts > 0 ? `<span class="pts-sub">✨ ${{pts.toLocaleString()}} 點</span>` : "";
                        cells.push(`<td><span style="color:#64748b;">無現金房</span>${{ptsHtml}}</td>`);
                    }}
                }});

                const noteStr = holiday ? `<span style="color:#fda4af;font-weight:600;">${{holiday}}</span>` : (wDay === 6 ? `<span class="sat-badge">🔥 週六尖峰</span>` : (wDay === 5 ? `<span style="color:#fcd34d;">週五晚</span>` : `-`));
                const bestSummary = (minPrice < Infinity)
                    ? `<strong style="color:#34d399;">${{minSym}}${{minPrice.toLocaleString()}}</strong> <span style="font-size:0.82rem;color:var(--muted);">(${{winners.join("、")}})</span>`
                    : `<span style="color:#64748b;">全部無房</span>`;

                rowsHtml.push(`
                <tr class="${{wDay === 6 ? 'sat-row' : ''}}">
                    <td class="mono">${{d}}</td>
                    <td class="${{wDay === 6 || wDay === 0 ? 'sat-badge' : ''}}">${{WEEKDAYS_ZH[wDay]}}</td>
                    <td>${{noteStr}}</td>
                    ${{cells.join("")}}
                    <td>${{bestSummary}}</td>
                </tr>`);
            }});

            tbody.innerHTML = rowsHtml.join("");
        }}

        function renderAllHotelsTable() {{
            const dates = getDatesForRange(startDate, endDate);
            const regionVal = document.getElementById("regionFilter").value;
            const q = document.getElementById("hotelSearch").value.trim().toLowerCase();
            const sortMode = document.getElementById("sortSelect").value;

            const enriched = APP_DATA.hotels.map(h => {{
                const s = computeSummary(h, dates);
                return {{ ...h, summary: s }};
            }}).filter(h => {{
                if (regionVal === "COUNTRY_TW" && h.country !== "TW") return false;
                if (regionVal === "COUNTRY_JP" && h.country !== "JP") return false;
                if (regionVal !== "ALL" && regionVal !== "COUNTRY_TW" && regionVal !== "COUNTRY_JP" && h.region !== regionVal) return false;
                if (q) {{
                    const hay = `${{h.code}} ${{h.name}} ${{h.zh}} ${{h.region}}`.toLowerCase();
                    if (!hay.includes(q)) return false;
                }}
                return true;
            }});

            enriched.sort((a, b) => {{
                const sa = a.summary, sb = b.summary;
                if (sortMode === "min_asc") return (sa.minCash || 99999999) - (sb.minCash || 99999999);
                if (sortMode === "min_desc") return (sb.minCash || -1) - (sa.minCash || -1);
                if (sortMode === "avg_asc") return (sa.avgCash || 99999999) - (sb.avgCash || 99999999);
                if (sortMode === "total_asc") return (sa.totalCash || 999999999) - (sb.totalCash || 999999999);
                if (sortMode === "pts_asc") return (sa.minPts || 99999999) - (sb.minPts || 99999999);
                return a.region.localeCompare(b.region) || a.zh.localeCompare(b.zh);
            }});

            document.getElementById("overviewTitle").textContent = `🗾 日本＆台灣萬豪全飯店 (${{startDate}} ～ ${{endDate}}) 房價總覽（符合篩選共 ${{enriched.length}} 家，可勾選最多 5 家比較）`;

            const tbody = document.getElementById("allHotelsTbody");
            tbody.innerHTML = enriched.map(h => {{
                const isSel = selectedCodes.includes(h.code);
                const sym = h.sym || "¥";
                const s = h.summary;
                const selIdx = selectedCodes.indexOf(h.code);
                const btnTxt = isSel ? `✓ 已選 (#${{selIdx+1}})` : `＋ 加入比較`;
                return `
                <tr>
                    <td>
                        <button class="pick-btn ${{isSel ? 'selected' : ''}}" onclick="toggleHotelSelection('${{h.code}}')">${{btnTxt}}</button>
                    </td>
                    <td style="font-size:0.84rem; color:var(--muted);">${{h.region}}</td>
                    <td class="mono" style="font-weight:700; color:var(--accent);">${{h.code}}</td>
                    <td>
                        <div style="font-weight:700;">${{h.zh}}</div>
                        <div style="font-size:0.78rem; color:var(--muted);">${{h.name}}</div>
                    </td>
                    <td class="price-val" style="color:${{s.minCash ? '#34d399' : '#64748b'}}">${{s.minCash ? sym+s.minCash.toLocaleString() : '無空房'}}</td>
                    <td class="price-val">${{s.avgCash ? sym+s.avgCash.toLocaleString() : '-'}}</td>
                    <td class="price-val" style="color:${{s.maxCash ? '#fda4af' : '#64748b'}}">${{s.maxCash ? sym+s.maxCash.toLocaleString() : '-'}}</td>
                    <td class="price-val" style="color:var(--accent);">${{s.totalCash ? sym+s.totalCash.toLocaleString() : '-'}}</td>
                    <td>${{s.availDays}} / ${{dates.length}} 晚</td>
                    <td style="color:${{s.minPts ? 'var(--amber)' : '#64748b'}}; font-weight:600;">
                        ${{s.minPts ? s.minPts.toLocaleString() + ' pts (' + s.ptsDays + '天)' : '未開放'}}
                    </td>
                </tr>`;
            }}).join("");
        }}

        function exportMarkdownReport() {{
            const dates = getDatesForRange(startDate, endDate);
            const rangeStr = `${{startDate}} ～ ${{endDate}}`;
            const lines = [
                `# 🇯🇵🇹🇼 日台萬豪飯店 (${{rangeStr}}) 每日價格比較報告`,
                ``,
                `- **查詢日期區間**：${{startDate}} 至 ${{endDate}}（共 ${{dates.length}} 晚）`,
                `- **比較飯店 (${{selectedCodes.length}} 家)**：${{selectedCodes.map(c => `${{hotelMap[c].zh}} (${{c}})`).join("、")}}`,
                ``,
                `## 📊 區間統計摘要`,
                `| 代碼 | 飯店名稱 | 區間最低價 | 區間平均價 | 區間最高價 | 區間總房價 | 最低點數 |`,
                `| :---: | :--- | :---: | :---: | :---: | :---: | :---: |`
            ];
            selectedCodes.forEach(c => {{
                const h = hotelMap[c];
                const sym = h.sym || "¥";
                const s = computeSummary(h, dates);
                lines.push(`| \\`${{c}}\\` | **${{h.zh}}** (${{h.name}}) | ${{s.minCash ? sym+s.minCash.toLocaleString() : '無'}} | ${{s.avgCash ? sym+s.avgCash.toLocaleString() : '-'}} | ${{s.maxCash ? sym+s.maxCash.toLocaleString() : '-'}} | ${{s.totalCash ? sym+s.totalCash.toLocaleString() : '-'}} | ${{s.minPts ? s.minPts.toLocaleString()+' pts' : '未開放'}} |`);
            }});
            lines.push(``, `## 📅 每日房價並排比較 (${{rangeStr}})`, ``);
            const cols = ["日期", "星期", ...selectedCodes.map(c => `${{hotelMap[c].zh}} (${{c}})`), "當日最低價"];
            lines.push(`| ${{cols.join(" | ")}} |`);
            lines.push(`| ${{cols.map(()=>":---:").join(" | ")}} |`);

            dates.forEach(d => {{
                const dt = new Date(d + "T00:00:00");
                const wTxt = WEEKDAYS_ZH[dt.getDay()];
                let minP = Infinity;
                let minSym = "¥";
                selectedCodes.forEach(c => {{
                    const pair = hotelMap[c].days[d];
                    if (pair && pair[0] > 0 && pair[0] < minP) {{
                        minP = pair[0];
                        minSym = hotelMap[c].sym || "¥";
                    }}
                }});
                const rowCells = selectedCodes.map(c => {{
                    const sym = hotelMap[c].sym || "¥";
                    const pair = hotelMap[c].days[d] || [-1, -1];
                    if (pair[0] > 0) {{
                        return pair[0] === minP ? `**${{sym}}${{pair[0].toLocaleString()}}** 👑` : `${{sym}}${{pair[0].toLocaleString()}}`;
                    }}
                    return "無房";
                }});
                const bestStr = minP < Infinity ? `**${{minSym}}${{minP.toLocaleString()}}**` : "-";
                lines.push(`| \\`${{d}}\\` | ${{wTxt}} | ${{rowCells.join(" | ")}} | ${{bestStr}} |`);
            }});

            const nl = String.fromCharCode(10);
            const blob = new Blob([lines.join(nl)], {{ type: "text/markdown;charset=utf-8" }});
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `萬豪五館比較_${{startDate}}_to_${{endDate}}.md`;
            a.click();
            showToast("✅ 已匯出並下載 Markdown 報告！");
        }}

        function renderAll() {{
            const dates = getDatesForRange(startDate, endDate);
            document.getElementById("nightsBadge").textContent = `共 ${{dates.length}} 晚`;
            renderSlots(dates);
            renderChart(dates);
            renderDailyComparison();
            renderAllHotelsTable();
        }}

        initApp();
    </script>
</body>
</html>
"""
    output_path.write_text(html_doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="日本萬豪全飯店日期區間價格與最多五館每日比較產生器")
    parser.add_argument("--start-date", default="2027-02-01", help="預設開始日期 (格式: YYYY-MM-DD，預設 2027-02-01)")
    parser.add_argument("--end-date", default="2027-02-28", help="預設結束日期 (格式: YYYY-MM-DD，預設 2027-02-28)")
    parser.add_argument(
        "--hotels",
        default="OSAKB,OSACO,OSAYS,OSAUU,OSAAL",
        help="預設比較的最多 5 家飯店代碼 (以逗號分隔)",
    )
    parser.add_argument("--no-browser", action="store_true", help="不自動開啟瀏覽器")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    cache_path = base_dir / "marriott_japan_cache.json"

    if not cache_path.exists():
        print("ℹ️ 尚未建立快取，正在呼叫 fetch_marriott_japan 進行抓取...")
        import fetch_marriott_japan
        fetch_marriott_japan.main()

    all_data = json.loads(cache_path.read_text(encoding="utf-8"))
    selected_codes = [c.strip().upper() for c in args.hotels.split(",") if c.strip()][:5]

    md_path = base_dir / "日本萬豪全飯店_整月房價與五館比較報告.md"
    html_path = base_dir / "日本萬豪全飯店_整月房價與五館比較.html"

    generate_markdown_report(all_data, selected_codes, args.start_date, args.end_date, md_path)
    generate_html_comparator(all_data, selected_codes, args.start_date, args.end_date, html_path)

    print(f"✅ 報表與互動比較網頁已更新完成！（查詢區間：{args.start_date} ～ {args.end_date}）")
    print(f"📄 Markdown 報告：{md_path}")
    print(f"🌐 HTML 互動比較網頁：{html_path}")

    if not args.no_browser:
        webbrowser.open(html_path.as_uri())


if __name__ == "__main__":
    main()
