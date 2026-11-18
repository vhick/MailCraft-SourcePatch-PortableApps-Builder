// b1r10: controlled bridge from MailCraft's EXISTING appointment/meeting and
// contact forms into the same b1r9 Google write queue. Does not use the
// local calendar/contact engine for Google records (no duplicate local item).
use serde_json::{json, Value};

impl MailApp {
    fn google_pim_queue_native(&mut self, account: Id, edit: GooglePimEdit) -> Result<Value, String> {
        if self.offline() { return Err("Work Offline is enabled. No Google changes were sent.".into()); }
        if !self.session.driver.auto_sync() { return Err("Enable automatic synchronization before saving to Google.".into()); }
        if self.google_pim.busy.is_some() || self.google_pim.pending_edit.is_some() {
            return Err("Google synchronization is busy. Try saving again after it finishes; nothing was queued.".into());
        }
        if self.services.google_pim.is_none() { return Err("Google editing is not enabled in this build.".into()); }
        if !self.session.mailbox.accounts.iter().any(|a| a.id == account &&
            a.oauth.as_ref().is_some_and(|o| o.provider == OAuthProvider::Google)) {
            return Err("The selected Google account is not connected.".into());
        }
        self.google_pim.pending_edit = Some((account, edit));
        self.google_pim.last.remove(&account);
        // The same queue triggers the existing guarded, one-at-a-time Google
        // worker. A lost response is NOT retried automatically.
        self.google_pim.last_summary = "Google edit queued from MailCraft form…".into();
        // The native editor gets an acknowledgement, not a claim that Google
        // already saved the item. Actual success/failure is shown in status.
        Ok(json!({"googleQueued": true}))
    }

    /// The original event form calls here only on a user-initiated Save/Send.
    /// Non-Google calendars use the original MailCraft command, unchanged.
    pub(crate) fn google_pim_native_event(&mut self, command: &str, params: &Value) -> Option<Result<Value, String>> {
        if !matches!(command, "calendar.new" | "calendar.newMeeting") { return None; }
        let calendar_id = params.get("calendar").and_then(Value::as_u64)
            .unwrap_or_else(|| mailcraft_engine::cmd::calendar::current_calendar(&self.session));
        let calendar = self.session.mailbox.calendar(calendar_id)?;
        let account = calendar.origin.account;
        if !self.session.mailbox.accounts.iter().any(|a| a.id == account &&
            a.oauth.as_ref().is_some_and(|o| o.provider == OAuthProvider::Google)) { return None; }
        let remote_calendar = if calendar.origin.id.is_empty() { "primary".to_string() } else { calendar.origin.id.clone() };
        let name = |key: &str| params.get(key).and_then(Value::as_str).unwrap_or("").trim().to_owned();
        let has_entries = |key: &str| params.get(key).and_then(Value::as_array).is_some_and(|v| !v.is_empty());
        if params.get("allDay").and_then(Value::as_bool) == Some(true) {
            return Some(Err("All-day Google events are not included in this native-form pilot. Use Google Calendar web.".into()));
        }
        if params.get("recurrence").is_some_and(|v| !v.is_null()) {
            return Some(Err("Recurring Google events are not supported by this pilot; use Google Calendar web.".into()));
        }
        if has_entries("categories") {
            return Some(Err("Google categories in native event forms are not supported yet. Remove categories or use Google Calendar web.".into()));
        }
        if params.get("online").and_then(Value::as_bool) == Some(true) {
            return Some(Err("Google Meet link creation is not enabled yet. Turn off Online Meeting or use Google Calendar web.".into()));
        }
        // The native form's Send button sets `send:true` when guests are named;
        // Save alone must NEVER dispatch invitations silently.
        let required = name("attendees");
        let optional = name("optional");
        let has_guests = !required.is_empty() || !optional.is_empty();
        if has_guests && params.get("send").and_then(Value::as_bool) != Some(true) {
            return Some(Err("To send a Google meeting invitation, press Send in the meeting form (not Save).".into()));
        }
        let timezone = params.get("startZone").and_then(Value::as_str).filter(|s| !s.is_empty())
            .unwrap_or("").to_owned();
        let zone = if timezone.is_empty() { self.session.zone().id() } else { timezone };
        let end_zone = params.get("endZone").and_then(Value::as_str).filter(|s| !s.is_empty()).unwrap_or(&zone);
        if end_zone != zone {
            return Some(Err("Events that cross time zones are not supported by this pilot.".into()));
        }
        let edit = GooglePimEdit::NativeEvent {
            calendar: remote_calendar, title: name("title"), start: name("start"), end: name("end"), zone,
            location: name("location"), description: name("description"),
            required, optional, reminder: params.get("reminder").and_then(Value::as_u64),
            private: params.get("private").and_then(Value::as_bool) == Some(true),
            free: name("showAs") == "free",
        };
        Some(self.google_pim_queue_native(account, edit))
    }

