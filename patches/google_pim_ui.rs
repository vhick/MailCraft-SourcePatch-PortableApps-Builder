// SPDX-License-Identifier: MIT OR Apache-2.0
//! b1r6 experimental Google Calendar and Contacts read-only synchronization.
//! Uses the same Google account and saved refresh authorization as Gmail.
//! Runs independently of mail Send/Receive and Microsoft's calendar sync.
use std::collections::HashMap;
use std::sync::mpsc::{Receiver, TryRecvError};
use std::time::{Duration, Instant};

use mailcraft_engine::cmd::remote;
use mailcraft_model::{Account, Id, OAuth, OAuthProvider};
use mailcraft_model::remote::{CalendarsDownload, ContactsDownload, EventsDownload};
use mailcraft_model::sync::Tokens;

use crate::MailApp;

/// The host owns sockets and refreshes the existing Google authorization.
/// The UI never stores access tokens in account data or the PortableApps builder.
pub struct GooglePimRequest {
    pub account: Account,
    pub oauth: OAuth,
    pub refresh: String,
    /// Reuse the current short-lived Google access token when it is still valid.
    pub access: String,
    pub expires_at: i64,
}

#[derive(Default)]
pub struct GooglePimResult {
    pub account: Id,
    pub email: String,
    pub refreshed: Option<Tokens>,
    pub calendars: Option<CalendarsDownload>,
    pub events: Vec<EventsDownload>,
    pub contacts: Option<ContactsDownload>,
    pub errors: Vec<String>,
}

#[derive(Default)]
pub(crate) struct GooglePimSync {
    /// At most one job across all Google accounts; no overlap or repeated network requests.
    pub(crate) busy: Option<(Id, u64, Receiver<GooglePimResult>)>,
    pub(crate) last: HashMap<Id, Instant>,
    /// Visible in Calendar and People; contains no token or private contact data.
    pub(crate) last_summary: String,
    /// Visible manual retry sequence, to show that a click was accepted.
    pub(crate) manual_attempts: u64,
}

impl MailApp {
    pub(crate) fn poll_google_pim(&mut self) {
        let Some((account, opening, rx)) = &self.google_pim.busy else { return };
        let (account, opening) = (*account, *opening);
        if opening != self.session.openings() {
            self.google_pim.busy = None;
            self.google_pim.last.clear();
            return;
        }
        let result = match rx.try_recv() {
            Ok(result) => result,
            Err(TryRecvError::Empty) => return,
            Err(TryRecvError::Disconnected) => {
                self.google_pim.busy = None;
                self.google_pim.last_summary = "Google sync failed: background connection ended; try Sync Google now".into();
                self.status("Google Calendar and Contacts connection ended before a response");
                return;
            }
        };
        self.google_pim.busy = None;
        let Some(current) = self.session.mailbox.account(account) else { return };
        if result.account != account || !current.email.eq_ignore_ascii_case(&result.email) { return; }
        // Refreshing Google PIM permissions must not overwrite the Gmail access token.
        // Google usually retains the original refresh token; if it rotates, update only it.
        if let Some(refreshed) = result.refreshed {
            if !refreshed.refresh.is_empty() {
                let changed = self.tokens.get(&account).is_some_and(|t| t.refresh != refreshed.refresh);
                if let Some(mail) = self.tokens.get_mut(&account) {
                    mail.refresh = refreshed.refresh.clone();
                }
                if changed { self.remember("refresh", account, &refreshed.refresh); }
            }
        }
        // Keep a visible diagnostic even if subsequent Gmail status messages overwrite the status bar.
        let calendar_count = result.calendars.as_ref().map_or(0, |r| r.calendars.len());
        let event_count: usize = result.events.iter().map(|r| r.events.len()).sum();
        let contact_count = result.contacts.as_ref().map_or(0, |r| r.contacts.len());
        let mut count = 0usize;
        let mut errors = result.errors;
        if let Some(calendars) = result.calendars {
            if let Err(e) = remote::apply_calendars(&mut self.session, &calendars) {
                errors.push(format!("Google calendars could not be merged: {e}"));
            } else { count += 1; }
        }
        for events in result.events {
            if let Err(e) = remote::apply_events(&mut self.session, &events) {
                errors.push(format!("Google events could not be merged: {e}"));
            } else { count += 1; }
        }
        if let Some(contacts) = result.contacts {
            if let Err(e) = remote::apply_contacts(&mut self.session, &contacts) {
                errors.push(format!("Google contacts could not be merged: {e}"));
            } else { count += 1; }
        }
        if errors.is_empty() {
            self.google_pim.last_summary = format!(
                "Google sync completed: {calendar_count} calendars, {event_count} events, {contact_count} contacts"
            );
            if count > 0 { self.status("Google Calendar and Contacts synchronized (read-only)"); }
        } else {
            // Only safe, short pre-authored errors; never include tokens, URLs, or API response bodies.
            let first = errors.first().map(String::as_str).unwrap_or("unknown error");
            let clean: String = first.chars().filter(|c| !c.is_control()).take(180).collect();
            self.google_pim.last_summary = format!("Google sync problem: {clean}");
            self.status(format!("Google Calendar/Contacts: {} sync problem(s); Gmail is unaffected", errors.len()));
            for error in &errors { log::warn!("google PIM: {}", error); }
        }
    }

