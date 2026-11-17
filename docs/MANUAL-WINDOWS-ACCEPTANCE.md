# Windows desktop acceptance checklist (required after first successful Actions run)

These tests must be performed on a normal Windows 10/11 x64 desktop, NOT merely a GitHub Actions runner. Use a disposable test mail account, backup any real data before starting, and compare installed MailCraft in a separate test profile if present.

1. **Source and release:** Confirm downloaded ZIP and installer are from *your builder repo*, versions match intended upstream, and SHA-256 matches `SHA256SUMS.txt`.
2. **Normal launch:** Extract `MailCraftPortable` to a writable folder, double-click **MailCraftPortable.exe**. Confirm mail window, no unexpected console window, and normal mail/calendar/contacts features.
3. **Persistence:** Add disposable account, change app options, quit fully, reopen, confirm settings and (where selected) mailbox state persist under `Data\MailCraft`.
4. **Credential behavior:** Before/after compare Windows Credential Manager for newly created `MailCraft` secrets, ensure portable account secrets not persisted there. Confirm supported sign-in still works after restarting, even if credentials have to be re-entered.
5. **Storage observation:** Use Process Monitor (or similar) with filters for `mailcraft.exe`, `mailcraft-cli.exe` and `MailCraftPortable.exe`. Compare writes to `%APPDATA%\MailCraft`, `%LOCALAPPDATA%\MailCraft`, `%PROGRAMDATA%`, registry, Downloads, Documents, temporary storage, and package `Data`. Attribute writes to app, external file viewer or Windows. Never delete any observed host data without ownership proof.
6. **Attachments:** Open a harmless PDF/text attachment; the temp copy must be inside `Data\MailCraft\Attachments`. Note Windows/external-viewer history is not controlled by the launcher.
7. **User file actions:** Export/save a sample document to a deliberately chosen outside path; confirm this user-authorized external save works and is not swept.
8. **Tray:** Close to tray where enabled; root launcher should remain waiting. Quit using MailCraft's full Exit/Quit command, verify program and launcher both finish. Close USB drive only then.
9. **Single instance:** Launch a second instance while first is open; check upstream brings first window forward or otherwise enforces its lock, without corrupting `Data`.
10. **Relocation:** Exit fully, move the complete folder to a path with spaces and non-ASCII letters and (if available) another USB drive letter. Run root launcher, confirm mailbox/settings remain.
11. **Reparse safety:** Temporarily replace a disposable `Data` path with junction/symlink; launcher must refuse rather than write private mail to unexpected outside location. Do this **only in a disposable test copy**, not real profiles.
12. **Installed coexistence:** If official MSI MailCraft exists, compare installed profile and shortcuts before/after portable launch. Confirm neither package takes over the other's profile or Windows registration. Do NOT repair by deleting installed user state.
13. **Shell and notifications:** Verify portable launcher does not create Start Menu, Startup, Desktop shortcuts, scheduled tasks, services, COM or app protocol associations. Test notifications and click activation; record whether upstream MSI identity is required. No fake success.
14. **Upgrade and rollback:** Back up `Data`, install next builder package over the same folder and verify Data preservation. Revert app binaries only after checking database compatibility. Never downgrade a migrated database without a backup.
15. **Crash recovery:** Close a disposable instance forcefully; reopen. Confirm MailCraft's own mailbox/index recovery and portable Data remain; no host harvesting or registry cleanup should happen.
16. **External functionality:** Test keychain or certificate-related features that matter (e.g., S/MIME, smartcard, OAuth app), external viewers and commands; note any OS-bound or sign-in limitations.

Record date, Windows build, machine, upstream tag, builder/package revision, SHA-256, and status for each. Fail a release when profile loss, installed-app interference, or unexpected persistent host credential writes are observed.
