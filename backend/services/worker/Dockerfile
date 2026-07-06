# build with: docker build -f services/worker/Dockerfile -t worker backend/
FROM python:3.12-slim
WORKDIR /app
# shared lib first for better layer caching
COPY libs/platform_common /app/libs/platform_common
RUN pip install /app/libs/platform_common
# then the service
COPY services/worker /app/service
RUN pip install /app/service
CMD ["python", "-m", "app.worker"]
