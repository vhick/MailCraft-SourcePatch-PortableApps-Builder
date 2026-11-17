# MailCraft Enhanced PortableApps Builder b1r7 — Google Sync Troubleshooting + Manual Retry

**Experimental; not yet verified by Windows runtime.** b1r5 is the confirmed working signature and Gmail baseline. This version retains b1r6 Google read-only Calendar and Contacts integration and adds direct visible diagnostics in the Calendar and People screens.

**Why b1r7:** The first reported b1r6 build showed Gmail working but an empty Calendar and Contacts. b1r6 silently stored sync errors in logs and retried only at 15-minute intervals. A missing Google Calendar/Contacts grant, Workspace administrator block, disabled auto-sync, or API failure could all look like an empty calendar. This build shows these states and adds **Sync Google now** to retry without waiting.

**Important:** This is an observability + retry patch, not proof that the Google API integration will work. Its new code must first compile on Windows and be tested with real Google credentials. If the diagnostic shows an OAuth consent problem, reconnect with Google and approve the Calendar/Contacts permissions. Never paste Google tokens or client secrets into GitHub Issues or ChatGPT.

## Build

1. Replace enhanced builder repo contents with this kit, including hidden `.github` directory; do not modify the original stable builder repo.
2. GitHub Actions workflow: `upstream_version=v0.13.0`, `package_revision=b1r7`, `compact_signature_preview=true`, `signature_picture_button=true`, `google_calendar_contacts=true`, `publish=false`.
3. Download and run in **separate PortableApps installation**, with a separate `Data` directory. Keep b1r5 and your existing data backup safe.
4. Open **Calendar** or **People**. Look for **Sync Google now** and its adjacent status. Click once. Possible statuses: `Google sync paused: ...`, `Google sync not started: reconnect ...`, `Google sync problem: Google permission denied ...`, or `Google sync completed: N calendars, N events, N contacts`.
5. If permissions are missing, use **Send/Receive → Account Settings → Reconnect with Google**, authorize Gmail + Calendar + Contacts. The app must request all scopes. Use **Sync Google now** afterward to avoid the 15-minute b1r6 retry delay.
6. If status says successful with zero results, verify the Google account has items and check the selected calendars/date range; if the status shows an error, collect just the error status (never secrets).
7. Test Gmail Send/Receive and signature pictures; if any regression, disable `google_calendar_contacts` in workflow or restore b1r5.

**What changes in the native app:** `google_pim.rs` displays sync lifecycle/summary; `calendar_view.rs` and `people_view.rs` each include a read-only sync status row and manual retry control. The underlying Google API downloader, incoming mail, outgoing HTML and signature preview patches remain unchanged. Google sync remains read-only on Google's server.

**Limitations:** Does not yet implement two-way sync, Tasks, push changes, editing, sync while closed, or a verified Gmail + Calendar + Contacts production solution. Google External/Testing can force periodic reauthorization.

---

# MailCraft Enhanced PortableApps Builder b1r6 — Google Calendar + Contacts (experimental)

**Source builder ZIP, not an executable.** b1r5 is the latest user-verified working enhanced build (Gmail OAuth and HTML signature preview with all seven icons). b1r6 adds an **optional** read-only Google Calendar/Contacts native connector built over official upstream **v0.13.0**, WITHOUT replacing or altering your original stable MailCraft builder.

**First read:** [`docs/B1R6-GOOGLE-PIM-ACCEPTANCE.md`](docs/B1R6-GOOGLE-PIM-ACCEPTANCE.md). It covers Google permissions, GitHub Actions settings, sign-in, separate-profile tests, and rollback. This code has **not** been compiled or run on Windows. The first GitHub Actions build is the native compiler test; only after it passes can the Windows GUI be tested. Do not upload credentials or your private signature HTML to the repository.

## Implemented for the b1r6 test build

