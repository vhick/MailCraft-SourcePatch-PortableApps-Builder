"""b1r14: remove obsolete b1r9 action UI without affecting sync/native CRUD."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cleanup', ROOT / 'scripts/b1r14_remove_legacy_google_buttons.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class LegacyGoogleButtonsCleanup(unittest.TestCase):
    def prepare(self, directory: Path) -> Path:
        path = directory / 'crates/ui-egui/src/google_pim.rs'
        path.parent.mkdir(parents=True, exist_ok=True)
        # Representative post-b1r13 source. The retired block comes from the
        # exact fragment that b1r9 injects; the retained native block is distinct.
        source = '''pub(crate) struct GooglePimState {
    pub(crate) manual_attempts: u64,
    pub(crate) pending_edit: Option<(Id, GooglePimEdit)>,
    pub(crate) editor: GooglePimEditor,
}
impl MailApp {
    pub(crate) fn google_pim_controls(&mut self, ui: &mut egui::Ui) {
        if ui.button("Sync Google now").clicked() {
            self.google_pim.manual_attempts += 1;
        }
        let r = Duration::from_secs(15 * 60);
        self.google_pim_edit_controls(ui);
        self.google_pim_edit_window(ui.ctx());
    }
}
impl MailApp {
    pub(crate) fn google_pim_native_event(&mut self) {
        self.google_pim.pending_edit = None;
    }
    pub(crate) fn google_pim_native_contact(&mut self) {}
}
'''
        source += '\n' + (ROOT / 'patches/google_pim_write_ui.rs').read_text(encoding='utf-8')
        source += '\n' + (ROOT / 'patches/b1r13_main_google_actions.rs').read_text(encoding='utf-8')
        path.write_text(source, encoding='utf-8')
        return path

    def test_only_redundant_controls_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            ui = self.prepare(Path(temp))
            before = ui.read_bytes()
            changed = cleanup.plan(Path(temp))
            self.assertEqual(ui.read_bytes(), before, 'planning cannot mutate source')
            self.assertEqual(list(changed), [ui])
            new = changed[ui]
            for text in ('Sync Google now', 'manual_attempts', 'Duration::from_secs(15 * 60)',
                         'google_pim_native_event', 'google_pim_native_contact',
                         'google_pim_main_action', 'google_pim.pending_edit'):
                self.assertIn(text, new)
            for text in ('New Google contact…', 'New Google appointment…',
                         'Rename selected Google contact…', 'Rename selected Google event…',
                         'GooglePimEditor', 'GoogleEditorMode', 'google_pim_edit_controls(',
                         'google_pim_edit_window('):
                self.assertNotIn(text, new)
            self.assertIn('native Calendar and People forms replace legacy Google', new)
            cleanup.patch(Path(temp))
            self.assertEqual(ui.read_text(), new)
            with self.assertRaisesRegex(RuntimeError, 'legacy editor state'):
                cleanup.plan(Path(temp))

    def test_fails_closed_without_main_window_native_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            ui = self.prepare(Path(temp))
            ui.write_text(ui.read_text().replace('pub(crate) fn google_pim_main_action', 'pub(crate) fn removed'))
            before = ui.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'google_pim_main_action'):
                cleanup.patch(Path(temp))
            self.assertEqual(ui.read_bytes(), before)

    def test_fails_closed_when_sync_control_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            ui = self.prepare(Path(temp))
            ui.write_text(ui.read_text().replace('"Sync Google now"', '"Other action"'))
            before = ui.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'Sync Google now'):
                cleanup.patch(Path(temp))
            self.assertEqual(ui.read_bytes(), before)

    def test_fails_closed_if_legacy_source_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            ui = self.prepare(Path(temp))
            ui.write_text(ui.read_text().replace('New Google contact…', 'New Google person…'))
            before = ui.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'legacy editor implementation'):
                cleanup.patch(Path(temp))
            self.assertEqual(ui.read_bytes(), before)

    def test_pipeline_after_b1r13_only_in_native_mode(self):
        yaml = (ROOT / '.github/workflows/build-portableapps.yml').read_text()
        self.assertRegex(yaml, r'(?m)^        default: b\d+r\d+$')
        self.assertIn('scripts/b1r14_remove_legacy_google_buttons.py --source upstream', yaml)
        self.assertLess(yaml.index('scripts/b1r13_main_actions_patch.py --source upstream'),
                        yaml.index('scripts/b1r14_remove_legacy_google_buttons.py --source upstream'))
        self.assertLess(yaml.index('scripts/b1r14_remove_legacy_google_buttons.py --source upstream'),
                        yaml.index('Compile real Rust application'))
        self.assertIn('inputs.google_native_forms == true', yaml)
        self.assertIn('inputs.google_two_way_edit == true', yaml)


if __name__ == '__main__':
    unittest.main()
