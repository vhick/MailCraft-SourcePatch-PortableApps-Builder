import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(name, script):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/script)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

native=load('b1r10_native','google_pim_native_forms_patch.py')
repair=load('b1r11_repair','b1r11_repair_patch.py')

class RepairTests(unittest.TestCase):
    def test_existing_contact_source_etag_preserved(self):
        net=(ROOT/'patches/google_pim_net.rs').read_text()
        two_way=(ROOT/'scripts/google_pim_two_way_patch.py').read_text()
        self.assertIn('metadata/sources',two_way)
        self.assertIn('"CONTACT"',two_way)
        self.assertIn('change_key: item.pointer(',two_way)
        self.assertIn('rights: Rights::Read',net, 'Old engine read-only flags must not be lifted before native delete/edit is implemented')

    def test_all_day_patch_after_native_forms_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            paths = {
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
            for name,content in paths.items():
                f=base/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content)
            native_planned=native.plan(base)
            for file, content in native_planned.items(): file.write_text(content)
            # fail closed transaction, no mutation during planning
            before={p:p.read_text() for p in native_planned}
            planned=repair.plan(base)
            self.assertEqual({p:p.read_text() for p in native_planned},before)
            self.assertIn('all_day: bool',planned[base/'crates/model/src/remote.rs'])
            self.assertIn('end_day.add_days(1).iso()',planned[base/'crates/net/src/google_pim.rs'])
            self.assertIn('all_day: params.get("allDay")',planned[base/'crates/ui-egui/src/google_pim.rs'])
            self.assertNotIn('All-day Google events are not included',planned[base/'crates/ui-egui/src/google_pim.rs'])
            self.assertNotIn('"DELETE"',planned[base/'crates/net/src/google_pim.rs'])
            for path, content in planned.items():path.write_text(content)
            with self.assertRaisesRegex(RuntimeError, 'source anchor|expected one anchor'):
                repair.plan(base)

    def test_workflow_is_optional_and_publish_disabled(self):
        yml=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('default: b1r13',yml)
        self.assertIn('scripts/b1r11_repair_patch.py --source upstream',yml)
        self.assertIn('inputs.google_native_forms == true',yml)
        self.assertIn('publish:',yml)
        self.assertIn('default: false',yml)

if __name__=='__main__': unittest.main()
