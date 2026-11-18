# MailCraft b1r12 — native Calendar and Contacts form fix (TEST BUILD)

## What is being fixed

The successful extra Google buttons proved that Google authorization and basic write-back work. The old built-in MailCraft forms still forwarded some Google operations to Microsoft/local commands. This kit routes Google-owned native form operations directly through the **same b1r9 guarded Google worker**.

### Native Calendar

- **Create:** New Appointment and New Meeting on a selected **Google calendar**, timed or all-day, simple one-time events; location, description, reminder, private, and free/busy. New meeting invitations are sent only through **Send** when email guests were entered.
- **Edit:** An existing *non-recurring, organizer-owned* Google appointment can change title, location, description, start/end, all-day, reminder and visibility/free-busy. Uses Google Calendar `PATCH` and `If-Match` with the saved ETag.
- **Delete:** Existing eligible Google event uses Calendar `DELETE`, `If-Match`, and a two-press native-form confirmation.
- **Not yet supported:** recurring series/occurrences, guest-owned meetings, editing attendees, moving an existing event to another calendar, cross-zone time changes, Google Meet link creation. Those operations are explicitly declined.

### Native Contacts

- **Create:** Uses existing Contact form with **Save to** destination. Supports given/family name, multiple email/phone rows, organization/title/department, a postal address, first website, notes, birthday with a year.
- **Edit:** Uses the same native Contact form for Google-origin contact names/emails/phones/organization and these supported properties. Sends Google `updateContact` with a field mask, preserving unrelated remote fields and the source ETag.
- **Delete:** Uses Google `deleteContact`. Since that endpoint has no documented ETag parameter, the worker checks the current source ETag with `getPerson` immediately before deleting. Two presses of native-form Delete required.
- **Not yet supported:** custom display-name override, categories, favorites, public keys/certificates, or full editing of a contact's second and later postal address/website. These are not silently discarded when modified; unsupported native form changes are refused.

## Starting the build (GitHub)

From the extracted ZIP update your enhanced-builder repository files, then choose **Actions > MailCraft PortableApps - source build / ZIP / NSIS / Release > Run workflow** and set:

```
upstream_version          v0.13.0
package_revision          b1r12
compact_signature_preview true
signature_picture_button  true
google_calendar_contacts  true
google_two_way_edit      true
google_native_forms       true
publish                   false
```

The b1r12 patch runs after b1r8 download support, b1r9 write support, b1r10 native-form bridge, and b1r11 all-day fix. Each source anchor must match exactly or the workflow stops. A build failure is not an application release.

## Windows test checklist — use test records only

| Step | What to do | Pass criterion |
| --- | --- | --- |
| 1 | Back up portable `Data`; run b1r12 from a separate directory | Your original b1r9 data remains intact |
| 2 | Open Gmail and signature preview | Send/receive still works; seven signature images present |
| 3 | Press **Sync Google now** | Connected Calendar/Contacts count and status update |
| 4 | New Appointment → **Calendar: Google** → Save | New test event appears on calendar.google.com after refresh |
| 5 | Open that event in MailCraft's native form → edit its title, start/end, location → Save | Existing **same event** changes on Google; no duplicate is created |
| 6 | Open it again → Delete once, then again | First press only warns; second causes remote deletion; it disappears after refresh |
| 7 | New Contact → **Save to: your Google account** → Save | New test contact appears on contacts.google.com |
| 8 | Open the Google test contact in native form → change phone, email, company and notes → Save | The **same contact** changes on Google; other fields remain |
| 9 | Open that contact → Delete once, then again | First press warns; second removes it from Google after refresh |
| 10 | Enable Work Offline, attempt another edit | No queued write; visible warning |
| 11 | Inspect Google status and restart MailCraft | Both services continue syncing; Gmail and signature still work |

**Important:** Native Save closes after the change is **queued**. Confirmation of remote success comes from Google status and Google web, not the Save button's immediate acknowledgement. If the network fails, **check Google first**, do not blindly press Save again. Do not test deletes on real contacts or real appointments.

## Safeguards

- Google and non-Google routing is based on the actual record's owning account, not a visual string or global toggle.
- A failed/unsupported operation cannot be silently redirected into MailCraft's local Microsoft edit/delete path once recognized as Google.
- Server version checking protects existing event edits/deletions and contact edits. Contact deletion checks current Google source version immediately before sending DELETE; a concurrent change between check and delete is still theoretically possible because the API does not offer an atomic precondition for that endpoint.
- No automatic replay of uncertain write requests. Manual Google status makes failures visible.
- HTTP requests are restricted to the existing Google APIs; Google source IDs are checked, and DELETE requests have an empty body.
- OAuth permissions remain `calendar.events` and `contacts` in addition to existing read scopes; no new passwords/secrets are included in the kit.

## Rollback

Do not overwrite the current working installation. If b1r12 fails build or any test, return to your backed-up b1r9 folder. Rebuild b1r9 by setting `google_native_forms=false` to use the old explicit Google buttons; keep `google_calendar_contacts=true`, `google_two_way_edit=true`. Do not copy an experimental profile over your working Data.

## What is confirmed / what is not

- **Checked:** source-anchored b1r10 → b1r11 → b1r12 transformation in a representative fixture; fail-on-source-drift; 41 Python regression tests; kit archive integrity.
- **Not checked in this environment:** compiling real Windows Rust/egui source, executing app UI, Google OAuth consent, real Calendar/People API writes. The builder is **test-only**, not an independently verified working binary.

Google references: https://developers.google.com/workspace/calendar/api/v3/reference/events/patch ; https://developers.google.com/workspace/calendar/api/v3/reference/events/delete ; https://developers.google.com/people/api/rest/v1/people/updateContact ; https://developers.google.com/people/api/rest/v1/people/deleteContact
