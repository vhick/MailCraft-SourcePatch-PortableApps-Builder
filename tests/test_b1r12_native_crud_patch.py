"""b1r12 native Google operations: patch transaction, auth boundaries, safety regression."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def script(file):
    spec=importlib.util.spec_from_file_location(file,ROOT/'scripts'/file)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

native=script('google_pim_native_forms_patch.py')
repair=script('b1r11_repair_patch.py')
crud=script('b1r12_native_crud_patch.py')

class NativeCrud(unittest.TestCase):
    def _fixture(self,root):
        files={
        'crates/model/src/remote.rs':(ROOT/'patches/google_pim_write_model.rs').read_text(),
        'crates/net/src/google_pim.rs': '''fn contacts() {
    let url = "https://people.googleapis.com/v1/people/me/connections?pageSize=1000&personFields=names,emailAddresses,phoneNumbers,organizations,metadata";
        let title = first_str(&item, "organizations", "title");
        result.push(RemoteContact {
            id: id.to_string(), change_key: item.pointer("/metadata/sources").and_then(Value::as_array)
                .and_then(|v| v.iter().find(|source| txt(source, "type") == "CONTACT"))
                .map(|source| txt(source, "etag").to_string()).unwrap_or_default(),
            display_name: display.to_string(), first: first.to_string(), last: last.to_string(),
            company: company.to_string(), title: title.to_string(), emails, phones, ..Default::default()
        });
}
''' + (ROOT/'patches/google_pim_write_net.rs').read_text(),
        'crates/ui-egui/src/google_pim.rs':'    pub(crate) pending_edit: Option<(Id, GooglePimEdit)>,\n'+(ROOT/'patches/google_pim_write_ui.rs').read_text(),
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
                return match app.run("people.delete", json!({"id": id})) {
                    Ok(_) => true,
                    Err(e) => {
                        self.error = e;
                        false
                    }
                };
'''
        }
        for rel,s in files.items():
            f=root/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
        for mod in (native,repair):
            changes=mod.plan(root)
            for f,s in changes.items():f.write_text(s)

    def test_composite_patch_is_guarded_and_repeat_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root)
            originals={p:p.read_bytes() for p in root.rglob('*.rs')}
            changes=crud.plan(root)
            self.assertEqual(len(changes),4)
            self.assertEqual(originals,{p:p.read_bytes() for p in root.rglob('*.rs')},'planning must not mutate files')
            model=changes[root/'crates/model/src/remote.rs']
            for variant in ('NativeUpdateEvent','NativeDeleteEvent','NativeContact','NativeDeleteContact'):
                self.assertIn(variant,model)
            net=changes[root/'crates/net/src/google_pim.rs']
            self.assertIn('method=="DELETE" { Vec::new() }',net)
            self.assertIn('If-Match',net)
            self.assertIn('updatePersonFields=',net)
            self.assertIn('personFields=names,emailAddresses,phoneNumbers,organizations,metadata,addresses,urls,birthdays,biographies',net)
            self.assertIn('biographies',net)
            self.assertIn('current!=etag',net)
            forms=changes[root/'crates/ui-egui/src/forms.rs']
            self.assertIn('google_pim_native_contact("people.delete"',forms)
            ui=changes[root/'crates/ui-egui/src/google_pim.rs']
            self.assertIn('click Delete AGAIN',ui)
            self.assertIn('google_pim_native_event',ui)
            self.assertIn('google_pim_native_contact',ui)
            self.assertIn('self.google_pim.delete_confirm = None;',ui)
            for p,s in changes.items():p.write_text(s)
            with self.assertRaisesRegex(RuntimeError,'source anchor|expected one source|native form bridge anchor'):
                crud.plan(root)

    def test_source_drift_is_refused_without_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root)
            p=root/'crates/ui-egui/src/forms.rs';p.write_text(p.read_text().replace('people.delete','people.remove'))
            before={p:p.read_bytes() for p in root.rglob('*.rs')}
            with self.assertRaisesRegex(RuntimeError,'anchor'):
                crud.plan(root)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*.rs')})

    def test_workflow_retains_safe_options(self):
        text=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        for anchor in ('default: b1r14','google_native_forms:', 'scripts/b1r11_repair_patch.py',
                       'scripts/b1r12_native_crud_patch.py','default: false','inputs.google_two_way_edit == true'):
            self.assertIn(anchor,text)
        self.assertIn('rights: Rights::Read',(ROOT/'patches/google_pim_net.rs').read_text())
        self.assertIn('If-Match',(ROOT/'patches/google_pim_write_net.rs').read_text())

if __name__=='__main__':unittest.main()
