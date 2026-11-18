// SPDX-License-Identifier: MIT OR Apache-2.0
//! EXPERIMENTAL b1r6: read-only Google Calendar and Google Contacts downloads.
//! Mail data, OAuth sign-in screens and remote Google data cannot be changed here.
//! HTTPS allowlisted hosts only; no redirect follows; bounded pages and replies.
use mailcraft_model::{Account, Labeled, Rights};
use mailcraft_model::remote::{CalendarsDownload, ContactsDownload, EventsDownload, RemoteCalendar, RemoteContact, RemoteEvent};
use serde_json::Value;

use crate::https::{self, Request};

/// Each independent result is optional: a Calendar denial must not discard Contacts or Gmail.
#[derive(Default)]
pub struct Downloads {
    pub calendars: Option<CalendarsDownload>,
    pub events: Vec<EventsDownload>,
    pub contacts: Option<ContactsDownload>,
    pub errors: Vec<String>,
}

fn encode(raw: &str) -> String {
    let mut out = String::new();
    for b in raw.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'~') {
            out.push(char::from(b));
        } else {
            out.push('%');
            const HEX: &[u8; 16] = b"0123456789ABCDEF";
            out.push(char::from(HEX[(b >> 4) as usize]));
            out.push(char::from(HEX[(b & 0x0f) as usize]));
        }
    }
    out
}

fn fetch(url: &str, access: &str) -> Result<Value, String> {
    // Never let a server response supply a URL or send our token to a third party.
    if !(url.starts_with("https://www.googleapis.com/calendar/v3/")
        || url.starts_with("https://people.googleapis.com/v1/people/me/connections?")) {
        return Err("Google API URL is not permitted".into());
    }
    let auth = format!("Bearer {access}");
    let headers = [("Authorization", auth.as_str()), ("Accept", "application/json")];
    let response = https::send(&Request {
        method: "GET", url, fields: &headers, body: &[], max_response: 4_000_000, trusted: "",
    }).map_err(|_| "Google API connection or TLS verification failed".to_string())?;
    if response.status == 401 {
        return Err("Google API HTTP 401: access token expired or rejected".into());
    }
    if response.status == 403 {
        return Err("Google API HTTP 403: check granted scopes, Workspace policy and enabled APIs".into());
    }
    if response.status != 200 {
        return Err(format!("Google API returned HTTP {}", response.status));
    }
    serde_json::from_slice(&response.body).map_err(|_| "Google API returned invalid JSON".into())
}

/// Collect every page before handing it to MailCraft's merge function.
/// Never advertise a partial list as complete; prevent deleting data after a failed page.
fn pages(base: &str, key: &str, access: &str, cap: usize) -> Result<Vec<Value>, String> {
    let mut records = Vec::new();
    let mut token = String::new();
    for _ in 0..60 {
        let url = if token.is_empty() { base.to_string() } else { format!("{base}&pageToken={}", encode(&token)) };
        let body = fetch(&url, access)?;
        if let Some(items) = body.get(key).and_then(Value::as_array) {
            if items.len().saturating_add(records.len()) > cap {
                return Err(format!("Google {key} exceeds the safe {cap}-entry limit"));
            }
            records.extend(items.iter().cloned());
        }
        token = body.get("nextPageToken").and_then(Value::as_str).unwrap_or_default().to_string();
        if token.is_empty() { return Ok(records); }
    }
    Err("Google returned too many pages; local data was left unchanged".into())
}

fn txt<'a>(item: &'a Value, field: &str) -> &'a str {
    item.get(field).and_then(Value::as_str).unwrap_or_default()
}

fn first_str<'a>(item: &'a Value, list: &str, field: &str) -> &'a str {
    item.get(list).and_then(Value::as_array).and_then(|items| items.first())
        .and_then(|entry| entry.get(field)).and_then(Value::as_str).unwrap_or_default()
}

