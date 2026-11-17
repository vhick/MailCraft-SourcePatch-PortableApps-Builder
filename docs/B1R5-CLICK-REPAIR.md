# b1r5 opt-in signature picture button — interaction repair

## Root-cause hypothesis

MailCraft v0.13.0 `crates/ui-egui/src/reading/view.rs` registers a body click/drag interaction using the entire current `ui.clip_rect()` in `paint()`. In b1r4 the new `ui.small_button()` was inserted at the beginning of `view::show()`, but the later full-clip interaction could overlap the button and swallow clicks.

## Patch

Immediately after drawing the preview-only consent button and optional diagnostic line, clip the **subsequent body** region to start at the current UI cursor (`egui::Rect::everything_below(ui.cursor().min.y)`). The large hit region registered by MailCraft's painter then cannot cover the new button. Regular reading mail still uses the upstream clip region and the complete outgoing HTML is unchanged.

## Acceptance

1. GitHub Actions compiles `v0.13.0` + b1r5 patch and completes static/installer validation.
2. The button is visually enabled, responds to a click, and label becomes **Hide signature pictures**.
3. After activation, progress appears (downloaded/loading/queued/failed) or a useful error message.
4. The same seven icon placeholders either become pictures or the status explains why. If buttons work but image downloads fail, log this as a new b1r6 issue rather than changing this click fix.
5. Hide reverses the opt-in. No image fetch occurs before consent.
6. A sent Gmail test retains the original HTML signature and links.
7. Offline / unavailable image service does not crash or expose secrets.
8. Revert to b1r2 preview by setting `signature_picture_button=false` if necessary.

## Limitations

This is a source patch that passed local Python tests; there is no access here to the user's running Windows desktop or GitHub Actions runtime. Visual success is not claimed until manually reproduced.
