# b1r11 controlled repair: Calendar all-day support

This is a **targeted experimental revision** of b1r10. It intentionally does NOT enable native Google record deletion or remove MailCraft's underlying read-only flags. Use b1r9 as your last confirmed working version for basic Google write-back.

## Confirmed source defects addressed

1. The existing b1r9 two-way patch **already preserves** the Google CONTACT source ETag. A b1r10 contact-update error cannot safely be diagnosed from the generic message alone; a legitimate stale version or a different Google API request error may be responsible. b1r11 does not bypass this conflict protection.
2. b1r10 refuses *every* all-day Google event. b1r11 experimentally permits a **new, simple all-day event** created with the native New Appointment form. MailCraft's inclusive end day is translated to Google's exclusive end day (for a single-day 20 Nov event, start `2026-11-20`, end `2026-11-21`). No recurring events or deletions.
3. Keeps b1r9 read-only download, b1r5 signature picture preview, OAuth, portable data rules, and b1r10 timed native form path unchanged.

## Intentionally excluded

- Native Delete for Google Calendar and Google Contacts. **Do not** bypass the upstream rights checks; the existing local/Microsoft commands are not equivalent to a Google API delete.
- Editing an existing Google event through the original MailCraft event form. The guarded separate Rename Selected Google Event control is the only validated editing path.
- Full native contact card editing (addresses, phones, company, notes, etc.). The selected account can still say `Read-only` in the native contact card. Only the supported name-edit queue uses a Google write; the importer continues to protect every other original engine operation.
- Recurring or attendee modification, automatic Meet links, delete operations.

## Build

GitHub Actions > Run workflow:

- Upstream `v0.13.0`
- Package revision `b1r11`
- Compact signature preview: true
- Signature picture button: true
- Google Calendar + Contacts: true
- Google two-way editing: true
- Google native forms: true
- Publish: **false**

Separate portable folder and separate Data directory. Preserve the b1r9 working install and backups.

## Acceptance tests

1. Keep Gmail and all seven signature icons working.
2. Confirm Google Calendar/Contacts download counts in the app and Google web before making any edits.
3. In the native New Appointment form, choose the Google calendar and create an all-day test event on one day. Confirm one record appears on the same day in Google Calendar web; do not retry blindly after a timeout.
4. Create a new disposable Google contact (b1r9-specific button is okay), sync. Open native Edit Contact, change only its first/last name, save once, check Google Contacts web. Do not change other fields or repeat on a real business contact.
5. For timed appointments, uncheck `All day` and choose valid start/end times; verify the original native bridge still works.
6. Test **delete in Google Calendar/Contacts web**, not MailCraft, until the remote delete path and confirmation are implemented.
7. Record the number of Google contacts before and after sync. Previous screenshots showed a decrease from 175 to 166, so confirm these counts and compare with Google Contacts web before trusting future destructive operations. A lower count alone is not proof of data deletion.

## Rollback

Set `google_native_forms=false` to restore b1r9 Google creation/rename controls. The existing contact ETag and conflict checks are unchanged. If the build fails, leave the existing installation unchanged and attach GitHub Actions logs.

## Verification limits

All local Python tests, source-anchoring tests and ZIP integrity checks were run in a Linux container. Full Windows Rust compilation, Google API round-trips and GUI workflows are not run here. b1r11 is therefore a **test-only builder**, not a verified fix. Do not publish it or use native edits on business records until your test confirms them.
