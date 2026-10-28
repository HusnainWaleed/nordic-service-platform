FROM python:3.12-slim
WORKDIR /app
COPY app.py request_metrics.py ./
USER 10001:10001
EXPOSE 8080
CMD ["python", "-B", "app.py"]