    pub(crate) fn google_pim_tick(&mut self, ctx: &egui::Context) {
        if self.google_pim.busy.is_some() {
            ctx.request_repaint_after(Duration::from_millis(400));
            return;
        }
        if self.unconfirmed || self.data_removed { return; }
        if self.offline() {
            self.google_pim.last_summary = "Google sync paused: Work Offline is enabled".into();
            return;
        }
        if !self.session.driver.auto_sync() {
            self.google_pim.last_summary = "Google sync paused: automatic synchronization is disabled".into();
            return;
        }
        if self.services.google_pim.is_none() {
            self.google_pim.last_summary = "Google integration is unavailable in this build".into();
            return;
        }
        const REFRESH_EVERY: Duration = Duration::from_secs(15 * 60);
        // One Google account at a time; a newly signed-in account runs immediately.
        let account = self.session.mailbox.accounts.iter().find(|a| {
            a.oauth.as_ref().is_some_and(|o| o.provider == OAuthProvider::Google)
                && !a.email.trim().is_empty()
                && self.google_pim.last.get(&a.id).is_none_or(|at| at.elapsed() >= REFRESH_EVERY)
                && (self.tokens.get(&a.id).is_some_and(|t| !t.refresh.is_empty())
                    || self.remembered("refresh", a.id).is_some())
        }).cloned();
        let Some(account) = account else {
            if self.google_pim.last_summary.is_empty() {
                self.google_pim.last_summary = "Google sync not started: reconnect with Google to grant Calendar and Contacts access".into();
            }
            ctx.request_repaint_after(Duration::from_secs(30));
            return;
        };
        let Some(oauth) = account.oauth.clone() else { return };
        let refresh = self.tokens.get(&account.id).map(|t| t.refresh.clone())
            .filter(|t| !t.is_empty()).or_else(|| self.remembered("refresh", account.id)).unwrap_or_default();
        if refresh.is_empty() {
            self.google_pim.last_summary = "Google sync needs a saved Google sign-in: reconnect the account".into();
            return;
        }
        let (access, expires_at) = self.tokens.get(&account.id)
            .map(|tokens| (tokens.access.clone(), tokens.expires_at))
            .unwrap_or_default();
        let request = GooglePimRequest {
            account: account.clone(), oauth: self.effective_oauth(oauth), refresh, access, expires_at,
        };
        let Some(service) = self.services.google_pim.as_ref() else { return };
        self.google_pim.last.insert(account.id, Instant::now());
        self.google_pim.last_summary = format!("Syncing Google Calendar and Contacts for {}…", account.email);
        self.google_pim.busy = Some((account.id, self.session.openings(), service(request)));
        ctx.request_repaint_after(Duration::from_millis(400));
    }
}

impl MailApp {
    /// Manual troubleshooting entrypoint in Calendar and People.
    /// No separate credentials or unsafe network behavior: invokes the same guarded read-only job.
    pub(crate) fn google_pim_controls(&mut self, ui: &mut egui::Ui) {
        let has_google = self.session.mailbox.accounts.iter().any(|a| {
            a.oauth.as_ref().is_some_and(|o| o.provider == OAuthProvider::Google)
        });
        if !has_google { return; }
        ui.horizontal_wrapped(|ui| {
            let enabled = self.google_pim.busy.is_none();
            if ui.add_enabled(enabled, egui::Button::new("Sync Google now")).clicked() {
                // Explicit user retry bypasses the 15-minute timer, not offline/auth safeguards.
                self.google_pim.manual_attempts = self.google_pim.manual_attempts.saturating_add(1);
                self.google_pim.last.clear();
                self.google_pim.last_summary = format!("Google sync retry #{} requested…", self.google_pim.manual_attempts);
                self.google_pim_tick(ui.ctx());
            }
            let summary = if self.google_pim.last_summary.is_empty() {
                "Google Calendar/Contacts: awaiting first sync"
            } else {
                self.google_pim.last_summary.as_str()
            };
            ui.label(summary);
        });
    }
}
