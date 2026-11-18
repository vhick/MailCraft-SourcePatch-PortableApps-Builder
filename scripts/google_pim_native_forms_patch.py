#!/usr/bin/env python3
"""b1r10 experimental: route native MailCraft form saves to guarded Google queue.

Run only AFTER b1r8 read and b1r9 write patches on exact v0.13.0. Pure
planning first, then writes, with strict fail-closed anchors and no secrets.
"""
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[1]

def once(s,old,new,name):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'b1r10 {name}: expected exactly one source anchor, found {n}; STOP')
    return s.replace(old,new,1)

def plan(src:Path):
    model=src/'crates/model/src/remote.rs'
    net=src/'crates/net/src/google_pim.rs'
    ui=src/'crates/ui-egui/src/google_pim.rs'
    forms=src/'crates/ui-egui/src/forms.rs'
    for p in [model,net,ui,forms]:
        if not p.is_file(): raise RuntimeError(f'b1r10 missing dependency: {p}')
    m,n,u,f=[p.read_text(encoding='utf-8') for p in [model,net,ui,forms]]
    m=once(m,
      '    RenameAppointment { calendar: String, event: String, etag: String, title: String },\n}',
      '''    RenameAppointment { calendar: String, event: String, etag: String, title: String },
    /// From the actual native New Appointment / New Meeting form, not a local-only event.
    NativeEvent { calendar: String, title: String, start: String, end: String,
        zone: String, location: String, description: String, required: String,
        optional: String, reminder: Option<u64>, private: bool, free: bool },
}''','Google edit model')
    n=once(n,'        GooglePimEdit::RenameAppointment { calendar, event, etag, title } => {',
      (ROOT/'patches/google_pim_native_net.rs').read_text(encoding='utf-8')+
      '        GooglePimEdit::RenameAppointment { calendar, event, etag, title } => {','Google native network arm')
    u += '\n'+(ROOT/'patches/google_pim_native_ui.rs').read_text(encoding='utf-8')
    # Native event form: direct Google-only queue, otherwise unchanged behavior.
    f=once(f,
      '            let ran = if asks { app.run(command, params) } else { app.execute(command, params) };',
      '''            let ran = if let Some(remote) = app.google_pim_native_event(command, &params) {
                remote
            } else if asks { app.run(command, params) } else { app.execute(command, params) };''',
      'native Appointment/Meeting Save and Send')
    # New contact form: let the user choose a destination; default Google when
    # there is exactly one Google account; retain Local explicitly.
    f=once(f,'        id: Option<Id>,\n        first: String,\n        last: String,\n        display: String,',
      '        id: Option<Id>,\n        google_destination: Id,\n        google_destination_initialized: bool,\n        first: String,\n        last: String,\n        display: String,',
      'native ContactForm fields')
    f=once(f,
      '            let account = self.id.and_then(|id| app.session.mailbox.contact(id)).map_or(0, |c| c.origin.account);\n            let categories = app.session.mailbox.categories_of(account).to_vec();\n            body(ui, |ui| {\n                row(ui, tl!("First name"), |ui| {',
      '''            let account = self.id.and_then(|id| app.session.mailbox.contact(id)).map_or(0, |c| c.origin.account);
            let categories = app.session.mailbox.categories_of(account).to_vec();
            let google_accounts: Vec<(Id, String)> = app.session.mailbox.accounts.iter()
                .filter(|a| a.oauth.as_ref().is_some_and(|o| o.provider == mailcraft_model::OAuthProvider::Google))
                .map(|a| (a.id, a.email.clone())).collect();
            if self.id.is_none() && !self.google_destination_initialized {
                if google_accounts.len() == 1 { self.google_destination = google_accounts[0].0; }
                self.google_destination_initialized = true;
            }
            body(ui, |ui| {
                if self.id.is_none() && !google_accounts.is_empty() {
                    row(ui, "Save to", |ui| {
                        let selected = google_accounts.iter().find(|(id,_)| *id == self.google_destination)
                            .map_or("This computer (local)", |(_,name)| name.as_str());
                        egui::ComboBox::from_id_salt("b1r10_native_google_contact_destination")
                            .selected_text(selected).show_ui(ui, |ui| {
                                ui.selectable_value(&mut self.google_destination, 0, "This computer (local)");
                                for (id,email) in &google_accounts {
                                    ui.selectable_value(&mut self.google_destination, *id, email);
                                }
                            });
                    });
                    if self.google_destination != 0 {
                        ui.label("Google pilot: first name, last name, and one email only. Other fields require future support.");
                    }
                }
                row(ui, tl!("First name"), |ui| {''',
      'ContactForm Google destination selector')
    f=once(f,
      '            match run.map(|(command, params)| app.execute(command, params)) {',
      '''            match run.map(|(command, params)| {
                if let Some(remote) = app.google_pim_native_contact(command, &params, self.google_destination) {
                    remote
                } else { app.execute(command, params) }
            }) {''',
      'ContactForm native Save bridge')
    return {model:m,net:n,ui:u,forms:f}

def patch(src:Path):
    planned=plan(src)
    for p,content in planned.items():
        p.write_text(content,encoding='utf-8')
    print('b1r10 native form bridge patched: Google timed appointments/guest meetings and basic contacts')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True,type=Path)
    patch(ap.parse_args().source)
