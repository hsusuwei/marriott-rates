"""
產生專為 Google Sites (Google 協作平台) 最佳化的單一內嵌 HTML 程式碼檔案
- 收錄日本 109 家 + 台灣 26 家（共 135 家）萬豪集團飯店全年度房價與點數資料
- 採用純同步 RLE (Run-Length Encoding) 欄位壓縮，不依賴非同步 DecompressionStream，
  在任何瀏覽器、本機直接雙擊開啟或 Google Sites iframe 內皆可 100% 瞬間載入！
"""

from datetime import datetime
import json
from pathlib import Path
import sys

from build_marriott_comparator import (
    JP_HOLIDAYS,
    detect_region,
    get_all_available_dates,
    get_available_months,
    get_currency_symbol,
    is_taiwan_hotel,
    translate_fallback_name,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def rle_encode(arr: list[int]) -> str:
    """將整數陣列做 Run-Length Encoding 壓縮，例如 [19000, 19000, 19000] -> '19000*3'。"""
    out: list[str] = []
    prev: int | None = None
    cnt = 0
    for v in arr:
        if v == prev:
            cnt += 1
        else:
            if prev is not None:
                out.append(f"{prev}*{cnt}" if cnt > 1 else str(prev))
            prev = v
            cnt = 1
    if prev is not None:
        out.append(f"{prev}*{cnt}" if cnt > 1 else str(prev))
    return ",".join(out)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    cache_path = base_dir / "marriott_japan_cache.json"
    all_data = json.loads(cache_path.read_text(encoding="utf-8"))

    all_dates = get_all_available_dates(all_data)
    months_list = get_available_months(all_data)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    compact_hotels = []
    for code, h in all_data.items():
        zh_name = translate_fallback_name(h["name"], code)
        country = "TW" if is_taiwan_hotel(code, h) else "JP"
        region = detect_region(code, h["name"], country)
        sym = get_currency_symbol(code, h)
        days_map = h.get("days", {})
        cash_arr = [days_map.get(dt, [-1, -1])[0] for dt in all_dates]
        pts_arr = [days_map.get(dt, [-1, -1])[1] for dt in all_dates]
        compact_hotels.append(
            {
                "c": code,
                "n": h["name"],
                "z": zh_name,
                "k": country,
                "s": sym,
                "r": region,
                "cash": rle_encode(cash_arr),
                "pts": rle_encode(pts_arr),
            }
        )

    compact_hotels.sort(key=lambda x: (x["r"], x["z"]))

    payload_json = json.dumps(
        {
            "updatedAt": now_str,
            "defaultStartDate": "2027-02-01",
            "defaultEndDate": "2027-02-28",
            "defaultSelected": ["OSAKB", "OSACO", "OSAYS", "TPETM", "KHHMC"],
            "dates": all_dates,
            "months": months_list,
            "holidays": JP_HOLIDAYS,
            "hotels": compact_hotels,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>日本＆台灣萬豪全飯店房價與五館每日比較 (Google Sites 內嵌版)</title>
<style>
:root {{
    --bg: #0b1120;
    --panel: #151f32;
    --text: #f8fafc;
    --muted: #94a3b8;
    --border: #26354d;
    --accent: #38bdf8;
    --green: #10b981;
    --amber: #f59e0b;
    --rose: #f43f5e;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: "Segoe UI", "Microsoft JhengHei", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 1rem;
    line-height: 1.45;
}}
.container {{ max-width: 100%; margin: 0 auto; }}
header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding-bottom: 0.9rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}}
.brand-pill {{
    display: inline-block;
    background: rgba(56, 189, 248, 0.14);
    color: var(--accent);
    border: 1px solid rgba(56, 189, 248, 0.35);
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    margin-bottom: 0.35rem;
}}
h1 {{ font-size: 1.45rem; font-weight: 800; }}
.sub {{ color: var(--muted); font-size: 0.84rem; margin-top: 0.2rem; }}
.sub a {{ color: var(--accent); text-decoration: none; }}
.toolbar {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.95rem 1.1rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}}
.control-group {{ display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap; }}
label.ctrl-label {{ font-size: 0.84rem; color: var(--muted); font-weight: 600; }}
select, input[type="text"], input[type="date"] {{
    background: #0f172a;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 0.4rem 0.7rem;
    border-radius: 8px;
    font-size: 0.86rem;
    outline: none;
    color-scheme: dark;
}}
.nights-badge {{
    background: rgba(16, 185, 129, 0.16);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 0.28rem 0.65rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
}}
.preset-btn, .action-btn {{
    background: #0f172a;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 0.38rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    cursor: pointer;
}}
.preset-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
.action-btn.primary {{
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    border: none;
    color: #fff;
    font-weight: 700;
}}
.slots-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
}}
.slot-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 120px;
}}
.slot-card.empty {{
    border-style: dashed;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    cursor: pointer;
    text-align: center;
}}
.slot-top {{ display: flex; justify-content: space-between; align-items: center; }}
.slot-code {{ font-family: Consolas, monospace; font-size: 0.74rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 5px; }}
.remove-btn {{
    background: rgba(244, 63, 94, 0.18);
    color: #fda4af;
    border: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    cursor: pointer;
}}
.slot-title {{ font-weight: 700; font-size: 0.94rem; margin-top: 0.3rem; }}
.slot-en {{ font-size: 0.72rem; color: var(--muted); margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.slot-stats {{ display: flex; justify-content: space-between; font-size: 0.76rem; border-top: 1px solid var(--border); padding-top: 0.45rem; color: var(--muted); }}
.slot-stats strong {{ color: var(--text); font-size: 0.86rem; display: block; }}
.panel-box {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem;
    margin-bottom: 1rem;
}}
.panel-head {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.6rem; margin-bottom: 0.85rem; }}
.panel-head h2 {{ font-size: 1.08rem; font-weight: 700; }}
.chart-wrap {{ width: 100%; overflow-x: auto; background: #0f172a; border: 1px solid var(--border); border-radius: 10px; padding: 0.75rem; }}
.chart-legend {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.5rem; font-size: 0.8rem; }}
.legend-item {{ display: flex; align-items: center; gap: 0.35rem; }}
.legend-color {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
.table-scroll {{ overflow-x: auto; max-height: 540px; overflow-y: auto; border-radius: 10px; border: 1px solid var(--border); }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: #0f172a; color: var(--muted); font-weight: 600; position: sticky; top: 0; z-index: 4; }}
tr:hover td {{ background: rgba(30, 41, 59, 0.55); }}
.mono {{ font-family: Consolas, monospace; }}
.price-val {{ font-weight: 700; font-size: 0.92rem; font-variant-numeric: tabular-nums; }}
.cheapest-cell {{ background: rgba(16, 185, 129, 0.13) !important; border-left: 3px solid var(--green); }}
.crown-badge {{ display: inline-block; background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.68rem; font-weight: 700; padding: 0.08rem 0.4rem; border-radius: 999px; margin-left: 0.25rem; }}
.pts-sub {{ display: block; font-size: 0.7rem; color: var(--amber); }}
.price-link {{ color: inherit; text-decoration: none; display: block; }}
.price-link:hover {{ text-decoration: underline; color: var(--accent); }}
.sat-row {{ background: rgba(244, 63, 94, 0.04); }}
.sat-badge {{ color: #fda4af; font-weight: 700; }}
.pick-btn {{ background: #0f172a; color: var(--text); border: 1px solid var(--border); padding: 0.3rem 0.65rem; border-radius: 6px; cursor: pointer; font-size: 0.78rem; font-weight: 600; }}
.pick-btn.selected {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border-color: var(--green); }}
.toast {{ position: fixed; bottom: 16px; right: 16px; background: #1e293b; border: 1px solid var(--accent); color: var(--text); padding: 0.65rem 1rem; border-radius: 10px; display: none; z-index: 999; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <span class="brand-pill">Marriott Bonvoy · 日本 109 家 ＋ 台灣 26 家（共 135 家）動態比較</span>
            <h1>🇯🇵 日本 ＆ 🇹🇼 台灣萬豪各旅館房價總覽與最多五館每日比較</h1>
            <div class="sub">資料來源：<a href="https://www.ustatz.com/hotelGroups/Japan" target="_blank">USTATZ 日本</a> ＆ <a href="https://www.ustatz.com/hotelGroups/Taiwan" target="_blank">台灣酒店查詢</a> ｜ 支援自選開始與結束日期、勾選最多 5 家飯店逐日比價</div>
        </div>
        <div class="sub" style="text-align:right;">
            <span id="updateTimeLabel">更新：{now_str} (內建快取)</span><br>
            <a href="javascript:void(0)" onclick="configureCloudUrl()" style="color:var(--accent); font-weight:600;">☁️ 設定/更換雲端自動更新網址</a>
        </div>
    </header>

    <section class="toolbar">
        <div class="control-group">
            <label class="ctrl-label" for="startDate">📅 開始日期：</label>
            <input type="date" id="startDate" onchange="onDateRangeChange('start')">
            <label class="ctrl-label" for="endDate">結束日期：</label>
            <input type="date" id="endDate" onchange="onDateRangeChange('end')">
            <span class="nights-badge" id="nightsBadge">載入中...</span>
            <button class="preset-btn" onclick="setQuickDays(3)">3晚</button>
            <button class="preset-btn" onclick="setQuickDays(5)">5晚</button>
            <button class="preset-btn" onclick="setQuickDays(7)">7晚</button>
            <select id="quickMonthSelect" onchange="onQuickMonthSelect(this.value)">
                <option value="">⚡ 快速帶入整月...</option>
            </select>
        </div>
        <div class="control-group" style="justify-content:space-between; border-top:1px solid var(--border); padding-top:0.55rem;">
            <div class="control-group">
                <span class="ctrl-label">🏨 快速組合：</span>
                <button class="preset-btn" onclick="applyPreset(['TPETM','TPEWH','TPEST','TPECY','TPETW'])">🇹🇼 台北/北台灣 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['KHHMC','RMQMD','TNNAL','TPEYR','HUNMD'])">🇹🇼 中南部/宜花 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['OSAKB','OSACO','OSAYS','OSAUU','OSAAL'])">🏯 關西 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['OSALC','UKYRZ','UKYLC','UKYWI','UKYOX'])">⛩️ 京都 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['TYOCY','TYOAL','TYOMC','TYOWI','TYOSI'])">🗼 東京 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['CTSCY','CTSFI','CTSWI','HKDXF','SDJWI'])">❄️ 北海道 5 館</button>
                <button class="preset-btn" onclick="applyPreset(['OKASI','OKARN','OKARZ','OKALC','FUKRZ'])">🌺 沖繩/九州 5 館</button>
            </div>
            <button class="action-btn primary" onclick="exportMarkdownReport()">📥 匯出 Markdown (.md)</button>
        </div>
    </section>

    <section class="slots-grid" id="selectedSlots"></section>

    <section class="panel-box">
        <div class="panel-head">
            <h2 id="chartTitle">📈 所選飯店每日現金房價走勢比較</h2>
        </div>
        <div class="chart-wrap">
            <div class="chart-legend" id="chartLegend"></div>
            <div id="svgChartContainer"></div>
        </div>
    </section>

    <section class="panel-box">
        <div class="panel-head">
            <h2 id="dailyTableTitle">📅 每日房價＆點數並排比較表（最多 5 家）</h2>
            <div class="control-group">
                <select id="WeekendFilter" onchange="renderDailyComparison()">
                    <option value="all">顯示區間內全部日期</option>
                    <option value="weekend">只看週五 / 週六 / 國定假日</option>
                    <option value="weekday">只看平日 (週日~週四)</option>
                </select>
            </div>
        </div>
        <div class="table-scroll">
            <table>
                <thead id="dailyCompThead"></thead>
                <tbody id="dailyCompTbody"></tbody>
            </table>
        </div>
    </section>

    <section class="panel-box" id="allHotelsSection">
        <div class="panel-head">
            <h2 id="overviewTitle">🗾 日本＆台灣萬豪全 135 家飯店區間房價總覽</h2>
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
                <input type="text" id="hotelSearch" placeholder="🔍 搜尋飯店中英文或代碼 (如 台北, 高雄, 神戶, TPETM, OSAKB)..." oninput="renderAllHotelsTable()" style="min-width:240px;">
                <select id="sortSelect" onchange="renderAllHotelsTable()">
                    <option value="min_asc">排序：區間最低價 (低➔高)</option>
                    <option value="avg_asc">排序：區間平均價 (低➔高)</option>
                    <option value="total_asc">排序：區間總房價 (低➔高)</option>
                    <option value="pts_asc">排序：最低點數 (低➔高)</option>
                </select>
            </div>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th style="width:95px;">比較選擇</th>
                        <th>地區</th>
                        <th>代碼</th>
                        <th>飯店名稱</th>
                        <th>區間最低價</th>
                        <th>區間平均價</th>
                        <th>區間最高價</th>
                        <th>區間總房價</th>
                        <th>可訂天數</th>
                        <th>最低點數</th>
                    </tr>
                </thead>
                <tbody id="allHotelsTbody"></tbody>
            </table>
        </div>
    </section>
</div>
<div class="toast" id="toastMsg"></div>

<script>
const DEFAULT_CLOUD_API_URL = "";
const RAW_PAYLOAD = {payload_json};
const PALETTE = ["#38bdf8", "#10b981", "#f59e0b", "#f43f5e", "#a855f7"];
const WEEKDAYS_ZH = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];

let APP_DATA = null;
let startDate = "2027-02-01";
let endDate = "2027-02-28";
let selectedCodes = ["OSAKB", "OSACO", "OSAYS", "TPETM", "KHHMC"];
const hotelMap = {{}};

function rleDecode(rleStr) {{
    if (!rleStr) return [];
    const parts = rleStr.split(",");
    const out = [];
    for (let i = 0; i < parts.length; i++) {{
        const p = parts[i];
        const star = p.indexOf("*");
        if (star >= 0) {{
            const val = parseInt(p.slice(0, star), 10);
            const cnt = parseInt(p.slice(star + 1), 10);
            for (let k = 0; k < cnt; k++) out.push(val);
        }} else {{
            out.push(parseInt(p, 10));
        }}
    }}
    return out;
}}

function bootData() {{
    const allDates = RAW_PAYLOAD.dates;
    const hotels = RAW_PAYLOAD.hotels.map(h => {{
        const cashArr = rleDecode(h.cash);
        const ptsArr = rleDecode(h.pts);
        const daysObj = {{}};
        for (let i = 0; i < allDates.length; i++) {{
            const cVal = cashArr[i] || -1;
            const pVal = ptsArr[i] || -1;
            if (cVal > 0 || pVal > 0) {{
                daysObj[allDates[i]] = [cVal, pVal];
            }}
        }}
        return {{
            code: h.c,
            name: h.n,
            zh: h.z,
            country: h.k || "JP",
            sym: h.s || "¥",
            region: h.r,
            days: daysObj
        }};
    }});

    APP_DATA = {{
        defaultStartDate: RAW_PAYLOAD.defaultStartDate,
        defaultEndDate: RAW_PAYLOAD.defaultEndDate,
        minDate: allDates[0],
        maxDate: allDates[allDates.length - 1],
        dates: allDates,
        months: RAW_PAYLOAD.months,
        holidays: RAW_PAYLOAD.holidays,
        hotels: hotels
    }};
    hotels.forEach(h => {{ hotelMap[h.code] = h; }});
    initApp();
    tryFetchCloudData();
}}

async function tryFetchCloudData() {{
    let cloudUrl = DEFAULT_CLOUD_API_URL;
    try {{
        const saved = localStorage.getItem("MARRIOTT_CLOUD_API_URL");
        if (saved) cloudUrl = saved;
    }} catch (e) {{}}
    if (!cloudUrl) return;

    try {{
        document.getElementById("updateTimeLabel").textContent = "☁️ 正在同步雲端最新房價...";
        const resp = await fetch(cloudUrl);
        const cloudRaw = await resp.json();
        if (cloudRaw && cloudRaw.dates && cloudRaw.hotels) {{
            const cDates = cloudRaw.dates;
            cloudRaw.hotels.forEach(ch => {{
                const target = hotelMap[ch.c];
                if (target) {{
                    const daysObj = {{}};
                    for (let i = 0; i < cDates.length; i++) {{
                        if (ch.cash[i] > 0 || ch.pts[i] > 0) {{
                            daysObj[cDates[i]] = [ch.cash[i], ch.pts[i]];
                        }}
                    }}
                    target.days = daysObj;
                }}
            }});
            APP_DATA.dates = cDates;
            APP_DATA.minDate = cDates[0];
            APP_DATA.maxDate = cDates[cDates.length - 1];
            const mSet = new Set(cDates.map(d => d.slice(0, 7)));
            APP_DATA.months = Array.from(mSet).sort();
            document.getElementById("updateTimeLabel").textContent = `☁️ 雲端自動更新：${{cloudRaw.updatedAt || '最新'}}`;
            initApp();
            showToast("✅ 已同步雲端最新房價資料！");
        }}
    }} catch (err) {{
        document.getElementById("updateTimeLabel").textContent = "更新：{now_str} (離線快取)";
    }}
}}

function configureCloudUrl() {{
    let current = DEFAULT_CLOUD_API_URL;
    try {{ current = localStorage.getItem("MARRIOTT_CLOUD_API_URL") || current; }} catch (e) {{}}
    const input = prompt("請貼上你部署好的 Google Apps Script 網頁應用程式網址 (以 /exec 結尾)：", current);
    if (input !== null) {{
        const trimmed = input.trim();
        try {{ localStorage.setItem("MARRIOTT_CLOUD_API_URL", trimmed); }} catch (e) {{}}
        if (trimmed) {{
            tryFetchCloudData();
        }} else {{
            showToast("已清除雲端網址，改用內建快取資料。");
        }}
    }}
}}

function showToast(msg) {{
    const el = document.getElementById("toastMsg");
    el.textContent = msg;
    el.style.display = "block";
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => {{ el.style.display = "none"; }}, 2500);
}}

function getDatesForRange(sDate, eDate) {{
    return APP_DATA.dates.filter(d => d >= sDate && d <= eDate);
}}

function computeSummary(hotel, dates) {{
    const cashList = [], ptsList = [];
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
    sInput.min = APP_DATA.minDate; sInput.max = APP_DATA.maxDate;
    eInput.min = APP_DATA.minDate; eInput.max = APP_DATA.maxDate;
    sInput.value = startDate; eInput.value = endDate;

    const qSel = document.getElementById("quickMonthSelect");
    qSel.innerHTML = `<option value="">⚡ 快速帶入整月...</option>` +
        APP_DATA.months.map(m => `<option value="${{m}}">${{m}} 整月</option>`).join("");
    renderAll();
}}

function onDateRangeChange(which) {{
    const sInput = document.getElementById("startDate");
    const eInput = document.getElementById("endDate");
    let s = sInput.value || startDate, e = eInput.value || endDate;
    if (s > e) {{
        if (which === "start") {{ e = s; eInput.value = e; }}
        else {{ s = e; sInput.value = s; }}
    }}
    startDate = s; endDate = e;
    document.getElementById("quickMonthSelect").value = "";
    renderAll();
}}

function setQuickDays(n) {{
    const [y, m, d] = startDate.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    const endDt = new Date(dt.getTime() + (n - 1) * 86400000);
    let eStr = endDt.toISOString().slice(0, 10);
    if (eStr > APP_DATA.maxDate) eStr = APP_DATA.maxDate;
    endDate = eStr;
    document.getElementById("endDate").value = endDate;
    document.getElementById("quickMonthSelect").value = "";
    renderAll();
}}

function onQuickMonthSelect(mStr) {{
    if (!mStr) return;
    const mDates = APP_DATA.dates.filter(d => d.startsWith(mStr));
    if (mDates.length) {{
        startDate = mDates[0];
        endDate = mDates[mDates.length - 1];
        document.getElementById("startDate").value = startDate;
        document.getElementById("endDate").value = endDate;
        renderAll();
    }}
}}

function applyPreset(codes) {{
    selectedCodes = codes.filter(c => hotelMap[c]).slice(0, 5);
    renderAll();
}}

function toggleHotelSelection(code) {{
    const idx = selectedCodes.indexOf(code);
    if (idx >= 0) {{
        if (selectedCodes.length <= 1) {{ showToast("⚠️ 請至少保留 1 家飯店！"); return; }}
        selectedCodes.splice(idx, 1);
    }} else {{
        if (selectedCodes.length >= 5) {{ showToast("⚠️ 最多只能同時選擇 5 家飯店！"); return; }}
        selectedCodes.push(code);
    }}
    renderAll();
}}

function scrollToAllHotels() {{
    document.getElementById("allHotelsSection").scrollIntoView({{ behavior: "smooth" }});
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
                        <button class="remove-btn" onclick="toggleHotelSelection('${{h.code}}')">✕</button>
                    </div>
                    <div class="slot-title">${{h.zh}}</div>
                    <div class="slot-en">${{h.name}}</div>
                </div>
                <div class="slot-stats">
                    <div>最低<strong style="color:${{color}}">${{s.minCash ? sym+s.minCash.toLocaleString() : '無房'}}</strong></div>
                    <div>均價<strong>${{s.avgCash ? sym+s.avgCash.toLocaleString() : '-'}}</strong></div>
                    <div>總計<strong>${{s.totalCash ? sym+s.totalCash.toLocaleString() : '-'}}</strong></div>
                </div>
            </div>`);
        }} else {{
            cards.push(`
            <div class="slot-card empty" onclick="scrollToAllHotels()">
                <div style="font-size:1.3rem;">➕</div>
                <div style="font-weight:600; font-size:0.84rem;">點擊從下方加入第 ${{i+1}} 家飯店</div>
            </div>`);
        }}
    }}
    container.innerHTML = cards.join("");
}}

function renderChart(dates) {{
    document.getElementById("chartTitle").textContent = `📈 所選 ${{selectedCodes.length}} 家飯店每日房價走勢 (${{startDate}} ～ ${{endDate}})`;
    document.getElementById("chartLegend").innerHTML = selectedCodes.map((c, idx) => {{
        const h = hotelMap[c];
        const color = PALETTE[idx % PALETTE.length];
        return `<div class="legend-item"><span class="legend-color" style="background:${{color}}"></span><strong>${{h.zh}}</strong> (${{c}})</div>`;
    }}).join("");

    const svgWrap = document.getElementById("svgChartContainer");
    let maxVal = 0, minVal = Infinity;
    selectedCodes.forEach(c => {{
        dates.forEach(d => {{
            const pair = hotelMap[c].days[d];
            if (pair && pair[0] > 0) {{
                if (pair[0] > maxVal) maxVal = pair[0];
                if (pair[0] < minVal) minVal = pair[0];
            }}
        }});
    }});
    if (!dates.length || maxVal === 0) {{
        svgWrap.innerHTML = `<div style="padding:1.5rem; text-align:center; color:var(--muted);">所選區間暫無房價資料</div>`;
        return;
    }}
    minVal = Math.max(0, Math.floor(minVal * 0.85 / 1000) * 1000);
    maxVal = Math.ceil(maxVal * 1.08 / 1000) * 1000;
    const range = Math.max(1000, maxVal - minVal);
    const firstSym = (hotelMap[selectedCodes[0]] && hotelMap[selectedCodes[0]].sym) || "¥";
    const W = Math.max(820, dates.length * 38 + 80), H = 260;
    const padL = 62, padR = 20, padT = 18, padB = 44;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const xOf = (i) => padL + (dates.length > 1 ? (i / (dates.length - 1)) * plotW : plotW / 2);
    const yOf = (v) => padT + plotH - ((v - minVal) / range) * plotH;

    let gridSvg = "", xLabelsSvg = "", linesSvg = "";
    for (let g = 0; g <= 4; g++) {{
        const val = Math.round(minVal + (range * g) / 4);
        const y = yOf(val);
        gridSvg += `<line x1="${{padL}}" y1="${{y}}" x2="${{W - padR}}" y2="${{y}}" stroke="#1e293b" />`;
        gridSvg += `<text x="${{padL - 6}}" y="${{y + 4}}" fill="#94a3b8" font-size="10.5" text-anchor="end">${{firstSym}}${{(val/1000).toFixed(0)}}k</text>`;
    }}
    dates.forEach((d, i) => {{
        const x = xOf(i);
        const wDay = new Date(d + "T00:00:00").getDay();
        const isSat = wDay === 6;
        if (isSat) gridSvg += `<rect x="${{x - 13}}" y="${{padT}}" width="26" height="${{plotH}}" fill="rgba(244,63,94,0.08)" />`;
        const shortMd = Number(d.slice(5,7)) + "/" + Number(d.slice(8,10));
        xLabelsSvg += `<text x="${{x}}" y="${{H - 22}}" fill="${{isSat ? '#fda4af' : '#94a3b8'}}" font-size="10" text-anchor="middle">${{shortMd}}</text>`;
        xLabelsSvg += `<text x="${{x}}" y="${{H - 8}}" fill="${{isSat ? '#fda4af' : '#64748b'}}" font-size="9.5" text-anchor="middle">${{WEEKDAYS_ZH[wDay].slice(1)}}</text>`;
    }});
    selectedCodes.forEach((c, idx) => {{
        const color = PALETTE[idx % PALETTE.length], h = hotelMap[c], sym = h.sym || "¥", pts = [];
        dates.forEach((d, i) => {{
            const pair = h.days[d];
            if (pair && pair[0] > 0) pts.push({{ x: xOf(i), y: yOf(pair[0]), val: pair[0], date: d }});
        }});
        if (pts.length > 1) {{
            linesSvg += `<polyline fill="none" stroke="${{color}}" stroke-width="2.3" points="${{pts.map(p=>p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ')}}" />`;
        }}
        pts.forEach(p => {{
            linesSvg += `<circle cx="${{p.x.toFixed(1)}}" cy="${{p.y.toFixed(1)}}" r="3.8" fill="${{color}}" stroke="#0b1120" stroke-width="1.2"><title>${{p.date}} · ${{h.zh}}: ${{sym}}${{p.val.toLocaleString()}}</title></circle>`;
        }});
    }});
    svgWrap.innerHTML = `<svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}">${{gridSvg}}${{xLabelsSvg}}${{linesSvg}}</svg>`;
}}

function renderDailyComparison() {{
    const dates = getDatesForRange(startDate, endDate);
    const filterMode = document.getElementById("WeekendFilter").value;
    document.getElementById("dailyTableTitle").textContent = `📅 所選 ${{selectedCodes.length}} 家飯店每日並排比較 (${{startDate}} ～ ${{endDate}}，共 ${{dates.length}} 晚)`;

    let headHtml = `<tr><th>日期</th><th>星期</th><th>節日/備註</th>`;
    selectedCodes.forEach((c, idx) => {{
        const h = hotelMap[c], color = PALETTE[idx % PALETTE.length];
        headHtml += `<th style="border-top:3px solid ${{color}}">${{h.zh}}<br><small class="mono" style="color:${{color}}">${{c}}</small></th>`;
    }});
    headHtml += `<th>👑 當日最低推薦</th></tr>`;
    document.getElementById("dailyCompThead").innerHTML = headHtml;

    const rowsHtml = [];
    dates.forEach(d => {{
        const wDay = new Date(d + "T00:00:00").getDay();
        const isFriOrSat = (wDay === 5 || wDay === 6);
        const holiday = APP_DATA.holidays[d] || "";
        if (filterMode === "weekend" && !isFriOrSat && !holiday) return;
        if (filterMode === "weekday" && (isFriOrSat || holiday)) return;

        let minPrice = Infinity, minSym = "¥";
        selectedCodes.forEach(c => {{
            const pair = hotelMap[c].days[d];
            if (pair && pair[0] > 0 && pair[0] < minPrice) {{
                minPrice = pair[0];
                minSym = hotelMap[c].sym || "¥";
            }}
        }});

        const cells = [], winners = [];
        selectedCodes.forEach(c => {{
            const h = hotelMap[c], sym = h.sym || "¥", pair = h.days[d] || [-1, -1], cash = pair[0], pts = pair[1];
            const isCheapest = (cash > 0 && cash === minPrice);
            if (isCheapest) winners.push(h.zh);
            const bUrl = makeBookingUrl(c, d);
            if (cash > 0) {{
                const crown = isCheapest ? `<span class="crown-badge">👑最低</span>` : "";
                const ptsHtml = pts > 0 ? `<span class="pts-sub">✨ ${{pts.toLocaleString()}} 點</span>` : "";
                cells.push(`<td class="${{isCheapest ? 'cheapest-cell' : ''}}"><a class="price-link" href="${{bUrl}}" target="_blank"><span class="price-val" style="color:${{isCheapest ? '#34d399' : '#f8fafc'}}">${{sym}}${{cash.toLocaleString()}}</span>${{crown}}${{ptsHtml}}</a></td>`);
            }} else {{
                cells.push(`<td><span style="color:#64748b;">無房</span></td>`);
            }}
        }});

        const noteStr = holiday ? `<span style="color:#fda4af;">${{holiday}}</span>` : (wDay === 6 ? `<span class="sat-badge">🔥 週六</span>` : (wDay === 5 ? `<span style="color:#fcd34d;">週五</span>` : `-`));
        const bestSummary = (minPrice < Infinity) ? `<strong style="color:#34d399;">${{minSym}}${{minPrice.toLocaleString()}}</strong> <small style="color:var(--muted);">(${{winners.join("、")}})</small>` : `-`;
        rowsHtml.push(`<tr class="${{wDay === 6 ? 'sat-row' : ''}}"><td class="mono">${{d}}</td><td class="${{wDay===6||wDay===0?'sat-badge':''}}">${{WEEKDAYS_ZH[wDay]}}</td><td>${{noteStr}}</td>${{cells.join("")}}<td>${{bestSummary}}</td></tr>`);
    }});
    document.getElementById("dailyCompTbody").innerHTML = rowsHtml.join("");
}}

function renderAllHotelsTable() {{
    const dates = getDatesForRange(startDate, endDate);
    const regionVal = document.getElementById("regionFilter").value;
    const q = document.getElementById("hotelSearch").value.trim().toLowerCase();
    const sortMode = document.getElementById("sortSelect").value;

    const enriched = APP_DATA.hotels.map(h => ({{ ...h, summary: computeSummary(h, dates) }})).filter(h => {{
        if (regionVal === "COUNTRY_TW" && h.country !== "TW") return false;
        if (regionVal === "COUNTRY_JP" && h.country !== "JP") return false;
        if (regionVal !== "ALL" && regionVal !== "COUNTRY_TW" && regionVal !== "COUNTRY_JP" && h.region !== regionVal) return false;
        if (q && !(`${{h.code}} ${{h.name}} ${{h.zh}} ${{h.region}}`.toLowerCase().includes(q))) return false;
        return true;
    }});

    enriched.sort((a, b) => {{
        const sa = a.summary, sb = b.summary;
        if (sortMode === "min_asc") return (sa.minCash || 99999999) - (sb.minCash || 99999999);
        if (sortMode === "avg_asc") return (sa.avgCash || 99999999) - (sb.avgCash || 99999999);
        if (sortMode === "total_asc") return (sa.totalCash || 999999999) - (sb.totalCash || 999999999);
        if (sortMode === "pts_asc") return (sa.minPts || 99999999) - (sb.minPts || 99999999);
        return 0;
    }});

    document.getElementById("overviewTitle").textContent = `🗾 日本＆台灣萬豪全飯店 (${{startDate}} ～ ${{endDate}}) 房價總覽（共 ${{enriched.length}} 家）`;
    document.getElementById("allHotelsTbody").innerHTML = enriched.map(h => {{
        const isSel = selectedCodes.includes(h.code), sym = h.sym || "¥", s = h.summary;
        const btnTxt = isSel ? `✓ 已選 (#${{selectedCodes.indexOf(h.code)+1}})` : `＋ 比較`;
        return `<tr>
            <td><button class="pick-btn ${{isSel ? 'selected' : ''}}" onclick="toggleHotelSelection('${{h.code}}')">${{btnTxt}}</button></td>
            <td style="font-size:0.8rem; color:var(--muted);">${{h.region}}</td>
            <td class="mono" style="font-weight:700; color:var(--accent);">${{h.code}}</td>
            <td><div style="font-weight:700;">${{h.zh}}</div><div style="font-size:0.74rem; color:var(--muted);">${{h.name}}</div></td>
            <td class="price-val" style="color:${{s.minCash ? '#34d399' : '#64748b'}}">${{s.minCash ? sym+s.minCash.toLocaleString() : '無房'}}</td>
            <td class="price-val">${{s.avgCash ? sym+s.avgCash.toLocaleString() : '-'}}</td>
            <td class="price-val" style="color:${{s.maxCash ? '#fda4af' : '#64748b'}}">${{s.maxCash ? sym+s.maxCash.toLocaleString() : '-'}}</td>
            <td class="price-val" style="color:var(--accent);">${{s.totalCash ? sym+s.totalCash.toLocaleString() : '-'}}</td>
            <td>${{s.availDays}}/${{dates.length}}晚</td>
            <td style="color:${{s.minPts ? 'var(--amber)' : '#64748b'}}">${{s.minPts ? s.minPts.toLocaleString()+' pts' : '-'}}</td>
        </tr>`;
    }}).join("");
}}

function exportMarkdownReport() {{
    const dates = getDatesForRange(startDate, endDate);
    const lines = [
        `# 🇯🇵🇹🇼 日台萬豪飯店 (${{startDate}} ～ ${{endDate}}) 每日價格比較報告`,
        `- **比較飯店**：${{selectedCodes.map(c => `${{hotelMap[c].zh}} (${{c}})`).join("、")}}`,
        ``,
        `| 日期 | 星期 | ${{selectedCodes.map(c => hotelMap[c].zh).join(" | ")}} | 當日最低 |`,
        `| :---: | :---: | ${{selectedCodes.map(()=>":---:").join(" | ")}} | :---: |`
    ];
    dates.forEach(d => {{
        const wTxt = WEEKDAYS_ZH[new Date(d + "T00:00:00").getDay()];
        let minP = Infinity, minSym = "¥";
        selectedCodes.forEach(c => {{
            const pair = hotelMap[c].days[d];
            if (pair && pair[0] > 0 && pair[0] < minP) {{
                minP = pair[0];
                minSym = hotelMap[c].sym || "¥";
            }}
        }});
        const cells = selectedCodes.map(c => {{
            const sym = hotelMap[c].sym || "¥";
            const pair = hotelMap[c].days[d] || [-1, -1];
            return pair[0] > 0 ? (pair[0] === minP ? `**${{sym}}${{pair[0].toLocaleString()}}**👑` : `${{sym}}${{pair[0].toLocaleString()}}`) : "無房";
        }});
        lines.push(`| ${{d}} | ${{wTxt}} | ${{cells.join(" | ")}} | ${{minP < Infinity ? minSym+minP.toLocaleString() : '-'}} |`);
    }});
    const nl = String.fromCharCode(10);
    const blob = new Blob([lines.join(nl)], {{ type: "text/markdown;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `萬豪五館比較_${{startDate}}_to_${{endDate}}.md`;
    a.click();
}}

function renderAll() {{
    const dates = getDatesForRange(startDate, endDate);
    document.getElementById("nightsBadge").textContent = `共 ${{dates.length}} 晚`;
    renderSlots(dates);
    renderChart(dates);
    renderDailyComparison();
    renderAllHotelsTable();
}}

bootData();
</script>
</body>
</html>"""

    embed_path = base_dir / "日本萬豪_GoogleSites內嵌版.html"
    embed_path.write_text(html_doc, encoding="utf-8")
    print(f"✅ 已修復並更新 Google Sites 內嵌版（共收錄 {len(compact_hotels)} 家日台萬豪飯店）：{embed_path}")


if __name__ == "__main__":
    main()