- Same Google OAuth account. New interactive Google sign-in additionally requests `calendar.readonly` and `contacts.readonly`; the existing mail token-refresh scope remains unchanged. A Calendar denial never rejects a working Gmail refresh.
- Independent Google Calendar and People API reader through MailCraft's existing HTTPS network stack, with fixed Google hosts, bounded pages and response bodies.
- Normalized Google contacts and calendar events feed into MailCraft's **existing** Contacts and Calendar engine merges, not a second UI or database. Per-account isolation and read-only calendar permissions are applied.
- Automatic snapshot on first authorized connection and at most every **15 minutes** thereafter while online, auto sync enabled, and the application is running; requests run in the background.
- Calendar/Contacts errors are isolated from mail. Mail changes, sending, portable data adapters, signature b1r5 preview patch and Microsoft Graph synchronization are unchanged.
- `google_calendar_contacts` workflow toggle defaults to `true` for the experimental branch, and `false` returns the **b1r5 functional application** without this integration. Retained `signature_picture_button`/`compact_signature_preview` switches work as before.

### Important initial-release limits

Read-only **toward Google** does not mean the local mirror never changes: MailCraft will update its local Google copies and remove ones deleted on Google after a fully successful response. Contact/Calendar photos and Google Tasks are not included; it does not make Google Calendar editable, schedule background work when MailCraft is closed, or implement push notifications. Existing Google accounts must renew consent because old refresh tokens did not grant extra scopes. Publishing is OFF by default; keep your working b1r5.

## Quick build

1. Extract this ZIP into a new or existing independent *enhanced* builder repo, including `.github/workflows`.
2. On GitHub: **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow**.
3. `upstream_version=v0.13.0`, `package_revision=b1r6`, `google_calendar_contacts=true`, `compact_signature_preview=true`, `signature_picture_button=true`, `publish=false`.
4. Inspect workflow logs and validated artifacts. Test only in an independent portable installation with separate `Data` profile.
5. If b1r6 compile fails, turn `google_calendar_contacts=false` to retain tested b1r5 functionality, or restore the previous b1r5 builder files. Do not bypass strict source anchors.

### Provenance and technical files

- `scripts/google_pim_patch.py` — exact-anchor, fail-closed native source transformation.
- `patches/google_pim_net.rs` — Google read-only API adapters.
- `patches/google_pim_ui.rs` — account-level sync jobs, merge and interval scheduling.
- `tests/test_google_pim_patch.py` — source safety and packaging tests.
- `foundation/` — earlier separate Python sync prototype, **not** invoked by the native binary, included as a design reference.
- `.github/workflows/build-portableapps.yml` — complete builder with new optional integration step.

This is independent experimental engineering, not an official MailCraft feature or endorsed integration. Copyright applies to original upstream portions according to their licenses. Preserve the existing source and builder license information.

---
# MailCraft Enhanced PortableApps Builder — b1r5 Click Repair (Experimental)

**b1r5 fixes an interaction-area problem identified after b1r4 built successfully but its “Load signature pictures” button could not be clicked.** This is a separate enhanced repository build; keep the stable portable builder unchanged.

The b1r4 button was inserted **inside the reading body's rendering function**. MailCraft's body painter registers a click-and-drag surface spanning the full clip area, including the area where the new button is drawn. A later interaction can intercept the button's click. b1r5 clips the following signature body to start *below* the button and its optional status line. The button is outside that body's click surface.

**What remains unchanged:** b1r2 compact social-icon placeholders, b1r4 manual HTTPS downloads/status diagnostics, outgoing signature HTML, Gmail OAuth, stable data folders, and normal received-email privacy. Google Contacts and Calendar synchronization are not part of this release.

**Build settings:** `upstream_version=v0.13.0`, `package_revision=b1r5`, `compact_signature_preview=true`, `signature_picture_button=true`, `publish=false`. Upload all contents of the ZIP including `.github` to the **separate enhanced builder repository**.

**First acceptance test:** Open a new email, verify the button can be clicked once and its label changes to **Hide signature pictures**. A loading/error counter should appear. Only after that test should you check whether the seven Icons8 graphics load. Send one Gmail test to confirm that the outgoing HTML signature still looks correct. Keep a separate test install and separate writable `Data` folder.

**Validation limits:** Local Python tests and ZIP/workflow checks pass. Windows GUI behavior and full Rust compilation still require your GitHub Actions and real Windows test. This is an **untested runtime fix**, not a confirmed working MailCraft release. If it fails, turn `signature_picture_button` off to return to b1r2 preview behavior.

