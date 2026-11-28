"""Tests for the stand-ins; these are NOT MUnit tests or Mule-runtime validation."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('demo_platform', Path(__file__).parents[1] / 'scripts/platform.py')
platform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform)


class PlatformTests(unittest.TestCase):
    def fixture(self, folder):
        repository = Path(folder) / 'exchange'
        path = repository / 'org/example/mule/synthetic-timetable-api/1.0.0'
        path.mkdir(parents=True)
        jar = path / 'synthetic-timetable-api-1.0.0-mule-application.jar'
        # Only a test fixture, never used by the Maven build/publish workflow.
        with zipfile.ZipFile(jar, 'w') as archive:
            archive.writestr('timetable.json', json.dumps([{'id': 'demo-101', 'day': 'monday'}]))
        (path / 'synthetic-timetable-api-1.0.0.pom').write_text('<project/>')
        with contextlib.redirect_stdout(io.StringIO()):
            platform.manifest(repository, '1.0.0')
        return repository, jar

    def test_selects_published_package(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, jar = self.fixture(folder)
            data, selected = platform.select(repo, '1.0.0')
            self.assertEqual(selected, jar.resolve())
            self.assertEqual(data['munit']['executed'], 0)

    def test_rejects_changed_jar(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, jar = self.fixture(folder)
            jar.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                platform.select(repo, '1.0.0')

    def test_rejects_wrong_version(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, _ = self.fixture(folder)
            with self.assertRaisesRegex(ValueError, 'coordinates'):
                platform.select(repo, '2.0.0')

    def test_rejects_wrong_run(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, _ = self.fixture(folder)
            with self.assertRaisesRegex(ValueError, 'different workflow run'):
                platform.select(repo, '1.0.0', '999')

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'escapes'):
                platform.inside(Path(folder), '../outside.jar')

    def test_missing_secret_fails_before_deployment(self):
        with patch.dict(os.environ, {'DEMO_TOKEN': ''}):
            with self.assertRaisesRegex(ValueError, 'required'):
                platform.deploy(Path('not-used'), '1.0.0', 'DEV', require_secret=True)

    def test_http_checks_and_receipt_never_expose_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, _ = self.fixture(folder)
            previous = Path.cwd()
            try:
                os.chdir(folder)
                logs = io.StringIO()
                with patch.dict(os.environ, {'DEMO_TOKEN': 'inert-test-value', 'GITHUB_STEP_SUMMARY': ''}), contextlib.redirect_stdout(logs):
                    receipt = platform.deploy(repo, '1.0.0', 'UAT', require_secret=True)
                self.assertEqual(receipt['smoke_checks'], 3)
                self.assertFalse(receipt['rebuilt'])
                self.assertFalse(receipt['mule_runtime_executed'])
                self.assertNotIn('inert-test-value', logs.getvalue())
                self.assertNotIn('inert-test-value', Path('receipts/UAT.json').read_text())
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
