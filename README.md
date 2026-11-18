# MailCraft Enhanced PortableApps Builder Kit — b1r14 (Clean Native UI)

This ZIP contains **source code for a GitHub Actions Windows x64 PortableApps builder**, not a compiled MailCraft application. It is built on the user-tested **b1r13 native Google Calendar and Contacts add/edit/delete implementation** for upstream MailCraft `v0.13.0`. The b1r14 change is deliberately **UI cleanup only**.

## What changed in b1r14

With Google native forms enabled, remove the four redundant b1r9 shortcut buttons:

- New Google contact…
- New Google appointment…
- Rename selected Google contact…
- Rename selected Google event…

These are no longer necessary because MailCraft's regular **New Appointment / New Meeting / New Contact / Edit / Delete** commands have a native Google bridge through b1r10–b1r13.

**Keep** the **Sync Google now** button in Calendar and People, the sync status text, and the existing automatic 15-minute online refresh. Preserve the Google API worker, Gmail and OAuth integration, original mail features, signature preview, seven social-media icons, PortableApps data paths, and the b1r12/b1r13 native Google write/delete routing.

The source cleanup is gated by `google_native_forms=true`. In a fallback b1r9-style build with `google_native_forms=false` and `google_two_way_edit=true`, the old explicit buttons remain available. This makes rollback safe.

## Known native Delete behavior

b1r13 deletion requires a **two-step confirmation**. The first Delete may show a confirmation/warning without submitting the Google deletion. Repeat the Delete deliberately to confirm. **After the second press, verify Google Calendar or Google Contacts on the web before clicking again**; a delayed refresh can otherwise make a successful deletion look incomplete.

Do not use important records as test data. Event edits/deletes have restrictions for recurring or non-organizer-owned items. The application should refuse unsupported changes rather than silently rewriting them locally.

## Building b1r14

1. Keep a backup of your existing **working b1r13** installation and portable `Data` directory. Do not include your private data or Google credentials in the GitHub repository.
2. Extract this entire builder ZIP into the existing enhanced-builder GitHub repository, preserving `.github/workflows`, `scripts`, `patches`, `tests`, `docs`, `launcher` and `foundation`.
3. Navigate to **GitHub → Actions → MailCraft PortableApps → Run workflow**.
4. Use the following workflow inputs:

   | Input | Value |
   | --- | --- |
   | `upstream_version` | `v0.13.0` |
   | `package_revision` | `b1r14` |
   | `compact_signature_preview` | `true` |
   | `signature_picture_button` | `true` |
   | `google_calendar_contacts` | `true` |
   | `google_two_way_edit` | `true` |
   | `google_native_forms` | `true` |
   | `publish` | `false` for testing |

5. Download the newly built PortableApps artifact only after GitHub Actions succeeds. For initial testing, use a **separate portable directory** and avoid running both versions against the same active profile.
6. Confirm the extra Google shortcut row is gone but **Sync Google now** remains on **Calendar** and **People**. Verify sync status, native Calendar and People create/edit/delete, Gmail, signatures, and portable data persistence.
7. Confirm changes on the Google Calendar and Google Contacts websites. Keep b1r13 as your rollback until you verify the new build.

## Validation and scope

- `python -m unittest discover -s tests -v` runs builder patch regression tests.
- The b1r14 patch is `scripts/b1r14_remove_legacy_google_buttons.py`, applied **after** b1r13 in the workflow. It checks exact source anchors and refuses to modify the source if the build is missing native Google actions or manual sync.
- This cleanup does **not** change Google scopes, HTTP/API behavior, record deletion confirmation, the automatic-sync interval, or engine permissions.
- Local Python tests and ZIP checks are **not** a substitute for a successful GitHub Actions Windows compilation and user acceptance testing.

See [`docs/B1R14-UI-CLEANUP.md`](docs/B1R14-UI-CLEANUP.md) for detailed tests. Historical notes for b1r12 and b1r13 are in the `docs/` directory.
