# b1r14 — retire duplicate Google buttons; keep manual Sync

## Goal

The user reports native Google Calendar and Contacts operations are working under b1r13, although Delete requires repeating the action to confirm. Therefore, b1r14 makes **no new Google write, sync or Delete logic changes**. It removes the redundant b1r9 editor controls so there is only one native workflow.

| MailCraft screen | Remove | Keep |
| --- | --- | --- |
| Calendar | `New Google appointment…`, `Rename selected Google event…` | `Sync Google now`, sync status, native New Appointment/Meeting, Open/Edit/Delete |
| People | `New Google contact…`, `Rename selected Google contact…` | `Sync Google now`, sync status, native New/Edit/Delete Contact |

## Exact patch behavior

1. The build runs b1r9 and native-form integrations b1r10, b1r11, b1r12 and b1r13 unchanged.
2. When `google_native_forms=true`, b1r14 removes the two calls displaying the legacy editor buttons and modal; it removes the now-unused b1r9 `GooglePimEditor` type and state.
3. It **does not remove or change** the shared `pending_edit` Google worker, account authorization, native form APIs, central Google action routing, Google sync status/control, 15-minute auto refresh or any non-Google route.
4. When `google_native_forms=false`, b1r14 is intentionally skipped so that the b1r9 extra buttons remain available as a fallback.
5. A strict source check stops the build if required b1r13 native commands or the manual sync button are missing or a legacy block differs from the expected source.

## Windows acceptance checklist

- [ ] GitHub Actions b1r14 build succeeds, with both `google_two_way_edit=true` and `google_native_forms=true`.
- [ ] In Calendar, `Sync Google now` is present, the extra Google appointment and rename buttons are absent, and the standard New Appointment/Meeting controls remain.
- [ ] In People, `Sync Google now` is present, the extra Google contact and rename buttons are absent, and the standard New/Edit/Delete controls remain.
- [ ] Press `Sync Google now`; confirm both Calendar and Contacts refresh, and the status updates. The regular online 15-minute refresh still functions.
- [ ] Create a **disposable** native appointment and contact; confirm each appears in the matching Google web app.
- [ ] Edit each using the native form; verify the **same Google record** changes, rather than creating a duplicate.
- [ ] Delete each disposable record. The first Delete may only arm a confirmation; repeat once to confirm. **Check Google web before any third attempt**.
- [ ] Verify Gmail account, signatures and seven social icons remain functional.
- [ ] Verify portable profile persists across a clean restart, and Windows cleanup/launcher behavior is unchanged.

## Rollback

If b1r14 fails to build or displays a regression, keep using the already working b1r13 installation and its backup. Do **not** overwrite or replace a working `Data` folder with one modified by an experimental build. The b1r13 builder remains a usable source baseline. If you specifically need b1r9's separate Google controls, set `google_native_forms=false` while retaining Google write integration.

## Validation status

Source-scoped cleanup and automated Python regression checks were executed in this environment. Full Windows Rust compilation and end-to-end Google account testing must be completed by GitHub Actions and a user-run test. No external account records or credentials were accessed.

## Primary source

Official MailCraft source: https://github.com/UCS-Care-Group/mailcraft
