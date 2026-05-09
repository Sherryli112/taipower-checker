# 水電查詢日報 - 台電停電 + 台水停水自動通知

每天自動查詢台電計劃停電與台水施工停水公告，比對指定地址，依規則寄送通知信。
無需伺服器，運行於 GitHub Actions（免費）。

---

## 功能

- 每天台灣時間 00:00 自動執行
- 同時查詢：
  - **台電**：指定地址當天及未來 7 天的計劃停電（支援全台 24 個區處）
  - **台水**：臺北自來水事業處施工停水 RSS 公告（適用台北市、新北市永和/中和/新店/三重/汐止）
- 發信規則：
  - **週一**：固定發信，無論有無停電停水（週報）
  - **其餘六天**：查詢到停電或停水時才發信（即時警示）
- 單封信件同時涵蓋台電與台水兩項資訊

---

## 設定步驟

### 1. 取得 Gmail 應用程式密碼

1. 登入 Gmail → 右上角頭像 → **管理 Google 帳戶**
2. 左側選「**安全性**」→ 確認已開啟「兩步驟驗證」
3. 搜尋「**應用程式密碼**」→ 建立新密碼（名稱隨意，如「水電查詢」）
4. 複製產生的 16 字密碼

### 2. Fork 或 Clone 這個 repo 到你的 GitHub

### 3. 設定 GitHub Variables 和 Secrets

進入 repo → **Settings → Secrets and variables → Actions**

**Variables 分頁**（點 New repository variable）：

| 名稱 | 說明 | 範例 |
|------|------|------|
| `TARGET_ADDRESS` | 要監控的地址 | `新北市永和區XX路XX號` |
| `RECIPIENT_EMAIL` | 收件信箱 | `yourname@gmail.com` |
| `CHECK_DAYS` | 查詢未來幾天（預設 7） | `7` |

**Secrets 分頁**（點 New repository secret）：

| 名稱 | 說明 |
|------|------|
| `GMAIL_USER` | 寄件 Gmail 帳號 |
| `GMAIL_APP_PASSWORD` | 步驟 1 取得的應用程式密碼 |

> 發信和收信可以設定為同一個 Gmail 信箱。

### 4. 確認 Actions 已啟用

repo → **Actions** 分頁 → 若看到提示請點「I understand my workflows, go ahead and enable them」

---

## 手動測試

repo → **Actions** → 左側「水電查詢日報」→ 右側「**Run workflow**」→「Run workflow」

幾秒後即可收到測試信。

---

## 修改設定

| 想改的東西 | 去哪裡改 |
|-----------|---------|
| 監控地址 | GitHub → Settings → Variables → `TARGET_ADDRESS` |
| 收件信箱 | GitHub → Settings → Variables → `RECIPIENT_EMAIL` |
| 查詢天數 | GitHub → Settings → Variables → `CHECK_DAYS` |
| 發信時間 | `.github/workflows/check_outage.yml` 的 `cron` 行 |

### 修改發信時間

編輯 `.github/workflows/check_outage.yml`：

```yaml
- cron: '0 16 * * *'
```

| 台灣時間 | cron 設定 |
|---------|-----------|
| 每天 00:00 | `'0 16 * * *'` |
| 每天 07:00 | `'59 22 * * *'` |
| 每天 08:00 | `'0 0 * * *'` |

> cron 使用 UTC 時間，台灣（UTC+8）需減去 8 小時。

---

## 台水適用範圍說明

台水部分使用**臺北自來水事業處** RSS，適用地區為：
- 台北市（全區）
- 新北市：永和區、中和區、新店區、三重區、汐止區（部分里）

其餘新北市地區及台灣其他縣市由**台灣自來水公司**負責，目前不在查詢範圍內。

---

## 資料來源

- [台電計劃性工作停電公告](https://www.taipower.com.tw/2289/2406/2420/2421/11934/)
- [臺北自來水事業處施工停水公告](https://www.water.gov.taipei/Content_List.aspx?n=4D250114FCEAF4CE)
