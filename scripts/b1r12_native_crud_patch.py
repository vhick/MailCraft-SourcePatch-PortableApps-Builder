#!/usr/bin/env python3
"""b1r12: repair Google-native add/edit/delete dispatch after b1r11.

Applies to *exact* b1r11 patched MailCraft v0.13.0 only.  Plan all files
before writing; detect drift; avoid edits to authorization, Gmail, signatures
and PortableApps data roots.
"""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[1]

def once(txt, old, new, what):
    n=txt.count(old)
    if n!=1: raise RuntimeError(f'b1r12 {what}: expected one source anchor, found {n}; STOP')
    return txt.replace(old,new,1)

def plan(src:Path):
    model=src/'crates/model/src/remote.rs'
    net=src/'crates/net/src/google_pim.rs'
    ui=src/'crates/ui-egui/src/google_pim.rs'
    forms=src/'crates/ui-egui/src/forms.rs'
    for p in (model,net,ui,forms):
        if not p.is_file():raise RuntimeError(f'b1r12 prerequisite missing: {p}')
    m,n,u,f=[p.read_text(encoding='utf-8') for p in (model,net,ui,forms)]
    m=once(m,'    NativeEvent { calendar: String, title: String, start: String, end: String,\n        all_day: bool, zone: String, location: String, description: String, required: String,\n        optional: String, reminder: Option<u64>, private: bool, free: bool },',
       '''    NativeEvent { calendar: String, title: String, start: String, end: String,
        all_day: bool, zone: String, location: String, description: String, required: String,
        optional: String, reminder: Option<u64>, private: bool, free: bool },
    NativeUpdateEvent { calendar: String, event: String, etag: String, fields: String, zone: String },
    NativeDeleteEvent { calendar: String, event: String, etag: String },
    NativeContact { resource: String, etag: String, fields: String },
    NativeDeleteContact { resource: String, etag: String },''','model variants')
    # b1r11 Google UI fragment is at the very end, after the b1r9 edit UI.
    marker='// b1r10: controlled bridge from MailCraft\'s EXISTING appointment/meeting and'
    if u.count(marker)!=1 or not u.rstrip().endswith('}'):
        raise RuntimeError('b1r12 old Google native UI fragment missing or unexpected tail; STOP')
    base=u[:u.index(marker)]
    if 'fn google_pim_queue_native(' not in u[u.index(marker):]:raise RuntimeError('b1r12 queue guard missing; STOP')
    queue_start=u.index('impl MailApp {',u.index(marker))
    if '    /// The original event form calls here' not in u[queue_start:]:
        raise RuntimeError('b1r12 expected original native form bridge anchor; STOP')
    event_start=u.index('    /// The original event form calls here',queue_start)
    queue_part=u[queue_start:event_start]
    # Rewrite the native segment while preserving the queue behavior exactly.
    u=base+marker+'\nuse serde_json::{json, Value};\n\n'+queue_part+\
       (ROOT/'patches/b1r12_native_google_ui.rs').read_text(encoding='utf-8').replace('impl MailApp {','',1)
    u=once(u,'    pub(crate) pending_edit: Option<(Id, GooglePimEdit)>,',
       '    pub(crate) pending_edit: Option<(Id, GooglePimEdit)>,\n    pub(crate) delete_confirm: Option<(Id, String)>,','Google UI confirmation state')
    # Need to clear pending delete upon a successful non-destructive queue as well.
    u=once(u,'        self.google_pim.pending_edit = Some((account, edit));',
       '        self.google_pim.delete_confirm = None;\n        self.google_pim.pending_edit = Some((account, edit));','queue delete confirmation cleanup')
    # net: additional four variants just before the match closes and HTTPS allowlist.
    anchor='    };\n    let allowed = url.starts_with("https://people.googleapis.com/v1/people")'
    n=once(n,anchor,(ROOT/'patches/b1r12_native_google_net.rs').read_text(encoding='utf-8')+anchor,'Google edit network arms')

    # Read the fields the native contact editor exposes, not just names/emails.
    n=once(n,'personFields=names,emailAddresses,phoneNumbers,organizations,metadata',
       'personFields=names,emailAddresses,phoneNumbers,organizations,metadata,addresses,urls,birthdays,biographies',
       'expanded contact download fields')
    import_fragment=(ROOT/'patches/b1r12_native_contact_import.rs').read_text(encoding='utf-8')
    n=once(n,'        let title = first_str(&item, "organizations", "title");\n        result.push(RemoteContact {',
       '        let title = first_str(&item, "organizations", "title");\n'+import_fragment+'        result.push(RemoteContact {',
       'contact download parsing')
    n=once(n,'company: company.to_string(), title: title.to_string(), emails, phones, ..Default::default()',
       'company: company.to_string(), title: title.to_string(), department: department.to_string(),\n            emails, phones, addresses, websites, birthday, notes: notes.to_string(), ..Default::default()',
       'contact download mapping')

    n=once(n,'    let data=serde_json::to_vec(&body).map_err(|_|"Could not serialize Google edit")?;',
       '    let data=if method=="DELETE" { Vec::new() } else {serde_json::to_vec(&body).map_err(|_|"Could not serialize Google edit")?};',
       'empty DELETE request body')
    # For calendar and people, send safe delete, do NOT misuse local engine delete.
    f=once(f,'            let ran = if let Some(remote) = app.google_pim_native_event(command, &params) {',
       '            let ran = if let Some(remote) = app.google_pim_native_event(command, &params) {','event bridge survives')
    f=once(f,'            if let (true, Some(id)) = (clicked.delete, self.id) {',
       '            if let (true, Some(id)) = (clicked.delete, self.id) {','contact delete anchor') if False else f
    f=once(f,'''                return match app.run("people.delete", json!({"id": id})) {
                    Ok(_) => true,
                    Err(e) => {
                        self.error = e;
                        false
                    }
                };''','''                let deletion=json!({"id": id});
                let ran=if let Some(google)=app.google_pim_native_contact("people.delete", &deletion, self.google_destination) {
                    google
                } else {app.run("people.delete", deletion)};
                return match ran {
                    Ok(_) => true,
                    Err(e) => { self.error=e; false }
                };''','contact native delete bridge')
    return {model:m,net:n,ui:u,forms:f}

def patch(src):
    changes=plan(src)
    for p,s in changes.items():p.write_text(s,encoding='utf-8')
    print('b1r12 native Google form create/edit/delete bridge applied; Google rights unchanged')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source',required=True,type=Path)
    patch(a.parse_args().source)
