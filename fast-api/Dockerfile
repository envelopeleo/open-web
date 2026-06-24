FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENV PYTHONPATH=/app

# 啟動時先 seed 再開 server
CMD ["./entrypoint.sh"]