See `docs/B1R5-CLICK-REPAIR.md` for technical details. Older b1r4/b1r3/b1r2 sections below are included for historical reference; their default workflow values are superseded by the instructions above.

---

# MailCraft Enhanced Builder b1r4 — diagnostic preview update

**Testing release; Windows compilation and runtime behavior still require GitHub Actions verification.** This is not the stable MailCraft builder. It adds a visible **loading / successful / failed / last error** indication to the optional signature image preview button and allows the user's exact `img.icons8.com/color/48/` signature icons through even if the HTML parser lost their explicit size (still manually requested, HTTPS-only, maximum twelve URLs, 512 KiB each). All other remote image hosts remain eligible only when both small dimensions survive parsing. It retains the previously tested b1r2 layout adjustment and does not modify outgoing HTML, normal received-mail privacy settings, Gmail OAuth, or portable data handling. Turn the `signature_picture_button` input off to fall back to b1r2 behavior.

**Test:** Click **Load signature pictures** once and confirm it changes to **Hide signature pictures**. Check the live status line and, if images remain missing, record the *last error*. Click **Hide** and **Load** to retry after a failure. The host image downloader may reject a request; there is no guarantee every third-party image will load. No new Google or account credentials are required.

---

# MailCraft Enhanced PortableApps Builder b1r3 — Manual signature picture preview

**EXPERIMENTAL independent enhanced repo.** This kit builds Windows PortableApps MailCraft using official immutable upstream release source plus small fail-closed optional patches. **Keep your original stable MailCraft builder repository untouched.**

## What's new in b1r3

- Preserves the **user-confirmed b1r2 horizontal social-icon placement** in the HTML signature preview.
- Adds an explicit **Load signature pictures (contacts external sites)** button in MailCraft's OWN signature preview. The button appears above the preview only when its HTML references eligible remote pictures and the desktop host offers guarded image downloads.
- Only after the owner clicks the button, the application requests **HTTPS image URLs with explicit 3–48 pixel width and height**, through MailCraft's existing host-controlled guarded downloader. Maximum 12 unique icons, three simultaneous requests, 512 KiB/image, 30-second timeout. The normal image decoder checks the payload; no new HTTP or Rust crate dependency is needed.
- Clicking **Hide signature pictures** hides them again; consent is held in the current app's temporary UI memory, not written to disk. It may be remembered for the same HTML preview within the same running session. Fetching a picture does contact its remote host; press this only for signatures you trust.
- Normal received-message privacy behavior, mailbox remote-image rules, outgoing HTML/MIME, OAuth, Contacts, Calendar, profile and PortableApps launcher are **not modified**.

## Limitations and supported baseline

- This is a **source patch for v0.13.0**, not proof of a Windows build. Run GitHub Actions with `upstream_version=v0.13.0`, revision `b1r3`, `compact_signature_preview=true`, `signature_picture_button=true`, and `publish=false` for first test. Upstream changes deliberately cause an anchor refusal; inspect and update rather than forcing a patch.
- Social icons may still fail if the remote server refuses the request or returns unsupported data; a preview click is not permission to load pictures from received emails.
- The **three vertical contact symbols are Unicode glyphs, not images**; they need the simplified HTML styling from the successful Test 01. This code patch does not restyle complex inline `span` tags because that could affect all mail. Keep the original signature unchanged until you validate an alternative. The tested Test 01 is a per-signature workaround, not part of this public repo.
- Embedded `data:` images remain unsupported in this preview path, as shown by your Test 02.
- Contacts and Google Calendar synchronization are **not included** in b1r3.

## Nontechnical installation

1. Create or select **MailCraft-Enhanced-Portable-Builder**, separate from the original working repository.
2. Upload **all contents of this ZIP** into the enhanced builder's root, including `.github/workflows/build-portableapps.yml`.
3. Go to **Actions → MailCraft PortableApps - source build / ZIP / NSIS / Release → Run workflow**.
4. Set version `v0.13.0`, revision `b1r3`, **Compact signature preview=on**, **Signature picture button=on**, **Publish=off**. Start workflow.
5. After GitHub Actions passes, download its validated ZIP, back up your existing portable install, and test in a **separate folder** with a separate `Data` profile. Do not replace the stable installation.
6. Open a compose message with the original HTML signature. Click **Load signature pictures** above the preview. Confirm remote Icons8 images appear; verify Gmail still receives an unchanged signature. Test Hide afterwards.
7. If any Rust compile error or visual regression occurs, disable `signature_picture_button` (returns to b1r2 behavior) or revert to your working b1r2 kit. See `docs/B1R3-PREVIEW-ACCEPTANCE.md`.

