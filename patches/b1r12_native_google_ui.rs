// b1r12: The existing MailCraft forms own these calls.  Google items are never
// sent through MailCraft's local/Microsoft mutation commands.
impl MailApp {
    /// A deliberate second press is required for destructive Google operations.
    /// This also prevents a native form from mistakenly deleting the local copy.
    fn google_pim_confirm_delete(&mut self, account: Id, fingerprint: String) -> Result<(), String> {
        let wanted = (account, fingerprint);
        if self.google_pim.delete_confirm.as_ref() != Some(&wanted) {
            self.google_pim.delete_confirm = Some(wanted);
            return Err("Google deletion is permanent. Review this record, then click Delete AGAIN to confirm; no change was sent.".into());
        }
        self.google_pim.delete_confirm = None;
        Ok(())
    }

    pub(crate) fn google_pim_native_event(&mut self, command: &str, params: &Value) -> Option<Result<Value, String>> {
        if !matches!(command, "calendar.new" | "calendar.newMeeting" | "calendar.edit" | "calendar.delete") {return None;}
        let existing = if matches!(command, "calendar.edit" | "calendar.delete") {
            let id=params.get("id").and_then(Value::as_u64)?;
            Some(self.session.mailbox.event(id)?.clone())
        } else {None};
        let calendar_id = existing.as_ref().map(|e| e.calendar).or_else(||params.get("calendar").and_then(Value::as_u64))
            .unwrap_or_else(||mailcraft_engine::cmd::calendar::current_calendar(&self.session));
        let calendar=self.session.mailbox.calendar(calendar_id)?;
        let account=existing.as_ref().map_or(calendar.origin.account, |e| e.origin.account);
        if !self.session.mailbox.accounts.iter().any(|a| a.id==account &&
            a.oauth.as_ref().is_some_and(|o| o.provider==OAuthProvider::Google)) {return None;}
        if calendar.origin.account!=account {return Some(Err("Cannot move a Google event between different accounts".into()));}
        let remote_calendar=if calendar.origin.id.is_empty() {"primary".to_owned()} else {calendar.origin.id.clone()};
        let name=|k:&str| params.get(k).and_then(Value::as_str).unwrap_or("").trim().to_owned();
        if let Some(e)=existing {
            if e.origin.id.trim().is_empty() || e.origin.change_key.trim().is_empty() {
                return Some(Err("Refresh Google Calendar first: this event has no server ID/version".into()));
            }
            if e.origin.guest || !e.origin.series.is_empty() || e.origin.occurrence.is_some() || e.recurrence.is_some() {
                return Some(Err("Editing or deleting Google guest/recurring events is not supported by this safe native-form update".into()));
            }
            if command=="calendar.delete" {
                if let Err(explain)=self.google_pim_confirm_delete(account,format!("event:{}:{}",e.origin.id,e.origin.change_key)) {
                    return Some(Err(explain));
                }
                return Some(self.google_pim_queue_native(account,GooglePimEdit::NativeDeleteEvent {
                    calendar:remote_calendar,event:e.origin.id,etag:e.origin.change_key,
                }));
            }
            if params.get("calendar").and_then(Value::as_u64).is_some_and(|c| c!=calendar_id) {
                return Some(Err("Moving an existing Google event to another calendar is not supported".into()));
            }
            let allowed=["id","scope","occurrence","title","location","description","start","end","allDay","startZone","endZone","reminder","showAs","private"];
            if params.as_object().is_some_and(|m|m.keys().any(|k|!allowed.contains(&k.as_str()))) {
                return Some(Err("This Google event edit changes unsupported fields (guests, recurrence, categories or meeting settings). Nothing was queued.".into()));
            }
            if params.get("scope").and_then(Value::as_str).is_some_and(|s|!s.is_empty()) {
                return Some(Err("Editing part of a Google recurring series is not supported".into()));
            }
            let zone=self.session.zone().id();
            let fields=match serde_json::to_string(params) {Ok(s)=>s,Err(_)=>return Some(Err("Could not prepare Google event changes".into()))};
            return Some(self.google_pim_queue_native(account,GooglePimEdit::NativeUpdateEvent {
                calendar:remote_calendar,event:e.origin.id,etag:e.origin.change_key,fields,zone,
            }));
        }
        // New: preserve b1r11 simple appointment/meeting behavior, including all-day.
        if params.get("recurrence").is_some_and(|v|!v.is_null()) ||
            params.get("categories").and_then(Value::as_array).is_some_and(|v|!v.is_empty()) ||
            params.get("online").and_then(Value::as_bool)==Some(true) {
            return Some(Err("Google recurring events, categories and Meet creation are not supported by this form. No event was queued.".into()));
        }
        let required=name("attendees");let optional=name("optional");
        if (!required.is_empty() || !optional.is_empty()) && params.get("send").and_then(Value::as_bool)!=Some(true) {
            return Some(Err("Press Send to invite attendees; Save does not silently send invitations".into()));
        }
        let zone=params.get("startZone").and_then(Value::as_str).filter(|s|!s.is_empty()).map(str::to_owned)
            .unwrap_or_else(||self.session.zone().id());
        if params.get("endZone").and_then(Value::as_str).is_some_and(|s|!s.is_empty() && s!=zone.as_str()) {
            return Some(Err("Events across different time zones are not supported".into()));
        }
        let action=GooglePimEdit::NativeEvent {
            calendar:remote_calendar,title:name("title"),start:name("start"),end:name("end"),
            all_day:params.get("allDay").and_then(Value::as_bool)==Some(true),zone,
            location:name("location"),description:name("description"),required,optional,
            reminder:params.get("reminder").and_then(Value::as_u64),
            private:params.get("private").and_then(Value::as_bool)==Some(true),free:name("showAs")=="free",
        };
        Some(self.google_pim_queue_native(account,action))
    }

