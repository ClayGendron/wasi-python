# The experiment's container (context/research/2026-10-17-the-linux-build-experiment/Dockerfile),
# parameterised by the uv tarball so the same file serves linux/arm64 and linux/amd64.
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
ARG UV_TRIPLE
ARG UV_SHA
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make curl ca-certificates xz-utils git perl \
 && rm -rf /var/lib/apt/lists/*
COPY uv-${UV_TRIPLE}.tar.gz /tmp/uv.tar.gz
RUN echo "${UV_SHA}  /tmp/uv.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/uv.tar.gz -C /tmp \
 && install -m 0755 /tmp/uv-${UV_TRIPLE}/uv /usr/local/bin/uv \
 && rm -rf /tmp/uv.tar.gz /tmp/uv-${UV_TRIPLE} \
 && git config --system --add safe.directory '*'