    /// Google contacts use the normal MailCraft contact form. A Google write
    /// only happens if the user picked a Google account as the destination, or
    /// the selected existing contact is already owned by Google.
    pub(crate) fn google_pim_native_contact(&mut self, command: &str, params: &Value, destination: Id) -> Option<Result<Value, String>> {
        if !matches!(command, "people.new" | "people.edit") { return None; }
        let account = if command == "people.edit" {
            let id = params.get("id").and_then(Value::as_u64)?;
            let contact = self.session.mailbox.contact(id)?;
            let account = contact.origin.account;
            if !self.session.mailbox.accounts.iter().any(|a| a.id == account &&
                a.oauth.as_ref().is_some_and(|o| o.provider == OAuthProvider::Google)) { return None; }
            account
        } else {
            if destination == 0 { return None; }
            destination
        };
        let name = |key: &str| params.get(key).and_then(Value::as_str).unwrap_or("").trim().to_owned();
        let edit = if command == "people.new" {
            // Do not quietly discard fields the pilot cannot currently write.
            let unsupported = ["displayName", "company", "title", "department", "website", "notes"]
                .into_iter().any(|k| !name(k).is_empty())
                || ["phones", "categories", "keys"].into_iter()
                    .any(|k| params.get(k).and_then(Value::as_array).is_some_and(|a| !a.is_empty()))
                || params.get("favorite").and_then(Value::as_bool) == Some(true)
                || params.get("birthday").is_some_and(|v| !v.is_null())
                || params.get("address").is_some_and(|v| {
                    ["street","city","region","postalCode","country"].into_iter()
                        .any(|k| v.get(k).and_then(Value::as_str).is_some_and(|s| !s.trim().is_empty()))
                });
            if unsupported {
                return Some(Err("Google's native-contact pilot supports first name, last name, and ONE email only. Clear other fields or select Local.".into()));
            }
            let emails: Vec<String> = params.get("emails").and_then(Value::as_array)
                .into_iter().flatten().filter_map(|x| x.get("value").and_then(Value::as_str))
                .filter(|x| !x.trim().is_empty()).map(str::to_owned).collect();
            if emails.len() != 1 { return Some(Err("Enter exactly one email address for this Google contact pilot.".into())); }
            GooglePimEdit::NewContact { first: name("first"), last: name("last"), email: emails[0].clone() }
        } else {
            let id = params.get("id").and_then(Value::as_u64)?;
            let Some(contact) = self.session.mailbox.contact(id) else { return Some(Err("Selected contact was removed.".into())); };
            if params.as_object().is_some_and(|m| m.keys().any(|k| k != "id" && k != "first" && k != "last")) {
                return Some(Err("Google contact editing currently supports first and last names only. Other fields were NOT changed.".into()));
            }
            GooglePimEdit::RenameContact {
                resource: contact.origin.id.clone(), etag: contact.origin.change_key.clone(),
                first: params.get("first").and_then(Value::as_str).unwrap_or(&contact.first).to_owned(),
                last: params.get("last").and_then(Value::as_str).unwrap_or(&contact.last).to_owned(),
            }
        };
        Some(self.google_pim_queue_native(account, edit))
    }
}
