FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SUITE_DATA=/data SUITE_LAYOUTS=/data/layouts SUITE_GALLERY=/data/gallery
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY VERSION /app/VERSION
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY --from=web /web/dist /app/web/dist
WORKDIR /app/backend
EXPOSE 8787
HEALTHCHECK --interval=10s --timeout=5s --start-period=45s --retries=12 \
  CMD curl -sf http://127.0.0.1:8787/api/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
