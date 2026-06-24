# Arch1 API

訂單/庫存資料與聚合分析 API。Arch2 的資料來源 —— MCP server 透過這些端點取數。

FastAPI + SQLAlchemy,預設 SQLite,可無痛切換 MySQL/MSSQL。

## 結構

```
arch1-api/
├── app/
│   ├── main.py          # FastAPI + 聚合端點
│   ├── models.py        # 資料表（products/inventory/orders/order_status_log）
│   ├── database.py      # 連線設定（SQLite/MySQL 切換）
│   ├── seed.py          # 種子資料（10 筆訂單）
│   └── __init__.py
├── requirements.txt
├── Dockerfile
├── entrypoint.sh
├── docker-compose.yml          # SQLite 版（單服務）
└── docker-compose.mysql.yml    # MySQL 版（雙服務）
```

## 端點

對齊 Arch2 MCP server 的 `arch1_client.py`：

| 端點 | 說明 |
|---|---|
| `GET /health` | 健康檢查 |
| `GET /inventory` | 庫存清單（含缺貨標示） |
| `GET /orders/status` | 訂單狀態分布，可 `?status=failed` 過濾 |
| `GET /orders/failure-rate` | 失敗率，可 `?start=&end=` 帶區間 |
| `GET /orders/failure-breakdown` | 失敗環節分組（payment/inventory…） |

## 資料表設計

| 表 | 用途 |
|---|---|
| `products` | 物品主檔 |
| `inventory` | 庫存（與物品分開，利於歷史追蹤） |
| `orders` | 訂單主檔（當前狀態） |
| `order_status_log` | 狀態變更歷程 —— **失敗率/失敗處分析的地基** |

關鍵設計：`order_status_log` 記錄每次狀態變更與 `reason`，所以訂單失敗後查得出「卡在哪個環節、為什麼」。只存當前狀態的話這分析做不出來。

## 種子資料

10 筆訂單，狀態刻意分布：5 done / 2 shipped / 3 failed。3 筆失敗分屬不同環節（2 payment、1 inventory），讓失敗率與失敗處分析有東西可算。

## 快速開始（SQLite 版）

```bash
docker compose up -d
```

啟動時會自動 seed（冪等，重啟不會重複累積），然後開在 8000。

測試：

```bash
curl http://localhost:8000/orders/failure-rate
# {"total":10,"failed":3,"failure_rate":0.3,...}
```

互動式 API 文件（FastAPI 自動生成）：開 <http://localhost:8000/docs>

## 切換到 MySQL

```bash
docker compose -f docker-compose.mysql.yml up -d
```

差別只在 `DATABASE_URL` 連線字串，程式碼一行都不用改。MySQL 版會等 DB 健康才啟動 API。

## 本機直接跑（不用 Docker）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # 塞種子資料
uvicorn app.main:app --reload
```

## 接到 Arch2

Arch2 的 MCP server 用 `ARCH1_BASE_URL` 指到這個 API。同一個 docker 網路裡用服務名：

```
ARCH1_BASE_URL=http://arch1-api:8000
```

這樣整條鏈路就通了：Open WebUI → MCP server → Arch1 → DB。
