"""b1r13: main-window command routing regression and fail-on-drift checks."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('main_action',ROOT/'scripts/b1r13_main_actions_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

class MainActions(unittest.TestCase):
    def fixture(self,path):
        a=path/'crates/ui-egui/src/lib.rs'
        b=path/'crates/ui-egui/src/google_pim.rs'
        a.parent.mkdir(parents=True,exist_ok=True)
        a.write_text('''pub fn enabled(&self, id: &str) -> bool {
        match self.session.registry.get(id) {
            // Cancel All, while the window has a Send/Receive under way.
}
}
pub fn execute(&mut self,id:&str,params:Value)->Result<Value,String>{
        let before: Vec<u64> = self.session.all_composing().map(|c| c.id).collect();
        let r = self.session.run(id, &params);
}
''')
        b.write_text('fn google_pim_native_event() {}\nfn google_pim_native_contact() {}\n')
        return a,b

    def test_native_toolbar_path_is_intercepted_before_local_engine(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.fixture(Path(t))
            originals=(a.read_bytes(),b.read_bytes())
            change=patch.plan(Path(t))
            self.assertEqual((a.read_bytes(),b.read_bytes()),originals,'planning is side-effect-free')
            self.assertEqual(len(change),2)
            self.assertLess(change[a].index('self.google_pim_main_action(id, &params)'),change[a].index('self.session.run(id, &params)'))
            self.assertIn('self.google_pim_main_enabled(id)',change[a])
            self.assertIn('"people.delete" | "people.edit"',change[b])
            self.assertIn('"calendar.delete" | "calendar.edit"',change[b])
            self.assertIn('self.google_pim_native_contact(command,&scoped,0)',change[b])
            self.assertIn('self.google_pim_native_event(command,&scoped)',change[b])
            self.assertIn('if params.get("ids").is_some() {return None;}',change[b])
            self.assertIn('or(self.session.sel.contact)',change[b])
            self.assertIn('or(self.session.sel.event)',change[b])
            for f,s in change.items():f.write_text(s)
            with self.assertRaisesRegex(RuntimeError,'one anchor|already applied'):
                patch.plan(Path(t))

    def test_source_drift_refuses_all_edits(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.fixture(Path(t))
            a.write_text(a.read_text().replace('self.session.run(id, &params)','other_engine(id, &params)'))
            before=(a.read_bytes(),b.read_bytes())
            with self.assertRaisesRegex(RuntimeError,'central command execution bridge'):
                patch.patch(Path(t))
            self.assertEqual((a.read_bytes(),b.read_bytes()),before)

    def test_does_not_change_local_microsoft_rights(self):
        fragment=(ROOT/'patches/b1r13_main_google_actions.rs').read_text()
        self.assertIn('OAuthProvider::Google',fragment)
        self.assertIn('_=>None',fragment)
        self.assertIn('_ => false',fragment)
        self.assertNotIn('Rights::Write',fragment)
        self.assertNotIn('calendar.owner =',fragment)
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertRegex(workflow, r'(?m)^        default: b\d+r\d+$')
        self.assertIn('scripts/b1r13_main_actions_patch.py --source upstream',workflow)
        self.assertLess(workflow.index('scripts/b1r12_native_crud_patch.py'),workflow.index('scripts/b1r13_main_actions_patch.py'))
        self.assertLess(workflow.index('scripts/b1r13_main_actions_patch.py'),workflow.index('Compile real Rust application'))

if __name__=='__main__':unittest.main()
