# Integration roadmap: one Google sign-in -> mail + calendar + contacts

## What the MailCraft v0.13.0 source audit establishes

- `crates/net/src/oauth.rs` currently sets `GOOGLE_SCOPE` to `https://mail.google.com/ openid email` and restricts Google to the Mail resource rather than Microsoft Graph.
- `crates/ui-egui/src/account_setup.rs` handles Add Account, Google OAuth and account switching. It must own the user decision to enable Calendar / Contacts and preserve Gmail on denied scopes.
- `crates/ui-egui/src/calendar_sync.rs` and `crates/engine/src/sync_driver/calendar.rs` drive Microsoft Graph calendar/contacts synchronization. They do not yet recognize Google accounts as providers of synchronized calendar and contacts data.
- `crates/host/src/graph.rs` defines Microsoft Graph request/result types, not a generic Google PIM service. Never pass Google bearer tokens to Graph endpoints.
- `crates/model/src/calendar.rs`, remote contact models, and MailCraft contact UI need explicit, versioned mapping of Google event/person data.
- `crates/dav/src/lib.rs` exposes bounded document parsing only; DAV discovery/sync are not wired up at this release, so merely entering CalDAV/CardDAV URLs cannot meet the user's requested automatic setup.

## Phase 1 — read-only native sync (next work item; NOT implemented in this kit)

1. Add opt-in scope constants to Google OAuth: Calendar read-only, Contacts read-only. A user's explicit choice grants the permissions in the **same** browser sign-in, and existing users reauthorize once to upgrade. Verify tokens have the granted scopes before reading each API.
2. Add a Google PIM service to the host layer with TLS, timeouts, response limits, account-bound access token, and 429/5xx backoff. Never expose tokens in logs. Reuse existing Google OAuth refresh grants and ensure it remains independent of Gmail success.
3. Map Calendar API event objects and People API `Person` objects to native MailCraft `Calendar`, `Event`, `Contact` (rather than duplicating UI screens). Preserve IDs, recurring instances, timezone, all-day dates, cancellation/deletion flags, and the Google etag.
4. Add an account-scoped sync scheduler: initial sync on approved login, refresh on restart, faster refresh when calendar/contacts foreground, normal periodic refresh (~15 minutes as a starting policy). Skip while offline.
5. Persist only bounded account-scoped cache and sync cursors in `Data/MailCraft` for portable mode. Store OAuth refresh secrets using the existing *portable-safe* credential policy and never in a public repo; don't alter the b1r5 profile model until migrations and rollback tests pass.
6. Implement server-derived deletion only after a **complete**, successful per-collection sync; never remove local objects on network timeout or 429. Use Google 410 / `EXPIRED_SYNC_TOKEN` to reset the cursor and replace the snapshot only after successfully retrieving the entire result set.
7. The UI should show provider+account identity and individual statuses ('Gmail connected', 'Calendar syncing', 'Contacts sync failed', etc.). Contacts must be available for compose address autocomplete.

## Phase 2 — controlled two-way sync (future, NOT included)

After read-only production acceptance, implement Google Calendar create/update/delete/RSVP and Google Contacts create/update/delete with separate scopes and safeguards. This requires conflict resolution with etags, detached occurrences, cancellations, and accidental deletion prevention.

## Mandatory acceptance tests before calling a release 'working'

- Same Google sign-in grants mail, Calendar and Contacts on a newly added account.
- An existing MailCraft Google account can reconnect once to upgrade scopes without losing downloaded mail.
- Denying either API doesn't stop Gmail.
- Correct calendar events including all-day, recurring, DST/tz, secondary calendars; correct contact email/name/phone and address autocomplete.
- Different Google accounts never cross-populate data. A removed account has its own caches removed safely; other accounts remain unchanged.
- Incremental updates and tombstones work; expired cursors trigger full safe sync; 401 asks user to reconnect; 429/5xx leave existing data intact.
- Offline and restart behavior; no duplicate contacts/events after repeated sync, no malicious links, no secret leaks in logs or installer, private profile preserved.
- Windows x64 build + GUI test on the user's separate enhanced builder; existing b1r5 signature preview and Gmail sending remain unchanged.

## API and security sources

https://developers.google.com/workspace/calendar/api/guides/sync
https://developers.google.com/people/api/rest/v1/people.connections/list
https://developers.google.com/workspace/calendar/api/auth
https://developers.google.com/identity/protocols/oauth2/resources/granular-permissions
https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/docs/google-accounts.md
