#!/bin/sh
# 啟動時先塞種子資料（冪等，重啟不會重複累積），再開 API server。
set -e

# 確保 SQLite 資料目錄存在（MySQL 版用不到，無害）
mkdir -p /app/data

echo "[entrypoint] seeding database..."
python -m app.seed

echo "[entrypoint] starting API on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
