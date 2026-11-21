from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('google_pim_patch_new',ROOT/'scripts/google_pim_patch.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Compatibility(unittest.TestCase):
    def test_legacy_hook_retained(self):
        text='        self.poll_calendar();\n        self.poll_graph();'
        self.assertEqual(mod.choose_google_poll_hook(text),'        self.poll_calendar();')
    def test_modern_lifecycle_fallback(self):
        text='pub fn logic(&mut self, ctx: &egui::Context) {\n        self.poll_graph();\n}'
        self.assertEqual(mod.choose_google_poll_hook(text),'        self.poll_graph();')
    def test_missing_modern_logic_refused(self):
        with self.assertRaises(RuntimeError):
            mod.choose_google_poll_hook('        self.poll_graph();')
    def test_duplicates_refused(self):
        with self.assertRaises(RuntimeError):
            mod.choose_google_poll_hook('pub fn logic(&mut self, ctx: &egui::Context) {\n        self.poll_graph();\n        self.poll_graph();\n}')

if __name__=='__main__': unittest.main()
