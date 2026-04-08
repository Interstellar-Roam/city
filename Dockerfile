# ---- Stage 1: Build dependencies ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install dependencies to system python
RUN uv pip install --system -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

LABEL maintainer="CityWalk Team"
LABEL description="CityWalk Backend API Server"

# Install mongosh for data import, and ca-certificates for HTTPS
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
    echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" > /etc/apt/sources.list.d/mongodb-org-8.0.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends mongodb-mongosh mongodb-database-tools && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application code
COPY app/ ./app/

# Copy MongoDB data for initialization
COPY citywalk_mongo.archive /app/data/citywalk_mongo.archive
COPY scripts/init_docker.sh /app/init_docker.sh

# Environment defaults (override via docker-compose or -e)
ENV MONGODB_URL=mongodb://mongodb:27017 \
    MONGODB_DB_NAME=citywalk \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    DEBUG=false

EXPOSE 8000

RUN chmod +x /app/init_docker.sh

CMD ["/app/init_docker.sh"]
