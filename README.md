# MailCraft Enhanced PortableApps Builder b1r8

## Purpose

Experimental b1r8 corrects the Google Calendar and Contacts synchronization error discovered during b1r7 testing. Email works, Google has authorized all five listed services, but the Calendar and People views repeatedly report that new consent is required. The previous builder misleadingly labeled every refresh failure as a consent problem.

## What changed from b1r7

1. Try MailCraft's existing in-memory Google access token first if it has more than 90 seconds remaining. This avoids a needless token-refresh request immediately after successful Google sign-in.
2. If the first API request is rejected with HTTP 401 or 403, attempt one token refresh and retry with the new token.
3. Distinguish rejected/expired tokens, HTTP 401/403, and connection/renewal failures. Do not display token strings or provider error bodies.
4. Show an incrementing retry number when **Sync Google now** is pressed, so you can tell that the button registered your click.
5. Keep the b1r5 signature preview, Gmail authentication, PortableApps launcher, and separate Data handling untouched.

This does not introduce Calendar or Contacts writing. Only read-only Google APIs are called.

## Building with GitHub Actions

Upload this archive's entire contents—including `.github`—to your **separate enhanced MailCraft builder repository**. Then choose **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow**.

| Input | Value |
|---|---|
| Upstream version | `v0.13.0` |
| Package revision | `b1r8` |
| Compact signature preview | `true` |
| Signature picture button | `true` |
| Google Calendar + Contacts | `true` |
| Publish | `false` |

## Acceptance test

1. Use a separate MailCraft installation and `Data` folder. Back up the current working data first.
2. Open **Calendar** and click **Sync Google now** once. Look for the attempt number and the subsequent status. Repeat in **People**.
3. If the result is HTTP 403, recheck Google's granted permissions, enabled APIs, and Workspace app access; if it reports token rejection, reconnect Google. Do not repeatedly reconnect unless it says authorization was rejected.
4. If it succeeds, verify several known appointments and contacts, then test automatic refresh and Gmail send/receive.
5. Confirm the manual **Load signature pictures** button still loads all seven icons.
6. If it fails, report the *visible status wording* and relevant non-sensitive diagnostic details, not access tokens, client secrets, or full credential JSON.

## Rollback and limitations

The **b1r5** signature and Gmail build is the latest confirmed reliable version. b1r8 is an experimental source kit, and has only been validated by offline Python tests. Windows compilation and live API synchronization have not been verified here. Disable `google_calendar_contacts` or revert to b1r5 if necessary. Do not put personal Google credentials in GitHub.

Read `docs/B1R8-TOKEN-REUSE.md` for technical reasoning, and the existing `docs/B1R6-GOOGLE-PIM-ACCEPTANCE.md` for the initial integration's limitations.
