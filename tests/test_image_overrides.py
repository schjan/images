"""Exercise actual Bake tag resolution and smoke-test argument generation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
DIGEST = 'sha256:' + 'a' * 64


class BakeImageOverrides(unittest.TestCase):
    def tags(self, reference):
        env = dict(os.environ, NODE_IMAGE=reference, IMAGE_PREFIX='ci')
        result = subprocess.run(['docker', 'buildx', 'bake', '--print', 'base'],
                                cwd=ROOT, env=env, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)['target']['base']['tags']

    def test_registry_ports_do_not_become_tags(self):
        for reference in ('registry.example:5000/library/node:26-trixie',
                          '[::1]:5000/library/node:26-trixie'):
            with self.subTest(reference=reference):
                self.assertEqual(self.tags(reference),
                                 ['ci-base:node26-trixie', 'ci-base:node-trixie'])

    def test_tagged_digest_keeps_its_version_tag(self):
        self.assertEqual(self.tags('registry.example:5000/library/node:26-trixie@' + DIGEST),
                         ['ci-base:node26-trixie', 'ci-base:node-trixie'])

    def test_digest_only_and_untagged_images_only_use_the_unversioned_base_tag(self):
        for reference in ('node@' + DIGEST,
                          'registry.example:5000/library/node@' + DIGEST,
                          'registry.example:5000/library/node'):
            with self.subTest(reference=reference):
                self.assertEqual(self.tags(reference), ['ci-base:node-trixie'])


class SmokeImageOverrides(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.capture = self.directory / 'docker-args.json'
        fake_docker = self.directory / 'docker'
        fake_docker.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, sys\n'
            'from pathlib import Path\n'
            'Path(os.environ["CAPTURE_DOCKER_ARGS"]).write_text(json.dumps(sys.argv[1:]))\n')
        fake_docker.chmod(0o755)

    def smoke(self, node, docker, **expectations):
        plan = {'group': {'default': {'targets': ['base']}}, 'target': {'base': {
            'tags': ['ci-base:node-trixie'],
            'args': {'NODE_IMAGE': node, 'DOCKER_IMAGE': docker}}}}
        path = self.directory / 'plan.json'
        path.write_text(json.dumps(plan))
        env = dict(os.environ, PATH=f'{self.directory}{os.pathsep}{os.environ["PATH"]}',
                   CAPTURE_DOCKER_ARGS=str(self.capture), NODE_MAJOR='', DOCKER_VERSION='')
        env.update(expectations)
        return subprocess.run(['bash', 'scripts/test-images.sh', str(path)],
                              cwd=ROOT, env=env, text=True, capture_output=True)

    def assert_versions(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.capture.read_text())
        self.assertEqual(args[-4:], ['base', '26', '-', '29.9.3'])

    def test_registry_ports_are_not_smoke_test_versions(self):
        self.assert_versions(self.smoke('registry.example:5000/library/node:26-trixie',
                                        'registry.example:5001/library/docker:29.9.3-cli'))

    def test_tagged_digests_keep_the_tag_versions(self):
        self.assert_versions(self.smoke('registry.example:5000/library/node:26-trixie@' + DIGEST,
                                        'registry.example:5001/library/docker:29.9.3-cli@' + DIGEST))

    def test_digest_only_references_accept_explicit_expectations(self):
        self.assert_versions(self.smoke('node@' + DIGEST,
                                        'registry.example:5001/library/docker@' + DIGEST,
                                        NODE_MAJOR='26', DOCKER_VERSION='29.9.3'))

    def test_missing_digest_expectations_fail_clearly_before_docker_runs(self):
        result = self.smoke('node@' + DIGEST, 'docker@' + DIGEST)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('NODE_MAJOR', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.capture.exists())

    def test_missing_docker_expectation_fails_clearly(self):
        result = self.smoke('node@' + DIGEST, 'docker@' + DIGEST, NODE_MAJOR='26')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DOCKER_VERSION', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.capture.exists())

    def test_invalid_explicit_expectations_are_rejected(self):
        for overrides in ({'NODE_MAJOR': '26\n27'}, {'DOCKER_VERSION': 'latest'}):
            with self.subTest(overrides=overrides):
                result = self.smoke('node:26-trixie', 'docker:29.9.3-cli', **overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.capture.exists())


if __name__ == '__main__':
    unittest.main()
