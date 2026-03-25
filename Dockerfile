# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Use --extra-index-url so we can still fetch standard tools from PyPI
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md ./
COPY src/ src/
# Build wheels, but skip re-building torch (already in site-packages if lucky, or fetch it again via extra-index)
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels --extra-index-url https://download.pytorch.org/whl/cpu .

# Final stage
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install CPU-only torch to save space in the final image
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

# Copy wheels and install
COPY --from=builder /app/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Configuration and data setup
COPY src/cyanide/configs/ configs/

RUN mkdir -p var/log/cyanide/tty var/quarantine var/lib/cyanide/run \
    && groupadd -r cyanide && useradd -r -g cyanide cyanide \
    && chown -R cyanide:cyanide var/log/cyanide var/quarantine var/lib/cyanide/run

USER cyanide
EXPOSE 2222 2223

ENTRYPOINT ["cyanide"]
