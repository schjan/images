#!/usr/bin/env bash
# Runs inside a disposable image container; all output stays under /tmp.
set -euo pipefail
kind=${1:?Expected base, rust or dotnet}
node_major=${2:?Expected Node major from the Bake plan}
toolchain=${3:?Expected toolchain version from the Bake plan}
docker_version=${4:?Expected Docker version from the Bake plan}
case "$kind" in base|rust|dotnet) ;; *) echo "Unknown image kind: $kind" >&2; exit 2 ;; esac
# shellcheck source=/dev/null
. /etc/os-release
test "$VERSION_ID" = 13
test "$(node -p 'process.versions.node.split(".")[0]')" = "$node_major"
npm --version
git --version
curl --version > /dev/null
jq --version
docker --version
actual_docker=$(docker --version | cut -d ' ' -f 3 | tr -d ',')
case "$actual_docker" in
    "$docker_version"|"$docker_version".*) ;;
    *) echo "Expected Docker $docker_version, got $actual_docker" >&2; exit 1 ;;
esac
docker buildx version
# GNU tar/zstd interoperability is required by Actions caching.
mkdir -p /tmp/cache-source /tmp/cache-restored
printf 'cache-roundtrip-ok\n' > /tmp/cache-source/proof
tar --zstd -cf /tmp/cache.tar.zst -C /tmp/cache-source proof
tar --zstd -xf /tmp/cache.tar.zst -C /tmp/cache-restored
cmp /tmp/cache-source/proof /tmp/cache-restored/proof
case "$kind" in
    rust)
        test "$(rustc --version | cut -d ' ' -f 2)" = "$toolchain"
        cmake --version
        pkg-config --version
        cargo new --quiet --vcs none /tmp/rust-smoke
        cd /tmp/rust-smoke
        cargo fmt --check
        cargo clippy --offline -- -D warnings
        test "$(cargo run --offline --quiet)" = 'Hello, world!'
        ;;
    dotnet)
        test "$(dotnet --version)" = "$toolchain"
        dotnet new console --framework net10.0 --no-restore --output /tmp/dotnet-smoke
        mkdir -p /tmp/empty-nuget-feed
        cd /tmp/dotnet-smoke
        # This SDK-only sample must restore/build/run without external packages.
        dotnet restore --source /tmp/empty-nuget-feed
        test "$(dotnet run --no-restore --verbosity quiet)" = 'Hello, World!'
        ;;
esac
printf '%s smoke tests passed\n' "$kind"
