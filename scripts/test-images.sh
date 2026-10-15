#!/usr/bin/env bash
# Smoke-test only the images exported by this resolved Bake plan.
set -euo pipefail
cd "$(dirname "$0")/.."
plan=${1:?Expected a Bake --print JSON file}
rows=$(python3 - "$plan" <<'PLAN'
import json, sys
with open(sys.argv[1]) as stream:
    plan = json.load(stream)
selected = plan['group']['default']['targets']
assert selected and all(kind in ('base', 'rust', 'dotnet') for kind in selected)
for kind in selected:
    print(kind + '\t' + plan['target'][kind]['tags'][0])
PLAN
)
while IFS=$'\t' read -r kind image; do
    echo "Testing $kind image: $image"
    docker run --rm -i "$image" bash -s -- "$kind" < tests/smoke.sh
done <<< "$rows"
