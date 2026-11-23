# ÅKEPOL digitalt — spelservern med webbklienten. Byggs från repots rot:
#   docker build -f spel/Dockerfile .
FROM node:22-slim AS webb
WORKDIR /webb
COPY spel/webb/package.json spel/webb/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY spel/webb/ ./
RUN npx vite build

FROM python:3.12-slim
WORKDIR /app
COPY spel/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY motor/ ./motor/
COPY kortdata/ ./kortdata/
COPY spel/__init__.py ./spel/__init__.py
COPY spel/server/ ./spel/server/
COPY --from=webb /webb/dist ./spel/webb/dist
# partierna sparas här; montera en volym på /data för att de ska överleva nya driftsättningar
ENV SPEL_DATA=/data/partier
CMD ["sh", "-c", "python -m uvicorn spel.server.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
