
## b1r13 — main Calendar and People actions fix (experimental)

The b1r12 native-form patch did not intercept Delete from the main Calendar ribbon or People contact card. The **b1r13 patch** adds a guarded Google-only intercept at MailCraft's central command execution path and permits native form opening for selected Google records without changing the original engine permissions. See [b1r13 test checklist](docs/B1R13-MAIN-WINDOW-ACTIONS.md). Preserve a working b1r9/b1r12 installation and test with disposable Google data before publishing.

# MailCraft Enhanced PortableApps Builder Kit — b1r12 native-form repair

This is an **experimental, source-building GitHub Actions kit** for MailCraft `v0.13.0` on Windows x64. It builds a real PortableApps package; **this ZIP is the builder source, not a prebuilt application**.

**Goal:** Make MailCraft's existing **New Appointment, New Meeting and Contact** forms perform Google's create, edit and delete operations on Google-owned records, replacing the requirement to use the separate Google action buttons. The separate working b1r9 buttons remain available as a fallback.

## Safety and known status

- Latest user-confirmed working Google write-back baseline is **b1r9** (Gmail + signature preview + Calendar/Contacts sync + separate Google write buttons). Do not delete or overwrite that working installation.
- b1r10 native-form routing and b1r11 all-day correction are dependencies. b1r12 builds on both; it adds native edit and delete routing, broader native contact fields, ETag checks and guarded deletion.
- Google-origin calendars **remain read-only to MailCraft's original local engine**; only the explicit Google bridge may send mutations. This avoids accidentally editing only the local copy.
- The native form returns **queued**, not **saved**, immediately. Look at MailCraft's Google sync status and confirm changes in the Google web interface. In uncertain network errors, check Google web before trying again.
- **41 local source-level Python tests passed.** The kit has **not been built with Windows Rust toolchain or live-tested against Google** in this environment. An Actions compile failure or a failed live test means the fix is not verified.
- No broad publication: `publish=false` for testing.

## Build from the ZIP

1. Unzip and upload **the extracted contents** to your existing separate *MailCraft Enhanced PortableApps Builder* GitHub repository. Preserve `.github/workflows/build-portableapps.yml` and all `patches/` and `scripts/` subfolders. Do not upload credentials, your portable `Data` directory, or your working installation.
2. In GitHub open **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow**.
3. Set the following inputs:

| Input | Value |
| --- | --- |
| `upstream_version` | `v0.13.0` |
| `package_revision` | `b1r12` |
| `compact_signature_preview` | `true` |
| `signature_picture_button` | `true` |
| `google_calendar_contacts` | `true` |
| `google_two_way_edit` | **`true`** |
| `google_native_forms` | **`true`** |
| `publish` | **`false`** |

4. When all workflow steps succeed, download the **newly built PortableApps artifact**, make a backup of the existing portable `Data` directory, and install the test build to a **separate** folder. Do not run both installations against the same data at the same time.
5. Authorize Google Calendar/Contacts write permissions as already done for b1r9. Keep the same Google account. Verify Gmail, all seven signature images, Calendar and Contacts refresh **before** exercising native saves.
6. Test a uniquely named throwaway appointment and contact using the **original MailCraft forms**. The native Calendar form has a **Calendar** selector — choose the Google calendar; the new Contact form has **Save to** — choose the connected Google account. Then test edits and deletions on these throwaway objects, checking the corresponding Google websites and MailCraft's Google status.
7. On the first native **Delete**, the form shows a warning without sending a request. Press **Delete AGAIN** to confirm. Never test on important records first.

See **`docs/B1R12-NATIVE-GOOGLE-CRUD.md`** for a detailed pass/fail checklist, limitations, and rollback.

## Preserved

Gmail/OAuth workflow, the working signature preview with seven social icons, 15-minute automatic Google synchronization while online, portable `Data` location, the b1r9 extra write controls, source audit checks, and test-only release handling are not replaced.

## Current limitations

Only **single, non-recurring, organizer-owned Google events** are eligible for existing-event changes and deletion. Editing guests, recurrence, cross-account calendar moves, and Google Meet setup are intentionally refused, not silently dropped. Google Contacts native form cannot save display-name overrides, categories, favorites, or encryption keys; it rejects those changes. For contacts with multiple addresses/websites, MailCraft's original form only exposes the first, so these edits need care. Birthdays with no year cannot be fully represented in the original form. Deletion from Google is real and may not be recoverable, even if the separate MailCraft list has not refreshed yet.
