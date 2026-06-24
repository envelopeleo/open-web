"""種子資料：建表並塞入示範資料。

塞 10 筆訂單，其中刻意安排幾筆 failed 並帶不同失敗環節，
這樣失敗率與失敗處分析才有東西可算。
冪等：重跑會先清空再塞，不會重複累積。
"""
from datetime import datetime, timedelta, timezone

from app.database import Base, engine, SessionLocal
from app.models import Product, Inventory, Order, OrderStatusLog


def seed():
    # 建表（若不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 冪等：先清掉舊資料（注意順序，先清有外鍵的）
        db.query(OrderStatusLog).delete()
        db.query(Order).delete()
        db.query(Inventory).delete()
        db.query(Product).delete()
        db.commit()

        # ── 物品 ──
        products = [
            Product(sku="SKU-001", name="無線滑鼠", category="周邊"),
            Product(sku="SKU-002", name="機械鍵盤", category="周邊"),
            Product(sku="SKU-003", name="27吋螢幕", category="顯示"),
            Product(sku="SKU-004", name="USB-C 集線器", category="周邊"),
            Product(sku="SKU-005", name="筆電支架", category="配件"),
        ]
        db.add_all(products)
        db.flush()  # 拿到 product.id

        # ── 庫存 ──
        inventories = [
            Inventory(product_id=products[0].id, quantity=120, location="A1"),
            Inventory(product_id=products[1].id, quantity=80, location="A2"),
            Inventory(product_id=products[2].id, quantity=15, location="B1"),
            Inventory(product_id=products[3].id, quantity=0, location="B2"),   # 缺貨
            Inventory(product_id=products[4].id, quantity=45, location="C1"),
        ]
        db.add_all(inventories)

        # ── 10 筆訂單，狀態分布刻意設計 ──
        # 5 done, 2 shipped, 3 failed（失敗環節各異）
        now = datetime.now(timezone.utc)
        order_specs = [
            # (order_no, status, 幾天前建立, 失敗環節 or None, 失敗原因 or None)
            ("ORD-1001", "done",     1, None, None),
            ("ORD-1002", "done",     2, None, None),
            ("ORD-1003", "shipped",  1, None, None),
            ("ORD-1004", "failed",   3, "payment",   "信用卡授權失敗"),
            ("ORD-1005", "done",     4, None, None),
            ("ORD-1006", "failed",   2, "inventory", "庫存不足無法出貨"),
            ("ORD-1007", "shipped",  1, None, None),
            ("ORD-1008", "done",     5, None, None),
            ("ORD-1009", "failed",   2, "payment",   "付款逾時"),
            ("ORD-1010", "done",     6, None, None),
        ]

        for order_no, status, days_ago, fail_stage, fail_reason in order_specs:
            created = now - timedelta(days=days_ago)
            order = Order(
                order_no=order_no,
                status=status,
                created_at=created,
                updated_at=created,
            )
            db.add(order)
            db.flush()

            # 每筆都記一條「建立」歷程
            db.add(OrderStatusLog(
                order_id=order.id, from_status=None, to_status="pending",
                reason="訂單建立", changed_at=created,
            ))
            # failed 的再記一條失敗歷程，帶失敗環節與原因
            if status == "failed":
                db.add(OrderStatusLog(
                    order_id=order.id, from_status="processing", to_status="failed",
                    reason=f"{fail_stage}:{fail_reason}",
                    changed_at=created + timedelta(hours=2),
                ))

        db.commit()
        print("種子資料完成：5 物品 / 5 庫存 / 10 訂單（3 筆 failed）")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
