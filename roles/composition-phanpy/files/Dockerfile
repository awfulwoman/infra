# Phanpy has no upstream image. Upstream recommends a custom build, since
# PHANPY_* settings are baked in at build time by Vite.

FROM node:24.22.0-alpine AS build

# renovate: datasource=github-releases depName=cheeaun/phanpy versioning=loose
ARG PHANPY_VERSION=2026.10.09.febb38d

ARG PHANPY_CLIENT_NAME
ARG PHANPY_WEBSITE
ARG PHANPY_DEFAULT_INSTANCE
ARG PHANPY_DISALLOW_ROBOTS

WORKDIR /src
RUN wget -qO- "https://codeload.github.com/cheeaun/phanpy/tar.gz/refs/tags/${PHANPY_VERSION}" \
      | tar -xz --strip-components=1
RUN npm ci --no-audit --no-fund
RUN PHANPY_CLIENT_NAME="${PHANPY_CLIENT_NAME}" \
    PHANPY_WEBSITE="${PHANPY_WEBSITE}" \
    PHANPY_DEFAULT_INSTANCE="${PHANPY_DEFAULT_INSTANCE}" \
    PHANPY_DISALLOW_ROBOTS="${PHANPY_DISALLOW_ROBOTS}" \
    npm run build

# Unprivileged nginx: runs as uid 101, listens on 8080.
FROM nginxinc/nginx-unprivileged:1.31.7-alpine
COPY --from=build /src/dist /usr/share/nginx/html
