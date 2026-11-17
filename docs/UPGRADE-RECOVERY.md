# Safe updates, relocation and rollback

## Before changing anything

1. Use MailCraft's own **Quit/Exit** (closing to tray may leave it running). Wait until `mailcraft.exe` and the root `MailCraftPortable.exe` exit.
2. Copy the **entire `MailCraftPortable\Data` tree** to a safe backup, preserving hidden items and completely empty subdirectories. For sensitive mail, choose an encrypted local backup destination.
3. Save the exact old ZIP, version/commit info and `SHA256SUMS.txt`. Do not copy private user mail into GitHub build artifacts.
4. New build output should be downloaded only from your **builder repository's release**. Verify both new asset SHA-256 and the version.

## ZIP update

Extract new ZIP to a different folder first. In the existing portable directory, replace the launcher and `App`/`Other` managed files from the new package **without copying the new empty `Data` over the existing Data**. Do not blanket-delete the portable root. If old application binary version directories exist under `App\MailCraft`, remove them only after fully backing up and checking they contain no user data. This app normally ships fixed `mailcraft.exe`, not version-number directories.

## Shared installer upgrade

Use the new `.paf.exe` installer and point it at the same PortableApps destination. The pinned shared NSIS implementation stages files and preserves `Data`; its behavior is exercised in a disposable Windows Actions fixture that seeds a sentinel file, nested empty folders and an obsolete application file. This test must pass before publishing the installer. Do not run unsigned installer files unless their source and hashes are verified and they came from the trusted builder run.

## Rollback or interrupted update

- If launch fails after upgrade, **stop, copy the current Data first**, and restore the previous known-good binaries.
- Data schema upgrades may be incompatible with older MailCraft: restore a matching **pre-upgrade Data backup** if rollback cannot read the current Data; don't make blind edits to mailbox databases.
- If the installer fails during transition, stop and preserve any `.__UPB_Backup`/`.__UPB_Stage` folders for diagnosis. Avoid manually deleting backups before inspecting them.
- If a workflow fails, the release may contain only a validated ZIP. This is explicitly marked as an installer failure in CI; never assume an installer existed.
- Changing a folder or drive letter is allowed when all of `MailCraftPortable` (including `Data`) is moved together while app is fully stopped. External file associations, OAuth provider identities and OS credential services may still depend on the host.
- There is **no automatic copying from `%APPDATA%\MailCraft`**. An existing conventional MailCraft profile is intentionally left untouched; manual migration needs an explicit backup and user approval.

## Recover Data without dangerous cleanup

All application-owned portable folders live under `Data\MailCraft`, which may contain credentials only in memory while the program runs (not a portable credential vault). User-saved files can exist outside the portable folder because the user selected their destination. There is no TraceGuard post-exit scavenger; it would be unsafe to treat an installed MailCraft profile as disposable. Any host registration that Windows manages should be recorded, not broadly removed.
