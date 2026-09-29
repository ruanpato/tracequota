# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

FROM node:24.21.0-alpine AS build
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31.5-alpine
LABEL org.opencontainers.image.title="TraceQuota web" \
      org.opencontainers.image.description="Local-first observability and quota intelligence for AI coding agents" \
      org.opencontainers.image.source="https://github.com/ruanpato/tracequota" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.authors="Ruan Pato"
COPY LICENSE NOTICE /usr/share/licenses/tracequota/
COPY --from=build /app/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
