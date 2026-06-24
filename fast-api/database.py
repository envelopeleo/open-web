"""資料庫連線設定。

預設用 SQLite（零設定、檔案即資料庫），但透過環境變數 DATABASE_URL
可無痛切換到 MySQL / MSSQL — 只改連線字串，其餘程式碼不動。

切換範例：
  SQLite : sqlite:///./arch1.db                （預設）
  MySQL  : mysql+pymysql://user:pass@db:3306/arch1
  MSSQL  : mssql+pyodbc://user:pass@host/arch1?driver=ODBC+Driver+18
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./arch1.db")

# SQLite 需要這個參數才能在 FastAPI 的多執行緒下運作；其他 DB 不需要
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依賴注入用：每個請求拿一個 session，結束自動關閉。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
