# 四服務上 minikube

把本機跑通的整套（Open WebUI + LiteLLM + MCP server + Arch1）搬上本機 minikube。

## 服務一覽

| 服務 | image 來源 | 對外? | k8s 資源 |
|---|---|---|---|
| Open WebUI | 官方 | 是（Ingress） | Deployment + Service + PVC |
| LiteLLM | 官方 | 否 | Deployment + Service |
| MCP server | **自建** | /charts（Ingress） | Deployment + Service |
| Arch1 | **自建** | 否 | Deployment + Service |

叢集內服務互連用 Service 名；對外（瀏覽器）走 Ingress 的 orders.local。

## 檔案

```
k8s/
├── 01-secret.yaml       # 三把金鑰（含實際值，不要推 git）
├── 02-configmap.yaml    # litellm 設定
├── 03-arch1.yaml        # Arch1
├── 04-mcp-server.yaml   # MCP server（取數+繪圖）
├── 05-litellm.yaml      # LiteLLM
├── 06-open-webui.yaml   # Open WebUI + PVC
└── 07-ingress.yaml      # 對外入口，/charts → MCP server
dockerfiles/
├── mcp-server.Dockerfile  # 含中文字型
└── arch1.Dockerfile
```

## 部署步驟

### 1. 啟動 minikube 與 ingress

```bash
minikube start
minikube addons enable ingress      # 開啟 ingress 功能
```

### 2. 把自建 image build 進 minikube（關鍵步驟）

minikube 有自己的 Docker 環境，跟你 Mac 的 Docker 分開。MCP server 和 Arch1 是自建 image，要 build 進 minikube 的環境，它才看得到。

**做法：先切換到 minikube 的 Docker 環境，再 build。**

```bash
# 切換到 minikube 的 docker（這行讓接下來的 docker 指令作用在 minikube 內）
eval $(minikube docker-env)

# build MCP server（在你 mcp-server 資料夾，用這包的 Dockerfile）
cd mcp-server
docker build -t mcp-server:local -f /path/to/dockerfiles/mcp-server.Dockerfile .

# build Arch1（在你 arch1-api 資料夾）
cd ../arch1-api
docker build -t arch1-api:local .
```

> manifest 裡 image 寫 `mcp-server:local`、`arch1-api:local`，搭配 `imagePullPolicy: IfNotPresent`，就會用 minikube 內這份本機 image，不去外面拉。
>
> 注意：`eval $(minikube docker-env)` 只在當前終端機有效。關掉終端機要重跑。要還原成 Mac 的 docker：`eval $(minikube docker-env -u)`。

### 3. 填好 Secret

編輯 `k8s/01-secret.yaml`，填三個值（跟本機 .env 同一組）：
ANTHROPIC_API_KEY、LITELLM_MASTER_KEY、WEBUI_SECRET_KEY。

### 4. 套用所有 manifest

```bash
kubectl apply -f k8s/
```

### 5. 確認 pod 都起來

```bash
kubectl get pods
```

等四個都 Running（官方 image 要拉、自建的已在本機）：
```
arch1-api-xxx     1/1 Running
litellm-xxx       1/1 Running
mcp-server-xxx    1/1 Running
open-webui-xxx    1/1 Running
```

### 6. 設定對外網址 orders.local

```bash
minikube ip                    # 拿到 IP，例如 192.168.49.2
sudo nano /etc/hosts           # 加一行：
# 192.168.49.2  orders.local
```

macOS 若連不到，另開終端機跑著：
```bash
minikube tunnel
```

### 7. 開啟服務

瀏覽器開 <http://orders.local>，就是你的 Open WebUI。

## 部署後的設定

### 接 LiteLLM

Open WebUI 已透過環境變數指向 litellm Service，模型選單應該有 claude-opus-4-8。沒有的話進 Admin → Connections 確認連線是 `http://litellm:4000/v1`。

### 接 MCP server

進 Admin → External Tools → 新增：
- 類型：MCP (Streamable HTTP)
- URL：`http://mcp-server:8000/mcp`（叢集內用 Service 名，不是 host.docker.internal）
- 驗證：None

### 驗證繪圖

問「把庫存畫成圓餅圖」。圖片 URL 會是 `http://orders.local/charts/xxx.png`，
瀏覽器透過 Ingress 連到 MCP server 拿圖。中文標籤正常（Dockerfile 已裝 fonts-noto-cjk）。

## 位址對照（本機 vs k8s）

本機踩過的位址坑，在 k8s 換成這樣：

| 用途 | 本機裸跑 | k8s |
|---|---|---|
| Open WebUI 連 LiteLLM | localhost:4000 | http://litellm:4000/v1 |
| Open WebUI 連 MCP | host.docker.internal:8000 | http://mcp-server:8000/mcp |
| MCP 連 Arch1 | localhost:8001 | http://arch1-api:8000 |
| 瀏覽器抓圖（PUBLIC_BASE_URL）| localhost:8000 | http://orders.local |

重點：叢集內互連用 Service 名；唯獨 PUBLIC_BASE_URL 用對外 Ingress 網址，
因為圖片是瀏覽器（叢集外）抓的，要對外可達。

## charts.py 字型提醒

本機你可能加了 PingFang TC（macOS 字型）。容器是 Linux 沒有 PingFang，
靠 Dockerfile 裝的 Noto。確認 charts.py 字型名單**兩者都有**：

```python
for name in ["PingFang TC", "Heiti TC",            # 本機 macOS
             "Noto Sans CJK TC", "Noto Sans CJK SC"]:  # 容器 Linux
```

這樣本機和容器都畫得出中文。

## 常用指令

| 想做的事 | 指令 |
|---|---|
| 看所有資源 | kubectl get all |
| 看某 pod 日誌 | kubectl logs -f deploy/mcp-server |
| 進 pod 測連線 | kubectl exec -it deploy/open-webui -- curl http://mcp-server:8000/mcp |
| 改 manifest 後重新套用 | kubectl apply -f k8s/ |
| 重 build image 後讓 pod 重拉 | kubectl rollout restart deploy/mcp-server |
| 全部刪掉 | kubectl delete -f k8s/ |
| 關叢集 | minikube stop |

## 除錯

### pod 卡 ImagePullBackOff（自建 image）

代表 minikube 找不到 mcp-server:local 或 arch1-api:local。
原因通常是 build 時沒先 `eval $(minikube docker-env)`，image build 到 Mac 的 docker 去了。
重新 `eval $(minikube docker-env)` 再 build 一次。

### 改了 code 重新部署

自建 image 改了 code 要重 build + 讓 pod 重拉：
```bash
eval $(minikube docker-env)
docker build -t mcp-server:local -f .../mcp-server.Dockerfile .
kubectl rollout restart deploy/mcp-server
```

### 圖出不來

1. 圖片 URL 是不是 http://orders.local/charts/...？（PUBLIC_BASE_URL 對不對）
2. orders.local 有沒有在 /etc/hosts？
3. Ingress 的 /charts 規則有沒有生效：kubectl describe ingress orders-ingress
4. 中文方框 → 確認 Dockerfile 有裝 fonts-noto-cjk、charts.py 名單有 Noto

### 圖中文變方框

容器沒中文字型。確認 mcp-server.Dockerfile 有那行 apt-get install fonts-noto-cjk，
重 build image、rollout restart。
