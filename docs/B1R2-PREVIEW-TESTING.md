# b1r2 — Controlled preview-only experiment

## Patch scope

The source patch is applied after b1r1's portable data adaptation and before the Rust compilation in GitHub Actions. It only modifies `crates/ui-egui/src/reading/layout.rs` and `crates/ui-egui/src/reading/view.rs` on the verified published upstream tag.

Small web-hosted image placeholders (both explicit HTML dimensions <= 48 pixels) in `Place::Preview` keep their declared icon size rather than the wide text-chip slot. This is intended for signature social icons so that tables are less likely to stack. It does not load external image URLs, change the MIME sent to recipients, bypass network/URL restrictions, or modify all mail rendering.

## Manual acceptance test

- [ ] Keep the original working b1r1 ZIP and back up the installed portable Data profile.
- [ ] Build b1r2 on GitHub Actions and verify it compiles and packages with no source drift.
- [ ] Open File > Signatures; verify original HTML source is unchanged.
- [ ] Compose a new email; compare the icon *placeholder geometry* (not icon artwork) with b1r1.
- [ ] Send a test to Gmail; verify exact original HTML rendering, images and working links.
- [ ] Receive IMAP mail; send a reply with signature; verify no new errors.
- [ ] Close and reopen the portable app; verify account and profile remain present.
- [ ] Confirm that no new network downloads happen just because the signature preview opened.
- [ ] If visual result is not an improvement, rerun build with the preview option disabled.

## Not part of this patch

- True Gmail-quality rendering of HTML/CSS (the native renderer is intentionally not a WebView).
- Fetching brand/social icons from remote hosts during composition.
- Google Calendar API and Google People API synchronization.

Google Contacts and Calendar need distinct, carefully tested account-scoped sync implementations. Do not add broad permissions to the working Google OAuth client just for this preview fix.
