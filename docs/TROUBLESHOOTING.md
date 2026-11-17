# GitHub Actions troubleshooting

| Symptom / workflow stage | Meaning | Safe fix |
|---|---|---|
| Actions workflow missing | `.github` directory was omitted or nested inside another folder | Move `.github/workflows/build-portableapps.yml` to exact repository root, commit and push |
| GitHub releases API 404 | A specifically requested tag was not published | Choose `latest` or a *published stable* `vX.Y.Z`. Unpublished releases cannot be assumed |
| GitHub API 401/403/429 or 5xx | Permission/rate-limit/server failure | Check Actions permissions and retry later. Resolver is designed not to misread this as missing release |
| No stable release | GitHub released no matching numeric tag | Don't compile `main` silently; select another suitable published version |
| Source patch drift | Upstream changed one of the three source locations | Compare new upstream Rust files, update **exact patch anchors** and tests, bump `package_revision`; never remove fail-closed checks |
| Rust toolchain / cargo build error | Missing target, compiler tools, upstream dependency or real compilation error | Read first Rust/Cargo error; validate upstream rust-version and Cargo.lock, avoid manually pinning unrelated older dependency versions |
| `vswhere` or `cl`/`rc` missing | Hosted image or toolchain changed | Verify Visual Studio C++ toolset and Windows SDK on Windows hosted runner; select supported runner image; do not silently skip launcher compilation |
| Source/icon verification failed | Original upstream ICO absent or missing required frames; another PE compiled to wrong architecture/subsystem | Do not substitute a fake icon or rename an unrelated binary. Audit upstream asset and build steps |
| `mailcraft-cli --version` fails | Source-built CLI did not pass headless smoke test | Inspect CLI accepted switches and update test, or fix CLI build, rather than bypassing all validation |
| Custom-NSIS action fails | ZIP might still be valid but installer not validated | Check `dist` stage and action logs; ZIP is preserved, installer excluded; bump revision to retry corrected release |
| `7z` not available | Static NSIS payload verification cannot run | Install or locate 7-Zip on hosted image; no silent bypass |
| Installer test fails in Unicode destination | Real silent installer may have a quoting, Unicode or staging bug | Keep installer unpublished, inspect shared Package Builder against documented `/S /D=` and test, fix upstream shared action only after verification |
| Publisher tag collision | Existing release has different assets or someone created a manual release with same tag | Do not overwrite unrelated assets; choose a new package revision |
| Run skipped (already published) | Existing complete release matches source/build/revision identity | Use existing release or bump revision when necessary |
| OAuth password required each run | Intentional: avoid host Windows Credential Manager writes | Sign in when needed; secure persistent portable secrets would require separate reviewed encryption/consent design |
| Windows toast not shown | MSI Start Menu AUMID/activator identity may not exist | Do not steal installed app identity. Keep functional app and record limitation |
| Antivirus warning | Community binaries are unsigned, no commercial signing identity claimed | Verify provenance/hash and inspect with Windows Defender; never disable antivirus or advise blind allowlisting |

**Windows runtime failures must be distinguished from CI/static checks.** Screenshots from GitHub Actions showing green checkmarks are not evidence that a GUI launched successfully on a normal user desktop.
