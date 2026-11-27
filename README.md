# 🇯🇵 日本 ＆ 🇹🇼 台灣萬豪 (Marriott Bonvoy) 全 135 家飯店房價與點數比較系統

🌐 **線上互動比價網站**：https://hsusuwei.github.io/marriott-rates/

## 功能特色
- 收錄 **日本 109 家** ＋ **台灣 26 家**（共 **135 家**）萬豪體系飯店整年度每日現金價與點數資料（資料來源：[USTATZ 日本](https://www.ustatz.com/hotelGroups/Japan) ＆ [USTATZ 台灣](https://www.ustatz.com/hotelGroups/Taiwan)）。
- 支援自選**入住／退房日期區間**、地區篩選、關鍵字搜尋，以及**最多 5 家飯店逐日並排比價**與價格走勢折線圖。
- 透過 **GitHub Actions** 於每日台灣時間早上 **06:00** 自動更新最新房價並重新發佈網站（亦可於 Actions 頁面手動觸發 `Daily Update Japan & Taiwan Marriott Rates`）。

## 本機手動更新方式
```bash
python update_all.py
```
