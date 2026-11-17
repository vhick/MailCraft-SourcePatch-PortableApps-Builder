# Application-specific audit — UCS-Care-Group/mailcraft (PORTABLEAPPS)

**Source snapshot inspected:** published stable upstream `v0.13.0`, November 15, 2026. The exact immutable commit is looked up and checked by the build workflow; do not assume the website's portable-mode statements describe this tagged repository. The release tag and commit are NOT hardcoded to `main`.

**Build:** Rust workspace edition 2024, min Rust 1.95 in `Cargo.toml`; `mailcraft` GUI based on `eframe/egui/wgpu`, `mailcraft-cli` console tool, Windows MSVC x64 with static CRT. Use `cargo build --release --locked -p mailcraft -p mailcraft-cli --target x86_64-pc-windows-msvc`, VS Build Tools, Windows SDK and upstream source icon. Dependencies pinned by upstream `Cargo.lock`, fingerprinted in `BUILD-IDENTITY.json`. Upstream dual license MIT OR Apache-2.0; original icon is attributed in `ATTRIBUTION.md`, third-party material in `NOTICE`.

### Mode-specific findings

The table's source links are inspectable evidence; **SOURCE-INSPECTED** does not mean an interactive Windows test passed. NATIVE remedy is **not implemented** because only PORTABLEAPPS was selected.

| Finding/status | Source evidence | File/registry path | Responsible component | NATIVE remedy | PORTABLEAPPS remedy | Data safety | Functionality tradeoff | Test | Limitation |
|---|---|---|---|---|---|---|---|---|---|
| SOURCE-INSPECTED: settings/keys/logs/mail | `crates/control-key/src/lib.rs`, `settings_dir` | `%APPDATA%\MailCraft` | App | N/A | Exact source patch redirects to `Data\MailCraft` before application use | Leaves installed profiles unmodified | None expected | Source anchor fixture, GUI and profile comparison | Paths beyond settings root must be observed |
| SOURCE-INSPECTED: opened attachments | `apps/mailcraft/src/opened_files.rs`, `base` | `%LOCALAPPDATA%\MailCraft\Attachments` | App | N/A | Source patch puts attachment copies under `Data\MailCraft\Attachments` | No broad cleanup | External file viewer still receives a file | Patch fixture; manual open attachment and ProcMon | Windows file access/history managed by external viewer |
| SOURCE-INSPECTED: credentials | `apps/mailcraft/src/secrets.rs`, `store` | Windows Credential Manager | App/Windows | N/A | Portable runtime passes no OS store; secrets held only in running memory | Existing Credential Manager entries left alone | Sign-in may be needed again, including OAuth refresh tokens | Source patch fixture; live account restart | Long-lived portable credential persistence intentionally unavailable |
| SOURCE-INSPECTED: single instance | `apps/mailcraft/src/single_instance.rs` | mailbox lock + local IPC | App | N/A | Retain upstream protection, launcher waits until exit | No external process termination | None expected | Manual second launch and quit to tray | Not run in GUI CI |
| SOURCE-INSPECTED: self update | `apps/mailcraft/src/install.rs`, `updater.rs` | Read-only MSI install path registry; update API | App | N/A | Preserve ZIP/non-MSI `NoticeOnly` behavior; builder-controlled upgrades | No deletion of MSI | No in-app replacement for ZIP installation | Manual update check; static source | No automatic builder refresh |
| SOURCE-INSPECTED: notifications | `apps/mailcraft/src/alerts.rs` | Start Menu AUMID/toasts | App/Windows shell | N/A | Do not imitate installed MSI identity; document unsupported portable toast activation | Never modify installed shortcut or COM entry | Native Windows toasts may not appear | Manual toast and click-to-open check | Not enabled/tested |
| SOURCE-INSPECTED: close-to-tray | `apps/mailcraft/src/tray_native.rs` | Tray/runtime process | App | N/A | Win32 launcher waits on exact started process | Cannot detach active Data | Extra launcher stays while app runs | Manual tray close/full quit | Child process trees need live observation |
| SOURCE-INSPECTED: external key & file services | `apps/mailcraft/Cargo.toml` Windows dependencies | OS certificate store, file explorer, external apps | Dependencies/Windows | N/A | Keep system functionality; do not intercept global registries, filesystem or credentials | Installed app coexistence prioritized | Some hardware-bound keys not USB portable | Manual S/MIME/external app checks | External runtime services may write host state |
| INFERRED: OS-managed caches | Windows execution/shell/GPU facilities | RecentFiles, GPU/shell history, DNS, etc | Windows OS/driver | N/A | Document; do not sweep unrelated state | Avoid destructive cleanup | Host histories possible | Manual before/after observe | Cannot promise no OS trace |
| NOT YET VERIFIED: other app-owned write paths | Full runtime ProcMon not available | Unknown | App/dependencies | N/A | Fail-safe: no speculative wildcard TraceGuard/ShellGuard | No destructive host scavenging | A real leftover path would require a focused update | Manual acceptance checklist | This is the primary remaining portability uncertainty |

### Specific source references

- Upstream source: https://github.com/UCS-Care-Group/mailcraft/tree/v0.13.0
- Settings root: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/crates/control-key/src/lib.rs
- Attachments: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/apps/mailcraft/src/opened_files.rs
- Secrets: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/apps/mailcraft/src/secrets.rs
- Multiple instance: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/apps/mailcraft/src/single_instance.rs
- Windows notifications: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/apps/mailcraft/src/alerts.rs
- Installer identification: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/apps/mailcraft/src/install.rs
- Source Windows build: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/packaging/windows/package.ps1
- Author and assets: https://github.com/UCS-Care-Group/mailcraft/blob/v0.13.0/ATTRIBUTION.md

### Action verification

Package Builder action: https://github.com/vhick/Portable-Package-Builder/blob/v1.0.0/action.yml  
Release Publisher action: https://github.com/vhick/portable-release-publisher/blob/v1.1.1/action.yml  
Both pinned to full GitHub release commit SHAs in `.github/workflows/build-portableapps.yml`, not floating version tags.

### Why neither TraceGuard nor ShellGuard is included

The source supports narrow pre-start redirection of the two application-owned folder roots and avoiding Credential Manager. That is less risky than copying real private email profiles from `%APPDATA%` after shutdown. No runtime evidence warrants taking over global Start Menu or registry state. Windows toasts are **not disabled by deleting registry keys**; they may simply be unsupported in this unofficial ZIP identity. If an actual installed-app coexistence or host-write test identifies a specific additional path, add only that observed path and a safe ownership-specific test in a revised kit.
