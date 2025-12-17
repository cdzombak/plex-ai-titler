FROM python:3.12-slim
ARG BIN_VERSION=<dev>

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY plex_ai_titler.py .

# Inject version into the Python script
RUN sed -i "s/<dev>/${BIN_VERSION}/g" plex_ai_titler.py

# Create a directory for credentials and config that can be mounted as a volume
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1
ENV PLEX_CREDS_FILE=/data/.creds.json

ENTRYPOINT ["python", "plex_ai_titler.py", "--config", "/data/config.yaml"]

LABEL license="GPL-3.0"
LABEL maintainer="Chris Dzombak <https://www.dzombak.com>"
LABEL org.opencontainers.image.authors="Chris Dzombak <https://www.dzombak.com>"
LABEL org.opencontainers.image.url="https://github.com/cdzombak/plex-ai-titler"
LABEL org.opencontainers.image.documentation="https://github.com/cdzombak/plex-ai-titler/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/cdzombak/plex-ai-titler.git"
LABEL org.opencontainers.image.version="${BIN_VERSION}"
LABEL org.opencontainers.image.licenses="GPL-3.0"
LABEL org.opencontainers.image.title="plex-ai-titler"
LABEL org.opencontainers.image.description="Use an LLM to generate titles for Plex media items based on filenames"
