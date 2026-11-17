import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from resolve import stable_version
from patch import patch


class KitTests(unittest.TestCase):
    def test_semver(self):
        tags = ['v0.9.0', 'v0.13.0', 'v0.10.2', 'v0.14.0-rc.1', 'nightly']
        self.assertEqual(max(filter(stable_version, tags), key=stable_version), 'v0.13.0')
        self.assertIsNone(stable_version('v1.0.0-rc1'))

    def test_patch_and_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            files = {
                'crates/control-key/src/lib.rs': 'use std::path::{Path, PathBuf};\npub fn settings_dir() -> Option<PathBuf> {\n    if cfg!(target_os = "macos") {\nNone\n}\n',
                'apps/mailcraft/src/opened_files.rs': 'use std::path::PathBuf;\npub fn base() -> Option<PathBuf> {\n    let cache = if cfg!(windows) {\nNone\n}\n',
                'apps/mailcraft/src/secrets.rs': 'use mailcraft_host::SecretStore;\npub fn store() -> Option<std::sync::Arc<dyn SecretStore>> {\n    #[cfg(any(target_os = "windows"))]\n    {None}\n}\n'}
            for name, value in files.items():
                f = r / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(value, encoding='utf-8')
            patch(r)
            self.assertIn('MailCraftPortable.exe', (r / 'crates/control-key/src/lib.rs').read_text())
            self.assertIn('Attachments', (r / 'apps/mailcraft/src/opened_files.rs').read_text())
            self.assertIn('return None', (r / 'apps/mailcraft/src/secrets.rs').read_text())
            with self.assertRaisesRegex(RuntimeError, 'Source drift'):
                patch(r)


if __name__ == '__main__':
    unittest.main()
