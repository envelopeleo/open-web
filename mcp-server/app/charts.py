"""繪圖模組：把結構化數據畫成統計圖表 PNG。

支援圓餅圖、長條圖、折線圖、水平長條圖。
設計原則：
  - 輸入是乾淨的「標籤 + 數值」，不關心資料從哪來。
  - 中文標籤正常顯示（用 Noto CJK 字型）。
  - 存成 PNG 檔，回傳檔名，由上層決定怎麼給出 URL。
"""
import os
import uuid
import matplotlib
matplotlib.use("Agg")  # 無頭環境（伺服器沒有螢幕）必須用 Agg
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 圖片輸出目錄（容器內路徑，之後對外用靜態服務暴露）
CHART_DIR = os.environ.get("CHART_DIR", "/tmp/charts")
os.makedirs(CHART_DIR, exist_ok=True)

# 設定中文字型，避免標籤變方框
for name in ["PingFang TC", "Heiti TC", "Songti TC", "Noto Sans CJK TC", "Noto Sans CJK SC", "Microsoft JhengHei"]:
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False  # 負號正常顯示

# 一組好看的配色
COLORS = ["#4C78A8", "#F58518", "#54A24B", "#E45756",
          "#72B7B2", "#B279A2", "#FF9DA6", "#9D755D"]


def _new_filename() -> str:
    return f"chart_{uuid.uuid4().hex[:12]}.png"


def _save(fig) -> str:
    fname = _new_filename()
    path = os.path.join(CHART_DIR, fname)
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return fname


def pie_chart(labels, values, title="") -> str:
    """圓餅圖：適合比例/佔比。"""
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.pie(values, labels=labels, autopct="%1.1f%%",
           colors=COLORS[:len(values)], startangle=90,
           textprops={"fontsize": 11})
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.axis("equal")
    return _save(fig)


def bar_chart(labels, values, title="", xlabel="", ylabel="") -> str:
    """長條圖：適合各類別數量比較。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=COLORS[:len(values)])
    ax.set_title(title, fontsize=14, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    # 在每根長條上標數值
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                str(v), ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    return _save(fig)


def hbar_chart(labels, values, title="", xlabel="") -> str:
    """水平長條圖：適合環節/原因分布（類別名稱較長時）。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.barh(labels, values, color=COLORS[:len(values)])
    ax.set_title(title, fontsize=14, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    for b, v in zip(bars, values):
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                f" {v}", ha="left", va="center", fontsize=10)
    fig.tight_layout()
    return _save(fig)


def line_chart(labels, values, title="", xlabel="", ylabel="") -> str:
    """折線圖：適合時間趨勢。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(labels, values, marker="o", color=COLORS[0], linewidth=2)
    ax.set_title(title, fontsize=14, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig)


# 圖型分派表，讓上層用字串選圖
CHART_TYPES = {
    "pie": pie_chart,
    "bar": bar_chart,
    "hbar": hbar_chart,
    "line": line_chart,
}


def render(chart_type: str, labels, values, title="", **kwargs) -> str:
    """統一入口：依 chart_type 畫圖，回傳檔名。"""
    fn = CHART_TYPES.get(chart_type)
    if fn is None:
        raise ValueError(f"不支援的圖型：{chart_type}，可用：{list(CHART_TYPES)}")
    # 只傳該函式收的參數
    import inspect
    sig = inspect.signature(fn)
    allowed = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(labels, values, title=title, **allowed)
