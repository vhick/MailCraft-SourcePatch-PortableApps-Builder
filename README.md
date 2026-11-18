# MailCraft Enhanced PortableApps Builder b1r11 — experimental safe repair

**New:** Keeps b1r10 native forms; adds guarded all-day Google appointment creation, preserving existing contact ETag conflict protection. Original native delete and all other unsupported Google writes remain unavailable. See `docs/B1R11-SAFE-CORRECTIONS.md` before building. **This has not been compiled or live-tested on Windows.**

# MailCraft Enhanced PortableApps Builder b1r10 (EXPERIMENTAL native form bridge)

**b1r9 is the latest user-confirmed working enhanced baseline for Gmail, seven signature pictures, Google Calendar/Contacts downloads and basic event/contact creation.**

## Baseline

**b1r8 and b1r9 have been confirmed working on Windows** by the user: Gmail; HTML signature and all seven pictures; **2 Google calendars, 118 events, and 174 contacts** downloaded successfully. **Do not replace that working installation** with this experimental revision until the tests below pass. This repository remains separate from the original stable MailCraft builder.

## New b1r10 native-form pilot

- **Existing New Appointment / New Meeting:** When the calendar selected in the normal MailCraft editor belongs to a Google account, the form now queues a Google event rather than a local-only copy. The pilot supports **simple timed appointments**, description, location, reminders, privacy/free-busy, and meetings with direct plain-email guests entered with semicolons. Guest invitations are sent **only when pressing Send** in the native meeting editor. Selecting a local/Microsoft calendar retains the original behavior.
- **Existing New Contact:** A Save to destination selector appears in MailCraft's normal new-contact form. It defaults to the only connected Google account when exactly one exists; the user can switch to **This computer (local)**. Google creation supports first name, last name and exactly one email. Other populated fields are explicitly rejected, not silently discarded. Existing synced Google contacts can change first and last name through the native contact editor; unsupported edits are rejected.
- Original Google-specific b1r9 buttons remain as fallback. This pilot **does not yet** handle Google Meet link creation, recurring or all-day events, modifying event times/attendees after creation, contact phone/address/organization fields, deletes, or full conflict resolution. Native event edit of an existing synced Google item remains read-only for now.
- The `google_native_forms` switch defaults to **false**; turn it on only for a separate test installation, with `google_calendar_contacts=true`, `google_two_way_edit=true`, and `publish=false`.
- A native form queues a write and immediately closes; only the **later Google sync status** confirms a successful remote save. After a network error **check Google web before retrying** to avoid duplicate appointments or invitations.

## Improvements in b1r9

1. Existing automatic, read-only Google Calendar and Contacts refresh every **15 minutes** remains intact. It runs while MailCraft is open, online, and its automatic synchronization is enabled. The optional editor patch now shows the last successful refresh and number of completed runs so the timing can be checked without repeatedly pressing **Sync Google now**.
2. **Optional, explicit first-stage two-way editing controls**: create a Google contact (first/last name and email), rename an existing selected Google contact (first/last name only), create a *simple timed appointment* on the primary Google calendar, and rename an existing selected Google event (title only). Each operation requires the user to check **I understand this will change data in Google** and click **Save to Google**.
3. Google writes use Google's existing account authentication, with independent error reporting. On success the application downloads Calendar and Contacts again. Outgoing Gmail and signature behavior are not modified.
4. Existing-event writes include the server ETag (`If-Match`), and contacts use their CONTACT-source ETag, so changes made elsewhere cause the operation to fail rather than silently overwrite new edits. A potentially completed request is **never auto-retried**.

**Not implemented yet:** deletion of events/contacts; bulk edits; changing event attendees, recurrence, location or date/time of existing events; changing multiple addresses/phone numbers of existing contacts; bidirectional editing through *MailCraft's original* ribbon/editor. Google-origin calendars remain marked read-only to that original editor: use the new explicit **Google** buttons instead. These limitations deliberately prevent data loss in this experimental first write-enabled revision.

