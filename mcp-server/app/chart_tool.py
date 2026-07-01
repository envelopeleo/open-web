"""繪圖 tool — 加進現有 MCP server。

把這個檔案放進 app/ 旁邊（app/chart_tool.py），
然後在 server.py 裡 import 並註冊（見 README 整合說明）。

設計：繪圖 tool 收「資料 + 圖型」，畫成 PNG，回傳可被 Open WebUI 顯示的 URL。
URL 由 MCP server 內嵌的靜態路由提供（見 server 整合）。
"""
import os
from app import charts

# MCP server 對外可達的基底 URL，用來組圖片連結。
# 本機：http://host.docker.internal:8000  （Open WebUI 容器連得到主機）
# k8s ：http://<service名>:8000
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://host.docker.internal:8000")


def make_chart(chart_type: str, labels: list, values: list,
               title: str = "", xlabel: str = "", ylabel: str = "") -> dict:
    """產生統計圖表，回傳圖片 URL。

    什麼時候用：使用者要求「畫圖」「圖表」「視覺化」，或問分布/比例/趨勢
    且圖比文字更清楚時。先用其他 tool 取得數據，再把數據丟進來畫。

    參數：
        chart_type: 圖型。pie(圓餅,比例) / bar(長條,數量比較) /
                    hbar(水平長條,環節分布) / line(折線,時間趨勢)
        labels: 標籤清單，例如 ["已完成","已出貨","失敗"]
        values: 對應數值清單，例如 [5,2,3]，長度需與 labels 相同
        title: 圖標題
        xlabel/ylabel: 軸標籤（圓餅圖可省略）
    回傳：
        {"image_url": "http://.../charts/xxx.png"} — 把這個 URL 用
        markdown 圖片語法 ![](url) 呈現給使用者。
    """
    if len(labels) != len(values):
        return {"error": f"labels({len(labels)}) 與 values({len(values)}) 數量不符"}
    try:
        fname = charts.render(
            chart_type, labels, values,
            title=title, xlabel=xlabel, ylabel=ylabel,
        )
        return {
            "image_url": f"{PUBLIC_BASE_URL}/charts/{fname}",
            "hint": "請用 markdown 圖片語法把這個 image_url 顯示出來：![chart](image_url)",
        }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"繪圖失敗：{e}"}
