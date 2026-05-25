FROM python:3.11-slim

# Java 17 for PySpark
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

WORKDIR /workspace
COPY . .
RUN uv sync --all-extras

CMD ["bash"]

