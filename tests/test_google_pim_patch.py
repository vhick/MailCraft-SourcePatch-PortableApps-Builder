from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('google_pim_patch', ROOT/'scripts/google_pim_patch.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class GooglePimPatchTests(unittest.TestCase):
    def test_nonexistent_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, 'missing upstream'):
                MOD.patch(Path(temp))
    def test_replaced_text_requires_exactly_one_anchor(self):
        with self.assertRaisesRegex(RuntimeError, 'source drift'):
            MOD.replace_once('a a', 'a', 'new', 'duplicate')
        with self.assertRaisesRegex(RuntimeError, 'source drift'):
            MOD.replace_once('b', 'a', 'new', 'missing')
    def test_net_uses_only_gets_and_fixed_hosts(self):
        s = (ROOT/'patches/google_pim_net.rs').read_text()
        self.assertIn('method: "GET"',s)
        self.assertNotIn('method: "POST"',s)
        self.assertIn('https://www.googleapis.com/calendar/v3/',s)
        self.assertIn('https://people.googleapis.com/v1/people/me/connections?',s)
        self.assertIn('Rights::Read',s)
        self.assertIn('complete: true',s)
        self.assertIn('if calendar.main { String::new() }', s)
    def test_ui_is_mail_independent(self):
        s = (ROOT/'patches/google_pim_ui.rs').read_text()
        self.assertIn('self.poll_google_pim', (ROOT/'scripts/google_pim_patch.py').read_text())
        self.assertIn('self.google_pim_tick', (ROOT/'scripts/google_pim_patch.py').read_text())
        self.assertIn('remote::apply_calendars',s)
        self.assertIn('remote::apply_contacts',s)
        self.assertIn('remote::apply_events',s)
        self.assertIn('self.session.openings()',s)
        self.assertIn('15 * 60',s)
        self.assertNotIn('write_calendar',s)
    def test_oauth_preserves_mail_scope(self):
        s = (ROOT/'scripts/google_pim_patch.py').read_text()
        self.assertIn('const GOOGLE_SCOPE: &str = "https://mail.google.com/ openid email";',s)
        self.assertIn('refresh_google_pim',s)
        self.assertIn('scope: format!(\"{GOOGLE_SCOPE} {GOOGLE_PIM_SCOPE}\")',s)
        self.assertNotIn('consent: GOOGLE_PIM_SCOPE.into()',s)
    def test_all_patches_are_reversible(self):
        s = (ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('google_calendar_contacts:',s)
        self.assertIn('inputs.google_calendar_contacts == true',s)
        self.assertIn('scripts/google_pim_patch.py --source upstream',s)
        self.assertIn('inputs.signature_picture_button == true',s)

if __name__ == '__main__': unittest.main()