    pub(crate) fn google_pim_native_contact(&mut self, command:&str, params:&Value, destination:Id) -> Option<Result<Value,String>> {
        if !matches!(command,"people.new"|"people.edit"|"people.delete") {return None;}
        let existing=if command=="people.new" {None} else {
            let id=params.get("id").and_then(Value::as_u64)?;
            Some(self.session.mailbox.contact(id)?.clone())
        };
        let account=existing.as_ref().map_or(destination,|c|c.origin.account);
        if account==0 {return None;}
        if !self.session.mailbox.accounts.iter().any(|a|a.id==account &&
            a.oauth.as_ref().is_some_and(|o|o.provider==OAuthProvider::Google)) {return None;}
        if command=="people.delete" {
            let c=existing.as_ref().expect("delete needs existing contact");
            if !c.origin.id.starts_with("people/") || c.origin.change_key.is_empty() {
                return Some(Err("Refresh Google Contacts before deletion: the Google ID/version is missing".into()));
            }
            if let Err(e)=self.google_pim_confirm_delete(account,format!("contact:{}:{}",c.origin.id,c.origin.change_key)) {
                return Some(Err(e));
            }
            return Some(self.google_pim_queue_native(account,GooglePimEdit::NativeDeleteContact {
                resource:c.origin.id.clone(),etag:c.origin.change_key.clone(),
            }));
        }
        let unsupported=["displayName","categories","favorite","keys"];
        if unsupported.iter().any(|k| params.get(*k).is_some_and(|v|{
            if v.is_null() {false} else if let Some(s)=v.as_str() { !s.trim().is_empty() }
            else if let Some(a)=v.as_array() {!a.is_empty()} else {v.as_bool()==Some(true)}
        })) {return Some(Err("Google native contact form cannot save Display Name overrides, categories, favorites or certificates yet. These were NOT discarded.".into()));}
        let mut changes=params.clone();
        if let Some(c)=existing.as_ref() {
            if !c.origin.id.starts_with("people/") || c.origin.change_key.is_empty() {
                return Some(Err("Refresh Google Contacts first: record ID/version is unavailable".into()));
            }
            // Google names and organizations are edited as single compound fields.
            if let Some(map)=changes.as_object_mut() {
                if map.contains_key("first") || map.contains_key("last") {
                    map.entry("first").or_insert_with(||json!(c.first));
                    map.entry("last").or_insert_with(||json!(c.last));
                }
                if map.contains_key("company") || map.contains_key("title") || map.contains_key("department") {
                    map.entry("company").or_insert_with(||json!(c.company));
                    map.entry("title").or_insert_with(||json!(c.title));
                    map.entry("department").or_insert_with(||json!(c.department));
                }
            }
        }
        let allowed=["id","first","last","company","title","department","emails","phones","address","website","notes","birthday"];
        if changes.as_object().is_some_and(|m|m.keys().any(|k|!allowed.contains(&k.as_str()))) {
            return Some(Err("Google native form contains a field unsupported by Google integration. No changes were queued.".into()));
        }
        let fields=match serde_json::to_string(&changes) {Ok(s)=>s,Err(_)=>return Some(Err("Could not prepare Google contact changes".into()))};
        let resource=existing.as_ref().map_or_else(String::new,|c|c.origin.id.clone());
        let etag=existing.as_ref().map_or_else(String::new,|c|c.origin.change_key.clone());
        Some(self.google_pim_queue_native(account,GooglePimEdit::NativeContact {resource,etag,fields}))
    }
}
