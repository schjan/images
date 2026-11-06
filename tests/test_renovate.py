"""Keep Rust's Bake/standalone pins covered by the Renovate custom manager."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[1]
RUST_FILES = ('docker-bake.hcl', 'rust/Dockerfile')


def rust_matches(path, content):
    config = json.loads((ROOT / 'renovate.json').read_text())
    matches = []
    for manager in config.get('customManagers', []):
        if (manager.get('customType') != 'regex'
                or manager.get('datasourceTemplate') != 'rust-version'
                or manager.get('depNameTemplate') != 'rust'):
            continue
        if not any(re.search(pattern[1:-1], path)
                   for pattern in manager['managerFilePatterns']):
            continue
        for pattern in manager['matchStrings']:
            # These RE2 patterns use only syntax shared with Python, except
            # for named groups: (?<name>...) becomes (?P<name>...).
            pattern = pattern.replace('(?<currentValue>', '(?P<currentValue>')
            matches.extend(re.finditer(pattern, content))
    return matches


class RustRenovate(unittest.TestCase):
    def test_both_rust_pins_are_tracked(self):
        versions = []
        for path in RUST_FILES:
            with self.subTest(path=path):
                matches = rust_matches(path, (ROOT / path).read_text())
                self.assertEqual(len(matches), 1, f'Rust tracking missing or duplicated: {path}')
                versions.append(matches[0]['currentValue'])
        self.assertEqual(len(set(versions)), 1, 'Bake and standalone Rust versions differ')

    def test_version_replacement_keeps_each_pin_tracked(self):
        for path in RUST_FILES:
            with self.subTest(path=path):
                content = (ROOT / path).read_text()
                matches = rust_matches(path, content)
                self.assertEqual(len(matches), 1)
                start, end = matches[0].span('currentValue')
                updated = content[:start] + '1.100.0' + content[end:]
                updated_matches = rust_matches(path, updated)
                self.assertEqual(len(updated_matches), 1)
                self.assertEqual(updated_matches[0]['currentValue'], '1.100.0')


if __name__ == '__main__':
    unittest.main()
