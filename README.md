# MailCraft Enhanced PortableApps Builder Kit — b1r15 (Adaptive Checkout / Guarded Compatibility)

This is a complete **GitHub Actions Windows source-builder kit**, not a precompiled MailCraft app. It is derived from the **user-confirmed working b1r14 Clean Native UI** builder. The goal is to support compatible upstream releases with fewer revisions, without silently breaking portable data, Google Calendar/Contacts, Gmail, or signature features.

## Diagnosed failure: upstream v0.14.0 on November 21, 2026

The supplied GitHub Actions run (`logs_121467734198.zip`) failed in **Verify upstream tag via shallow HTTPS checkout**, not in Rust or any Google patch:

`error: unable to create file .../apps/mailcraft-android/app/src/test/snapshots/images/...png: Filename too long`

`fatal: unable to checkout working tree`

Release resolution had already selected **v0.14.0**, commit `979953f012636fa7c2380124fd307152404c29bf`. Git could not create unrelated long Android test screenshot paths on Windows. This failure alone says nothing about whether the existing patch chain will compile against v0.14.0.

## What b1r15 changes

1. **Verified checkout without long Windows paths.** `scripts/checkout_upstream.py` clones the released tag without initially writing the source tree; enables `core.longpaths=true` **locally only in that checkout**; and performs a sparse checkout excluding *only* Android screenshot test fixtures at `apps/mailcraft-android/app/src/test/snapshots/images/`. All Rust crates, root manifests/lockfile, Windows application sources, assets and launcher dependencies remain included. The checked-out commit and annotated tag are both verified against GitHub's immutable resolved commit, and incomplete checkouts are removed if an operation fails.
2. **Version-aware per-frame Google sync hook.** `scripts/google_pim_patch.py` retains b1r14's original `self.poll_calendar()` integration when that call exists. If it does not, it recognizes the separately audited `self.poll_graph()` call **within the per-frame `MailApp::logic` function**, which appears in upstream v0.14.0. It refuses missing, duplicated, or out-of-context hooks. It does **not** bypass the exact checks for authentication, native commands, Google writes or portable storage.
3. **Regression tests:** four local Git checkout tests (including an annotated tag, Android exclusion, SHA-mismatch rejection and preserving core source), plus four lifecycle hook compatibility tests. The historical b1r14 Google CRUD, sync and UI tests are retained.
4. **Workflow defaults** advance to `v0.14.0` / `b1r15`, with `publish: false`. Future releases can still be requested using `latest` or a specific stable tag. Existing opt-in options remain explicit and unchanged.

### Why this isn't an unrestricted "auto-patcher"

MailCraft changes frequently. A program can safely normalize **known** source variations and choose known equivalent hooks, but it cannot infer arbitrary new Rust architecture, security flows or API permissions. Therefore this builder **must stop without publishing** when a required source pattern or contract changes. That is intentional. The particular 0.14.0 release has not been compiled or end-to-end tested in this environment; additional patches may be required once the next Windows run reaches the source adaptation steps.

## How to run

1. Back up your working **b1r14** build, particularly the `Data` folder. Do **not** commit credentials or portable `Data` into your builder repository.
2. Extract the kit into the root of your existing **Enhanced MailCraft PortableApps builder** repository; include the hidden `.github/` folder, `patches/`, `scripts/`, `tests/`, `launcher/`, `foundation/`, `docs/`. Do not use it for the separate official upstream-only builder.
3. Commit in GitHub Desktop, push, then run **Actions → MailCraft PortableApps → Run workflow** with:

| Workflow input | Test value |
| --- | --- |
| `upstream_version` | `v0.14.0` (or `latest` for later compatible stable releases) |
| `package_revision` | `b1r15` |
| `compact_signature_preview` | `true` |
| `signature_picture_button` | `true` |
| `google_calendar_contacts` | `true` |
| `google_two_way_edit` | `true` |
| `google_native_forms` | `true` |
| `publish` | **`false`** |

4. Confirm the new step **Verify upstream tag with Windows long-path-safe sparse checkout** succeeds. If a later **source adaptation / Google integration** step fails, **do not disable that patch or set publish=true**. The error identifies the remaining upstream source drift. Provide the new GitHub Actions log ZIP for a targeted compatibility correction.
5. Only if the **entire** workflow succeeds, test the generated app in a **separate portable folder**. Verify Gmail, signature image preview, Calendar and Contacts add/edit/delete, manual **Sync Google now**, 15-minute refresh, and `Data` persistence; check the edits on Google's sites. Keep b1r14 as rollback until confirmed.

## Notes

- b1r14's native Google CRUD routing, two-step deletion confirmation, removal of redundant Google buttons, Gmail functionality, PortableApps profile path, and existing release publisher/package builder are retained.
- The default `publish=false` is important: upstream v0.14.0 compilation and live Google operations are **not verified** by local Python tests.
- `python -m unittest discover -s tests -v` exercises all unit tests. The validated ZIP can be unpacked directly into the builder repo.
- For the exact diagnosis and maintenance approach see `docs/B1R15-WINDOWS-CHECKOUT-AND-COMPATIBILITY.md`.
