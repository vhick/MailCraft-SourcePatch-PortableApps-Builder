#!/usr/bin/env python3
"""b1r14: retire the redundant Google create/rename controls in native mode.

Apply only after b1r13 on MailCraft v0.13.0. The b1r9 API worker,
Google PIM status, manual Sync Google now, 15-minute auto-refresh and
b1r12/b1r13 native form bridges MUST remain unchanged.

This intentionally leaves b1r9's legacy controls available in builds where
`google_native_forms=false` (no b1r14 step). Plan first, then write, with
strict fail-closed exact anchors.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_UI = (ROOT / 'patches/google_pim_write_ui.rs')


def exactly_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f'b1r14 {label}: expected exactly one source anchor, found {count}; STOP'
        )
    return content.replace(old, new, 1)


def plan(source: Path) -> dict[Path, str]:
    ui = source / 'crates/ui-egui/src/google_pim.rs'
    if not ui.is_file():
        raise RuntimeError('b1r14 missing Google PIM UI: apply b1r13 first')
    old = ui.read_text(encoding='utf-8')
    # Guard against silently removing the working fallback buttons on a
    # b1r9-only build, or a stale/partial native patch chain.
    for marker in (
        'pub(crate) fn google_pim_main_action',
        'pub(crate) fn google_pim_native_event',
        'pub(crate) fn google_pim_native_contact',
        'pub(crate) fn google_pim_controls',
        'Sync Google now',
        'Duration::from_secs(15 * 60)',
    ):
        if marker not in old:
            raise RuntimeError(f'b1r14 missing required native/sync anchor: {marker}; STOP')

    # Remove b1r9's obsolete editor state, not the shared pending_edit queue
    # used by the now-working native forms and Google API service.
    updated = exactly_once(
        old,
        '    pub(crate) editor: GooglePimEditor,\n',
        '',
        'legacy editor state',
    )
    # The legacy controls are rendered AFTER the separate manual-sync bar.
    # Remove only their display/window hooks. Keep the entire sync bar.
    updated = exactly_once(
        updated,
        '        self.google_pim_edit_controls(ui);\n'
        '        self.google_pim_edit_window(ui.ctx());',
        '        // b1r14: native Calendar and People forms replace legacy Google action buttons.',
        'legacy button and editor-window hooks',
    )
    # The extra editor is exclusively used by the retired buttons. Remove its
    # types and implementation to avoid unused-item warnings. Other b1r12/13
    # native form implementations reside elsewhere in google_pim.rs.
    retired = '\n' + LEGACY_UI.read_text(encoding='utf-8')
    updated = exactly_once(updated, retired, '', 'legacy editor implementation')

    # Verify unchanged manual sync and core Google mutation bridges.
    preserved = (
        'Sync Google now',
        'Duration::from_secs(15 * 60)',
        'google_pim_main_action',
        'google_pim_native_event',
        'google_pim_native_contact',
        'google_pim.pending_edit',
        'google_pim.manual_attempts',
    )
    for marker in preserved:
        if old.count(marker) - retired.count(marker) != updated.count(marker):
            raise RuntimeError(f'b1r14 would change preserved Google functionality: {marker}; STOP')
    for marker in ('GooglePimEditor', 'GoogleEditorMode', 'google_pim_edit_controls', 'google_pim_edit_window'):
        if marker in updated:
            raise RuntimeError(f'b1r14 left obsolete editor references: {marker}; STOP')
    return {ui: updated}


def patch(source: Path) -> None:
    edits = plan(source)
    for path, content in edits.items():
        path.write_text(content, encoding='utf-8')
    print('b1r14 removed four redundant Google action buttons; Sync Google now preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    patch(parser.parse_args().source)
