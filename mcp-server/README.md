# Arch2 MCP Server

把 Arch1 的查詢能力包成 MCP tool,供 Open WebUI 連接,讓 Claude 能在對話中查訂單/庫存資料。

這是 Arch2 設計裡的「工具層」。職責單一:**拿到結構化資料**,不做語意判斷、不繪圖。聚合運算在 Arch1 端完成,這層只轉手。

## 結構

```
arch2-mcp-server/
├── app/
│   ├── server.py         # MCP server 主程式，定義 4 個 tool
│   ├── arch1_client.py   # 所有對 Arch1 的 HTTP 呼叫集中於此
│   └── __init__.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 提供的 tool

| tool | 用途 | 對應 Arch1 端點 |
|---|---|---|
| `get_failure_rate` | 區間訂單失敗率 | `/orders/failure-rate` |
| `get_failure_breakdown` | 失敗環節/原因分組 | `/orders/failure-breakdown` |
| `get_order_status` | 訂單狀態分布 | `/orders/status` |
| `get_inventory` | 庫存清單 | `/inventory` |

每個 tool 的 docstring 就是給 LLM 看的「何時使用」說明 —— 改 docstring 等於改 LLM 的工具認知。

## 本機跑起來

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 指向你的 Arch1 API（沒填預設 http://arch1-api:8000）
export ARCH1_BASE_URL=http://localhost:8000

python -m app.server
```

啟動後 MCP server 以 streamable HTTP 監聽 `0.0.0.0:8000`。

## 接到 Open WebUI

在 Open WebUI:Admin Settings → External Tools → 新增,Type 選 **MCP (Streamable HTTP)**,URL 填 MCP server 的位址(k8s 裡是它的 Service,如 `http://arch2-mcp:8000`)。

> 注意:Type 一定選 MCP (Streamable HTTP),不要選 OpenAI —— 選錯會讓 UI 卡住。

## 環境變數

| 變數 | 說明 | 預設 |
|---|---|---|
| `ARCH1_BASE_URL` | Arch1 API 位址 | `http://arch1-api:8000` |

## 設計筆記

- `arch1_client.py` 把 HTTP 呼叫集中一處,Arch1 端點變動只改這檔。
- Arch1 掛掉時 tool 回傳 `{"error": "..."}` 而非崩潰,讓對話能顯示清楚原因(呼應狀態機的 failed 帶 reason)。
- 這版只「查資料」。繪圖層是另一個獨立職責,之後再加。

## 下一步

- 加 Dockerfile build CI(GitHub Actions → GHCR)。
- 寫 k8s manifest(Deployment + Service),併入既有的 k8s-arch2。
- 補繪圖層 tool(把資料轉成圖)。
