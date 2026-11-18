#!/usr/bin/env python3
"""OPTIONAL b1r9 guarded Google write UI for exact upstream v0.13.0 after b1r8 patch.

Modifies only upstream files in a transaction; fails closed when a source anchor drifts.
No writes in the absence of a direct user click; remote deletions are deliberately out of scope.
"""
from __future__ import annotations
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[1]
def once(s,old,new,name):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'b1r9 source drift in {name}: expected one anchor, found {n}')
    return s.replace(old,new,1)

def plan(src:Path):
    model=src/'crates/model/src/remote.rs'
    oauth=src/'crates/net/src/oauth.rs'
    net=src/'crates/net/src/google_pim.rs'
    ui=src/'crates/ui-egui/src/google_pim.rs'
    host=src/'apps/mailcraft/src/main.rs'
    for f in [model,oauth,net,ui,host]:
        if not f.is_file(): raise RuntimeError(f'Missing prerequisite: {f}; apply b1r8 first')
    a,b,c,d,e=[f.read_text(encoding='utf-8') for f in (model,oauth,net,ui,host)]
    model_enum=(ROOT/'patches/google_pim_write_model.rs').read_text(encoding='utf-8')
    a=once(a,'/// Where an event, a contact or a calendar comes from when an account\'s server keeps it.',
           model_enum+'\n/// Where an event, a contact or a calendar comes from when an account\'s server keeps it.', 'model enum')
    b=once(b,
           'const GOOGLE_PIM_SCOPE: &str = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/contacts.readonly";',
           'const GOOGLE_PIM_SCOPE: &str = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/contacts.readonly https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/contacts";',
           'extra OAuth write scopes')
    # Preserve Google contact source ETags so a rename cannot blindly overwrite a newer contact.
    c=once(c,
           'id: id.to_string(), display_name: display.to_string(), first: first.to_string(), last: last.to_string(),',
           'id: id.to_string(), change_key: item.pointer("/metadata/sources").and_then(Value::as_array)\n                .and_then(|v| v.iter().find(|source| txt(source, "type") == "CONTACT"))\n                .map(|source| txt(source, "etag").to_string()).unwrap_or_default(),\n            display_name: display.to_string(), first: first.to_string(), last: last.to_string(),',
           'Google contact ETag import')
    c += '\n'+(ROOT/'patches/google_pim_write_net.rs').read_text(encoding='utf-8')
    d=once(d,'use mailcraft_model::sync::Tokens;',
           'use mailcraft_model::sync::Tokens;\nuse mailcraft_model::remote::GooglePimEdit;', 'UI imports')
    d=once(d,'    pub expires_at: i64,','    pub expires_at: i64,\n    pub edit: Option<GooglePimEdit>,', 'UI request edit field')
    d=once(d,'    pub errors: Vec<String>,','    pub errors: Vec<String>,\n    pub write_saved: bool,', 'UI response edit flag')
    d=once(d,'    pub(crate) manual_attempts: u64,',
           '    pub(crate) manual_attempts: u64,\n    pub(crate) pending_edit: Option<(Id, GooglePimEdit)>,\n    pub(crate) editor: GooglePimEditor,\n    pub(crate) last_success: Option<Instant>,\n    pub(crate) run_count: u64,', 'UI state')
    d=once(d,'        self.google_pim.busy = None;\n        let Some(current)',
           '        self.google_pim.busy = None;\n        let edited_on_google = result.write_saved;\n        let Some(current)', 'UI consume write')
    d=once(d,'        if errors.is_empty() {\n            self.google_pim.last_summary',
           '        if errors.is_empty() {\n            self.google_pim.last_success = Some(Instant::now());\n            self.google_pim.run_count = self.google_pim.run_count.saturating_add(1);\n            self.google_pim.last_summary', 'UI success metric')
    d=once(d,'            if count > 0 { self.status("Google Calendar and Contacts synchronized (read-only)"); }',
           '            if edited_on_google { self.status("Google edit saved; Google Calendar and Contacts refreshed"); }\n            else if count > 0 { self.status("Google Calendar and Contacts synchronized"); }', 'UI success status')
    d=once(d,
           '            self.google_pim.last_summary = format!("Google sync problem: {clean}");',
           '            self.google_pim.last_summary = if edited_on_google {\n                format!("Google edit SAVED but refresh failed: {clean}. Check Google web before retrying")\n            } else { format!("Google sync problem: {clean}") };',
           'write-succeeded/read-failed warning')
    d=once(d,'                && self.google_pim.last.get(&a.id).is_none_or(|at| at.elapsed() >= REFRESH_EVERY)',
           '                && (self.google_pim.pending_edit.as_ref().is_some_and(|(id,_)| *id == a.id)\n                    || self.google_pim.last.get(&a.id).is_none_or(|at| at.elapsed() >= REFRESH_EVERY))', 'UI bypass interval on edit')
    d=once(d,'        let request = GooglePimRequest {\n            account: account.clone(), oauth: self.effective_oauth(oauth), refresh, access, expires_at,\n        };',
           '        let edit = if self.google_pim.pending_edit.as_ref().is_some_and(|(id,_)| *id == account.id) { self.google_pim.pending_edit.take().map(|(_,action)| action) } else { None };\n        let request = GooglePimRequest {\n            account: account.clone(), oauth: self.effective_oauth(oauth), refresh, access, expires_at, edit,\n        };', 'UI request edit')
    d=once(d,'        ui.horizontal_wrapped(|ui| {\n            let enabled',
           '        ui.horizontal_wrapped(|ui| {\n            let enabled', 'button section') # no-op ensures anchor
    d=once(d,'            ui.label(summary);\n        });',
           '            ui.label(summary);\n            if let Some(then) = self.google_pim.last_success {\n                ui.label(format!("Last successful refresh {} minute(s) ago; {} successful run(s). Automatic refresh every 15 minutes while online.", then.elapsed().as_secs()/60, self.google_pim.run_count));\n            }\n        });\n        self.google_pim_edit_controls(ui);\n        self.google_pim_edit_window(ui.ctx());', 'edit UI entrypoint')
    d += '\n'+(ROOT/'patches/google_pim_write_ui.rs').read_text(encoding='utf-8')
    # We add write dispatch before any READ access-token reuse. Writes are never replayed automatically.
    anchor='                // The current access token came from the same Google sign-in as Gmail.'
    injected=(ROOT/'patches/google_pim_write_host.rs').read_text(encoding='utf-8')
    e=once(e,anchor,injected+'\n'+anchor,'host edit dispatch')
    return {model:a,oauth:b,net:c,ui:d,host:e}

def patch(source:Path):
    modified=plan(source)
    for p,s in modified.items():
        p.write_text(s,encoding='utf-8')
    print('b1r9 opt-in Google write UI and 15-minute auto-refresh diagnostics patched')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True,type=Path)
    patch(ap.parse_args().source)
