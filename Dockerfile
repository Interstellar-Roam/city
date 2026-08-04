ARG PYTHON_IMAGE=registry.access.redhat.com/ubi9/python-312:latest
FROM ${PYTHON_IMAGE}

LABEL maintainer="CityWalk Team"
LABEL description="CityWalk Backend API Server"

USER 0
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Environment defaults (override via docker-compose or -e)
ENV MONGODB_URL=mongodb://mongodb:27017 \
    MONGODB_DB_NAME=citywalk \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    DEBUG=false

EXPOSE 8000

USER 1001
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
