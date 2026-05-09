#!/usr/bin/env python3
"""
台電計劃停電每日查詢 - 自動發信通知
"""

import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# ── 設定（從環境變數讀取）─────────────────────────────────────────────────────
TARGET_ADDRESS     = os.environ.get("TARGET_ADDRESS")     or "台北市中正區忠孝東路一段1號"
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL")    or "a0979680465@gmail.com"
GMAIL_USER         = os.environ.get("GMAIL_USER")         or ""
GMAIL_APP_PASSWORD = re.sub(r"\s+", "", os.environ.get("GMAIL_APP_PASSWORD") or "")
CHECK_DAYS         = int(os.environ.get("CHECK_DAYS") or "7")

TAIWAN_TZ = ZoneInfo("Asia/Taipei")

# ── 台電各區處公告 URL ──────────────────────────────────────────────────────────
BRANCHES = {
    "d101": ("基隆區處",  "https://service.taipower.com.tw/branch/d101/xcnotice?xsmsid=0M242581316312033070"),
    "d102": ("北市區處",  "https://service.taipower.com.tw/branch/d102/xcnotice?xsmsid=0M242581312773778160"),
    "d103": ("桃園區處",  "https://service.taipower.com.tw/branch/d103/xcnotice?xsmsid=0M242581312675626779"),
    "d104": ("新竹區處",  "https://service.taipower.com.tw/branch/d104/xcnotice?xsmsid=0M242581313964252236"),
    "d105": ("台中區處",  "https://service.taipower.com.tw/branch/d105/xcnotice?xsmsid=0M242581317628413301"),
    "d106": ("彰化區處",  "https://service.taipower.com.tw/branch/d106/xcnotice?xsmsid=0M242581314418510444"),
    "d107": ("嘉義區處",  "https://service.taipower.com.tw/branch/d107/xcnotice?xsmsid=0M242581317006659586"),
    "d108": ("台南區處",  "https://service.taipower.com.tw/branch/d108/xcnotice?xsmsid=0M242581311248677644"),
    "d109": ("高雄區處",  "https://service.taipower.com.tw/branch/d109/xcnotice?xsmsid=0M242581310382588530"),
    "d110": ("屏東區處",  "https://service.taipower.com.tw/branch/d110/xcnotice?xsmsid=0M242581319136855888"),
    "d111": ("台東區處",  "https://service.taipower.com.tw/branch/d111/xcnotice?xsmsid=0M242581313752905496"),
    "d112": ("花蓮區處",  "https://service.taipower.com.tw/branch/d112/xcnotice?xsmsid=0M242581312305799678"),
    "d113": ("宜蘭區處",  "https://service.taipower.com.tw/branch/d113/xcnotice?xsmsid=0M242581316816175510"),
    "d114": ("澎湖區處",  "https://service.taipower.com.tw/branch/d114/xcnotice?xsmsid=0M242581315569736204"),
    "d115": ("北南區處",  "https://service.taipower.com.tw/branch/d115/xcnotice?xsmsid=0M242581317718023029"),
    "d116": ("北北區處",  "https://service.taipower.com.tw/branch/d116/xcnotice?xsmsid=0M242581312941137933"),
    "d117": ("北西區處",  "https://service.taipower.com.tw/branch/d117/xcnotice?xsmsid=0M242581310300276906"),
    "d118": ("南投區處",  "https://service.taipower.com.tw/branch/d118/xcnotice?xsmsid=0M242581317452513865"),
    "d119": ("鳳山區處",  "https://service.taipower.com.tw/branch/d119/xcnotice?xsmsid=0M242581312415567180"),
    "d120": ("雲林區處",  "https://service.taipower.com.tw/branch/d120/xcnotice?xsmsid=0M242581310910082112"),
    "d121": ("新營區處",  "https://service.taipower.com.tw/branch/d121/xcnotice?xsmsid=0M242581311631230866"),
    "d122": ("苗栗區處",  "https://service.taipower.com.tw/branch/d122/xcnotice?xsmsid=0M242581315483543322"),
    "d123": ("金門區處",  "https://service.taipower.com.tw/branch/d123/xcnotice?xsmsid=0M242581316172686774"),
    "d124": ("馬祖區處",  "https://service.taipower.com.tw/branch/d124/xcnotice?xsmsid=0M242581313368873957"),
}

