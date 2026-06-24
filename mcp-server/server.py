"""Arch2 MCP server.

把 Arch1 的查詢能力包成 MCP tool，供 Open WebUI（streamable HTTP）連接呼叫。
設計原則（呼應 SDD）：
  - 這層只負責「拿到結構化資料」，不做語意判斷、不繪圖。
  - 聚合在 Arch1 端完成，tool 只轉手。
  - 每個 tool 的 docstring 就是給 LLM 看的工具說明，要寫清楚「何時用」。
"""
from mcp.server.fastmcp import FastMCP

from app import arch1_client
from app.arch1_client import Arch1Error

# FastMCP 實例。名稱會顯示在 Open WebUI 的工具清單裡。
mcp = FastMCP("arch2-order-analytics")


def _safe(coro_result: dict) -> dict:
    """tool 共用的回傳包裝，成功就原樣回，方便之後統一加欄位。"""
    return coro_result


@mcp.tool()
async def get_failure_rate(start: str, end: str) -> dict:
    """查詢指定區間的訂單失敗率。

    什麼時候用：使用者問「失敗率」「多少訂單失敗」「成功率」等比例類問題時。
    參數：
        start: 起始日期，格式 YYYY-MM-DD
        end:   結束日期，格式 YYYY-MM-DD
    回傳：各狀態的數量與比例（已由 Arch1 聚合）。
    """
    try:
        return _safe(await arch1_client.fetch_failure_rate(start, end))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_failure_breakdown(start: str, end: str) -> dict:
    """依失敗環節與原因分組，用於定位「失敗處」。

    什麼時候用：使用者問「卡在哪」「為什麼失敗」「哪個環節最常失敗」時。
    參數：
        start: 起始日期 YYYY-MM-DD
        end:   結束日期 YYYY-MM-DD
    回傳：各失敗環節/原因的數量分組。
    """
    try:
        return _safe(await arch1_client.fetch_failure_breakdown(start, end))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_order_status(status: str | None = None) -> dict:
    """查詢訂單狀態分布。

    什麼時候用：使用者問「訂單狀態」「有多少待處理/已出貨」時。
    參數：
        status: 可選。只查某個狀態（如 pending、shipped、failed）；留空查全部。
    回傳：各狀態的訂單數量。
    """
    try:
        return _safe(await arch1_client.fetch_order_status(status))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_inventory() -> dict:
    """查詢庫存清單。

    什麼時候用：使用者問「庫存」「還剩多少」「哪些缺貨」時。
    回傳：各物品的庫存數量。
    """
    try:
        return _safe(await arch1_client.fetch_inventory())
    except Arch1Error as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 以 streamable HTTP 模式啟動，供 Open WebUI 連接。
    # 預設監聽 0.0.0.0:8000，容器化時對外開這個 port。
    mcp.run(transport="streamable-http")
