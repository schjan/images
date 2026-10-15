# syntax=docker/dockerfile:1
# Bake substitutes its base target; standalone builds can pass a published ref.
ARG CI_BASE_IMAGE=ci-base:node24-trixie
FROM ${CI_BASE_IMAGE}

ARG RUST_VERSION=1.99.0
ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup \
    CARGO_INCREMENTAL=0 \
    CARGO_TERM_COLOR=always
ENV PATH="/usr/local/cargo/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
       https://sh.rustup.rs -o /tmp/rustup-init.sh \
    && sh /tmp/rustup-init.sh -y --no-modify-path --profile minimal \
       --default-toolchain "${RUST_VERSION}" --component rustfmt --component clippy \
    && rm /tmp/rustup-init.sh \
    && rustc --version \
    && cargo --version \
    && cargo fmt --version \
    && cargo clippy --version
