from pathlib import Path
import importlib.util
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'signature_images_patch.py'
spec=importlib.util.spec_from_file_location('signature_images_patch',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SignatureImagePatchTests(unittest.TestCase):
    def test_missing_source_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'Cannot find'):
                module.patch(Path(tmp))
    def test_older_source_refused_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'crates/ui-egui/src/reading/view.rs'
            p.parent.mkdir(parents=True)
            p.write_text('unpatched view',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'b1r2'):
                module.patch(Path(tmp))
            self.assertEqual(p.read_text(encoding='utf-8'),'unpatched view')
    def test_one_anchor_fixture_and_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'crates/ui-egui/src/reading/view.rs'
            p.parent.mkdir(parents=True)
            p.write_text("/// About how many characters of text are laid out in one frame.\n// compact_preview(matches!(place, Place::Preview))\n    let pictures = Pictures::of(&ctx);\n    let mut pictures = pictures.lock().unwrap_or_else(|e| e.into_inner());\n    let showing = access == Access::Allowed && !entry.doc.remote.is_empty();\n",encoding='utf-8')
            module.patch(Path(tmp))
            s=p.read_text(encoding='utf-8')
            self.assertIn('Load signature pictures (contacts external sites)',s)
            self.assertIn('signature_picture_preview_tick',s)
            self.assertIn('pictures.set_remote',s)
            self.assertIn('3..=48',s)
            self.assertIn('const MAX_ICONS: usize = 12',s)
            self.assertIn('img.icons8.com/color/48/',s)
            self.assertIn('last error:',s)
            self.assertIn('forget_failure',s)
            self.assertIn('ui.set_clip_rect(ui.clip_rect().intersect(egui::Rect::everything_below(signature_body_top)))',s)
            self.assertIn('let signature_body_top = ui.cursor().min.y;',s)
            self.assertIn('access = Access::Blocked',s)
    def test_preview_button_excluded_from_body_interaction(self):
        helper=module.PREVIEW_UI
        button=helper.index('if ui.small_button(label).clicked()')
        clip=helper.index('ui.set_clip_rect(ui.clip_rect().intersect(egui::Rect::everything_below(signature_body_top)))')
        self.assertLess(button, clip)
        self.assertIn('if matches!(place, Place::Preview)', helper)
        # Upstream view::paint's full clip-rect click surface must start below the control.
        self.assertIn('let signature_body_top = ui.cursor().min.y;', helper)

    def test_bad_anchor_refuses_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'crates/ui-egui/src/reading/view.rs'
            p.parent.mkdir(parents=True)
            raw='compact_preview(matches!(place, Place::Preview))\nnot the right anchor'
            p.write_text(raw,encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'anchor'):
                module.patch(Path(tmp))
            self.assertEqual(p.read_text(encoding='utf-8'),raw)

if __name__=='__main__':unittest.main()
