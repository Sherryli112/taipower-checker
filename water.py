#!/usr/bin/env python3
"""
臺北自來水事業處 施工停水公告查詢
適用範圍：台北市、新北市三重/新店/永和/中和/汐止部分地區
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import requests

RSS_URL = "https://webs.water.gov.taipei/apps/StopWaterRSS"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UtilityChecker/1.0)"}


def fetch_water_notices(district: str | None, road: str | None, check_days: int = 7) -> list[dict]:
    """從臺北自來水事業處 RSS 取得近期施工停水公告，回傳符合地址的項目。"""
    try:
        resp = requests.get(RSS_URL, headers=_HEADERS, timeout=15)
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"[台水] 抓取失敗: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[台水] XML 解析失敗: {e}")
        return []

    items = root.findall(".//item")
    cutoff = datetime.now(timezone.utc) - timedelta(days=check_days)
    matches = []

    for item in items:
        title   = (item.findtext("title")   or "").strip()
        link    = (item.findtext("link")    or "").strip()
        pub_str = (item.findtext("pubDate") or "").strip()

        if pub_str:
            try:
                if parsedate_to_datetime(pub_str) < cutoff:
                    continue
            except Exception:
                pass

        if _matches(title, district, road):
            matches.append({"title": title, "link": link, "pub_date": pub_str})

    print(f"[台水] RSS 共 {len(items)} 筆，符合 {len(matches)} 筆")
    return matches


def _matches(text: str, district: str | None, road: str | None) -> bool:
    if district and road:
        return district in text and road in text
    if district:
        return district in text
    if road:
        return road in text
    return False
