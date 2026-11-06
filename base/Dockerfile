# syntax=docker/dockerfile:1
ARG NODE_IMAGE=docker.io/library/node:26-trixie
ARG DOCKER_IMAGE=docker.io/library/docker:29.9.3-cli

FROM ${DOCKER_IMAGE} AS docker-cli
FROM ${NODE_IMAGE}

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# The Node image brings buildpack-deps; declare our CI tools explicitly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates curl git gzip jq tar unzip xz-utils zip zstd \
    && rm -rf /var/lib/apt/lists/*

# Client tools only. The runner provides DOCKER_HOST and the CI engine.
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/ /usr/local/libexec/docker/cli-plugins/

RUN node --version \
    && npm --version \
    && git --version \
    && zstd --version \
    && docker --version \
    && docker buildx version

WORKDIR /workspace
# Jobs and local smoke tests supply their own command.
ENTRYPOINT []
CMD ["bash"]
