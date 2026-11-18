from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('twoway', ROOT/'scripts/google_pim_two_way_patch.py')
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class TwoWayPatchTests(unittest.TestCase):
    def test_missing_upstream_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError,'Missing prerequisite'):
                mod.plan(Path(temp))
    def test_no_partial_patch_on_missing_anchors(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            paths=[root/'crates/model/src/remote.rs',root/'crates/net/src/oauth.rs',root/'crates/net/src/google_pim.rs',root/'crates/ui-egui/src/google_pim.rs',root/'apps/mailcraft/src/main.rs']
            for path in paths:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('source without expected anchors')
            with self.assertRaisesRegex(RuntimeError,'source drift'):
                mod.patch(root)
            self.assertTrue(all(path.read_text()=='source without expected anchors' for path in paths))
    def test_write_scope_opt_in_and_readonly_fallback(self):
        wf=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('google_two_way_edit:',wf)
        self.assertIn('default: false',wf)
        self.assertIn('inputs.google_two_way_edit == true',wf)
        self.assertIn('scripts/google_pim_two_way_patch.py',wf)
        self.assertIn('inputs.google_calendar_contacts == true',wf)
        oauth=(ROOT/'scripts/google_pim_two_way_patch.py').read_text()
        self.assertIn('calendar.events',oauth)
        self.assertIn('auth/contacts";',oauth)
        self.assertIn('auth/calendar.readonly',oauth)
    def test_only_explicit_writes_not_deletions_or_bulk(self):
        rust=(ROOT/'patches/google_pim_write_net.rs').read_text()
        self.assertIn('method,url:&url',rust)
        self.assertIn('GooglePimEdit::NewContact',rust)
        self.assertIn('GooglePimEdit::RenameContact',rust)
        self.assertIn('GooglePimEdit::NewAppointment',rust)
        self.assertIn('GooglePimEdit::RenameAppointment',rust)
        self.assertNotIn('"DELETE"',rust)
        self.assertIn('If-Match',rust)
        self.assertIn('metadata',rust)
        self.assertIn('Network error during Google edit: outcome uncertain',rust)
        self.assertIn('https://people.googleapis.com',rust)
        self.assertIn('https://www.googleapis.com/calendar/v3',rust)
    def test_ui_requires_positive_consent_and_explicit_save(self):
        s=(ROOT/'patches/google_pim_write_ui.rs').read_text()
        self.assertIn('Save to Google',s)
        self.assertIn('editor.confirm && can_write',s)
        self.assertIn('I understand this will change data in Google',s)
        self.assertIn('self.google_pim.pending_edit=Some',s)
        self.assertIn('New Google contact',s)
        self.assertIn('New Google appointment',s)
    def test_existing_autosync_interval_stays(self):
        s=(ROOT/'patches/google_pim_ui.rs').read_text()
        self.assertIn('Duration::from_secs(15 * 60)',s)
        self.assertIn('ctx.request_repaint_after(Duration::from_secs(30))',s)
        self.assertIn('self.offline()',s)
    def test_patches_do_not_store_or_log_credentials(self):
        parts='\n'.join((ROOT/'patches'/x).read_text() for x in ['google_pim_write_model.rs','google_pim_write_net.rs','google_pim_write_ui.rs','google_pim_write_host.rs'])
        self.assertNotIn('CLIENT_SECRET=',parts)
        self.assertNotIn('refresh_token:',parts)
        self.assertNotIn('token={}',parts)

if __name__=='__main__': unittest.main()

class WholePatchFixture(unittest.TestCase):
    def test_plan_succeeds_against_b1r8_source_pattern(self):
        with tempfile.TemporaryDirectory() as temp:
            src=Path(temp)
            fixtures={
                'crates/model/src/remote.rs': '/// Where an event, a contact or a calendar comes from when an account\'s server keeps it.\n',
                'crates/net/src/oauth.rs': 'const GOOGLE_PIM_SCOPE: &str = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/contacts.readonly";\n',
                'crates/net/src/google_pim.rs': (ROOT/'patches/google_pim_net.rs').read_text(),
                'crates/ui-egui/src/google_pim.rs': (ROOT/'patches/google_pim_ui.rs').read_text(),
                'apps/mailcraft/src/main.rs': '                // The current access token came from the same Google sign-in as Gmail.\n',
            }
            for name,content in fixtures.items():
                p=src/name
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(content)
            changed=mod.plan(src)
            self.assertEqual(len(changed),5)
            self.assertIn('pub enum GooglePimEdit',changed[src/'crates/model/src/remote.rs'])
            self.assertIn('write_saved',changed[src/'crates/ui-egui/src/google_pim.rs'])
            self.assertIn('response.write_saved = true',changed[src/'apps/mailcraft/src/main.rs'])
            self.assertIn('change_key: item.pointer',changed[src/'crates/net/src/google_pim.rs'])
            self.assertIn('calendar.events',changed[src/'crates/net/src/oauth.rs'])
            # Planning is pure: no file is touched until every anchor passes.
            self.assertEqual((src/'crates/model/src/remote.rs').read_text(),fixtures['crates/model/src/remote.rs'])