**Validation:** Unit/patch tests are included, but Windows compilation and GUI acceptance must be completed by the GitHub workflow and on your machine. Never place OAuth client secrets, user mail folders, tokens, or the signature HTML (which contains personal details) in this public builder repo.

---

# Archived historical reference: b1r2 baseline

**The section below documents the previous experimental kit for context only. Follow the b1r3 instructions at the top for the enhanced repository.**

# MailCraft PortableApps Builder Kit b1r2 — Signature Preview Geometry Fix

**This is a full replacement of the original b1r1 builder repository**, not a standalone executable. Keep your installed `MailCraftPortable\Data` folder untouched. Default build remains the latest *published stable tag* (currently v0.13.0), not the moving main branch.

**What is implemented:** An **opt-out**, preview-only source patch that stops small missing web-hosted social-icon images from occupying oversized text placeholder slots in HTML signature previews. This should reduce the unwanted vertical stacking visible in the compose window. Images still show as placeholders unless separately loaded; **this patch does not and cannot reproduce Gmail/Thunderbird's pixel-perfect HTML layout**. It does not change outgoing email, the Gmail OAuth integration, message rendering outside previews, or the PortableApps profile/launcher.

**Not implemented:** Google Contacts / People API sync, Google Calendar API sync, image downloading in the signature editor, automatic browser-quality HTML rendering, or two-way synchronization. Those are separate integrations requiring development, permissions and regression testing. The existing read-only ICS subscription and manual VCF import are safer temporary options.

## Nontechnical setup

1. Create a **new GitHub builder repository or update the existing MailCraft PortableApps builder repository** using the complete contents of this ZIP (not only the script). Preserve the `.github` folder.
2. In GitHub, open **Actions** and choose **MailCraft PortableApps - source build / ZIP / NSIS / Release**.
3. Click **Run workflow**. Leave `upstream_version` as `latest`, use **package_revision `b1r2`**, and leave **compact_signature_preview checked**.
4. For the first experiment, turn **publish off**; collect the workflow artifacts after GitHub completes its build and validation. If GitHub reports an upstream source-drift error, do not bypass it: update the patch anchors for the selected release or switch off the optional preview patch to keep your original working b1r1 behavior.
5. Close MailCraft fully. Back up the existing portable directory, especially **`Data`**, before a test update. **Never delete or replace `Data`** while copying the updated app binaries / installing the new PAF. Validate the signature preview and send a test email as before.
6. Only after successful tests, rerun with **publish on** if you want a published ZIP/installer release.

**Credentials:** This kit does not include or request your real Google Client ID, Client Secret, token or Workspace mailbox data. Continue using the existing working local OAuth setup. Never commit credentials to the repository or include `Data` in a public package.

**Validation status:** The builder Python unit tests and source-anchor fixture tests can run locally. The modified Rust application **has not been compiled or executed in this environment**; GitHub Actions must perform the Windows build, and the user should perform visual tests in the actual application. If the patch does not visibly improve the signature preview, switch off `compact_signature_preview` and keep b1r1 behavior until a renderer change is developed.

---

# MailCraft PortableApps — source-built Windows x64 builder kit (b1r1)

**Application:** https://github.com/UCS-Care-Group/mailcraft  
**Mode:** PORTABLEAPPS only. No native portable product is built.  
**Build:** Compiles actual MailCraft/Rust and its CLI from a verified published stable upstream tag, plus a real Win32 C++ root launcher.  
**Packaging:** Validated standalone ZIP, then an independently compiled **PortableApps-style** (not certified official) installer via the pinned shared NSIS builder.  
**Publishing:** The pinned shared Release Publisher, dry-run first and real publish second.  
**Kit revision:** b1r1; update this revision for any materially changed/repaired build.

