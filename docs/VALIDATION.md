# Verification and acceptance matrix — b1r1

Only list tests as passed when evidence is available. The kit's local authoring machine is NOT a Windows runner. A GitHub Actions workflow existing in the ZIP is not evidence that it ran successfully.

| Stage | Status as delivered | Evidence / next gate |
|---|---|---|
| Upstream source and packaging review | SOURCE-INSPECTED | v0.13.0 Rust files, manifest, assets and license declarations; see `AUDIT.md` |
| Shared action input/output review | SOURCE-INSPECTED | Actual pinned `action.yml` reviewed, Git tag commits captured |
| Kit Python syntax/tests | STATIC-VALIDATED | `python -m unittest discover -s tests -v`, fixture-based checks |
| Workflow YAML | STATIC-VALIDATED | Parsed locally; `workflow_dispatch`, Windows runner, actions present |
| Source tag SHA and Cargo.lock | NOT YET VERIFIED for an actual build | GitHub Actions resolves live release and asserts clone SHA, Cargo.lock exists |
| Rust app and CLI compilation | NOT YET VERIFIED | Real hosted Windows run must succeed with `--locked` |
| C++ launcher PE compilation and icon | NOT YET VERIFIED | Real VS + Windows SDK invocation on hosted runner |
| CLI `--version` | NOT YET VERIFIED | Headless smoke test in workflow |
| Source-built binaries have required subsystem | NOT YET VERIFIED | `verify.py` checks PE machine and GUI/console subsystem |
| PortableApps stage and ZIP SHA-256 comparison | NOT YET VERIFIED | `verify.py` compares all staging files with ZIP digests |
| Portable settings/mailbox Data containment | NOT YET VERIFIED | Source patched; confirm real account/config with GUI and ProcMon |
| Attachment-copy containment | NOT YET VERIFIED | Real mail attachment open and external viewer required |
| Windows credential avoidance | NOT YET VERIFIED | Source patch; real Credential Manager before/after comparison needed |
| TraceGuard/empty-tree recovery | NOT APPLICABLE as a host harvester | No app-owned host harvesting allowed by current source evidence; `Data` nested-empty protection tested in installer fixture once run |
| ShellGuard/shortcut/registry cleanup | NOT APPLICABLE as a harvester | No app/runtime registrations are created by launcher; installed app coexistence manual test still required |
| Tray and second launch | NOT YET VERIFIED | Manual desktop Windows test |
| Native Windows notifications | NOT YET VERIFIED / KNOWN LIMITATION | MSI-based AUMID identity; no claims about functional portable toast activation |
| Appbars, work area and autostart | NOT APPLICABLE | MailCraft is not a bar/WM and no autostart is built |
| Shared NSIS installer generation | NOT YET VERIFIED | Official shared builder action at checked commit runs after verified ZIP |
| NSIS static payload/hash integrity | NOT YET VERIFIED | `verify-installer.ps1` checks 7z listing and exact output hash |
| Sandbox installer install/reinstall | NOT YET VERIFIED | `test-installer.ps1` uses disposable runner folder, checks preservation of Data and nested empty tree |
| Actual GUI, email, calendar, contacts | NOT YET VERIFIED | Real Windows desktop account setup and acceptance checklist |
| Published GitHub Release and SHA256SUMS | NOT YET VERIFIED | Shared Publisher dry-run then real action in workflow |
| User-confirmed installed portability | NOT YET VERIFIED | Only after hands-on Windows confirmation |

**No test result in this document should be understood to assert Windows-compiled, manually Windows-tested, or user-confirmed functionality before that test actually runs.**

## Conditional artifact publication

- ZIP validation failure: stop pipeline. Do not call installer or publisher.
- ZIP success + installer failure: preserve and optionally publish **ZIP only** through shared publisher; explicit failing job result documents installer failure, and the old generated `.paf.exe` is removed from `dist/installers`.
- ZIP + installer validation success: publish both only after publisher dry-run; `SHA256SUMS.txt` created by the publisher.
- Publishing disabled: upload validated ZIP and optional PAF as a short-retention Actions artifact instead of a public Release.
- Existing complete matching release: skip duplicate expensive compilation.
- Existing partial/same-name release or manual release conflicting with tag: abort, never overwrite.

Do not mistake the sandbox unattended installer test for interactive mail client or shell/notification tests.