# 縣市 → 負責區處代碼（台北市/台南市/高雄市因範圍大，各由多個區處負責）
CITY_TO_BRANCHES: dict[str, list[str]] = {
    "基隆市": ["d101"],
    "台北市": ["d102", "d115", "d116", "d117"],
    "臺北市": ["d102", "d115", "d116", "d117"],
    "新北市": ["d115", "d116", "d117"],
    "桃園市": ["d103"],
    "新竹市": ["d104"],
    "新竹縣": ["d104"],
    "苗栗縣": ["d122"],
    "台中市": ["d105"],
    "臺中市": ["d105"],
    "南投縣": ["d118"],
    "彰化縣": ["d106"],
    "雲林縣": ["d120"],
    "嘉義市": ["d107"],
    "嘉義縣": ["d107"],
    "台南市": ["d108", "d121"],
    "臺南市": ["d108", "d121"],
    "高雄市": ["d109", "d119"],
    "屏東縣": ["d110"],
    "台東縣": ["d111"],
    "臺東縣": ["d111"],
    "花蓮縣": ["d112"],
    "宜蘭縣": ["d113"],
    "澎湖縣": ["d114"],
    "金門縣": ["d123"],
    "連江縣": ["d124"],
}

_DATE_RE = re.compile(r"(\d{3})年(\d{1,2})月(\d{1,2})日")
_TIME_RE = re.compile(r"自\s*(\d+)時\s*(\d+)分至\s*(\d+)時\s*(\d+)分")


def roc_to_date(roc_year: str, month: str, day: str) -> date:
    return date(int(roc_year) + 1911, int(month), int(day))


def parse_address(address: str) -> tuple[str | None, str | None, str | None]:
    """從台灣地址字串解析出 (縣市, 行政區, 路名)。"""
    cities = list(CITY_TO_BRANCHES.keys())
    city_re = "|".join(re.escape(c) for c in sorted(cities, key=len, reverse=True))
    city_m = re.search(f"({city_re})", address)
    city = city_m.group(1) if city_m else None

    district_m = re.search(r"(?:市|縣)([^\d\s路街巷弄號]+[區鄉鎮])", address)
    district = district_m.group(1) if district_m else None

    road_m = re.search(r"([^\d\s區鄉鎮市縣]+[路街大道])", address)
    road = road_m.group(1) if road_m else None

    return city, district, road


def fetch_branch_outages(branch_code: str) -> list[dict]:
    """抓取指定區處的計劃停電公告，回傳結構化資料。"""
    branch_name, url = BRANCHES[branch_code]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaipowerChecker/1.0)"}

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"[{branch_code}] 抓取失敗: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines() if ln.strip()]

    outages: list[dict] = []
    current_date: date | None = None
    current_outage: dict | None = None

    for line in lines:
        date_m = _DATE_RE.search(line)
        time_m = _TIME_RE.search(line)

        # 日期標題行（不含時間範圍）
        if date_m and not time_m:
            current_date = roc_to_date(date_m.group(1), date_m.group(2), date_m.group(3))
            continue

        # 時間行 → 一筆新的停電記錄
        if time_m and current_date:
            if current_outage:
                outages.append(current_outage)
            current_outage = {
                "branch": branch_name,
                "date": current_date,
                "time": f"{time_m.group(1)}:{time_m.group(2).zfill(2)}–{time_m.group(3)}:{time_m.group(4).zfill(2)}",
                "description": line,
                "locations": [],
            }
            continue

        # 地址行
        if current_outage and any(k in line for k in ("路", "街", "巷", "弄")):
            current_outage["locations"].append(line)

    if current_outage:
        outages.append(current_outage)

    print(f"[{branch_code}] {branch_name}: 找到 {len(outages)} 筆停電記錄")
    return outages


def address_matches(outage: dict, district: str | None, road: str | None) -> bool:
    location_text = " ".join(outage["locations"])
    if district and road:
        return district in location_text and road in location_text
    if district:
        return district in location_text
    if road:
        return road in location_text
    return False


def build_outage_row(o: dict) -> str:
    loc = o["locations"][0] if o["locations"] else "（無地址資訊）"
    if len(loc) > 90:
        loc = loc[:90] + "..."
    return (
        f"<tr>"
        f"<td style='padding:6px 10px'>{o['date'].strftime('%Y/%m/%d')}</td>"
        f"<td style='padding:6px 10px;white-space:nowrap'>{o['time']}</td>"
        f"<td style='padding:6px 10px;white-space:nowrap'>{o['branch']}</td>"
        f"<td style='padding:6px 10px;font-size:12px'>{loc}</td>"
        f"</tr>\n"
    )


