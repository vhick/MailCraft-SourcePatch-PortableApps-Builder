
/// b1r9 opt-in write operations. Never retry an uncertain POST/PATCH result;
/// the server may have received it even if the response was lost.
/// All destinations are exact Google API hosts and allowlisted paths.
pub fn write(access: &str, edit: &mailcraft_model::remote::GooglePimEdit) -> Result<(), String> {
    use mailcraft_model::remote::GooglePimEdit;
    let with_explicit_zone = |stamp: &str| {
        let clock = stamp.split_once('T').map(|(_, v)| v).unwrap_or("");
        clock.ends_with('Z') || clock.contains('+') || clock.get(1..).is_some_and(|tail| tail.contains('-'))
    };
    let (method, url, body, etag): (&str, String, Value, &str) = match edit {
        GooglePimEdit::NewContact { first, last, email } => {
            if (first.trim().is_empty() && last.trim().is_empty()) || !email.contains('@') || email.len() > 254 {
                return Err("Google contact needs a name and valid-looking email".into());
            }
            if first.len()>200 || last.len()>200 { return Err("Contact name is too long".into()); }
            ("POST", "https://people.googleapis.com/v1/people:createContact?personFields=names,emailAddresses,metadata".into(),
                serde_json::json!({"names":[{"givenName":first,"familyName":last}], "emailAddresses":[{"value":email}]}), "")
        }
        GooglePimEdit::RenameContact { resource, etag, first, last } => {
            if !resource.starts_with("people/") || resource.len() <= 7 || !resource[7..].bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_') || etag.is_empty() {
                return Err("Cannot update contact without a saved Google resource and version".into());
            }
            if first.trim().is_empty() && last.trim().is_empty() { return Err("Contact name cannot be empty".into()); }
            if first.len()>200 || last.len()>200 { return Err("Contact name too long".into()); }
            ("PATCH", format!("https://people.googleapis.com/v1/{}:updateContact?updatePersonFields=names&personFields=names,emailAddresses,metadata", resource),
                serde_json::json!({"resourceName":resource,"metadata":{"sources":[{"type":"CONTACT","etag":etag}]},"names":[{"givenName":first,"familyName":last}]}), "")
        }
        GooglePimEdit::NewAppointment { title, start, end } => {
            if title.trim().is_empty() || title.len() > 500 { return Err("Appointment title is required (500 characters max)".into()); }
            if !with_explicit_zone(start) || !with_explicit_zone(end) { return Err("Please include a time zone offset such as +08:00".into()); }
            let Some(s)=mailcraft_time::iso_to_timestamp(start,0) else { return Err("Start must include an ISO date and time-zone offset".into()); };
            let Some(e)=mailcraft_time::iso_to_timestamp(end,0) else { return Err("End must include an ISO date and time-zone offset".into()); };
            if e <= s { return Err("Appointment must end after it starts".into()); }
            ("POST", "https://www.googleapis.com/calendar/v3/calendars/primary/events?sendUpdates=none".into(),
                serde_json::json!({"summary":title,"start":{"dateTime":start},"end":{"dateTime":end}}), "")
        }
        GooglePimEdit::RenameAppointment { calendar, event, etag, title } => {
            if calendar.is_empty() || event.is_empty() || etag.is_empty() || title.trim().is_empty() || title.len() > 500 {
                return Err("To rename a Google event, select a synced event with a saved server version".into());
            }
            ("PATCH",format!("https://www.googleapis.com/calendar/v3/calendars/{}/events/{}?sendUpdates=none",encode(calendar),encode(event)),
                serde_json::json!({"summary":title}),etag)
        }
    };
    let allowed = url.starts_with("https://people.googleapis.com/v1/people")
        || url.starts_with("https://www.googleapis.com/calendar/v3/calendars/");
    if !allowed { return Err("Disallowed Google write destination".into()); }
    let data=serde_json::to_vec(&body).map_err(|_|"Could not serialize Google edit")?;
    if data.len()>16_000 {return Err("Google edit exceeds request size limit".into());}
    let bearer=format!("Bearer {access}");
    let base_headers=[("Authorization",bearer.as_str()),("Content-Type","application/json")];
    let version_headers=[("Authorization",bearer.as_str()),("Content-Type","application/json"),("If-Match",etag)];
    let fields: &[(&str,&str)] = if etag.is_empty() { &base_headers } else { &version_headers };
    let resp=https::send(&Request{method,url:&url,fields,body:&data,max_response:256_000,trusted:""})
        .map_err(|_|"Network error during Google edit: outcome uncertain; check Google before retrying".to_string())?;
    match resp.status {
        200|201|204=>Ok(()),
        400|409|412=>Err("Google rejected the edit or its record changed: refresh and try again; nothing was overwritten".into()),
        401=>Err("Google write token rejected: reconnect the account".into()),
        403=>Err("Google write permission denied: approve contacts and calendar.events scopes".into()),
        429=>Err("Google write rate limit reached: try later".into()),
        n=>Err(format!("Google write returned HTTP {n}; verify the change before retrying")),
    }
}
