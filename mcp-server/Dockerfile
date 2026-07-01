FROM python:3.12-slim

WORKDIR /app

# 裝中文字型 —— 不裝的話繪圖層畫的中文會變方框
RUN apt-get update && apt-get install -y fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000
ENV PYTHONPATH=/app

# host/port 已寫在 FastMCP(...) 裡（0.0.0.0:8000）
CMD ["python", "-m", "app.server"]
