#!/usr/bin/env bash
# Build/load the selected targets and test the resulting images. Needs Python 3.
set -euo pipefail
cd "$(dirname "$0")/.."
plan=$(mktemp)
trap 'rm -f "$plan"' EXIT
docker buildx bake --print "$@" > "$plan"
docker buildx bake --load "$@"
bash scripts/test-images.sh "$plan"
