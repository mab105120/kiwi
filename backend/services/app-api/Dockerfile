# build with: docker build -f services/app-api/Dockerfile -t app-api backend/
FROM python:3.12-slim
WORKDIR /app
# shared lib first for better layer caching
COPY libs/platform_common /app/libs/platform_common
RUN pip install /app/libs/platform_common
# then the service
COPY services/app-api /app/service
RUN pip install /app/service
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:create_app()"]
