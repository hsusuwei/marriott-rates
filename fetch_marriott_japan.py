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

INDEX_URL = "https://www.ustatz.com/hotelGroups/Japan"
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


def get_marriott_hotel_list() -> list[dict]:
    req = urllib.request.Request(INDEX_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        page_html = resp.read().decode("utf-8", errors="ignore")

    links = re.findall(
        r"/hotelGroups/Japan/marriott\?hotelcode=([^&\"']+)&(?:amp;)?hotelname=([^\"'>]+)",
        page_html,
    )
    unique = {}
    for code, raw_name in links:
        unique[code] = html_lib.unescape(raw_name).strip()

    hotels = [
        {"code": c, "name": n}
        for c, n in sorted(unique.items(), key=lambda x: x[1])
    ]
    return hotels


def fetch_single_hotel(
    hotel: dict,
    max_attempts: int = 3,
    timeout: int = 30,
    backoff_base: float = 1.5,
) -> tuple[str, dict]:
    code = hotel["code"]
    name = hotel["name"]
    url = (
        "https://www.ustatz.com/hotelGroups/Japan/marriott?"
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
            currency = "JPY"
            for m in RECORD_PATTERN.finditer(html_text):
                _, checkin, pts_str, curr, cash_str, _ = m.groups()
                currency = curr or "JPY"
                c_val = int(round(float(cash_str))) if float(cash_str) > 0 else -1
                p_val = int(round(float(pts_str))) if float(pts_str) > 0 else -1
                days[checkin] = [c_val, p_val]

            return code, {
                "code": code,
                "name": name,
                "country": "JP",
                "currency": currency,
                "days": days,
            }
        except Exception as e:
            if attempt == max_attempts - 1:
                return code, {
                    "code": code,
                    "name": name,
                    "country": "JP",
                    "currency": "JPY",
                    "days": {},
                    "error": str(e),
                }
            time.sleep(backoff_base * (attempt + 1))
    return code, {"code": code, "name": name, "country": "JP", "currency": "JPY", "days": {}}


def main() -> None:
    t0 = time.time()
    cache_path = Path(__file__).resolve().parent / "marriott_japan_cache.json"
    old_cache: dict = {}
    if cache_path.exists():
        try:
            old_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ 讀取舊快取失敗，將重新建立：{e}")

    hotels = get_marriott_hotel_list()
    print(f"📋 共找到 {len(hotels)} 家日本萬豪集團飯店，開始穩健平行抓取 (workers=6)...")

    all_data = {}
    done_count = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_single_hotel, h, 3, 30, 1.5): h for h in hotels}
        for fut in as_completed(futures):
            code, data = fut.result()
            all_data[code] = data
            done_count += 1
            if done_count % 20 == 0 or done_count == len(hotels):
                err_so_far = sum(1 for v in all_data.values() if "error" in v)
                print(
                    f"  ⏳ 進度: {done_count}/{len(hotels)} ({time.time() - t0:.1f}s, 暫時失敗: {err_so_far})"
                )

    failed_hotels = [h for h in hotels if "error" in all_data.get(h["code"], {})]
    recovered_count = 0
    if failed_hotels:
        print(f"🔄 第一輪有 {len(failed_hotels)} 家日本飯店逾時，等待 2 秒後啟動低併發補抓 (workers=2)...")
        time.sleep(2.0)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(fetch_single_hotel, h, 3, 40, 2.5): h
                for h in failed_hotels
            }
            for fut in as_completed(futures):
                code, data = fut.result()
                if "error" not in data:
                    all_data[code] = data
                    recovered_count += 1

    fallback_count = 0
    final_failed: list[tuple[str, str, str]] = []
    for code, data in list(all_data.items()):
        if "error" in data:
            err_msg = data["error"]
            prev = old_cache.get(code)
            if prev and prev.get("days"):
                all_data[code] = prev
                fallback_count += 1
                print(f"  ⚠️ [{code}] {data['name']} 補抓仍失敗 ({err_msg})，已保留舊快取有效房價。")
            else:
                final_failed.append((code, data["name"], err_msg))
                print(f"  ❌ [{code}] {data['name']} 抓取失敗且無舊快取可用：{err_msg}")

    # 保留既有快取中的台灣飯店資料（避免單獨執行本檔時洗掉台灣資料）
    for k, v in old_cache.items():
        if k not in all_data and v.get("country") == "TW":
            all_data[k] = v

    cache_path.write_text(
        json.dumps(all_data, ensure_ascii=False), encoding="utf-8"
    )
    ok_jp = len(hotels) - len(final_failed) - fallback_count
    print(
        f"✅ 日本萬豪抓取完成！耗時 {time.time() - t0:.1f} 秒｜成功更新: {ok_jp}/{len(hotels)} 家"
        f"（含第二輪補抓成功 {recovered_count} 家、舊快取保護 {fallback_count} 家、無資料 {len(final_failed)} 家）"
        f"｜快取大小: {cache_path.stat().st_size / 1024:.1f} KB"
    )


if __name__ == "__main__":
    main()
