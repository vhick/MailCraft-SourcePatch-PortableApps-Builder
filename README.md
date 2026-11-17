# MailCraft Google PIM Integration — Developer Foundation (November 17, 2026)

**Status: core only, not a functioning MailCraft Calendar or Contacts integration.**

This project is a validated, read-only synchronization/data-normalization core for future MailCraft Enhanced PortableApps work. It does not obtain Google tokens, call live APIs, modify MailCraft's GUI, persist contacts/events, alter the user's existing Gmail OAuth credentials, or perform automatic synchronization. **Do not describe it as a ready-to-use Calendar / Contacts release.**

The current working portable baseline is **MailCraft Enhanced b1r5**, confirmed by the owner to render all seven remote HTML-signature icons and preserve Gmail email sending. Keep b1r5 as-is while developing native Google PIM support.

## Contents

- `integration/google_pim_core.py`: deterministic account-scoped Google Calendar + People API pagination, full and incremental sync, tombstones, and safe expired-token fallback. Transport is injected; no outbound network access and no tokens are stored.
- `tests/test_google_pim_core.py`: offline tests for the normal and failure paths.
- `docs/GOOGLE-SETUP.md`: Google Cloud configuration and Workspace admin considerations.
- `docs/NATIVE-INTEGRATION-ROADMAP.md`: exact native integration gaps and acceptance gate.

## Check core functionality

`python -m unittest discover -s tests -v`

These tests demonstrate only the Google API data synchronization core. They do **not** demonstrate one-sign-in MailCraft integration.

## Important security boundaries

Only enable scopes after a functional UI and native host path exists. Never place OAuth credentials, contacts, calendars, tokens, or an individual's HTML signature inside a public builder. Keep calendar/contact sync opt-in and read-only first. Reject all data outside the active account identity and collection. Treat failed or missing pages as an incomplete sync; never purge prior data because of transient failures.
