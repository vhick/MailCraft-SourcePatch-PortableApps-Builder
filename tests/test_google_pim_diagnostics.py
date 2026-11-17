import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DiagnosticsTests(unittest.TestCase):
    def test_manual_refresh_guard_and_visible_feedback(self):
        s=(ROOT/'patches/google_pim_ui.rs').read_text()
        for fragment in ['Sync Google now', 'google_pim.last.clear()', 'google_pim_tick(ui.ctx())', 'last_summary', 'Google sync completed:', 'Google sync problem:']:
            self.assertIn(fragment,s)
        self.assertIn('self.google_pim.busy.is_none()',s)
        self.assertIn('self.offline()',s)
        self.assertNotIn('method: "POST"', (ROOT/'patches/google_pim_net.rs').read_text())
    def test_ui_anchor_changes(self):
        s=(ROOT/'scripts/google_pim_patch.py').read_text()
        self.assertIn('Calendar Google status and manual refresh',s)
        self.assertIn('People Google status and manual refresh',s)
        self.assertIn('google_pim_controls(ui)',s)
    def test_builder_toggle(self):
        s=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('google_calendar_contacts:',s)
        self.assertIn('default: b1r7',s)
if __name__=='__main__': unittest.main()
