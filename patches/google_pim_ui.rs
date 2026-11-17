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
            if count > 0 { self.status("Google Calendar and Contacts synchronized (read-only)"); }
        } else {
            // Do not expose HTTP bodies, OAuth secrets or private contact details.
            self.status(format!("Google Calendar/Contacts: {} sync problem(s); Gmail is unaffected", errors.len()));
            for error in &errors { log::warn!("google PIM: {}", error); }
        }
    }

    pub(crate) fn google_pim_tick(&mut self, ctx: &egui::Context) {
        if self.google_pim.busy.is_some() {
            ctx.request_repaint_after(Duration::from_millis(400));
            return;
        }
        if self.unconfirmed || self.data_removed || self.offline()
            || !self.session.driver.auto_sync() || self.services.google_pim.is_none() {
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
            ctx.request_repaint_after(Duration::from_secs(30));
            return;
        };
        let Some(oauth) = account.oauth.clone() else { return };
        let refresh = self.tokens.get(&account.id).map(|t| t.refresh.clone())
            .filter(|t| !t.is_empty()).or_else(|| self.remembered("refresh", account.id)).unwrap_or_default();
        if refresh.is_empty() { return; }
        let request = GooglePimRequest {
            account: account.clone(), oauth: self.effective_oauth(oauth), refresh,
        };
        let Some(service) = self.services.google_pim.as_ref() else { return };
        self.google_pim.last.insert(account.id, Instant::now());
        self.google_pim.busy = Some((account.id, self.session.openings(), service(request)));
        ctx.request_repaint_after(Duration::from_millis(400));
    }
}
