import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_patch',ROOT/'scripts/google_pim_native_forms_patch.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class NativeFormsTests(unittest.TestCase):
    def test_script_fails_on_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('crates/model/src/remote.rs','crates/net/src/google_pim.rs','crates/ui-egui/src/google_pim.rs','crates/ui-egui/src/forms.rs'):
                f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('unrelated')
            with self.assertRaisesRegex(RuntimeError,'source anchor'):
                mod.plan(root)
            self.assertEqual((root/'crates/model/src/remote.rs').read_text(),'unrelated')
    def test_transaction_plan_with_b1r9_anchors(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            files={
                'crates/model/src/remote.rs': (ROOT/'patches/google_pim_write_model.rs').read_text(),
                'crates/net/src/google_pim.rs': (ROOT/'patches/google_pim_write_net.rs').read_text(),
                'crates/ui-egui/src/google_pim.rs': (ROOT/'patches/google_pim_write_ui.rs').read_text(),
                'crates/ui-egui/src/forms.rs': '''fn event() {
            let ran = if asks { app.run(command, params) } else { app.execute(command, params) };
}
        id: Option<Id>,
        first: String,
        last: String,
        display: String,
fn contact() {
            let account = self.id.and_then(|id| app.session.mailbox.contact(id)).map_or(0, |c| c.origin.account);
            let categories = app.session.mailbox.categories_of(account).to_vec();
            body(ui, |ui| {
                row(ui, tl!("First name"), |ui| {
            match run.map(|(command, params)| app.execute(command, params)) {
}
'''
            }
            for name,txt in files.items():
                f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(txt)
            result=mod.plan(root)
            self.assertEqual(len(result),4)
            self.assertIn('NativeEvent',result[root/'crates/model/src/remote.rs'])
            self.assertIn('sendUpdates={send}',result[root/'crates/net/src/google_pim.rs'])
            self.assertIn('google_pim_native_event',result[root/'crates/ui-egui/src/forms.rs'])
            self.assertIn('google_pim_native_contact',result[root/'crates/ui-egui/src/forms.rs'])
            self.assertIn('This computer (local)',result[root/'crates/ui-egui/src/forms.rs'])
            self.assertIn('Google edit queued',result[root/'crates/ui-egui/src/google_pim.rs'])
            # No files mutated during the planning phase.
            self.assertEqual((root/'crates/model/src/remote.rs').read_text(),files['crates/model/src/remote.rs'])
    def test_guardrails_and_unsupported_fields(self):
        ui=(ROOT/'patches/google_pim_native_ui.rs').read_text()
        net=(ROOT/'patches/google_pim_native_net.rs').read_text()
        for marker in ['recurrence','allDay','categories','online','send','offline()','busy.is_some()',
                       'Google contact editing currently supports first and last names only',
                       'Google edit queued from MailCraft form']:
            self.assertIn(marker,ui)
        for marker in ['sendUpdates={send}','timeZone','If-Match','50 guests']:
            if marker == 'If-Match':
                self.assertIn(marker,(ROOT/'patches/google_pim_write_net.rs').read_text())
            else:self.assertIn(marker,net)
        self.assertNotIn('DELETE',net)
        self.assertNotIn('MAILCRAFT_GOOGLE_CLIENT_SECRET=',ui+net)
        self.assertNotIn('contacts.updateContact',ui)
    def test_workflow_reversible_opt_in(self):
        yml=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('google_native_forms:',yml)
        self.assertIn('default: b1r13',yml)
        self.assertIn('scripts/google_pim_native_forms_patch.py --source upstream',yml)
        self.assertIn('inputs.google_two_way_edit == true && inputs.google_native_forms == true',yml)
        self.assertIn('publish:',yml)

if __name__=='__main__': unittest.main()
