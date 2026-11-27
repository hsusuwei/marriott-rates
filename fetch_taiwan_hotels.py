"""
平行抓取 USTATZ 上全台灣所有萬豪體系 (Marriott Bonvoy) 飯店（共 26 家）
並與日本萬豪快取整合儲存至 marriott_japan_cache.json
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import html as html_lib
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TAIWAN_INDEX_URL = "https://www.ustatz.com/hotelGroups/Taiwan"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

RECORD_PATTERN = re.compile(
    r'eachObj=\{\s*hotelname:\s*"([^"]*)",\s*checkin:\s*"([^"]*)",\s*'
    r'awardPoints:\s*"([^"]*)",\s*currency:\s*"([^"]*)",\s*'
    r'cash:\s*"([^"]*)",\s*bookingUrl:\s*"([^"]*)"',
    re.DOTALL,
)


def get_taiwan_marriott_list() -> list[dict]:
    req = urllib.request.Request(TAIWAN_INDEX_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        page_html = resp.read().decode("utf-8", errors="ignore")

    links = re.findall(
        r"/hotelGroups/Taiwan/marriott\?hotelcode=([^&\"']+)&(?:amp;)?hotelname=([^\"'>]+)",
        page_html,
    )
    unique = {}
    for code, raw_name in links:
        code = code.strip()
        name = html_lib.unescape(raw_name).strip()
        if code == "TPESC" and name == "Suz":
            name = "Suz & Catorze Taipei, a Tribute Portfolio Hotel"
        if code not in unique or len(name) > len(unique[code]):
            unique[code] = name

    return [
        {"code": c, "name": n}
        for c, n in sorted(unique.items(), key=lambda x: x[1])
    ]


def fetch_single_hotel(
    hotel: dict,
    max_attempts: int = 3,
    timeout: int = 30,
    backoff_base: float = 1.5,
) -> tuple[str, dict]:
    code = hotel["code"]
    name = hotel["name"]
    url = (
        "https://www.ustatz.com/hotelGroups/Taiwan/marriott?"
        + urllib.parse.urlencode({"hotelcode": code, "hotelname": name})
    )
    for attempt in range(max_attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")

            if "eachObj" not in html_text:
                raise ValueError("Invalid or incomplete HTML response (missing eachObj)")

            days = {}
            currency = "TWD"
            for m in RECORD_PATTERN.finditer(html_text):
                _, checkin, pts_str, curr, cash_str, _ = m.groups()
                currency = curr or "TWD"
                c_val = int(round(float(cash_str))) if float(cash_str) > 0 else -1
                p_val = int(round(float(pts_str))) if float(pts_str) > 0 else -1
                days[checkin] = [c_val, p_val]

            return code, {
                "code": code,
                "name": name,
                "country": "TW",
                "currency": currency,
                "days": days,
            }
        except Exception as e:
            if attempt == max_attempts - 1:
                return code, {
                    "code": code,
                    "name": name,
                    "country": "TW",
                    "currency": "TWD",
                    "days": {},
                    "error": str(e),
                }
            time.sleep(backoff_base * (attempt + 1))
    return code, {"code": code, "name": name, "country": "TW", "currency": "TWD", "days": {}}


def main() -> None:
    t0 = time.time()
    base_dir = Path(__file__).resolve().parent
    tw_cache_path = base_dir / "marriott_taiwan_cache.json"
    jp_cache_path = base_dir / "marriott_japan_cache.json"

    old_tw_cache: dict = {}
    if tw_cache_path.exists():
        try:
            old_tw_cache = json.loads(tw_cache_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ 讀取台灣舊快取失敗，將重新建立：{e}")

    tw_hotels = get_taiwan_marriott_list()
    print(f"📋 共找到 {len(tw_hotels)} 家台灣萬豪集團飯店，開始穩健平行抓取 (workers=6)...")

    tw_data = {}
    done_count = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_single_hotel, h, 3, 30, 1.5): h for h in tw_hotels}
        for fut in as_completed(futures):
            code, data = fut.result()
            tw_data[code] = data
            done_count += 1
            if done_count % 10 == 0 or done_count == len(tw_hotels):
                err_so_far = sum(1 for v in tw_data.values() if "error" in v)
                print(
                    f"  ⏳ 台灣萬豪進度: {done_count}/{len(tw_hotels)} ({time.time() - t0:.1f}s, 暫時失敗: {err_so_far})"
                )

    failed_hotels = [h for h in tw_hotels if "error" in tw_data.get(h["code"], {})]
    recovered_count = 0
    if failed_hotels:
        print(f"🔄 第一輪有 {len(failed_hotels)} 家台灣飯店逾時，等待 2 秒後啟動低併發補抓 (workers=2)...")
        time.sleep(2.0)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(fetch_single_hotel, h, 3, 40, 2.5): h
                for h in failed_hotels
            }
            for fut in as_completed(futures):
                code, data = fut.result()
                if "error" not in data:
                    tw_data[code] = data
                    recovered_count += 1

    fallback_count = 0
    final_failed: list[tuple[str, str, str]] = []
    for code, data in list(tw_data.items()):
        if "error" in data:
            err_msg = data["error"]
            prev = old_tw_cache.get(code)
            if prev and prev.get("days"):
                tw_data[code] = prev
                fallback_count += 1
                print(f"  ⚠️ [{code}] {data['name']} 補抓仍失敗 ({err_msg})，已保留舊快取有效房價。")
            else:
                final_failed.append((code, data["name"], err_msg))
                print(f"  ❌ [{code}] {data['name']} 抓取失敗且無舊快取可用：{err_msg}")

    tw_cache_path.write_text(json.dumps(tw_data, ensure_ascii=False), encoding="utf-8")

    # 合併至 marriott_japan_cache.json 讓全系統同時擁有日本 109 家 + 台灣 26 家 (共 135 家)
    merged_data = {}
    if jp_cache_path.exists():
        merged_data = json.loads(jp_cache_path.read_text(encoding="utf-8"))
        for k, v in merged_data.items():
            if "country" not in v:
                v["country"] = "JP"
            if "currency" not in v:
                v["currency"] = "JPY"

    merged_data.update(tw_data)
    jp_cache_path.write_text(json.dumps(merged_data, ensure_ascii=False), encoding="utf-8")
    ok_tw = len(tw_hotels) - len(final_failed) - fallback_count
    print(
        f"✅ 台灣萬豪抓取完成！耗時 {time.time() - t0:.1f} 秒｜成功更新: {ok_tw}/{len(tw_hotels)} 家"
        f"（含第二輪補抓成功 {recovered_count} 家、舊快取保護 {fallback_count} 家、無資料 {len(final_failed)} 家）"
    )
    print(f"✅ 目前已合併收錄共 {len(merged_data)} 家萬豪飯店。")


if __name__ == "__main__":
    main()
