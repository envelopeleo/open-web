"""Arch1 API client.

把所有對 Arch1 的 HTTP 呼叫集中在這裡，MCP tool 只呼叫這層、不直接碰 httpx。
這樣未來 Arch1 端點變動，只改這個檔案。
"""
import os
import httpx

# Arch1 API 的位址，從環境變數帶入（k8s 裡指向 Arch1 的 Service）
ARCH1_BASE_URL = os.environ.get("ARCH1_BASE_URL", "http://arch1-api:8001")

# 統一的逾時設定，避免單一慢請求拖垮整個工具呼叫
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class Arch1Error(Exception):
    """Arch1 回應非 2xx 或連線失敗時拋出，讓 tool 層能轉成清楚的錯誤訊息。"""


async def _get(path: str, params: dict | None = None) -> dict:
    """對 Arch1 發 GET，回傳 JSON。失敗統一拋 Arch1Error。"""
    url = f"{ARCH1_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise Arch1Error(
            f"Arch1 回應錯誤 {e.response.status_code}：{path}"
        ) from e
    except httpx.RequestError as e:
        raise Arch1Error(f"無法連到 Arch1（{path}）：{e}") from e


# ── 對應 SDD 設計的聚合端點。聚合運算在 Arch1 端完成，這裡只轉手。──

async def fetch_failure_rate(start: str, end: str) -> dict:
    """查詢區間訂單失敗率（已聚合）。"""
    return await _get("/orders/failure-rate", {"start": start, "end": end})


async def fetch_failure_breakdown(start: str, end: str) -> dict:
    """依失敗環節/原因分組（定位失敗處）。"""
    return await _get("/orders/failure-breakdown", {"start": start, "end": end})


async def fetch_order_status(status: str | None = None) -> dict:
    """訂單狀態分布，可選擇用 status 過濾。"""
    params = {"status": status} if status else None
    return await _get("/orders/status", params)


async def fetch_inventory() -> dict:
    """庫存清單。"""
    return await _get("/inventory")
