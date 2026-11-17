#!/usr/bin/env python3
"""MailCraft b1r2: preview-only geometry for small remote signature pictures.

The ordinary reading pane, outgoing MIME, OAuth, contacts/calendar, and PortableApps
profile/launcher remain untouched. Intentionally does NOT fetch web images.
Fail closed on upstream source drift; GitHub Actions compiles the modified source.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(path: Path, before: str, after: str) -> None:
    raw = path.read_text(encoding="utf-8")
    count = raw.count(before)
    if count != 1:
        raise RuntimeError(f"Refusing MailCraft source drift: {path}: expected one anchor, got {count}")
    path.write_text(raw.replace(before, after, 1), encoding="utf-8", newline="\n")


def patch(root: Path) -> None:
    layout = root / "crates/ui-egui/src/reading/layout.rs"
    view = root / "crates/ui-egui/src/reading/view.rs"
    if not layout.is_file() or not view.is_file():
        raise RuntimeError("Required MailCraft renderer files were not found; refusing patch")
    # Preflight all source anchors BEFORE mutating either file.
    modifications = [
      (layout, '    remote: bool,\n    /// The message brings its own design for a dark window,',
        '    remote: bool,\n    /// A preview may show small remote image placeholders at their declared size.\n    compact_preview: bool,\n    /// The message brings its own design for a dark window,'),
      (layout, '    pub fn showing_remote(self, remote: bool) -> Laid {\n        Laid { remote, ..self }\n    }',
        '    pub fn showing_remote(self, remote: bool) -> Laid {\n        Laid { remote, ..self }\n    }\n    /// Preview only: keep small externally hosted icons in their declared slots.\n    /// Neither network access nor the message MIME is affected.\n    pub fn compact_preview(self, compact_preview: bool) -> Laid {\n        Laid { compact_preview, ..self }\n    }'),
      (layout, '            remote: self.remote,\n            frame: images::frame(ctx),',
        '            remote: self.remote,\n            compact_preview: self.compact_preview,\n            frame: images::frame(ctx),'),
      (layout, '    remote: bool,\n    frame: u64,',
        '    remote: bool,\n    compact_preview: bool,\n    frame: u64,'),
      (layout, '    let wanted = CHIP_HEIGHT + text;\n    Tile { size: vec2(wanted.min((room - padding).max(CHIP_HEIGHT)), CHIP_HEIGHT), block, padding: None, data: None, label, described, wanted }',
        """    // A signature preview intentionally does not fetch its web images. For a tiny
    // icon (<48px), however, a 100px-wide label placeholder makes a seven-icon
    // layout table stack vertically. Keep the source picture's dimensions in
    // previews, while preserving the safe, blocked-image placeholder. Normal
    // mail reading, the actual image bytes and outgoing HTML are unchanged.
    // Keep wide, short banners (for example 500x24) untouched. Only genuinely
    // small images with two explicit dimensions get compact preview slots.
    if cx.compact_preview && images::is_remote(src)
        && asked(width).is_some_and(|w| w <= 48.0)
        && asked(height).is_some_and(|h| h <= 48.0)
    {
        let slot_width = asked(width).unwrap_or(CHIP_HEIGHT).clamp(12.0, 48.0);
        let slot_height = asked(height).unwrap_or(CHIP_HEIGHT).clamp(12.0, 48.0);
        return Tile {
            size: vec2(slot_width.min((room - padding).max(1.0)), slot_height),
            block,
            padding: None,
            data: None,
            label,
            described,
            wanted: slot_width,
        };
    }
    let wanted = CHIP_HEIGHT + text;
    Tile { size: vec2(wanted.min((room - padding).max(CHIP_HEIGHT)), CHIP_HEIGHT), block, padding: None, data: None, label, described, wanted }"""),
      (view, '                    .showing_remote(showing)\n                    .on_light_page(light)',
        '                    .showing_remote(showing)\n                    .compact_preview(matches!(place, Place::Preview))\n                    .on_light_page(light)'),
      (view, '            Laid::new(width).showing_remote(showing).on_light_page(light).sender_dark',
        '            Laid::new(width).showing_remote(showing).compact_preview(matches!(place, Place::Preview)).on_light_page(light).sender_dark'),
    ]
    for path, before, after in modifications:
        count = path.read_text(encoding='utf-8').count(before)
        if count != 1:
            raise RuntimeError(f"Refusing preview patch: {path.name}: anchor count {count}, need one: {before[:80]!r}")
    for path, before, after in modifications:
        replace_once(path, before, after)
    print("PREVIEW-PATCHED: small remote icon slots in Place::Preview only; mail/OAuth unchanged")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    patch(args.source)
