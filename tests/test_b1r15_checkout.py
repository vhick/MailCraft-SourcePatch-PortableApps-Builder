"""Real local Git checkout tests; no GitHub network or Windows runner required."""
from __future__ import annotations
import importlib.util
import subprocess
import tempfile
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/checkout_upstream.py'
spec = importlib.util.spec_from_file_location('checkout_module', SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


class Checkout(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'original'
        self.repo.mkdir()
        git('init', '-q', cwd=self.repo)
        git('config','user.email','test@localhost',cwd=self.repo)
        git('config','user.name','Fixture',cwd=self.repo)
        for file in mod.SOURCE_REQUIRED:
            path=self.repo/file
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('fixture',encoding='utf-8')
        android=self.repo/'apps/mailcraft-android/app/src/test/snapshots/images'
        android.mkdir(parents=True)
        (android/'work.mailcraft.android_AccountScreenshotTest_conditionalAccessDark200_add_account_conditional_access_dark_200.png').write_bytes(b'PNG')
        (self.repo/'crates/net/src/keep.rs').write_text('keep')
        git('add','.',cwd=self.repo)
        git('commit','-qm','test source',cwd=self.repo)
        git('tag','-a','v0.14.0','-m','annotated tag',cwd=self.repo)
        self.sha=git('rev-parse','HEAD',cwd=self.repo)
        self.dest=self.root/'upstream'

    def test_sparse_checkout_avoids_android_and_preserves_required_crates(self):
        mod.checkout('v0.14.0',self.sha,self.dest,str(self.repo))
        for file in mod.SOURCE_REQUIRED:
            self.assertTrue((self.dest/file).is_file(),file)
        self.assertTrue((self.dest/'crates/net/src/keep.rs').is_file())
        self.assertFalse((self.dest/'apps/mailcraft-android/app/src/test/snapshots/images').exists())
        self.assertEqual(git('rev-parse','HEAD',cwd=self.dest),self.sha)
        self.assertEqual(git('config','--local','core.longpaths',cwd=self.dest),'true')

    def test_commit_mismatch_refuses_source(self):
        with self.assertRaises(subprocess.CalledProcessError):
            mod.checkout('v0.14.0','f'*40,self.dest,str(self.repo))
        self.assertFalse(self.dest.exists())

    def test_invalid_tag_does_not_clone(self):
        with self.assertRaises(ValueError):
            mod.checkout('../main',self.sha,self.dest,str(self.repo))
        self.assertFalse(self.dest.exists())

    def test_existing_folder_refused(self):
        self.dest.mkdir()
        with self.assertRaises(RuntimeError):
            mod.checkout('v0.14.0',self.sha,self.dest,str(self.repo))
        self.assertTrue(self.dest.exists())

if __name__ == '__main__':
    unittest.main()
