FROM python:3.14-slim

LABEL org.opencontainers.image.source="https://github.com/featurecreep-cron/morsl" \
      org.opencontainers.image.description="A menu generator for Tandoor Recipes" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/featurecreep-cron/morsl"

# System deps for cairosvg / Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 shared-mime-info curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN mkdir -p morsl/app morsl/services && \
    touch morsl/__init__.py morsl/app/__init__.py morsl/services/__init__.py \
          morsl/models.py morsl/tandoor_api.py morsl/utils.py morsl/solver.py morsl/constants.py && \
    pip install --no-cache-dir . && \
    rm -rf morsl

# Copy actual source
COPY morsl/ morsl/
COPY scripts/ scripts/
COPY web/ web/
COPY docker-entrypoint.sh /usr/local/bin/

# Create writable dirs for runtime data
RUN mkdir -p data/branding data/custom-icons data/profiles data/templates data/weekly_plans web/icons

# Non-root user with configurable UID/GID
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID appgroup && \
    useradd -r -u $UID -g $GID -s /bin/false --no-create-home appuser && \
    chown -R appuser:appgroup data web/icons
USER appuser

ENV LOG_TO_STDOUT=1

EXPOSE 8321

ENTRYPOINT ["docker-entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8321/health || exit 1

CMD ["uvicorn", "morsl.app.main:app", "--host", "0.0.0.0", "--port", "8321"]
