"""Publication gates and digest handoff checks; never access a real registry."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('publish', Path(__file__).parents[1] / 'scripts/publish.py')
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class Publication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.revision = 'a' * 40
        self.plan = {'target': {kind: {'tags': [f'ghcr.io/example/images/ci-{kind}:version']}
                                for kind in publish.TARGETS}}
        self.tags = publish.image_tags(self.plan)
        for index, arch in enumerate(publish.ARCHITECTURES, start=1):
            record = {'architecture': arch, 'revision': self.revision, 'images': {
                kind: {'tag': tag, 'digest': 'sha256:' + str(index) * 64}
                for kind, tag in self.tags.items()}}
            (self.directory / f'digests-{arch}.json').write_text(json.dumps(record))

    def merge(self):
        publish.merge(self.plan, self.directory, self.revision, 'build-123-1')

    @patch.object(publish, 'docker')
    def test_missing_architecture_blocks_all_manifest_writes(self, docker):
        (self.directory / 'digests-arm64.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.merge()
        docker.assert_not_called()

    @patch.object(publish, 'docker')
    def test_bad_final_record_blocks_every_manifest_write(self, docker):
        path = self.directory / 'digests-arm64.json'
        original = json.loads(path.read_text())
        for fault in ('revision', 'tag', 'digest', 'missing_target'):
            with self.subTest(fault=fault):
                record = copy.deepcopy(original)
                if fault == 'revision':
                    record['revision'] = 'b' * 40
                elif fault == 'missing_target':
                    del record['images']['dotnet']
                else:
                    record['images']['dotnet'][fault] = 'invalid'
                path.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    self.merge()
                docker.assert_not_called()

    @patch.object(publish, 'docker_json')
    @patch.object(publish, 'docker')
    def test_stage_checks_local_architecture_before_push(self, docker, inspect):
        inspect.return_value = [{'Os': 'linux', 'Architecture': 'amd64'}]
        with self.assertRaises(ValueError):
            publish.stage(self.plan, self.directory, 'arm64', self.revision)
        docker.assert_not_called()

    @patch.object(publish, 'docker_json')
    @patch.object(publish, 'docker')
    def test_stage_records_registry_digests_of_tested_images(self, docker, inspect):
        inspect.side_effect = [
            *([{'Os': 'linux', 'Architecture': 'arm64'}] for _ in publish.TARGETS),
            *({'digest': 'sha256:' + '3' * 64} for _ in publish.TARGETS),
        ]
        publish.stage(self.plan, self.directory, 'arm64', self.revision)
        record = json.loads((self.directory / 'digests-arm64.json').read_text())
        self.assertEqual(record['revision'], self.revision)
        for kind, tag in self.tags.items():
            self.assertEqual(record['images'][kind]['digest'], 'sha256:' + '3' * 64)
            self.assertIn(unittest.mock.call('tag', tag, tag + '-arm64'), docker.call_args_list)
            self.assertIn(unittest.mock.call('push', tag + '-arm64'), docker.call_args_list)

    @patch.object(publish, 'docker_json')
    @patch.object(publish, 'docker')
    def test_merge_uses_content_digests_and_emits_pinned_summary(self, docker, inspect):
        inspect.return_value = {'digest': 'sha256:' + '4' * 64, 'manifests': [
            {'platform': {'os': 'linux', 'architecture': arch}}
            for arch in publish.ARCHITECTURES]}
        summary = self.directory / 'summary.md'
        with patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': str(summary)}):
            self.merge()
        self.assertEqual(docker.call_count, 3)
        for call, (kind, tag) in zip(docker.call_args_list, self.tags.items()):
            repository = tag.rsplit(':', 1)[0]
            self.assertEqual(call.args, ('buildx', 'imagetools', 'create', '--tag', tag,
                '--tag', repository + ':build-123-1', repository + '@sha256:' + '1' * 64,
                repository + '@sha256:' + '2' * 64))
            self.assertIn(repository + '@sha256:' + '4' * 64, summary.read_text())

    @patch.object(publish, 'docker')
    def test_unqualified_tags_are_refused(self, docker):
        self.plan['target']['rust']['tags'] = ['ci-rust:local']
        with self.assertRaises(ValueError):
            self.merge()
        docker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
