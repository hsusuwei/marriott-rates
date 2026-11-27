"""
一鍵更新日本 (109家) ＋ 台灣 (26家) 萬豪全 135 家飯店最新房價與所有報表 (update_all.py)
====================================================================================
執行此腳本會依序自動完成：
1. 重新連線至 ustatz.com 平行抓取全日本 109 家與全台灣 26 家萬豪飯店的最新每日房價與點數
2. 重新產生完整版 Markdown 報告與互動式 HTML 網頁 (build_marriott_comparator.py)
3. 重新產生 Google Sites 專用內嵌版 HTML (build_google_sites_embed.py)
"""

from pathlib import Path
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    py = sys.executable

    print("🚀 [步驟 1/4] 正在從 USTATZ 抓取全日本 109 家萬豪飯店最新房價資料...")
    subprocess.run([py, str(base_dir / "fetch_marriott_japan.py")], check=True)

    print("\n🇹🇼 [步驟 2/4] 正在從 USTATZ 抓取全台灣 26 家萬豪飯店最新房價資料並合併...")
    subprocess.run([py, str(base_dir / "fetch_taiwan_hotels.py")], check=True)

    print("\n📊 [步驟 3/4] 正在更新 Markdown 報告與互動式 HTML 網頁...")
    subprocess.run(
        [py, str(base_dir / "build_marriott_comparator.py"), "--no-browser"],
        check=True,
    )

    html_src = base_dir / "日本萬豪全飯店_整月房價與五館比較.html"
    index_dst = base_dir / "index.html"
    if html_src.exists():
        shutil.copyfile(html_src, index_dst)
        print(f"🏠 已同步產生網站首頁：{index_dst}")

    print("\n🌐 [步驟 4/4] 正在更新 Google Sites 內嵌版 HTML...")
    subprocess.run([py, str(base_dir / "build_google_sites_embed.py")], check=True)

    print("\n🎉 全部更新完成！日本 109 家 + 台灣 26 家（共 135 家）最新報告與網頁皆已重新產生。")


if __name__ == "__main__":
    main()
