# MailCraft Enhanced b1r6 — Google Calendar and Contacts test plan

## Status and limitations

**Experimental native source patch, Windows compilation NOT yet verified.** The provided ZIP is a complete GitHub Actions builder repository, **not a compiled application**. It is not safe to replace the known-working b1r5 daily installation until the workflow succeeds and real-account acceptance tests pass. A failed native compile must be treated as a patch failure, not a request to disable type checks or edit Cargo.lock.

The integration is read-only **with respect to Google**. Google Calendar and Google Contacts are downloaded through GET requests only; no Google write requests are implemented. Sync mirrors removals of previously synchronized items **inside MailCraft only** after successful complete paginated reads. Locally created items and another account's data are preserved by MailCraft's engine.

The integration fetches a bounded full snapshot every 15 minutes while MailCraft is open, auto-sync is enabled, the connection is online, and a Google refresh grant is available. On a new Google account authorization the first sync runs immediately after credentials arrive. It fetches contacts, the calendar list, and events from 30 days ago to 400 days ahead, expanding recurring events through Google's event-list response. Most Google data fits; more than 100 calendars or 20,000 contacts/events per calendar is refused safely rather than partially treated as complete. Other Google features (tasks, advanced recurrence editing, other contacts, two-way sync, push notifications) aren't implemented.

## One-time Google Cloud settings (already configured by the user)

- Select existing personal Gmail-owned `MailCraft Desktop OAuth` project.
- Enable **Google Calendar API** and **People API**.
- Data Access scopes: existing `https://mail.google.com/` plus `https://www.googleapis.com/auth/calendar.readonly`, `https://www.googleapis.com/auth/contacts.readonly`, `openid`, and `userinfo.email`.
- Keep Workspace email in **Audience → Test users** while External/Testing.
- Workspace administrator may need to approve the added data scopes. Google OAuth External Testing may have seven-day refresh token expiration.

## Build instructions

1. Keep the original stable PortableApps builder separate.
2. Extract every file in this ZIP into the **MailCraft Enhanced PortableApps Builder** GitHub repository, including `.github`.
3. GitHub **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow**.
4. `upstream_version=v0.13.0`, `package_revision=b1r6`, `compact_signature_preview=true`, `signature_picture_button=true`, `google_calendar_contacts=true`, `publish=false`.
5. GitHub must successfully compile Rust and validate the PortableApps ZIP. These checks cannot be performed in this development container.
6. Install the experimental build in an independent folder with a **separate test Data profile**. Back up the working b1r5 `Data`. Do not run two instances against the same profile.
7. Connect the Workspace Google account with **Sign in with Google** and **approve Calendar and Contacts permissions** in addition to Gmail. An old pre-b1r6 refresh grant may NOT contain the new permissions. If already connected, use MailCraft's account-level **Switch/Reconnect to Google sign-in** process to obtain fresh consent without deleting mail.
8. Keep automatic synchronization enabled and Work Offline disabled. Email should function even if Calendar/Contacts consent is denied.
9. Open MailCraft's **Calendar** and **Contacts** tabs; check event and contact appearances. Verify address autocomplete (the existing Contacts view should use the merged address book). Test a contact and appointment added on Google web; check after subsequent automatic sync.
10. Delete one test item on Google web and confirm only the corresponding MailCraft-synced copy is removed after a complete refresh; do not test with a valuable item.
11. Create another Google account if needed and verify its content stays account-isolated.
12. Compose an email, use `Load signature pictures`; confirm all seven icons. Send a test email to Gmail; verify signature and sending unchanged.

## Failure and rollback

- If the GitHub workflow fails during `scripts/google_pim_patch.py`, the upstream code changed. Do **not** bypass the anchors; use v0.13.0 or update the patch for the new source release.
- If Rust compilation fails, download the GitHub Actions log and use it for a specific correction. `google_calendar_contacts=false` builds the previous b1r5 features while keeping the full builder kit intact.
- If Gmail still works but Calendar or Contacts do not appear, verify the Workspace administrator approved these new permissions and redo Google authorization. Read-only Google sync failures are intentionally independent of Gmail.
- If a mailbox does not have a refresh token saved or in memory, Google Calendar/Contacts synchronization will not begin until you sign in with Google.
- If Calendar items have incorrect times, first compare their zone and all-day setting in Google Calendar; the integration uses UTC instants and MailCraft's existing timezone conversion.
- Restore b1r5 by using its already tested build in its original folder with the original `Data` backup. Do not use or merge the experimental `Data` until validated.

## Security and dependencies

No Client ID, Client Secret, personal Workspace credentials, tokens, account profile, or signature HTML is bundled. Existing client credentials remain local to your trusted Windows install/build mechanism. The only network hosts the b1r6 read-only connector permits are `www.googleapis.com` and `people.googleapis.com` through existing TLS validation.

## Verification achieved in this environment

Python builder/unit patch tests, package integrity, and workflow YAML structure. **No Windows binary compilation, live Google API requests, or MailCraft GUI test** has been run here.
