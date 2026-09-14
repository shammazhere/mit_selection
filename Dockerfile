# Multi-stage Dockerfile for Silent Shift (Unified Full-Stack Deployment)
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8787
ENV PORT=8787
ENV HOST=0.0.0.0

CMD ["python", "backend/api/main.py"]
