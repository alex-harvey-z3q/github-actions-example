import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from app import build, deploy


class DemoTests(unittest.TestCase):
    def test_build_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / 'dist'
            build('Hello demo audience', '2.0.0', artifact)
            data = json.loads((artifact / 'application.json').read_text())
            self.assertEqual(data['message'], 'Hello demo audience')
            self.assertEqual(data['release'], '2.0.0')
            self.assertTrue((artifact / 'app.py').exists())

    def test_invalid_release_is_rejected(self):
        with self.assertRaises(ValueError):
            build('Hello', '../unexpected')

    def test_required_secret_fails_when_missing(self):
        with self.assertRaisesRegex(ValueError, 'DEMO_TOKEN is missing'):
            deploy(Path('unused'), 'dev', require_secret=True, token=None)

    def test_secret_is_not_in_receipt_or_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / 'dist'
            output = Path(folder) / 'deployment'
            build('Hello', '1.0.0', artifact)
            logs = io.StringIO()
            with contextlib.redirect_stdout(logs):
                receipt = deploy(artifact, 'test', True, 'local-test-value', output)
            self.assertTrue(receipt['secret_supplied'])
            self.assertNotIn('local-test-value', logs.getvalue())
            self.assertNotIn('local-test-value', (output / 'receipt.json').read_text())


if __name__ == '__main__':
    unittest.main()
