# Open WebUI × Claude

用 Docker Compose 在本機架起一個接 Claude 的對話介面。

這個專案把 Open WebUI 跑起來,並直接連到 Anthropic 的 Claude。整個過程大約 10 分鐘。前面設計的工具層與繪圖層先不放,這一版的目標是先有一個能跟 Claude 對話的自架介面。

## 開始前需要準備

- 已安裝 Docker Desktop(macOS),並確認它正在執行。
- 一把 Anthropic API key(格式像 `sk-ant-...`)。沒有的話到 [console.anthropic.com](https://console.anthropic.com) 註冊並建立。
- 提醒:Claude API 按用量付費,建議在 console 設定用量上限,測試時才不會不小心超支。

## 專案檔案

| 檔案 | 用途 |
|------|------|
| `docker-compose.yml` | 定義 Open WebUI 服務怎麼跑 |
| `.env.example` | 環境變數範本(複製成 `.env` 後填值) |
| `.gitignore` | 確保填了 key 的 `.env` 不會被推上 git |

### 各設定的意思

| 設定 | 說明 |
|------|------|
| `OPENAI_API_BASE_URL` | 指向 Anthropic 的 OpenAI 相容端點。Open WebUI 會自動認出這是 Anthropic 並抓取可用模型。 |
| `OPENAI_API_KEY` | 放你的 Anthropic key(透過 `.env` 帶進來)。 |
| `WEBUI_SECRET_KEY` | 加密已儲存設定用。**一旦設定就不要更動**,否則容器重啟後存的連線會解不開。 |
| `ENABLE_OLLAMA_API=false` | 這版不跑本機模型,關掉以免啟動時找不到 Ollama 而報錯。 |
| `ports 3000:8080` | 容器內是 8080,對外開在你電腦的 3000。從 `localhost:3000` 打開。 |

## 快速開始

### 1. 設定環境變數

在專案資料夾裡開終端機,複製範本:

```bash
cp .env.example .env
```

產生一組 `WEBUI_SECRET_KEY`(任選一種):

```bash
openssl rand -hex 32
# 或
python3 -c "import secrets; print(secrets.token_hex(32))"
```

打開 `.env`,把兩個值填好:

```
ANTHROPIC_API_KEY=sk-ant-你的實際key
WEBUI_SECRET_KEY=剛剛產生的那串亂碼
```

### 2. 啟動服務

```bash
docker compose up -d
```

> `-d` 代表在背景執行。第一次會下載映像檔,需要等一兩分鐘。

確認容器有跑起來(狀態顯示 `running` / `Up` 就對了):

```bash
docker compose ps
```

### 3. 開啟介面

瀏覽器前往 <http://localhost:3000>。

第一次進入會要你建立帳號。這個帳號只存在你本機,直接設一組即可(它會自動成為管理員)。

## 確認 Claude 已連上

compose 已經把 Anthropic 連線寫進環境變數,正常情況下登入後在模型選單裡就會看到 Claude 系列模型可選。

如果模型選單裡沒看到 Claude,手動確認一次連線:

1. 點右上角頭像 → **Settings** → **Admin Settings** → **Connections**。
2. 看 OpenAI API 區塊,確認有一條連線:
   - **API Base URL**:`https://api.anthropic.com/v1`
   - **API Key**:你的 `sk-ant-` 開頭金鑰
3. 按旁邊的重新整理／驗證鈕,讓它重新抓模型清單。
4. 回到對話畫面,選一個 Claude 模型,送出一句「你好」測試。

## 如果直連抓不到模型(退路)

Anthropic 的相容端點與標準 OpenAI 格式仍有些差異。多數情況自動偵測沒問題,但萬一你的版本抓不到模型或對話報錯,最穩的解法是在中間加一個輕量轉接層 **LiteLLM**,由它統一翻譯格式。

作法是把 compose 改成兩個服務,Open WebUI 不再直連 Anthropic,改成連 LiteLLM:

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    # 需另備一個 litellm_config.yaml 列出要用的 Claude 模型

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    environment:
      - OPENAI_API_BASE_URL=http://litellm:4000/v1
      - OPENAI_API_KEY=dummy
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
```

> 需要這個完整版的話再說,我把 `litellm_config.yaml` 與完整 compose 一起給你。先用直連試,通常就夠了。

## 日常操作指令

| 想做的事 | 指令 |
|----------|------|
| 啟動(背景執行) | `docker compose up -d` |
| 看運行狀態 | `docker compose ps` |
| 看即時日誌(除錯用) | `docker compose logs -f open-webui` |
| 停止但保留資料 | `docker compose down` |
| 重啟 | `docker compose restart` |
| 更新到最新版 | `docker compose pull && docker compose up -d` |

> **注意**:`docker compose down` 只會停掉容器,你的對話記錄與設定存在 `open-webui-data` 這個 volume 裡,不會消失。除非你加 `-v`(`docker compose down -v`),那會連資料一起刪除。

## 常見問題

### 打開 localhost:3000 沒反應

先用 `docker compose ps` 確認容器是不是 running。若不是,用 `docker compose logs open-webui` 看錯誤訊息。常見原因是 3000 連接埠被其他程式佔用 — 把 compose 裡的 `3000` 改成例如 `3001` 再重啟。

### 對話送出後報錯、或一直轉圈

多半是 key 或連線問題。檢查:

1. `.env` 裡的 `ANTHROPIC_API_KEY` 有沒有填對、有沒有多餘空白。
2. console 額度是否用完。
3. 改了 `WEBUI_SECRET_KEY` 嗎?改過的話舊連線會解不開,重設一條 Connection 即可。

若仍不行,改用上面的 LiteLLM 退路。

### 容器重啟後要重新設定連線

這正是 `WEBUI_SECRET_KEY` 沒設定或被更動的症狀。確認 `.env` 裡有固定的 `WEBUI_SECRET_KEY`,且之後不再變動。

### key 會不會不小心進到 git

專案附的 `.gitignore` 已經把 `.env` 排除。實際的 key 只存在 `.env`(不進版控),範本 `.env.example` 裡是假值,可以安心推上 git。
