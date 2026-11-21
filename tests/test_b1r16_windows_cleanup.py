"""Windows Git checkout cleanup regressions (portable test fixtures)."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import os
import stat
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/checkout_upstream.py'
spec = importlib.util.spec_from_file_location('checkout_cleanup_module', SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class CheckoutCleanupTests(unittest.TestCase):
    def test_permission_error_clears_readonly_bit_then_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'readonly-git-object'
            file.write_bytes(b'git object fixture')
            file.chmod(stat.S_IREAD)
            calls = []

            def simulated_unlink(path):
                calls.append(path)
                if not (os.stat(path).st_mode & stat.S_IWUSR):
                    raise PermissionError('read-only file')
                os.unlink(path)

            with self.assertRaises(PermissionError) as failure:
                simulated_unlink(str(file))
            mod._retry_readonly_removal(simulated_unlink, str(file), failure.exception)
            self.assertEqual(len(calls), 2)
            self.assertFalse(file.exists())

    def test_unrelated_error_is_not_swallowed_or_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture'
            path.write_text('test', encoding='utf-8')
            tries = []
            error = ValueError('not a file permission error')
            with self.assertRaises(ValueError):
                mod._retry_readonly_removal(lambda name: tries.append(name), str(path), error)
            self.assertEqual(tries, [])
            self.assertTrue(path.exists())

    def test_persistent_access_denial_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture'
            path.write_text('test', encoding='utf-8')
            def still_locked(name):
                raise PermissionError('file is locked by another process')
            with self.assertRaisesRegex(PermissionError, 'locked'):
                mod._retry_readonly_removal(still_locked, str(path), PermissionError('read-only'))
            self.assertTrue(path.exists())

    def test_only_disposable_checkout_path_is_cleaned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = root / 'temp-checkout'
            checkout.mkdir()
            (checkout / '.git').mkdir()
            (checkout / '.git' / 'object').write_bytes(b'git')
            other = root / 'working-data'
            other.mkdir()
            (other / 'userdata').write_text('keep')
            mod._remove_failed_checkout(checkout)
            self.assertFalse(checkout.exists())
            self.assertEqual((other / 'userdata').read_text(), 'keep')

if __name__ == '__main__':
    unittest.main()
