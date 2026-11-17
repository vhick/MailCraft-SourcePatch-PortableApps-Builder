#!/usr/bin/env python3
"""b1r3: manual, privacy-aware signature picture preview integration.

This extends the b1r2 compact-slot patch. It modifies ONLY reading/view.rs; no
outgoing MIME, account data, OAuth, normal mail access, or launcher changes.
The owner must click the preview's Load button; only small HTTPS images qualify.
"""
from __future__ import annotations
import argparse
from pathlib import Path

# Call host-owned image fetching only after manual opt-in. Host has network
# safety checks and returns an asynchronous receiver. Decode with the SAME
# image/probe limits already used for incoming mail; never write credentials.
PREVIEW_HELPER = r'''
/// One manually requested signature image, downloaded by the host's guarded service.
struct SignaturePictureFlight {
    url: Arc<str>,
    answer: std::sync::mpsc::Receiver<Result<Vec<u8>, String>>,
    since: std::time::Instant,
}

#[derive(Default)]
struct SignaturePicturePreview {
    started: HashSet<Arc<str>>,
    flying: Vec<SignaturePictureFlight>,
}

/// The preview is the owner's OWN draft, not received email. This is only
/// called AFTER the owner clicks "Load signature pictures" in that preview.
/// Requests are HTTPS-only, at most twelve, and only for icons explicitly
/// sized at 3..=48 pixels. Network handling remains in Services::pictures.
fn signature_picture_preview_tick(app: &MailApp, ctx: &egui::Context, doc: &Doc, id: egui::Id) {
    const MAX_ICONS: usize = 12;
    const AT_ONCE: usize = 3;
    const MAX_ICON_BYTES: usize = 512 * 1024;
    let Some(download) = &app.services.pictures else { return };
    let shared = ctx.data_mut(|d| d.get_temp_mut_or_default::<Arc<Mutex<SignaturePicturePreview>>>(id).clone());
    let mut state = shared.lock().unwrap_or_else(|e| e.into_inner());
    let mut landed: Vec<(Arc<str>, Remote)> = Vec::new();
    state.flying.retain(|flight| {
        use std::sync::mpsc::TryRecvError;
        let outcome = match flight.answer.try_recv() {
            Ok(Ok(bytes)) if bytes.len() <= MAX_ICON_BYTES && images::probe(&bytes).is_some() => {
                Some(Remote::Ready(Arc::new(bytes)))
            }
            Ok(Ok(_)) => Some(Remote::Failed(Arc::from("not a supported small image"))),
            Ok(Err(why)) => Some(Remote::Failed(images::reason(&why))),
            Err(TryRecvError::Disconnected) => Some(Remote::Failed(Arc::from("image download stopped"))),
            Err(TryRecvError::Empty) if flight.since.elapsed() > std::time::Duration::from_secs(30) => {
                Some(Remote::Failed(Arc::from("image download timed out")))
            }
            Err(TryRecvError::Empty) => None,
        };
        if let Some(result) = outcome {
            landed.push((flight.url.clone(), result));
            false
        } else {
            true
        }
    });
    let picture_store = Pictures::of(ctx);
    {
        let mut pictures = picture_store.lock().unwrap_or_else(|e| e.into_inner());
        for (url, result) in landed {
            pictures.set_remote(url, result, images::frame(ctx));
        }
        for block in mailcraft_html::images(&doc.blocks) {
            let BlockKind::Image { src, width, height, .. } = &block.kind else { continue };
            // Explicit sizes prevent tracking pixels, arbitrary large mail images,
            // banners and unbounded image requests from entering this preview path.
            if !width.is_some_and(|w| (3..=48).contains(&w))
                || !height.is_some_and(|h| (3..=48).contains(&h)) { continue }
            let url = src.trim();
            if !url.starts_with("https://") || url.len() > 2048 { continue }
            if state.started.contains(url) || pictures.remote_peek(url).is_some() { continue }
            if state.started.len() >= MAX_ICONS || state.flying.len() >= AT_ONCE { break }
            let url: Arc<str> = Arc::from(url);
            state.started.insert(url.clone());
            state.flying.push(SignaturePictureFlight {
                answer: download(url.to_string()), url, since: std::time::Instant::now(),
            });
        }
    }
    if !state.flying.is_empty() {
        ctx.request_repaint_after(std::time::Duration::from_millis(250));
    }
}
'''

PREVIEW_UI = r'''    // This control belongs only to a signature preview. It must NEVER opt
    // received mail into downloading pictures, even if a global mail setting
    // differs; only a deliberate click enables these preview image requests.
    let mut access = access;
    if matches!(place, Place::Preview) && !entry.doc.remote.is_empty() && super::remote::available(app) {
        let choice = egui::Id::new("enhanced-signature-picture-consent").with(message.body.html.as_deref().unwrap_or_default());
        let mut show = ctx.data(|d| d.get_temp::<bool>(choice)).unwrap_or(false);
        let label = if show { "Hide signature pictures" } else { "Load signature pictures (contacts external sites)" };
        if ui.small_button(label).clicked() {
            show = !show;
            ctx.data_mut(|d| d.insert_temp(choice, show));
            ctx.request_repaint();
        }
        if show {
            signature_picture_preview_tick(app, &ctx, &entry.doc, choice.with("download-state"));
            access = Access::Allowed;
        } else {
            access = Access::Blocked;
        }
    }
'''


def patch(root: Path) -> None:
    view = root / "crates/ui-egui/src/reading/view.rs"
    if not view.is_file():
        raise RuntimeError(f"Cannot find MailCraft renderer: {view}")
    raw = view.read_text(encoding="utf-8")
    # b1r2 must already be applied. Verify both the preview geometry change and
    # the exact v0.13.0 call site; fail safely before writing anything.
    if "compact_preview(matches!(place, Place::Preview))" not in raw:
        raise RuntimeError("Apply the tested b1r2 compact preview patch first")
    anchor = "    let pictures = Pictures::of(&ctx);\n    let mut pictures = pictures.lock().unwrap_or_else(|e| e.into_inner());\n    let showing = access == Access::Allowed && !entry.doc.remote.is_empty();"
    n=raw.count(anchor)
    if n != 1:
        raise RuntimeError(f"MailCraft view.rs changed: need exactly one image-preview anchor, found {n}")
    helper_anchor = "/// About how many characters of text are laid out in one frame."
    n=raw.count(helper_anchor)
    if n != 1:
        raise RuntimeError(f"MailCraft view.rs changed: need exactly one helper anchor, found {n}")
    out = raw.replace(helper_anchor, PREVIEW_HELPER + "\n" + helper_anchor, 1)
    out = out.replace(anchor, PREVIEW_UI + anchor, 1)
    view.write_text(out, encoding="utf-8", newline="\n")
    print("b1r3 signature image preview: explicit button; HTTPS small images; host guard; preview only")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args=parser.parse_args()
    patch(args.source)