fn contacts(account: &Account, access: &str) -> Result<ContactsDownload, String> {
    let url = "https://people.googleapis.com/v1/people/me/connections?pageSize=1000&personFields=names,emailAddresses,phoneNumbers,organizations,metadata";
    let rows = pages(url, "connections", access, 20_000)?;
    let mut result = Vec::new();
    for item in rows {
        let id = txt(&item, "resourceName");
        if id.is_empty() || item.pointer("/metadata/deleted").and_then(Value::as_bool) == Some(true) { continue; }
        let first = first_str(&item, "names", "givenName");
        let last = first_str(&item, "names", "familyName");
        let display = first_str(&item, "names", "displayName");
        let emails = item.get("emailAddresses").and_then(Value::as_array)
            .map(|xs| xs.iter().filter_map(|e| {
                let address = txt(e, "value").trim();
                if address.is_empty() { None } else { Some(Labeled::new(txt(e, "type"), address)) }
            }).take(50).collect()).unwrap_or_default();
        let phones = item.get("phoneNumbers").and_then(Value::as_array)
            .map(|xs| xs.iter().filter_map(|e| {
                let number = txt(e, "value").trim();
                if number.is_empty() { None } else { Some(Labeled::new(txt(e, "type"), number)) }
            }).take(50).collect()).unwrap_or_default();
        let company = first_str(&item, "organizations", "name");
        let title = first_str(&item, "organizations", "title");
        result.push(RemoteContact {
            id: id.to_string(), display_name: display.to_string(), first: first.to_string(), last: last.to_string(),
            company: company.to_string(), title: title.to_string(), emails, phones, ..Default::default()
        });
    }
    Ok(ContactsDownload { account: account.id, email: account.email.clone(), complete: true, contacts: result })
}

fn calendars(account: &Account, access: &str) -> Result<CalendarsDownload, String> {
    let url = "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=250&minAccessRole=reader";
    let rows = pages(url, "items", access, 100)?;
    let result = rows.iter().filter_map(|entry| {
        let id = txt(entry, "id").trim();
        if id.is_empty() { return None; }
        Some(RemoteCalendar {
            id: id.to_string(), name: txt(entry, "summary").to_string(),
            // Read-only at the UI even when the Google user owns this calendar.
            rights: Rights::Read,
            main: entry.get("primary").and_then(Value::as_bool).unwrap_or(false),
            ..Default::default()
        })
    }).collect();
    Ok(CalendarsDownload { account: account.id, email: account.email.clone(), complete: true, calendars: result, ..Default::default() })
}

fn event_time(value: &Value) -> Option<i64> {
    let raw = value.get("dateTime").or_else(|| value.get("date")).and_then(Value::as_str)?;
    mailcraft_time::iso_to_timestamp(raw, 0)
}

fn events(account: &Account, calendar: &RemoteCalendar, access: &str, from: i64, to: i64) -> Result<EventsDownload, String> {
    let start = encode(&mailcraft_time::format_iso_utc(from));
    let end = encode(&mailcraft_time::format_iso_utc(to));
    let url = format!("https://www.googleapis.com/calendar/v3/calendars/{}/events?maxResults=2500&singleEvents=true&showDeleted=false&timeMin={start}&timeMax={end}", encode(&calendar.id));
    let rows = pages(&url, "items", access, 20_000)?;
    let mut result = Vec::new();
    for item in rows {
        if txt(&item, "status") == "cancelled" { continue; }
        let id = txt(&item, "id");
        if id.is_empty() { continue; }
        let (Some(start), Some(end)) = (event_time(&item["start"]), event_time(&item["end"])) else { continue };
        if end <= start { continue; }
        let all_day = item.pointer("/start/date").and_then(Value::as_str).is_some();
        result.push(RemoteEvent {
            id: id.to_string(), change_key: txt(&item, "etag").to_string(),
            uid: txt(&item, "iCalUID").to_string(),
            title: txt(&item, "summary").to_string(),
            location: txt(&item, "location").to_string(),
            description: txt(&item, "description").to_string(),
            start, end, all_day,
            start_zone: txt(&item["start"], "timeZone").to_string(),
            end_zone: txt(&item["end"], "timeZone").to_string(),
            ..Default::default()
        });
    }
    Ok(EventsDownload {
        account: account.id, email: account.email.clone(), calendar: if calendar.main { String::new() } else { calendar.id.clone() },
        from, to, complete: true, events: result, ..Default::default()
    })
}

/// A full bounded snapshot every fifteen minutes. No Google write APIs are called.
/// Calendar events use a window from 30 days ago through 400 days in the future.
pub fn download(account: &Account, access: &str) -> Downloads {
    let mut out = Downloads::default();
    match contacts(account, access) {
        Ok(found) => out.contacts = Some(found),
        Err(error) => out.errors.push(format!("Google Contacts: {error}")),
    }
    match calendars(account, access) {
        Ok(found) => {
            let now = mailcraft_time::now();
            let from = now.saturating_sub(30 * 86_400);
            let to = now.saturating_add(400 * 86_400);
            // Never mark the calendar list complete until at least its selected events were requested.
            for cal in &found.calendars {
                match events(account, cal, access, from, to) {
                    Ok(found) => out.events.push(found),
                    Err(error) => out.errors.push(format!("Google Calendar: {error}")),
                }
            }
            out.calendars = Some(found);
        }
        Err(error) => out.errors.push(format!("Google Calendar: {error}")),
    }
    out
}
