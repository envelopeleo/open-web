# Arch2 上 minikube

把本機跑通的 Open WebUI + LiteLLM 兩服務,搬到本機 minikube 練 k8s。

> 目的是練 k8s,不是讓服務變好用 —— 使用者體驗跟 compose 版一樣。資料庫不在這套裡(屬 Arch1,留在 k8s 外)。

## 檔案結構

```
k8s/
├── 01-secret.yaml      # 三把金鑰（含實際值，不要推 git）
├── 02-configmap.yaml   # litellm 設定檔
├── 03-litellm.yaml     # litellm Deployment + Service（內部）
└── 04-open-webui.yaml  # open-webui PVC + Deployment + Service
```

## 步驟

### 1. 啟動 minikube

```bash
brew install minikube      # 還沒裝的話
minikube start
kubectl get nodes          # 看到一個 Ready 節點就對了
```

### 2. 填好 Secret

編輯 `k8s/01-secret.yaml`,把三個值填成你本機 `.env` 裡用的同一組:

- `ANTHROPIC_API_KEY` — 你的 Anthropic key
- `LITELLM_MASTER_KEY` — 內部金鑰
- `WEBUI_SECRET_KEY` — Open WebUI 加密金鑰

### 3. 套用所有 manifest

```bash
kubectl apply -f k8s/
```

一次套用整個資料夾。k8s 會依序建立 Secret、ConfigMap、兩個 Deployment 與 Service、PVC。

### 4. 確認都起來了

```bash
kubectl get pods
```

等到兩個 pod 都是 `Running`(第一次要拉 image,等一兩分鐘):

```
NAME                          READY   STATUS    RESTARTS   AGE
litellm-xxxxxxxxx-xxxxx       1/1     Running   0          90s
open-webui-xxxxxxxxx-xxxxx    1/1     Running   0          90s
```

pod 卡在 `Pending` 或 `CrashLoopBackOff` → 看下面除錯。

### 5. 開啟服務

Open WebUI 的 Service 是 ClusterIP(叢集內部),要開一條通道才能從瀏覽器連:

```bash
kubectl port-forward svc/open-webui 3000:8080
```

保持這個指令開著,瀏覽器開 <http://localhost:3000>。用完按 Ctrl+C 關掉通道。

> 也可以用 `minikube service open-webui --url` 取得一個臨時網址,但要先把 Service 改成 NodePort。port-forward 最單純,先用這個。

## 常用指令

| 想做的事 | 指令 |
|---|---|
| 看所有資源 | `kubectl get all` |
| 看某 pod 日誌 | `kubectl logs -f deploy/litellm` |
| 進 pod 裡測連線 | `kubectl exec -it deploy/open-webui -- curl http://litellm:4000/v1/models -H "Authorization: Bearer 你的master-key"` |
| 改了 manifest 重新套用 | `kubectl apply -f k8s/` |
| 改了 ConfigMap 後讓 pod 重讀 | `kubectl rollout restart deploy/litellm` |
| 全部刪掉 | `kubectl delete -f k8s/` |
| 關掉整個叢集 | `minikube stop` |

## 除錯

### pod 卡在 Pending

通常是資源不夠或 PVC 沒綁定。看詳情:

```bash
kubectl describe pod <pod名稱>
```

最底下的 Events 會說原因。

### pod 一直 CrashLoopBackOff

容器啟動後就掛,看日誌找原因(最常見是 Secret 沒填對、或 config 格式錯):

```bash
kubectl logs <pod名稱>
```

### Open WebUI 沒有可用模型

跟 compose 版同樣的排查邏輯:先確認 litellm 通不通。

```bash
kubectl exec -it deploy/open-webui -- \
  curl http://litellm:4000/v1/models \
  -H "Authorization: Bearer 你的LITELLM_MASTER_KEY"
```

回模型清單 = litellm 正常,問題在 Open WebUI 端;連不到 = 看 litellm 日誌。

## 跟 compose 版的對應

| compose | k8s |
|---|---|
| `open-webui` service | Deployment + Service + PVC |
| `litellm` service | Deployment + Service(ClusterIP) |
| `litellm_config.yaml` 掛載 | ConfigMap |
| `.env` 三把金鑰 | Secret |
| `open-webui-data` volume | PersistentVolumeClaim |
| `ports: 3000:8080` | `kubectl port-forward` |

## 下一步(進階,選做)

- 對 open-webui 加一個 **HPA**(自動擴縮)練手 —— 雖然這服務不太需要,但繪圖層之後會用得到。
- 把 Secret 改用 **External Secrets** 或 sealed-secrets,讓機密能安全進 git。
- 學 **Helm** 把這些 manifest 樣板化,管理多環境。
