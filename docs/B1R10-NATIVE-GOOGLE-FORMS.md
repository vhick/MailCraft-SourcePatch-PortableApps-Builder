# MailCraft Enhanced b1r10 — native Google form pilot

## Objective and boundaries

Based on the user-confirmed b1r9 MailCraft Gmail, Calendar and Contacts builder. This **experimental source patch** connects only carefully scoped operations in MailCraft's **existing** New Appointment, New Meeting and New Contact forms to the existing b1r9 Google write queue. This is NOT a general two-way Google editor.

- Choose the **Google calendar** in the normal New Appointment or New Meeting form; choose a **local/Microsoft calendar** to retain original MailCraft behavior.
- **Appointment:** timed start/end, summary, description, location, popup reminder, visibility and busy/free. Writes directly to selected Google Calendar. The form closing means **queued**, not yet saved.
- **Meeting:** attendees are plain email addresses separated with semicolons, maximum 50; the user must press **Send** to dispatch real Google Calendar invitations (`sendUpdates=all`). Save with guests refuses safely. **Google Meet links are NOT created.**
- **New Contact:** normal contact form has a **Save to** selector. When exactly one Google account exists, Google is preselected; local can be chosen. First, last, exactly one email only in the pilot. Any unsupported populated fields produce an error, not a partial save.
- **Edit existing Google contact:** first and last name only, guarded by the saved People API ETag. Other field modifications are rejected. Use original b1r9 Google editing controls for supported renames as fallback.
- **Not implemented:** Google event editing after creation (time, attendees, recurrence), automatic Google Meet links, all-day/recurring meetings, contact phones/organizations/addresses, deletes, bulk writes, conflict resolution between two open devices, or direct management of event responses.
- **Security:** private credentials never appear in the builder; original Gmail authorization and signature are unchanged. Writes are only sent after direct user Save/Send and are never blindly retried. API errors and sync failures are displayed; avoid retrying until checking Google web.

## GitHub Actions build

1. Back up your confirmed working b1r9 portable installation and all `Data` contents. Test in a **different portable directory with its own Data**.
2. Upload this builder kit's contents to the **separate enhanced builder repository** (not the stable one), preserving `.github`.
3. Actions > `MailCraft PortableApps - source build / ZIP / NSIS / Release` > Run workflow:

| Field | Value |
| --- | --- |
| upstream_version | `v0.13.0` |
| package_revision | `b1r10` |
| compact_signature_preview | `true` |
| signature_picture_button | `true` |
| google_calendar_contacts | `true` |
| google_two_way_edit | `true` |
| **google_native_forms** | **`true`** |
| **publish** | **`false`** |

4. A compile or patch failure is a **stop**, not a reason to patch the GitHub Actions step away. Keep using b1r9 until fixed.
5. Your existing Google Cloud OAuth client and `calendar.events` / `contacts` scopes should already be set from b1r9. Do not upload any client secret, refresh token or account data into GitHub.

## Safe acceptance sequence

1. Confirm Gmail send/receive, the full seven-icon signature and two existing Google calendars are still correct.
2. Create a unique test appointment **using the native New Appointment** button. Select the Google calendar; enter a normal timed start/end, title and location. Click Save once. In MailCraft's Google sync status, verify the write is complete, then in Google Calendar web confirm the item exists once and in the correct calendar.
3. Create a meeting **only to a disposable email account you control**. In native New Meeting, type a plain email, title and dates, select the Google calendar, leave Online Meeting unchecked and press Send. Verify an actual invite arrived once. Do not test with clients or colleagues.
4. Open native New Contact. Verify the Save to selector lets you choose Google or This computer (local). Create a new basic contact on Google with first and last name and one email. Check Google Contacts web. Try adding a company name as a deliberate **negative test**: it must refuse rather than silently drop the data.
5. Rename the test Google contact's first or last name through the normal contact form, and check it in Google Contacts web.
6. Test a local calendar/contact entry: native MailCraft behavior must remain unchanged. Test an all-day/recurring Google event or Google Meet toggle: it must refuse safely, not create an incorrect item.
7. Test restart and background refresh. Never repeat a submission after a network error until Google Calendar/Contacts web confirms whether it was received. Multiple save retries can create duplicate events or invitations.

## Rollback

Keep b1r9 source and installed portable folder intact. To compile the previous behavior from this kit, set **`google_native_forms=false`** while keeping `google_two_way_edit=true`. For read-only behavior set both editing flags false. Do not share writable `Data` between simultaneous instances.

## Verification performed here

- Python source-anchoring / fail-closed patch tests and ZIP structure checks: pass.
- The b1r10 source patch was reviewed against the **v0.13.0** upstream forms and Google API docs.
- Actual Windows Rust compilation, interaction with native forms, real guest invites and Google contact writes: **NOT yet verified**.

This is a pilot build requiring a GitHub Actions compile and live acceptance tests before general use. Real attendee invitations are external actions; review addresses carefully.
