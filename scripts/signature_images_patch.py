#!/usr/bin/env python3
"""b1r4: image preview retry, supported Icons8 size fallback and visible diagnostics.

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
/// One manually requested signature icon downloaded through MailCraft's host service.
struct SignaturePictureFlight {
    url: Arc<str>,
    answer: std::sync::mpsc::Receiver<Result<Vec<u8>, String>>,
    since: std::time::Instant,
}

#[derive(Default)]
struct SignaturePicturePreview {
    started: HashSet<Arc<str>>,
    flying: Vec<SignaturePictureFlight>,
    succeeded: usize,
    failed: usize,
    last_error: Option<String>,
}

/// v1r4 fixes the b1r3 silent failure: for the owner's original Icons8 signature,
/// image URLs are kept even if the HTML parser loses their width/height.
/// Every other host still requires both explicit small dimensions. The user
/// must opt in each time; no network fetch is performed for incoming email.
fn signature_picture_urls(doc: &Doc) -> Vec<Arc<str>> {
    const MAX_ICONS: usize = 12;
    let mut result = Vec::new();
    for url in &doc.remote {
        if !url.starts_with("https://") || url.len() > 2048 { continue }
        // The exact third-party asset service used by this user's HTML signature.
        // Other signature images must retain explicit small sizes to prevent
        // accidental fetching of arbitrary large images or tracking pixels.
        let recognized_icons8 = url.starts_with("https://img.icons8.com/color/48/");
        let measured_small = mailcraft_html::images(&doc.blocks).into_iter().any(|block| {
            let BlockKind::Image { src, width, height, .. } = &block.kind else { return false };
            src.trim() == url.as_ref()
                && width.is_some_and(|w| (3..=48).contains(&w))
                && height.is_some_and(|h| (3..=48).contains(&h))
        });
        if recognized_icons8 || measured_small {
            result.push(url.clone());
            if result.len() >= MAX_ICONS { break }
        }
    }
    result
}

/// Returns live status for the button (requested, loading, succeeded, failed).
/// This runs only after explicit opt-in. Byte validation and caching reuse
/// MailCraft's standard bounded image decoding path.
fn signature_picture_preview_tick(app: &MailApp, ctx: &egui::Context, doc: &Doc, id: egui::Id) -> String {
    const AT_ONCE: usize = 3;
    const MAX_ICON_BYTES: usize = 512 * 1024;
    if app.session.prefs.offline { return "MailCraft is offline — disable Work Offline to load pictures".to_owned() }
    let Some(download) = &app.services.pictures else { return "Picture downloads are unavailable in this build".to_owned() };
    let candidates = signature_picture_urls(doc);
    if candidates.is_empty() { return "No eligible small HTTPS signature images found".to_owned() }
    let shared = ctx.data_mut(|d| d.get_temp_mut_or_default::<Arc<Mutex<SignaturePicturePreview>>>(id).clone());
    let mut state = shared.lock().unwrap_or_else(|e| e.into_inner());
    let mut landed: Vec<(Arc<str>, Remote)> = Vec::new();
    let mut failed = 0usize;
    let mut succeeded = 0usize;
    let mut error = None;
    state.flying.retain(|flight| {
        use std::sync::mpsc::TryRecvError;
        let outcome = match flight.answer.try_recv() {
            Ok(Ok(bytes)) if bytes.len() <= MAX_ICON_BYTES && images::probe(&bytes).is_some() => {
                succeeded += 1;
                Some(Remote::Ready(Arc::new(bytes)))
            }
            Ok(Ok(_)) => {
                failed += 1;
                error = Some("The server did not return a supported small image".to_owned());
                Some(Remote::Failed(Arc::from("not a supported small image")))
            }
            Ok(Err(why)) => {
                failed += 1;
                error = Some(why.chars().take(100).collect::<String>());
                Some(Remote::Failed(images::reason(&why)))
            }
            Err(TryRecvError::Disconnected) => {
                failed += 1;
                error = Some("The image download service disconnected".to_owned());
                Some(Remote::Failed(Arc::from("image download stopped")))
            }
            Err(TryRecvError::Empty) if flight.since.elapsed() > std::time::Duration::from_secs(30) => {
                failed += 1;
                error = Some("Image download timed out after 30 seconds".to_owned());
                Some(Remote::Failed(Arc::from("image download timed out")))
            }
            Err(TryRecvError::Empty) => None,
        };
        if let Some(result) = outcome {
            landed.push((flight.url.clone(), result));
            false
        } else { true }
    });
    state.failed += failed;
    state.succeeded += succeeded;
    if let Some(why) = error { state.last_error = Some(why) }

    let picture_store = Pictures::of(ctx);
    {
        let mut pictures = picture_store.lock().unwrap_or_else(|e| e.into_inner());
        for (url, outcome) in landed { pictures.set_remote(url, outcome, images::frame(ctx)); }
        for url in &candidates {
            if state.started.len() >= 12 || state.flying.len() >= AT_ONCE { break }
            if state.started.contains(url) || pictures.remote_peek(url).is_some() { continue }
            state.started.insert(url.clone());
            state.flying.push(SignaturePictureFlight {
                answer: download(url.to_string()), url: url.clone(), since: std::time::Instant::now(),
            });
        }
    }
    if !state.flying.is_empty() { ctx.request_repaint_after(std::time::Duration::from_millis(250)); }
    let downloaded = {
        let store = Pictures::of(ctx);
        let pictures = store.lock().unwrap_or_else(|e| e.into_inner());
        candidates.iter().filter(|url| matches!(pictures.remote_peek(url), Some(Remote::Ready(_)))).count()
    };
    let waiting = candidates.len().saturating_sub(state.started.len());
    let mut status = format!("Signature pictures: {} downloaded, {} loading, {} queued, {} failed", downloaded, state.flying.len(), waiting, state.failed);
    if let Some(why) = &state.last_error { status.push_str(&format!(" — last error: {why}")); }
    status
}
'''

PREVIEW_UI = r'''    // Only the user's own signature preview gets this control. Incoming email
    // continues to obey upstream remote-image privacy settings independently.
    let mut access = access;
    if matches!(place, Place::Preview) && !entry.doc.remote.is_empty() && super::remote::available(app) {
        let choice = egui::Id::new("enhanced-signature-picture-consent").with(message.body.html.as_deref().unwrap_or_default());
        let mut show = ctx.data(|d| d.get_temp::<bool>(choice)).unwrap_or(false);
        let label = if show { "Hide signature pictures" } else { "Load signature pictures (contacts external sites)" };
        if ui.small_button(label).clicked() {
            show = !show;
            ctx.data_mut(|d| d.insert_temp(choice, show));
            if show {
                let key = choice.with("download-state");
                let shared = ctx.data_mut(|d| d.get_temp_mut_or_default::<Arc<Mutex<SignaturePicturePreview>>>(key).clone());
                let mut state = shared.lock().unwrap_or_else(|e| e.into_inner());
                state.started.clear();
                state.flying.clear();
                state.succeeded = 0;
                state.failed = 0;
                state.last_error = None;
                let picture_store = Pictures::of(&ctx);
                let mut pictures = picture_store.lock().unwrap_or_else(|e| e.into_inner());
                for url in signature_picture_urls(&entry.doc) { pictures.forget_failure(&url); }
            }
            ctx.request_repaint();
        }
        if show {
            let progress = signature_picture_preview_tick(app, &ctx, &entry.doc, choice.with("download-state"));
            ui.label(egui::RichText::new(progress).small());
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
    print("b1r4 signature image preview: optional button + status; HTTPS images; host guard; preview only")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args=parser.parse_args()
    patch(args.source)
