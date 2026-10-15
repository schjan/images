#!/usr/bin/env bash
# Runs inside a disposable image container; all output stays under /tmp.
set -euo pipefail
kind=${1:?Expected base, rust or dotnet}
case "$kind" in base|rust|dotnet) ;; *) echo "Unknown image kind: $kind" >&2; exit 2 ;; esac
# shellcheck source=/dev/null
. /etc/os-release
test "$VERSION_ID" = 13
test "$(node -p 'process.versions.node.split(".")[0]')" = 24
npm --version
git --version
curl --version > /dev/null
jq --version
docker --version
docker buildx version
# GNU tar/zstd interoperability is required by Actions caching.
mkdir -p /tmp/cache-source /tmp/cache-restored
printf 'cache-roundtrip-ok\n' > /tmp/cache-source/proof
tar --zstd -cf /tmp/cache.tar.zst -C /tmp/cache-source proof
tar --zstd -xf /tmp/cache.tar.zst -C /tmp/cache-restored
cmp /tmp/cache-source/proof /tmp/cache-restored/proof
case "$kind" in
    rust)
        cmake --version
        pkg-config --version
        cargo new --quiet --vcs none /tmp/rust-smoke
        cd /tmp/rust-smoke
        cargo fmt --check
        cargo clippy --offline -- -D warnings
        test "$(cargo run --offline --quiet)" = 'Hello, world!'
        ;;
    dotnet)
        case "$(dotnet --version)" in 10.*) ;; *) exit 1 ;; esac
        dotnet new console --framework net10.0 --no-restore --output /tmp/dotnet-smoke
        mkdir -p /tmp/empty-nuget-feed
        cd /tmp/dotnet-smoke
        # This SDK-only sample must restore/build/run without external packages.
        dotnet restore --source /tmp/empty-nuget-feed
        test "$(dotnet run --no-restore --verbosity quiet)" = 'Hello, World!'
        ;;
esac
printf '%s smoke tests passed\n' "$kind"
