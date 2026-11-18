# b1r9: Automatic Google refresh and limited two-way editing

## Read-only schedule already in b1r8

`google_pim_tick` checks each configured Google account at startup and once every 15 minutes while running, online and automatic sync is enabled. `poll_google_pim` merges calendar, event and contact snapshots. The b1r9 opt-in editor displays a last-successful-sync timer and a completed-run counter. To prove auto-refresh, add a new test item on Google web and leave MailCraft open for longer than 15 minutes without pressing the manual button; then restart and confirm persistent data. This behavior was implemented in b1r8 but not independently user-tested.

## b1r9 opt-in write scope

| Google service | Previous scope | Additional scope |
| --- | --- | --- |
| Google Calendar | `calendar.readonly` | `https://www.googleapis.com/auth/calendar.events` |
| Google Contacts | `contacts.readonly` | `https://www.googleapis.com/auth/contacts` |
| Gmail | `https://mail.google.com/` | None |

Do not request or use the broader `https://www.googleapis.com/auth/calendar` scope when the narrower event scope is sufficient.

## Explicitly supported operations

- New contact (given name, family name, one email) via `people.createContact`.
- Rename existing contact (given name and family name only) via `people.updateContact`, including the current CONTACT-source ETag in its metadata; other fields are left untouched. A stale ETag must fail safely.
- New primary-calendar appointment with RFC3339 timezone-aware start/end via `events.insert`, using `sendUpdates=none` so no attendees are mailed.
- Rename existing event title only with `events.patch` using `If-Match` and `sendUpdates=none`. Recurring occurrences aren't supported by the dedicated editing button.

Delete, bulk changes, all attendee changes, and changes to existing appointment times are not implemented. The original MailCraft local editing commands remain unchanged and Google-owned calendar rights remain `Read`; do not mistake the dedicated Google buttons for all-purpose native editor support.

## Data safeguards

- The same Google account and OAuth client are reused, never hardcode credentials.
- Writes only happen after explicit user action plus an acknowledgment checkbox.
- No remote deletion, no automatic replay of unsafe requests.
- Fail closed on source drift, malformed source IDs, or missing ETags.
- All requests are to fixed HTTPS Google endpoints with limited response sizes and no redirects.
- Read-only errors do not break Gmail; user can revert by rebuilding with `google_two_way_edit=false`.
- A write can succeed even if its response is interrupted: always inspect Google web before retrying.
- Rebuilds must not share the same writable `Data` folder with the confirmed b1r8 installation.

## Exact user acceptance steps

1. Confirm Google web test event automatically arrives (wait longer than 15 minutes **without clicking Sync Google now**). Repeat for a Google web test contact.
2. Reopen application and confirm content is preserved.
3. Authorize calendar.events + contacts in the existing OAuth desktop project and Workspace policy.
4. Try new test contact, rename selected contact, new appointment, rename selected event, and compare to Google web.
5. Confirm Gmail and the seven-icon signature are unaffected.
6. Report the exact GitHub Actions compilation failure or on-screen write status on failure; do **not** share tokens or complete diagnostics with private mailbox content.

## Official Google references

- https://developers.google.com/workspace/calendar/api/auth
- https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
- https://developers.google.com/workspace/calendar/api/v3/reference/events/patch
- https://developers.google.com/people/api/rest/v1/people/createContact
- https://developers.google.com/people/api/rest/v1/people/updateContact
