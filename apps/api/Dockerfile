# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

FROM python:3.12.11-slim-bookworm AS dependencies
WORKDIR /app
COPY apps/api/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.lock

FROM python:3.12.11-slim-bookworm AS app
LABEL org.opencontainers.image.title="TraceQuota API" \
      org.opencontainers.image.description="Local-first observability and quota intelligence for AI coding agents" \
      org.opencontainers.image.source="https://github.com/ruanpato/tracequota" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.authors="Ruan Pato"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/apps/api
WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY apps/api apps/api
COPY pricing pricing
COPY examples examples
COPY tools tools
COPY pyproject.toml .
COPY LICENSE NOTICE ./
RUN useradd --uid 10001 --create-home tracequota
USER 10001
EXPOSE 8000
CMD ["python", "-m", "tracequota.entrypoint"]

FROM app AS test
ENV PYTEST_ADDOPTS="-p no:cacheprovider" RUFF_CACHE_DIR=/tmp/tracequota-ruff-cache
COPY tests tests
COPY infrastructure infrastructure
COPY dashboards dashboards
COPY docker-compose.yml .
CMD ["python", "-m", "pytest", "-q"]

# Keep normal builds on the application; tests require --target test.
FROM app AS runtime
