# b1r13 — main-window Calendar/People Delete and Edit fix (TEST BUILD)

## Why b1r12 didn't fix the screenshot

The prior repair intercepted the **Delete button inside the editor form**. The screenshots show the main Calendar ribbon (trash icon) and the People contact-card Delete button. These issue `calendar.delete` and `people.delete` through `MailApp::run` / `MailApp::execute`, which went to `self.session.run` in the original engine. That engine sees the Google record's local mirror as read-only and refuses it. The extra Google buttons bypassed that engine, which is why they worked.

Upstream inspection: v0.13.0 `crates/ui-egui/src/lib.rs` defines `MailApp::enabled` / `run` / `execute`, `people_view.rs` invokes `app.run("people.delete", {id})`, and `calendar_view.rs` invokes `app.run("calendar.delete", {id})`. This repair addresses that **previously missed call path**, without changing the imported record's original engine permissions.

## Changes

- Main-window Delete from People card, context menu, ribbon or shortcut now routes *Google-owned* contacts to the guarded `deleteContact` worker.
- Main-window Delete from Calendar ribbon or event context menu routes *Google-owned* simple events to the guarded Google Calendar delete worker.
- Main-window edit controls can open the native forms for Google data even while their local mirror remains engine-read-only.
- The central command handler now recognizes Google edit commands before the original engine, preventing their accidental fallthrough to the wrong writer.
- Does not change local/Microsoft records, does not fake calendar write permissions, does not bypass Google OAuth, rejects multiple-item delete and unsafe recurring events, and keeps the existing b1r12 two-press confirmation.
- An attempted delete is **queued**; it is not final until the Google API replies and a refresh confirms disappearance.

## Build and test

1. Back up your current working portable `Data` folder. Use a separate test installation; do not overwrite your working build.
2. Upload/extract the complete b1r13 builder kit to your GitHub builder repository.
3. Actions -> **MailCraft PortableApps** -> Run workflow. Set upstream version `v0.13.0`, revision `b1r13`, Google Calendar/Contacts = true, Google two-way editing = true, native forms = true, publish = false.
4. Download built application only on a successful workflow, preferably a debug/test artifact rather than a published release.
5. Synchronize, select a test event previously created by the separate button and click main **Delete**. Follow the two-press confirmation; a first warning is intentional. **Do not delete production events.** Confirm the same event disappeared on calendar.google.com.
6. Select a test contact previously created by the separate button, click the People card **Delete**, follow the two-press confirmation, and confirm removal on contacts.google.com.
7. Test main **Edit** opens the form, change a name/title, save, then verify that the *same* Google record changed. Test native New Contact/New Appointment separately.
8. Confirm Gmail, seven signature icons, sync status, auto refresh, and portable Data retention still work.

### If it still fails

Do **not** repeatedly press Delete or Save. Check Google web first. Save the GitHub Actions logs if compilation failed; if the app runs but refuses, copy MailCraft's diagnostics, the exact error text and identify whether you clicked the **main ribbon**, **People card**, or **form button**. This pinpoints the remaining path.

### Status

- **Checked here:** upstream v0.13.0 call paths via web source, exact-anchor source transformation, Python local tests, fail-on-drift behavior, ZIP integrity.
- **Not checked here:** full Windows Rust compilation, app GUI interactions or live Google API edits. This is an experimental builder; not yet a proven native-form fix.

## References

- Upstream UI: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/crates/ui-egui/src/lib.rs
- Upstream People: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/crates/ui-egui/src/people_view.rs
- Google Calendar delete: https://developers.google.com/workspace/calendar/api/v3/reference/events/delete
- Google Contacts delete: https://developers.google.com/people/api/rest/v1/people/deleteContact
