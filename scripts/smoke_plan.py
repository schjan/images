#!/usr/bin/env python3
"""Resolve smoke-test versions from image tags, not registry ports or digests."""
import argparse
import json
import os
from pathlib import Path
import re


def image_tag(reference):
    name = reference.split('@', 1)[0].rsplit('/', 1)[-1]
    _, separator, tag = name.rpartition(':')
    return tag if separator else ''


def expected_version(reference, override, variable, pattern, tag_pattern):
    if override:
        if not re.fullmatch(pattern, override):
            raise ValueError(f'{variable} must be a numeric version matching {pattern}')
        return override
    match = re.match(tag_pattern, image_tag(reference))
    if not match:
        raise ValueError(f'Cannot infer a version from the image tag; set {variable} '
                         'explicitly for digest-only or unversioned references')
    return match[1]


def smoke_rows(plan, node_major='', docker_version=''):
    selected = plan['group']['default']['targets']
    if not selected or any(kind not in ('base', 'rust', 'dotnet') for kind in selected):
        raise ValueError('Expected base, rust or dotnet targets in the Bake plan')
    args = plan['target']['base']['args']
    node_major = expected_version(args['NODE_IMAGE'], node_major, 'NODE_MAJOR',
                                  r'\d+', r'(\d+)(?:[.-]|$)')
    docker_version = expected_version(args['DOCKER_IMAGE'], docker_version, 'DOCKER_VERSION',
                                      r'\d+(?:\.\d+){0,2}', r'(\d+(?:\.\d+){0,2})(?:-|$)')
    rows = []
    for kind in selected:
        target = plan['target'][kind]
        expected = '-'
        if kind == 'rust':
            expected = target['args']['RUST_VERSION']
        elif kind == 'dotnet':
            expected = target['args']['DOTNET_SDK_PACKAGE_VERSION'].split('-')[0]
        rows.append((kind, target['tags'][0], node_major, expected, docker_version))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    try:
        rows = smoke_rows(json.loads(args.plan.read_text()),
                          os.environ.get('NODE_MAJOR', ''), os.environ.get('DOCKER_VERSION', ''))
    except (KeyError, ValueError) as error:
        parser.error(str(error))
    for row in rows:
        print('\t'.join(row))


if __name__ == '__main__':
    main()
