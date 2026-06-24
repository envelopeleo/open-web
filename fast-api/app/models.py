"""資料表設計（ORM 模型）。

對應最早 SDD 文件裡的資料表草案。關鍵設計：
  - order_status_log 記錄狀態變更歷程，是「失敗率/失敗處」分析的地基
    —— 只存當前狀態的話，訂單一旦 failed 就查不出它卡在哪個環節。
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """物品主檔。"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    inventory = relationship("Inventory", back_populates="product")


class Inventory(Base):
    """庫存。與 product 分開，利於日後做歷史追蹤。"""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False, default=0)
    location = Column(String(64))
    updated_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")


class Order(Base):
    """訂單主檔。status 為當前狀態，歷程記在 order_status_log。"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, nullable=False)
    # pending / processing / shipped / failed / done
    status = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    status_logs = relationship("OrderStatusLog", back_populates="order")


class OrderStatusLog(Base):
    """狀態變更歷程 —— 失敗率/失敗處分析的關鍵表。

    reason 欄位記錄失敗原因，讓「失敗處」分析查得出卡在哪、為什麼。
    """
    __tablename__ = "order_status_log"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    from_status = Column(String(32))
    to_status = Column(String(32))
    reason = Column(Text)
    changed_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="status_logs")
