
// b1r9 separate, guarded editing controls. The existing MailCraft editor stays
// read-only for Google-origin records. A click in this explicit dialog is the
// sole trigger for network mutations; no deletes are performed.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum GoogleEditorMode { NewContact, RenameContact, NewAppointment, RenameAppointment }
#[derive(Default)]
pub(crate) struct GooglePimEditor {
    pub(crate) mode: Option<GoogleEditorMode>,
    pub(crate) account: Id,
    pub(crate) remote: String,
    pub(crate) calendar: String,
    pub(crate) etag: String,
    pub(crate) first: String,
    pub(crate) last: String,
    pub(crate) email: String,
    pub(crate) title: String,
    pub(crate) start: String,
    pub(crate) end: String,
    pub(crate) confirm: bool,
    pub(crate) warning: String,
}

impl MailApp {
    pub(crate) fn google_pim_edit_controls(&mut self, ui: &mut egui::Ui) {
        let google_accounts: Vec<_> = self.session.mailbox.accounts.iter()
            .filter(|a| a.oauth.as_ref().is_some_and(|o| o.provider==OAuthProvider::Google))
            .map(|a| (a.id, a.email.clone())).collect();
        if google_accounts.is_empty() { return; }
        // UI module enum may differ upstream; use the selected view's behavior instead
        // of changing existing local or Microsoft editing controls.
        ui.horizontal_wrapped(|ui| {
            if ui.button("New Google contact…").clicked() {
                self.google_pim.editor = GooglePimEditor {mode:Some(GoogleEditorMode::NewContact), account:google_accounts[0].0, ..Default::default()};
            }
            if ui.button("New Google appointment…").clicked() {
                self.google_pim.editor = GooglePimEditor {mode:Some(GoogleEditorMode::NewAppointment), account:google_accounts[0].0, ..Default::default()};
            }
            if let Some(contact) = self.session.sel.contact.and_then(|id| self.session.mailbox.contacts.get(&id)) {
                if google_accounts.iter().any(|(id,_)| *id==contact.origin.account) && !contact.origin.id.is_empty()
                    && ui.button("Rename selected Google contact…").clicked() {
                    self.google_pim.editor = GooglePimEditor {
                        mode:Some(GoogleEditorMode::RenameContact), account:contact.origin.account,
                        remote:contact.origin.id.clone(), etag:contact.origin.change_key.clone(),
                        first:contact.first.clone(), last:contact.last.clone(), ..Default::default()
                    };
                }
            }
            if let Some(event) = self.session.sel.event.and_then(|id| self.session.mailbox.events.get(&id)) {
                if google_accounts.iter().any(|(id,_)| *id==event.origin.account)
                    && event.origin.occurrence.is_none() && !event.origin.id.is_empty()
                    && ui.button("Rename selected Google event…").clicked() {
                    let calendar = self.session.mailbox.calendar(event.calendar)
                        .map(|c| if c.origin.id.is_empty() {"primary".to_string()} else {c.origin.id.clone()})
                        .unwrap_or_else(|| "primary".to_string());
                    self.google_pim.editor = GooglePimEditor {
                        mode:Some(GoogleEditorMode::RenameAppointment), account:event.origin.account,
                        remote:event.origin.id.clone(), calendar, etag:event.origin.change_key.clone(),
                        title:event.title.clone(), ..Default::default()
                    };
                }
            }
        });
    }

    pub(crate) fn google_pim_edit_window(&mut self, ctx: &egui::Context) {
        let Some(mode) = self.google_pim.editor.mode else { return };
        let account_choices: Vec<_> = self.session.mailbox.accounts.iter()
            .filter(|a| a.oauth.as_ref().is_some_and(|o| o.provider==OAuthProvider::Google))
            .map(|a| (a.id,a.email.clone())).collect();
        let can_write = self.google_pim.busy.is_none();
        let mut save=false;
        let mut close=false;
        egui::Window::new("Google Calendar / Contacts — safe editing")
            .collapsible(false).resizable(false).show(ctx,|ui| {
                let editor=&mut self.google_pim.editor;
                if matches!(mode,GoogleEditorMode::NewContact|GoogleEditorMode::NewAppointment) {
                    egui::ComboBox::from_label("Google account")
                        .selected_text(account_choices.iter().find(|(id,_)|*id==editor.account).map_or("Select account", |(_,name)|name.as_str()))
                        .show_ui(ui,|ui| {for (id,label) in &account_choices {ui.selectable_value(&mut editor.account,*id,label);} });
                }
                match mode {
                    GoogleEditorMode::NewContact|GoogleEditorMode::RenameContact => {
                        ui.label("First name"); ui.text_edit_singleline(&mut editor.first);
                        ui.label("Last name"); ui.text_edit_singleline(&mut editor.last);
                        if mode==GoogleEditorMode::NewContact {ui.label("Email");ui.text_edit_singleline(&mut editor.email);}
                        else {ui.label("Only the contact's name will be changed. Other fields remain untouched.");}
                    }
                    GoogleEditorMode::NewAppointment => {
                        ui.label("Event title"); ui.text_edit_singleline(&mut editor.title);
                        ui.label("Start (with time-zone offset, e.g. 2026-11-20T09:00:00+08:00)");
                        ui.text_edit_singleline(&mut editor.start);
                        ui.label("End (e.g. 2026-11-20T10:00:00+08:00)");
                        ui.text_edit_singleline(&mut editor.end);
                        ui.label("Creates an appointment only in this account's primary calendar. No attendees are invited.");
                    }
                    GoogleEditorMode::RenameAppointment => {
                        ui.label("Event title"); ui.text_edit_singleline(&mut editor.title);
                        ui.label("Only the title is changed. Times, attendees and recurrence stay unchanged.");
                    }
                }
                if !editor.warning.is_empty() {ui.colored_label(egui::Color32::LIGHT_RED,&editor.warning);}
                ui.checkbox(&mut editor.confirm,"I understand this will change data in Google (not just MailCraft)");
                ui.horizontal(|ui| {
                    if ui.add_enabled(editor.confirm && can_write,egui::Button::new("Save to Google")).clicked() {save=true;}
                    if ui.button("Cancel").clicked() {close=true;}
                });
            });
        if close { self.google_pim.editor=GooglePimEditor::default(); }
        else if save {
            let e=&self.google_pim.editor;
            let action=match mode {
                GoogleEditorMode::NewContact=>GooglePimEdit::NewContact{first:e.first.clone(),last:e.last.clone(),email:e.email.clone()},
                GoogleEditorMode::RenameContact=>GooglePimEdit::RenameContact{resource:e.remote.clone(),etag:e.etag.clone(),first:e.first.clone(),last:e.last.clone()},
                GoogleEditorMode::NewAppointment=>GooglePimEdit::NewAppointment{title:e.title.clone(),start:e.start.clone(),end:e.end.clone()},
                GoogleEditorMode::RenameAppointment=>GooglePimEdit::RenameAppointment{calendar:e.calendar.clone(),event:e.remote.clone(),etag:e.etag.clone(),title:e.title.clone()},
            };
            let account=e.account;
            if account==0 { self.google_pim.editor.warning="Choose a Google account".into(); return; }
            self.google_pim.editor=GooglePimEditor::default();
            self.google_pim.pending_edit=Some((account,action));
            self.google_pim_tick(ctx);
        }
    }
}
