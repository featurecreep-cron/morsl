# Stage 1: Frontend build
FROM node:22-slim AS frontend
WORKDIR /app/web-vue
COPY web-vue/package*.json ./
RUN npm ci
COPY web-vue/ ./
RUN npm run build

# Stage 2: Python venv
FROM python:3.14-slim@sha256:5b3879b6f3cb77e712644d50262d05a7c146b7312d784a18eff7ff5462e77033 AS builder

WORKDIR /app

# Install Python deps into a virtualenv for clean copy to runtime stage.
# cairosvg/Pillow are pure-Python or ship prebuilt wheels — no build tools needed.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
RUN mkdir -p morsl/app morsl/services && \
    touch morsl/__init__.py morsl/app/__init__.py morsl/services/__init__.py \
          morsl/models.py morsl/tandoor_api.py morsl/utils.py morsl/solver.py morsl/constants.py && \
    pip install --no-cache-dir . && \
    rm -rf morsl

# ---

FROM python:3.14-slim@sha256:5b3879b6f3cb77e712644d50262d05a7c146b7312d784a18eff7ff5462e77033

LABEL org.opencontainers.image.source="https://github.com/featurecreep-cron/morsl" \
      org.opencontainers.image.description="A menu generator for Tandoor Recipes" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/featurecreep-cron/morsl"

# Runtime-only native libs + gosu for PUID/PGID support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 shared-mime-info gosu && \
    rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application source
COPY morsl/ morsl/
COPY scripts/ scripts/
COPY docker-entrypoint.sh /usr/local/bin/

# Vue build output replaces old web/ static files
COPY --from=frontend /app/web/ web/

# Create writable dirs for runtime data
RUN mkdir -p data/branding data/custom-icons data/profiles data/templates data/weekly_plans web/icons

# Default non-root user (overridden at runtime by PUID/PGID if set)
RUN groupadd -g 1000 appgroup && \
    useradd -r -u 1000 -g 1000 -s /bin/false --no-create-home appuser && \
    chown -R appuser:appgroup data web/icons

ARG APP_VERSION=dev
ENV MORSL_VERSION=$APP_VERSION
ENV LOG_TO_STDOUT=1

EXPOSE 8321

ENTRYPOINT ["docker-entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8321/health')" || exit 1

CMD ["uvicorn", "morsl.app.main:app", "--host", "0.0.0.0", "--port", "8321"]
