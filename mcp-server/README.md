# Arch2 MCP Server

把 Arch1 的查詢能力包成 MCP tool，供 Open WebUI 連接，讓 Claude 能在對話中查訂單/庫存資料**並產出統計圖表**。

這是 Arch2 設計裡的「工具層 + 繪圖層」。職責：取數（查 Arch1）+ 繪圖（把數據畫成圖）。聚合運算在 Arch1 端完成，這層只轉手與視覺化。

## 結構

```
mcp-server/
├── app/
│   ├── server.py         # MCP server 主程式：取數 tool + 繪圖 tool + 圖檔路由
│   ├── arch1_client.py   # 所有對 Arch1 的 HTTP 呼叫集中於此
│   ├── charts.py         # 繪圖邏輯（matplotlib），不碰 MCP
│   ├── chart_tool.py     # 把繪圖包成可回傳 URL 的函式
│   └── __init__.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 提供的 tool

### 取數 tool（查 Arch1）

| tool | 用途 | 對應 Arch1 端點 |
|---|---|---|
| `get_failure_rate` | 區間訂單失敗率 | `/orders/failure-rate` |
| `get_failure_breakdown` | 失敗環節/原因分組 | `/orders/failure-breakdown` |
| `get_order_status` | 訂單狀態分布 | `/orders/status` |
| `get_inventory` | 庫存清單 | `/inventory` |

### 繪圖 tool（數據圖表化）

| tool | 用途 |
|---|---|
| `make_chart` | 把數據畫成統計圖表，回傳圖片 URL |

每個 tool 的 docstring 就是給 LLM 看的「何時使用」說明 —— 改 docstring 等於改 LLM 的工具認知。

## 為什麼需要繪圖層

直接叫 Claude 畫圖，它只會回「文字表格 / 程式碼 / 給你資料自己做」——因為 API 版的 Claude 會寫出畫圖的指令，但 Open WebUI 沒有執行/渲染環境，變不成真圖。繪圖層補上這塊：

1. 繪圖 tool 用 matplotlib 把數據畫成 PNG，存檔。
2. MCP server 開一個 `/charts/{filename}` HTTP 路由提供圖檔。
3. tool 回傳**圖片 URL**（不是 base64 — Open WebUI 顯示 base64 圖會失敗），Claude 用 markdown `![](url)` 顯示。

支援圖型：`pie`(圓餅,比例) / `bar`(長條,數量) / `hbar`(水平長條,環節) / `line`(折線,趨勢)。

## 環境變數

| 變數 | 說明 | 本機值 |
|---|---|---|
| `ARCH1_BASE_URL` | Arch1 API 位址 | `http://localhost:8001` |
| `PUBLIC_BASE_URL` | 組圖片 URL 的基底，要是 Open WebUI 連得到 MCP server 的位址 | `http://host.docker.internal:8000` |
| `CHART_DIR` | 圖檔存放目錄 | `/tmp/charts`（預設） |

`PUBLIC_BASE_URL` 很關鍵：填「Open WebUI 連得到 MCP server 的位址」。
- 本機（Open WebUI 在容器、MCP 在主機）：`http://host.docker.internal:8000`
- k8s（都在叢集）：`http://<mcp-service名>:8000`

## 本機跑起來

```bash
cd mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 在 mcp-server/ 這層執行（不是進到 app/ 裡）
PUBLIC_BASE_URL=http://host.docker.internal:8000 \
ARCH1_BASE_URL=http://localhost:8001 \
python3 -m app.server
```

啟動後 MCP server 以 streamable HTTP 監聽 `0.0.0.0:8000`。

> 重點一：監聽要綁 `0.0.0.0` 不能綁 `127.0.0.1`，否則 Open WebUI 容器連不進來（已在 `FastMCP(..., host="0.0.0.0", port=8000)` 設好）。
> 重點二：要在 `mcp-server/` 這層用 `python3 -m app.server` 啟動，Python 才找得到 `app` 套件。

## 接到 Open WebUI

在 Open WebUI：**管理員設定**（左下角，不是一般使用者的「外掛功能」）→ **External Tools** → 新增：

1. 類型選 **MCP (Streamable HTTP)** — 絕不能選 OpenAPI（選錯 UI 會卡住）。
2. URL 填 `http://host.docker.internal:8000/mcp`（容器連主機用這個特殊名）。
3. 驗證設成 **None**，API 金鑰留空（這個 server 沒做認證）。
4. 儲存。

> 改了 tool（例如加繪圖）後，回這條連線按**重新整理鈕**讓它重抓工具清單，否則 Open WebUI 不會知道有新 tool。

## 怎麼用（在 Open WebUI 對話）

工具會自動觸發。例如：

> 把訂單狀態畫成圓餅圖

流程：Claude 先呼叫 `get_order_status` 拿數據 → 再呼叫 `make_chart` 畫圓餅圖 → 拿到 image_url → markdown 顯示出真圖。

也可以更明確：

> 用長條圖呈現各商品庫存
> 把失敗環節畫成水平長條圖

## 容器化注意：中文字型

matplotlib 預設不支援中文（標籤會變方框）。`charts.py` 已設定用 Noto Sans CJK TC，但**容器裡也要有這個字型**。Dockerfile 加：

```dockerfile
RUN apt-get update && apt-get install -y fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
```

否則容器裡畫出來的中文是方框。

## 設計筆記

- `arch1_client.py` 把 HTTP 呼叫集中一處，Arch1 端點變動只改這檔。
- 取數與繪圖分離：`charts.py` 純繪圖不碰 MCP，方便單獨測試或替換。
- 繪圖層回 URL 而非 base64，繞過 Open WebUI 顯示 base64 圖會失敗的問題。
- 繪圖強制「先查 tool 拿真數據 → 再畫」，避免 Claude 用幻覺數據畫圖。
- Arch1 掛掉時 tool 回 `{"error": "..."}` 而非崩潰，對話能顯示清楚原因。

## 常見踩坑

| 症狀 | 原因 | 解法 |
|---|---|---|
| `No module named 'app'` | 沒在 mcp-server/ 這層執行 / 缺 `__init__.py` | 在對的層用 `python3 -m app.server` |
| `arch1_client is not defined` | `import app.arch1_client` 名字錯 | 改 `from app import arch1_client` |
| 工具列表展不開 | 綁 127.0.0.1 容器連不到 | 改綁 0.0.0.0 |
| 加了 tool 但 Open WebUI 沒看到 | 連線沒重抓 | 按連線的重新整理鈕 |
| 圖顯示不出來 | 回了 base64 / PUBLIC_BASE_URL 填錯 | 回 URL，且 URL 要是 Open WebUI 連得到的位址 |
| 圖的中文變方框 | 容器缺中文字型 | Dockerfile 裝 fonts-noto-cjk |
| port 衝突（404 在 /mcp）| 8000 被 Arch1 佔了 | Arch1 改 8001，MCP 留 8000 |

## 下一步

- 容器化：把 MCP server 放進 compose，跟 Open WebUI、LiteLLM 同網路（用服務名連，不用 host.docker.internal）。
- 上 k8s：寫 Deployment + Service，PUBLIC_BASE_URL 改用 Service 名。
- CI/CD：MCP server 是自建 code，可做 GitHub Actions build image → GitOps 自動部署。
