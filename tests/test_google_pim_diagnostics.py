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
        self.assertIn('default: b1r8',s)
if __name__=='__main__': unittest.main()

class TokenRegressionTests(unittest.TestCase):
    def test_fresh_access_token_before_refresh(self):
        p=(ROOT/'scripts/google_pim_patch.py').read_text()
        self.assertLess(p.index('if !request.access.is_empty()'), p.index('match mailcraft_net::oauth::refresh_google_pim'))
        self.assertIn('return response;', p)
        self.assertIn('needs_new_token', p)
        self.assertIn('error.contains(\"Google API HTTP 403\")', p)
        self.assertIn('error.is_consent_needed()', p)
        self.assertIn('error.is_refused_sign_in()', p)
        self.assertNotIn('Err(_) => response.errors.push("New Google Calendar/Contacts consent',p)
    def test_explicit_http_categories(self):
        p=(ROOT/'patches/google_pim_net.rs').read_text()
        self.assertIn('Google API HTTP 401',p)
        self.assertIn('Google API HTTP 403',p)
    def test_ui_has_live_access_and_click_acknowledgement(self):
        p=(ROOT/'patches/google_pim_ui.rs').read_text()
        for marker in ['pub access: String', 'pub expires_at: i64', 'manual_attempts', 'Google sync retry #']:
            self.assertIn(marker,p)
