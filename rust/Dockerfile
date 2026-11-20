# syntax=docker/dockerfile:1
# Bake substitutes its base target; standalone builds can pass a published ref.
ARG CI_BASE_IMAGE=ci-base:node-trixie
FROM ${CI_BASE_IMAGE}

ARG RUST_VERSION=1.100.0
ARG MISE_VERSION=2026.11.10
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

# mise installs repo-pinned CI tools (mise.toml), such as release-plz. The
# binary is checked against the release's own checksum list.
RUN arch=$(dpkg --print-architecture) \
    && case "$arch" in amd64) arch=x64 ;; arm64) ;; *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; esac \
    && asset="mise-v${MISE_VERSION}-linux-${arch}" \
    && base="https://github.com/jdx/mise/releases/download/v${MISE_VERSION}" \
    && curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
       "${base}/${asset}" -o /usr/local/bin/mise \
    && curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
       "${base}/SHASUMS256.txt" -o /tmp/mise-shasums.txt \
    && echo "$(grep " ./${asset}$" /tmp/mise-shasums.txt | cut -d ' ' -f 1)  /usr/local/bin/mise" | sha256sum --check --strict \
    && rm /tmp/mise-shasums.txt \
    && chmod 0755 /usr/local/bin/mise \
    && mise --version
