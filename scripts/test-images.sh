#!/usr/bin/env bash
# Smoke-test only the images exported by this resolved Bake plan.
set -euo pipefail
cd "$(dirname "$0")/.."
plan=${1:?Expected a Bake --print JSON file}
rows=$(python3 scripts/smoke_plan.py "$plan")
while IFS=$'\t' read -r kind image node_major expected docker_version; do
    echo "Testing $kind image: $image"
    docker run --rm -i "$image" bash -s -- "$kind" "$node_major" "$expected" "$docker_version" < tests/smoke.sh
done <<< "$rows"