## Build choices

Upload the *contents of the extracted ZIP* to the separate enhanced-builder GitHub repository. Do not upload tokens, downloaded credential JSON, account data, or passwords.

Go to **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow** and use:

| Input | Value |
| --- | --- |
| `upstream_version` | `v0.13.0` |
| `package_revision` | `b1r10` |
| `compact_signature_preview` | `true` |
| `signature_picture_button` | `true` |
| `google_calendar_contacts` | `true` |
| **`google_two_way_edit`** | **`true` for b1r9 editing** |
| **`google_native_forms`** | **`true` to test native form bridge; `false` to keep b1r9 behavior** |
| `publish` | **`false`** for the initial test |

The new step runs **after** the proven b1r8 Google patch, checks exact source anchors, and stops on source drift. The download, launcher, PortableApps packaging, tests, and original b1r8 fallback remain included.

## Additional Google OAuth permissions required ONLY for editing

Existing read-only scopes are not sufficient for creating/changing Google records. In Google Cloud Console → Google Auth Platform → Data Access add:

- `https://www.googleapis.com/auth/calendar.events` (write events; no requirement for full `calendar` scope)
- `https://www.googleapis.com/auth/contacts` (write Google Contacts)

**Keep** existing `https://mail.google.com/`, `openid`, `userinfo.email`/`email`, `calendar.readonly` and `contacts.readonly`. Google Workspace administrator policy may require approval of the two new scopes. After building with editing enabled, reconnect the Google account and authorize the additional permissions; the *same* Google Desktop Client ID and Secret can be used. Do not publish the OAuth project or change to production just for testing.

**If `google_two_way_edit` is false, leave Google Cloud permissions and MailCraft b1r8 as they are.**

## Safe Windows acceptance order

1. **Backup** the existing portable `Data` folder and keep a separate complete b1r8 installation. Never launch two installations against the same writable profile.
2. Build b1r9 with `google_two_way_edit=true` and `publish=false` in GitHub Actions. Check compile and artifact verification; any failure means **do not install** the experimental build.
3. Install/test in a separate portable folder. Add the Google account; finish consent for write scopes. Verify Gmail send/receive and the signature's seven visible icons.
4. **Auto-refresh verification:** in Google Calendar web, create a uniquely named *test-only* event for the next few days. Do NOT click **Sync Google now**. Keep MailCraft running and online for at least one full 15-minute refresh interval. Check whether the event appeared and the *successful run count* increased. Repeat by adding a uniquely named contact in Google Contacts web. Verify both remain after restarting MailCraft.
5. **Write test 1:** In MailCraft, use **New Google contact…** to add a *test-only* contact. Explicitly confirm then Save. Look it up in Google Contacts web and in MailCraft after synchronization. Rename it using **Rename selected Google contact…** and check both places. Existing email/phone fields are not changed by rename.
6. **Write test 2:** Use **New Google appointment…** with a title and start/end time including the `+08:00` offset, e.g. `2026-11-21T09:00:00+08:00` through `2026-11-21T09:30:00+08:00`. Confirm and save. Check Google Calendar web and MailCraft. Select the event in MailCraft and use **Rename selected Google event…**, then verify the new title appears in Google Calendar.
7. Test **offline mode** and denied scopes. The app should report errors without changing Gmail. Do not press Save again after a network error until you check Google web to see if an earlier request was received.
8. **Rollback:** use your untouched b1r8 installation. Disabling `google_two_way_edit` in a rebuilt b1r9 also drops the experimental write feature while preserving b1r8 read-only sync.

## Verification status

- Local Python static/source patch tests: passed (see `tests/` and workflow).
- ZIP file integrity and YAML parsing: checked in this environment.
- **Actual Windows Rust compilation: not yet verified.**
- **Actual Google write and automated refresh behavior: not yet verified.**

The b1r9 kit is experimental and may require adjustment after GitHub Actions or live Google API feedback. Never test on important customer records first.
