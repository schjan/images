#!/usr/bin/env bash
# Smoke-test only the images exported by this resolved Bake plan.
set -euo pipefail
cd "$(dirname "$0")/.."
plan=${1:?Expected a Bake --print JSON file}
rows=$(python3 - "$plan" <<'PLAN'
import json, re, sys
with open(sys.argv[1]) as stream:
    plan = json.load(stream)
selected = plan['group']['default']['targets']
assert selected and all(kind in ('base', 'rust', 'dotnet') for kind in selected)
node_image = plan['target']['base']['args']['NODE_IMAGE']
node_major = re.search(r':(\d+)', node_image).group(1)
docker_image = plan['target']['base']['args']['DOCKER_IMAGE']
docker_version = re.search(r':(\d+(?:\.\d+)*)', docker_image).group(1)
for kind in selected:
    target = plan['target'][kind]
    expected = '-'
    if kind == 'rust':
        expected = target['args']['RUST_VERSION']
    elif kind == 'dotnet':
        expected = target['args']['DOTNET_SDK_PACKAGE_VERSION'].split('-')[0]
    print('\t'.join((kind, target['tags'][0], node_major, expected, docker_version)))
PLAN
)
while IFS=$'\t' read -r kind image node_major expected docker_version; do
    echo "Testing $kind image: $image"
    docker run --rm -i "$image" bash -s -- "$kind" "$node_major" "$expected" "$docker_version" < tests/smoke.sh
done <<< "$rows"
