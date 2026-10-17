# The second host: aarch64 Linux (Debian 13 "trixie"), base image pinned by digest (the multi-arch
# index digest of debian:trixie-slim, pulled 2026-10-17). Host tools from Debian's archive (versions
# recorded by run-build.sh, not pinned: apt has no digest pin without snapshot.debian.org), and uv
# 0.9.22 from its release tarball, verified against its published SHA-256. Container only.
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make curl ca-certificates xz-utils git perl \
 && rm -rf /var/lib/apt/lists/*
COPY uv-aarch64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN echo "2f8716c407d5da21b8a3e8609ed358147216aaab28b96b1d6d7f48e9bcc6254e  /tmp/uv.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/uv.tar.gz -C /tmp \
 && install -m 0755 /tmp/uv-aarch64-unknown-linux-gnu/uv /usr/local/bin/uv \
 && rm -rf /tmp/uv.tar.gz /tmp/uv-aarch64-unknown-linux-gnu \
 && git config --system --add safe.directory '*'
