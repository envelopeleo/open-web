"""Arch2 MCP server（含繪圖層整合版）。

在原本的取數 tool 之外，加上：
  - make_chart tool：把數據畫成統計圖表 PNG
  - /charts/{filename} 路由：用 HTTP 提供圖檔，讓 Open WebUI 顯示

把你原本的 server.py 換成這份（或對照把繪圖相關的部分加進去）。
"""
import os
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from mcp.server.fastmcp import FastMCP

from app import arch1_client
from app.arch1_client import Arch1Error
from app import charts
from app.chart_tool import make_chart as _make_chart

# host/port 綁 0.0.0.0 讓容器連得到
mcp = FastMCP("arch2-order-analytics", host="0.0.0.0", port=8000)

CHART_DIR = os.environ.get("CHART_DIR", "/tmp/charts")


def _safe(r): return r


# ── 取數 tool（原本的，不變）──

@mcp.tool()
async def get_failure_rate(start: str, end: str) -> dict:
    """查詢指定區間的訂單失敗率。問「失敗率」「成功率」時用。
    start/end 格式 YYYY-MM-DD。"""
    try:
        return _safe(await arch1_client.fetch_failure_rate(start, end))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_failure_breakdown(start: str, end: str) -> dict:
    """依失敗環節分組，定位「失敗處」。問「卡在哪」「為什麼失敗」時用。"""
    try:
        return _safe(await arch1_client.fetch_failure_breakdown(start, end))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_order_status(status: str | None = None) -> dict:
    """查訂單狀態分布。問「訂單狀態」「多少待處理」時用。"""
    try:
        return _safe(await arch1_client.fetch_order_status(status))
    except Arch1Error as e:
        return {"error": str(e)}


@mcp.tool()
async def get_inventory() -> dict:
    """查庫存清單。問「庫存」「缺貨」時用。"""
    try:
        return _safe(await arch1_client.fetch_inventory())
    except Arch1Error as e:
        return {"error": str(e)}


# ── 繪圖 tool（新增）──

@mcp.tool()
async def make_chart(chart_type: str, labels: list, values: list,
                     title: str = "", xlabel: str = "", ylabel: str = "") -> dict:
    """把數據畫成統計圖表，回傳圖片 URL。

    什麼時候用：使用者要「畫圖」「圖表」「視覺化」，或分布/比例/趨勢用圖更清楚時。
    流程：先用取數 tool 拿數據 → 把數據丟進這個 tool 畫圖。

    chart_type：pie(圓餅,比例) / bar(長條,數量) / hbar(水平長條,環節) / line(折線,趨勢)
    labels：標籤如 ["已完成","已出貨","失敗"]
    values：數值如 [5,2,3]，長度需與 labels 相同
    回傳 image_url，請用 markdown ![](image_url) 顯示給使用者。
    """
    return _make_chart(chart_type, labels, values, title, xlabel, ylabel)


# ── 圖檔路由：用 HTTP 提供 PNG，讓 Open WebUI 顯示 ──

@mcp.custom_route("/charts/{filename}", methods=["GET"])
async def serve_chart(request: Request):
    filename = request.path_params["filename"]
    # 防目錄穿越：只允許單純檔名
    if "/" in filename or ".." in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)
    path = os.path.join(CHART_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="image/png")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