This ZIP is the **builder source kit**, not a compiled MailCraft program. It is intended for GitHub-hosted Windows Actions. Building and publishing has **not** been executed by the kit author; the first Actions run is the integration test. Keep the first release for test purposes until the interactive Windows checklist is completed.

## Start: GitHub Desktop + GitHub website (no local compiler)

1. In your GitHub account create a **new empty repository**, e.g. `MailCraft-PortableApps-Builder`. **Do not fork** the upstream MailCraft repository.
2. Set the builder repository to **Public** unless you specifically need private code. This helps stay within GitHub's public hosted-runner allowances. It does **not** independently authorize distributing unrelated branded assets; this build uses MailCraft's permissively licensed source assets.
3. In GitHub Desktop choose **File → Clone repository**, then select that new repository.
4. Open your local repository folder using **Repository → Show in Explorer**.
5. Extract **all** files of this kit ZIP **directly into the repository root**. The `.github` directory MUST be present; on Windows File Explorer you may need to show hidden items. There must be a `.github/workflows/build-portableapps.yml` file at the root, not nested under a ZIP-name subdirectory.
6. In GitHub Desktop confirm the changes, enter a summary such as `Add MailCraft PortableApps source builder b1r1`, click **Commit to main**, then **Push origin**.
7. On GitHub open the repository → **Actions** → **MailCraft PortableApps - source build / ZIP / NSIS / Release** → **Run workflow**.
8. Choose `upstream_version=latest` (or specific published `v0.13.0`), `package_revision=b1r1`, and `publish=true`. The workflow builds on `windows-2025`; no local compiler or Git command is needed. First run can be resource-intensive due to fresh Rust dependencies.
9. If the build succeeds, open this **builder repository → Releases**, not the upstream MailCraft Releases. Download `MailCraftPortable_<version>_x64_<revision>.zip`, the `.paf.exe` if installer acceptance passed, and `SHA256SUMS.txt`.
10. Verify the hash from `SHA256SUMS.txt` before use; on Windows use PowerShell `Get-FileHash -Algorithm SHA256 'downloaded-file.zip'`.
11. For the ZIP, extract its `MailCraftPortable` folder to a writable drive and double-click `MailCraftPortable.exe`. For the installer, run the generated `.paf.exe` and choose the appropriate PortableApps directory. Refresh the PortableApps Platform menu when needed.
12. To update, **fully Quit MailCraft, including its tray process**, make a backup of `MailCraftPortable\Data`, and reinstall over the same portable folder or replace only the managed `App`, `Other`, and root launcher files from the new ZIP. **Never delete Data.**

For quick repeat packaging, the main workflow always recompiles when a new version/revision is requested. There is intentionally no separate untrusted ZIP-installer workflow: publishing from a prebuilt ZIP is a provenance-sensitive operation requiring a recorded, signed-off build manifest.

## What gets generated by GitHub Actions

```
MailCraftPortable_<upstream-version>_x64_<package-revision>.zip
  MailCraftPortable/
    MailCraftPortable.exe                     (compiled x64 Windows PE launcher)
    App/
      MailCraft/
        mailcraft.exe                         (source-built GUI)
        mailcraft-cli.exe                     (source-built CLI)
        portable.txt                          (strict local-mode marker)
      AppInfo/
        appinfo.ini
        appicon.ico
        appicon_16.png
        appicon_32.png
    Data/MailCraft/                            (private, preserved portable data)
    Other/Source/                             (licenses, attribution, build identity)

MailCraftPortable_<version>.0_custom-nsis-<revision>.paf.exe  (exact name emitted by shared builder)
SHA256SUMS.txt                                (published automatically)
```

The file names above are **expected** until GitHub Actions actually creates them. The release tag includes upstream version, upstream commit prefix, builder commit prefix, and package revision.

## Windows source and storage implementation

