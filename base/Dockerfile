# syntax=docker/dockerfile:1
ARG NODE_IMAGE=docker.io/library/node:24-trixie
ARG DOCKER_IMAGE=docker.io/library/docker:29.9.0-cli

FROM ${DOCKER_IMAGE} AS docker-cli
FROM ${NODE_IMAGE}

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# node:24-trixie already brings buildpack-deps; declare our CI tools explicitly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates curl git gzip jq tar unzip xz-utils zip zstd \
    && rm -rf /var/lib/apt/lists/*

# Client tools only. The runner provides DOCKER_HOST and the CI engine.
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/ /usr/local/libexec/docker/cli-plugins/

RUN test "$(node -p 'process.versions.node.split(".")[0]')" = 24 \
    && npm --version \
    && git --version \
    && zstd --version \
    && docker --version \
    && docker buildx version

WORKDIR /workspace
# Jobs and local smoke tests supply their own command.
ENTRYPOINT []
CMD ["bash"]
