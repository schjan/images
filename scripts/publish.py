#!/usr/bin/env python3
"""Push tested local images, then combine recorded digests without rebuilding."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

TARGETS = ('base', 'rust', 'dotnet')
ARCHITECTURES = ('amd64', 'arm64')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
TAG = re.compile(r'ghcr\.io/[a-z0-9._/-]+:[a-zA-Z0-9_][a-zA-Z0-9_.-]*')


def docker(*args):
    subprocess.run(['docker', *args], check=True)


def docker_json(*args):
    return json.loads(subprocess.check_output(['docker', *args], text=True))


def image_tags(plan):
    tags = {kind: plan['target'][kind]['tags'][0] for kind in TARGETS}
    if not all(TAG.fullmatch(tag) for tag in tags.values()):
        raise ValueError('Publication requires fully qualified GHCR image tags')
    return tags


def stage(plan, directory, arch, revision):
    tags = image_tags(plan)
    # Validate every loaded image before the first registry write.
    for tag in tags.values():
        info = docker_json('image', 'inspect', tag)[0]
        if (info['Os'], info['Architecture']) != ('linux', arch):
            raise ValueError(f'{tag} is not linux/{arch}')
    images = {}
    for kind, tag in tags.items():
        architecture_tag = f'{tag}-{arch}'
        docker('tag', tag, architecture_tag)
        docker('push', architecture_tag)
        manifest = docker_json('buildx', 'imagetools', 'inspect', architecture_tag,
                               '--format', '{{json .Manifest}}')
        digest = manifest['digest']
        if not DIGEST.fullmatch(digest):
            raise ValueError(f'Invalid registry digest for {tag}')
        images[kind] = {'tag': tag, 'digest': digest}
    directory.mkdir(parents=True, exist_ok=True)
    record = {'architecture': arch, 'revision': revision, 'images': images}
    (directory / f'digests-{arch}.json').write_text(json.dumps(record, indent=2) + '\n')


def merge(plan, directory, revision, build_tag):
    tags = image_tags(plan)
    if not re.fullmatch(r'build-[0-9]+-[0-9]+', build_tag):
        raise ValueError('Expected build-<run id>-<attempt> as immutable tag')
    sources = {kind: [] for kind in TARGETS}
    # Validate both architectures, every target and the commit before any writes.
    for arch in ARCHITECTURES:
        record = json.loads((directory / f'digests-{arch}.json').read_text())
        if record['architecture'] != arch or record['revision'] != revision:
            raise ValueError(f'Wrong architecture or source revision in {arch} record')
        if set(record['images']) != set(TARGETS):
            raise ValueError(f'Incomplete image set for {arch}')
        for kind, tag in tags.items():
            image = record['images'][kind]
            if image['tag'] != tag or not DIGEST.fullmatch(image['digest']):
                raise ValueError(f'Wrong image tag or digest for {kind}/{arch}')
            repository = tag.rsplit(':', 1)[0]
            sources[kind].append(f"{repository}@{image['digest']}")
    summary = ['## Published CI images', '', '| Image | Version tag | Build tag | Digest reference |',
               '| --- | --- | --- | --- |']
    for kind, tag in tags.items():
        repository = tag.rsplit(':', 1)[0]
        immutable = f'{repository}:{build_tag}'
        docker('buildx', 'imagetools', 'create', '--tag', tag, '--tag', immutable,
               *sources[kind])
        manifest = docker_json('buildx', 'imagetools', 'inspect', immutable,
                               '--format', '{{json .Manifest}}')
        platforms = {(entry['platform']['os'], entry['platform']['architecture'])
                     for entry in manifest['manifests']
                     if entry.get('platform', {}).get('architecture') != 'unknown'}
        if platforms != {('linux', arch) for arch in ARCHITECTURES}:
            raise ValueError(f'Unexpected published platforms for {kind}: {platforms}')
        digest = manifest['digest']
        if not DIGEST.fullmatch(digest):
            raise ValueError(f'Invalid multi-architecture digest for {kind}')
        reference = f'{repository}@{digest}'
        print(reference, flush=True)
        summary.append(f'| {kind} | `{tag}` | `{immutable}` | `{reference}` |')
    summary.append('')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('\n'.join(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('stage', 'merge'))
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--arch', choices=ARCHITECTURES)
    parser.add_argument('--build-tag')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', args.revision):
        parser.error('Expected a Git commit ID for --revision')
    plan = json.loads(args.plan.read_text())
    if args.command == 'stage':
        if not args.arch:
            parser.error('stage requires --arch')
        stage(plan, args.directory, args.arch, args.revision)
    else:
        if not args.build_tag:
            parser.error('merge requires --build-tag')
        merge(plan, args.directory, args.revision, args.build_tag)


if __name__ == '__main__':
    main()
