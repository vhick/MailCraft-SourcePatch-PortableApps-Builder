// b1r13: route main-window Calendar/People actions through the existing
// guarded Google PIM worker, not MailCraft's original local/Graph engine.
// Applies to exact v0.13.0; read-only imported Google rights are preserved.
impl MailApp {
    /// The native form is allowed to open for Google data even when its mirror
    /// is marked read-only to MailCraft's original Microsoft/local writer.
    pub(crate) fn google_pim_main_enabled(&self, command:&str) -> bool {
        let is_google = |account: Id| self.session.mailbox.accounts.iter().any(|a| {
            a.id==account && a.oauth.as_ref().is_some_and(|o|o.provider==OAuthProvider::Google)
        });
        match command {
            "calendar.new" | "calendar.newMeeting" => self.session.mailbox
                .calendar(mailcraft_engine::cmd::calendar::current_calendar(&self.session))
                .is_some_and(|c|is_google(c.origin.account)),
            "calendar.edit" | "calendar.delete" => self.session.sel.event
                .and_then(|id|self.session.mailbox.event(id))
                .is_some_and(|event|is_google(event.origin.account)),
            "people.edit" | "people.delete" => self.session.sel.contact
                .and_then(|id|self.session.mailbox.contact(id))
                .is_some_and(|contact|is_google(contact.origin.account)),
            _ => false,
        }
    }

    /// Some toolbar/keyboard callers pass the selected record implicitly,
    /// while context-menu/card callers pass its exact ID. Never redirect
    /// multi-selection, local records, or Microsoft records into Google.
    pub(crate) fn google_pim_main_action(&mut self, command:&str, params:&Value)
        -> Option<Result<Value,String>> {
        match command {
            "calendar.delete" | "calendar.edit" => {
                // A bulk operation must not affect just one of multiple items.
                if params.get("ids").is_some() { return None; }
                let id=params.get("id").and_then(Value::as_u64).or(self.session.sel.event)?;
                let event=self.session.mailbox.event(id)?;
                if !self.session.mailbox.accounts.iter().any(|a|a.id==event.origin.account
                    && a.oauth.as_ref().is_some_and(|o|o.provider==OAuthProvider::Google)) {return None;}
                let mut scoped=params.clone();
                if !scoped.is_object() {scoped=serde_json::json!({});}
                if let Some(fields)=scoped.as_object_mut() {fields.insert("id".into(),serde_json::json!(id));}
                self.google_pim_native_event(command,&scoped)
            }
            "people.delete" | "people.edit" => {
                if params.get("ids").is_some() {return None;}
                let id=params.get("id").and_then(Value::as_u64).or(self.session.sel.contact)?;
                let contact=self.session.mailbox.contact(id)?;
                if !self.session.mailbox.accounts.iter().any(|a|a.id==contact.origin.account
                    && a.oauth.as_ref().is_some_and(|o|o.provider==OAuthProvider::Google)) {return None;}
                let mut scoped=params.clone();
                if !scoped.is_object() {scoped=serde_json::json!({});}
                if let Some(fields)=scoped.as_object_mut() {fields.insert("id".into(),serde_json::json!(id));}
                self.google_pim_native_contact(command,&scoped,0)
            }
            _=>None,
        }
    }
}
