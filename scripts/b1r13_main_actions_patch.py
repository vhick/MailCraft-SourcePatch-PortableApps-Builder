#!/usr/bin/env python3
"""b1r13: route main-window Google Calendar/People actions before MailCraft's
local/Microsoft engine refuses read-only imported Google records.

Scope: exact MailCraft v0.13.0 patched with b1r6..b1r12 in order.
Fail-closed: check all anchors before writing any file. No broad rights changes.
"""
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[1]


def once(data: str, before: str, after: str, why: str) -> str:
    total=data.count(before)
    if total != 1:
        raise RuntimeError(f'b1r13 {why}: expected exactly one anchor; found {total}; no files modified')
    return data.replace(before,after,1)


def plan(source:Path):
    lib=source/'crates/ui-egui/src/lib.rs'
    ui=source/'crates/ui-egui/src/google_pim.rs'
    if not lib.is_file() or not ui.is_file():
        raise RuntimeError('b1r13 requires the complete upstream UI and existing Google PIM patch')
    main=lib.read_text(encoding='utf-8')
    pim=ui.read_text(encoding='utf-8')
    if 'fn google_pim_native_event' not in pim or 'fn google_pim_native_contact' not in pim:
        raise RuntimeError('b1r13 requires b1r12 native event/contact routing; refusing partial build')

    # Enabled() governs which commands open native forms. Only explicitly
    # selected Google records (or the current Google calendar when creating)
    # get a UI route; this does not alter mailbox permissions.
    main=once(main,
        '''        match self.session.registry.get(id) {
            // Cancel All, while the window has a Send/Receive under way.''',
        '''        // b1r13: the native Google forms are safe to OPEN even though the
        // imported calendar/contact remains read-only to the original engine.
        // The actual write still goes through the Google worker, with ETag and
        // account ownership checks; we never turn local engine rights to Write.
        if self.google_pim_main_enabled(id) { return true; }
        match self.session.registry.get(id) {
            // Cancel All, while the window has a Send/Receive under way.''',
        'native form enablement')

    # Executed ribbon, card, context menu and shortcut commands pass through
    # here. b1r12 only patched the *form* Delete buttons and missed this path.
    main=once(main,
        '''        let before: Vec<u64> = self.session.all_composing().map(|c| c.id).collect();
        let r = self.session.run(id, &params);''',
        '''        // b1r13: Google items must never fall through to the old read-only
        // engine. This intercepts the ribbon, contact-card, context menu and
        // keyboard actions as well as commands originating in an editor.
        if let Some(r) = self.google_pim_main_action(id, &params) {
            return r;
        }
        let before: Vec<u64> = self.session.all_composing().map(|c| c.id).collect();
        let r = self.session.run(id, &params);''',
        'central command execution bridge')

    extra=(ROOT/'patches/b1r13_main_google_actions.rs').read_text(encoding='utf-8')
    if 'b1r13: route main-window' in pim:
        raise RuntimeError('b1r13 already applied; refusing repeated patch')
    pim+='\n'+extra
    return {lib:main,ui:pim}


def patch(source:Path):
    changes=plan(source)
    for p,s in changes.items():p.write_text(s,encoding='utf-8',newline='\n')
    print('b1r13 Google main-window Calendar/People command bridge applied; original engine rights unchanged')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    patch(parser.parse_args().source)
