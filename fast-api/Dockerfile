# Arch1 的 Dockerfile（你 arch1-api 資料夾裡應該已有，這份是參考對照）
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENV PYTHONPATH=/app

# entrypoint 先 seed 再開 server
CMD ["./entrypoint.sh"]
