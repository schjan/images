"""Keep toolchain pins and Bake overrides covered by Renovate."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[1]


def dependency_matches(datasource, name, path, content):
    config = json.loads((ROOT / 'renovate.json').read_text())
    matches = []
    for manager in config.get('customManagers', []):
        if (manager.get('customType') != 'regex'
                or manager.get('datasourceTemplate') != datasource):
            continue
        if not any(re.search(pattern[1:-1], path)
                   for pattern in manager['managerFilePatterns']):
            continue
        for pattern in manager['matchStrings']:
            # These RE2 patterns use only syntax shared with Python, except
            # for named groups: (?<name>...) becomes (?P<name>...).
            pattern = re.sub(r'\(\?<([a-zA-Z]+)>', r'(?P<\1>', pattern)
            for match in re.finditer(pattern, content):
                dep_name = manager.get('depNameTemplate') or match['depName']
                if dep_name == name:
                    matches.append(match)
    return matches


class RenovatePins(unittest.TestCase):
    def assert_pins(self, datasource, name, paths, next_version):
        versions = []
        for path in paths:
            with self.subTest(path=path, dependency=name):
                content = (ROOT / path).read_text()
                matches = dependency_matches(datasource, name, path, content)
                self.assertEqual(len(matches), 1, f'Tracking missing or duplicated: {path}')
                versions.append(matches[0]['currentValue'])
                start, end = matches[0].span('currentValue')
                updated = content[:start] + next_version + content[end:]
                future = dependency_matches(datasource, name, path, updated)
                self.assertEqual(len(future), 1)
                self.assertEqual(future[0]['currentValue'], next_version)
        self.assertEqual(len(set(versions)), 1, 'Bake and standalone versions differ')

    def test_rust_pins_are_tracked_and_remain_updatable(self):
        self.assert_pins('rust-version', 'rust',
                         ('docker-bake.hcl', 'rust/Dockerfile'), '1.100.0')

    def test_dotnet_pins_are_tracked_and_remain_updatable(self):
        self.assert_pins('deb', 'dotnet-sdk-10.0',
                         ('docker-bake.hcl', 'dotnet/Dockerfile'), '10.0.404-1')

    def test_node_and_docker_bake_overrides_match_dockerfile_defaults(self):
        bake = (ROOT / 'docker-bake.hcl').read_text()
        dockerfile = (ROOT / 'base/Dockerfile').read_text()
        for variable, name in (('NODE_IMAGE', 'node'), ('DOCKER_IMAGE', 'docker')):
            with self.subTest(variable=variable):
                dep_name = f'docker.io/library/{name}'
                matches = dependency_matches('docker', dep_name, 'docker-bake.hcl', bake)
                self.assertEqual(len(matches), 1)
                pin = re.search(rf'ARG {variable}={re.escape(dep_name)}:([^\s@]+)', dockerfile)
                self.assertIsNotNone(pin)
                self.assertEqual(matches[0]['currentValue'], pin[1])

    def test_docker_digest_is_preserved_by_extraction(self):
        digest = 'sha256:' + 'a' * 64
        content = 'variable "NODE_IMAGE" { default = "docker.io/library/node:26-trixie@' + digest + '" }'
        matches = dependency_matches('docker', 'docker.io/library/node', 'docker-bake.hcl', content)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['currentValue'], '26-trixie')
        self.assertEqual(matches[0]['currentDigest'], digest)


if __name__ == '__main__':
    unittest.main()