- `scripts/resolve.py` selects published semver-stable GitHub Releases **numerically**, rejects pre-releases, resolves the annotated/lightweight Git tag to a full immutable source commit SHA, and distinguishes 404 from other API failures.
- Git shallow clones the exact selected tag over HTTPS and verifies `HEAD` matches that commit. Rust dependency resolution uses `Cargo.lock`, `cargo build --locked`, and the upstream-required Rust toolchain rather than guesses.
- `scripts/patch.py` edits exactly three v0.13.0 upstream Rust source files. If expected source text changes, it **stops** instead of applying a risky fuzzy patch.
- `crates/control-key/src/lib.rs`: MailCraft settings, mailbox and logs use `<portable-root>\Data\MailCraft`, triggered by the exact `App\MailCraft\portable.txt` and root launcher presence.
- `apps/mailcraft/src/opened_files.rs`: app-opened attachment copies use `<portable-root>\Data\MailCraft\Attachments`.
- `apps/mailcraft/src/secrets.rs`: **OS credential persistence is disabled in portable mode**. OAuth/password prompts may return after restart. No unreviewed local plaintext secret store is added.
- The root `launcher/MailCraftPortable.cpp` validates the exact package layout, prevents Data-directory junction/symlink redirection, tests writable Data, forwards command-line arguments, starts the real mailcraft.exe, and waits for its process (including close-to-tray behavior). It doesn't touch installed profiles or shell entries.
- The launcher's icon is compiled from the **actual upstream ICO**, with explicit 16/32 px images in the PortableApps metadata.
- `scripts/package.py` creates the ready-to-extract ZIP **before** calling any installer action; `scripts/verify.py` compares every archive file against the staging folder's SHA-256 and checks actual PE architecture and subsystems.
- The shared installer code is neither copied into this kit nor duplicated. Installer acceptance tests use a disposable Windows runner directory only.
- The shared Release Publisher performs dry-run first, then publishes only validated artifacts. Old releases are never pruned by default (`prune=false`, `keep-releases=3`).

## Verified pinned shared actions

These were inspected at the listed release tags and pinned to the following **immutable commits** in the workflow:

| Purpose | Baseline tag | Immutable commit |
| --- | --- | --- |
| PortableApps-style installer | `vhick/Portable-Package-Builder@v1.0.0` | `0112c35580e83b37eb8757ebcb949274e1631a04` |
| Release Publisher | `vhick/portable-release-publisher@v1.1.1` | `cb64f86ac2d8c67506db5832de07f9ff58cbeaeb` |

The builder uses `source-dir`, `output-dir`, `engine`, `running-exe`, `timeout-seconds`, `package-revision` and `installer-file`/`installer-sha256`. Publisher uses `files`, `tag`, `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run` and the current repo's `GITHUB_TOKEN` with `contents:write` only.

## Most important limitations

1. The builder is **not Windows-compiled or GUI-tested yet**. Static inspection and Python fixture unit tests do not establish runtime portability. See `docs/VALIDATION.md` and `docs/MANUAL-WINDOWS-ACCEPTANCE.md`.
2. **Credentials are not persistently portable.** Some OAuth providers, hardware-backed authentication, S/MIME, keychain or GnuPG functionality depends on the Windows host or external apps. Prompts may recur.
3. Native Windows notification toasts may be unavailable without the upstream MSI's Start Menu/AUMID identity. We do not install host notification registrations or delete an installed app's identity.
4. Windows OS-managed caches, jump lists, run history, antivirus, DNS, Windows Error Reporting, GPU caches, and shell state cannot be guaranteed absent. No broad TraceGuard or ShellGuard is enabled without specific observed need.
5. Saved As, exports, imported files, attachments opened in external programs, and host key operations are **user-controlled/external** and are not automatically moved/deleted.
6. This is an **unofficial community package**; binaries are not code-signed, and no PortableApps.com certification is claimed.
7. If the app or shared action changes unexpectedly, patches and validation stop; fix and increment the package revision, instead of bypassing checks.

## Further reading

- `docs/AUDIT.md` — real source audit, paths, responsible components, tradeoffs and tests.
- `docs/VALIDATION.md` — honest automated vs interactive test matrix.
- `docs/MANUAL-WINDOWS-ACCEPTANCE.md` — first real Windows acceptance.
- `docs/UPGRADE-RECOVERY.md` — data-preserving update, rollback and relocation.
- `docs/TROUBLESHOOTING.md` — common GitHub Actions problems and remedies.

**Source code license:** this community builder kit is offered under MIT OR Apache-2.0, at your choice. Actual MailCraft source and bundled assets remain under their corresponding upstream notices and licenses, copied into `Other/Source` by the workflow.
