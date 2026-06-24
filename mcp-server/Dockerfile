FROM python:3.12-slim

WORKDIR /app

# 先裝依賴（利用 layer cache：requirements 沒變就不重裝）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再複製程式碼
COPY app/ ./app/

# MCP server 以 streamable HTTP 監聽 8000
EXPOSE 8000

# 以模組方式啟動，PYTHONPATH 設為 /app 讓 app 套件可被 import
ENV PYTHONPATH=/app
CMD ["python", "-m", "app.server"]
