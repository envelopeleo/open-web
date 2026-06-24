"""Arch1 API。

提供 MCP server（arch1_client.py）需要的端點。聚合運算在這裡完成
（呼應 SDD：確定性計算留後端，省 token、結果準）。

端點對齊 arch1_client.py：
  /orders/failure-rate
  /orders/failure-breakdown
  /orders/status
  /inventory
"""
from collections import Counter
from datetime import datetime

from fastapi import FastAPI, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app.models import Product, Inventory, Order, OrderStatusLog

# 啟動時確保表存在
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arch1 API", description="訂單/庫存資料與聚合分析", version="0.1.0")


def _parse(d: str | None) -> datetime | None:
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """庫存清單（含物品名稱）。"""
    rows = db.query(Inventory, Product).join(Product, Inventory.product_id == Product.id).all()
    items = [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "quantity": inv.quantity,
            "location": inv.location,
            "out_of_stock": inv.quantity == 0,
        }
        for inv, p in rows
    ]
    return {"total_items": len(items), "items": items}


@app.get("/orders/status")
def order_status(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """訂單狀態分布，可用 status 過濾。"""
    q = db.query(Order.status, func.count(Order.id))
    if status:
        q = q.filter(Order.status == status)
    q = q.group_by(Order.status)
    dist = {s: c for s, c in q.all()}
    return {"total": sum(dist.values()), "by_status": dist}


@app.get("/orders/failure-rate")
def failure_rate(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """區間訂單失敗率（已聚合）。"""
    q = db.query(Order)
    s, e = _parse(start), _parse(end)
    if s:
        q = q.filter(Order.created_at >= s)
    if e:
        q = q.filter(Order.created_at <= e)
    orders = q.all()

    total = len(orders)
    counts = Counter(o.status for o in orders)
    failed = counts.get("failed", 0)
    rate = round(failed / total, 4) if total else 0.0
    return {
        "start": start,
        "end": end,
        "total": total,
        "failed": failed,
        "failure_rate": rate,
        "by_status": dict(counts),
    }


@app.get("/orders/failure-breakdown")
def failure_breakdown(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """依失敗環節/原因分組，用於定位『失敗處』。

    從 order_status_log 撈 to_status=failed 的紀錄，reason 格式為 '環節:原因'。
    """
    q = (
        db.query(OrderStatusLog)
        .join(Order, OrderStatusLog.order_id == Order.id)
        .filter(OrderStatusLog.to_status == "failed")
    )
    s, e = _parse(start), _parse(end)
    if s:
        q = q.filter(OrderStatusLog.changed_at >= s)
    if e:
        q = q.filter(OrderStatusLog.changed_at <= e)
    logs = q.all()

    stage_counter: Counter = Counter()
    detail = []
    for log in logs:
        reason = log.reason or ""
        stage = reason.split(":", 1)[0] if ":" in reason else "unknown"
        stage_counter[stage] += 1
        detail.append({"order_id": log.order_id, "stage": stage, "reason": reason})

    return {
        "start": start,
        "end": end,
        "total_failed": len(logs),
        "by_stage": dict(stage_counter),
        "detail": detail,
    }