def build_table(outages: list[dict]) -> str:
    rows = "".join(build_outage_row(o) for o in outages)
    return (
        "<table border='1' cellpadding='0' cellspacing='0' "
        "style='border-collapse:collapse;width:100%;border-color:#ccc'>\n"
        "<tr style='background:#f0f0f0;font-weight:bold'>"
        "<td style='padding:6px 10px'>日期</td>"
        "<td style='padding:6px 10px'>停電時段</td>"
        "<td style='padding:6px 10px'>所屬區處</td>"
        "<td style='padding:6px 10px'>影響地址（節錄）</td>"
        "</tr>\n"
        f"{rows}</table>"
    )


def build_email(address: str, today_hits: list, upcoming_hits: list, today: date) -> tuple[str, str]:
    if today_hits:
        subject = f"【今日停電警示】{address}"
        status_color = "#c0392b"
        status_text = "今日有計劃停電"
    elif upcoming_hits:
        subject = f"【近期停電預告】{address}"
        status_color = "#e67e22"
        status_text = "近期有計劃停電"
    else:
        subject = f"【今日無停電】{address}"
        status_color = "#27ae60"
        status_text = "近期無計劃停電"

    today_section = (
        f"<h3 style='color:#c0392b'>今日停電通知（{today}）</h3>{build_table(today_hits)}"
        if today_hits
        else f"<p style='color:#27ae60'><strong>今日（{today}）查無計劃停電。</strong></p>"
    )

    upcoming_section = (
        f"<h3 style='color:#e67e22'>未來 {CHECK_DAYS} 天停電預告</h3>{build_table(upcoming_hits)}"
        if upcoming_hits
        else ""
    )

    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:720px;margin:auto;color:#333">
<div style="background:{status_color};color:white;padding:12px 18px;border-radius:4px 4px 0 0">
  <h2 style="margin:0">台電計劃停電查詢報告</h2>
  <p style="margin:4px 0 0">{status_text}</p>
</div>
<div style="border:1px solid #ccc;border-top:none;padding:16px 18px;border-radius:0 0 4px 4px">
  <p><b>監控地址：</b>{address}</p>
  <p><b>查詢日期：</b>{today}（台灣時間）</p>
  <hr style="border:none;border-top:1px solid #eee">
  {today_section}
  {upcoming_section}
  <hr style="border:none;border-top:1px solid #eee;margin-top:20px">
  <p style="font-size:11px;color:#999">
    資料來源：台電計劃性工作停電公告｜
    <a href="https://www.taipower.com.tw/2289/2406/2420/2421/11934/">台電官網</a>
  </p>
</div>
</body></html>"""

    return subject, html


def send_email(subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print(f"信件已寄送至 {RECIPIENT_EMAIL}，主旨：{subject}")


def main() -> None:
    today = datetime.now(TAIWAN_TZ).date()
    check_until = today + timedelta(days=CHECK_DAYS)

    city, district, road = parse_address(TARGET_ADDRESS)
    print(f"地址解析：{TARGET_ADDRESS}")
    print(f"  縣市={city}，行政區={district}，路名={road}")

    if not city:
        raise SystemExit("ERROR：無法從地址解析出縣市，請確認 TARGET_ADDRESS 格式正確。")

    branch_codes = CITY_TO_BRANCHES.get(city, [])
    if not branch_codes:
        raise SystemExit(f"ERROR：找不到 {city} 對應的台電區處。")

    all_outages: list[dict] = []
    for code in branch_codes:
        all_outages.extend(fetch_branch_outages(code))

    print(f"共取得 {len(all_outages)} 筆停電記錄，開始比對地址...")

    today_hits    = [o for o in all_outages if o["date"] == today         and address_matches(o, district, road)]
    upcoming_hits = [o for o in all_outages if today < o["date"] <= check_until and address_matches(o, district, road)]

    print(f"今日符合：{len(today_hits)} 筆 / 近期符合：{len(upcoming_hits)} 筆")

    subject, body = build_email(TARGET_ADDRESS, today_hits, upcoming_hits, today)
    send_email(subject, body)


if __name__ == "__main__":
    import traceback
    print(f"TARGET_ADDRESS  = {TARGET_ADDRESS}")
    print(f"RECIPIENT_EMAIL = {RECIPIENT_EMAIL}")
    print(f"GMAIL_USER      = {GMAIL_USER}")
    print(f"GMAIL_APP_PASSWORD set = {'是' if GMAIL_APP_PASSWORD else '否'}")
    print(f"CHECK_DAYS      = {CHECK_DAYS}")
    print("─" * 60)
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
