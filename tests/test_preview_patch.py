"""b1r2 preview patch anchor and change-scope tests."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1]/'scripts'/'preview_patch.py'
spec=importlib.util.spec_from_file_location('mc_preview_patch',MODULE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SourcePatchTests(unittest.TestCase):
    def test_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, 'Required'):
                mod.patch(Path(td))

    def test_duplicate_anchor_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'s.rs'
            p.write_text('A A',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'expected one'):
                mod.replace_once(p,'A','X')
            self.assertEqual(p.read_text(encoding='utf-8'),'A A')

    def test_missing_anchor_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'s.rs'
            p.write_text('ABC',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'expected one'):
                mod.replace_once(p,'Z','X')
            self.assertEqual(p.read_text(encoding='utf-8'),'ABC')

    def test_bundle_scope(self):
        source=MODULE.read_text(encoding='utf-8')
        self.assertIn('matches!(place, Place::Preview)',source)
        self.assertIn('cx.compact_preview && images::is_remote(src)',source)
        self.assertIn('asked(height).is_some_and(|h| h <= 48.0)',source)
        self.assertNotIn('mailcraft_engine::html::',source)
        self.assertNotIn('oauth.rs',source)
        self.assertNotIn('secrets.rs',source)

if __name__=='__main__':
    unittest.main()
