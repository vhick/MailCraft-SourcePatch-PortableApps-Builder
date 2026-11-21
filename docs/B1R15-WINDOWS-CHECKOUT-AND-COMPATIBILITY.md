# b1r15: Windows long-path failure and guarded upstream compatibility

## What the uploaded November 21 GitHub Actions log proves

- `upstream_version=v0.14.0`; `package_revision=b1r14`; publish had been enabled.
- The resolver selected `979953f012636fa7c2380124fd307152404c29bf` for v0.14.0.
- The unit tests all ran successfully.
- `git clone` transferred objects but failed **while checking out** long files under `apps/mailcraft-android/app/src/test/snapshots/images/` on the `windows-2025` runner.
- The job aborted before any source patch or Rust compilation. This log therefore does **not** prove that b1r14 patches match v0.14.0.

## New checkout strategy

1. `git -c core.longpaths=true clone --no-checkout --depth 1 --single-branch --branch vX.Y.Z ... upstream`.
2. Write `core.longpaths=true` to this new repo's **local** config only. No machine-wide Windows setting is changed.
3. `git sparse-checkout set --no-cone '/*' '!/apps/mailcraft-android/app/src/test/snapshots/images/'` before creating the work tree.
4. `git checkout --detach --force <resolved-40-char-SHA>`.
5. Verify `HEAD` and the annotated tag's peeled commit both equal the immutable resolver SHA. Require Cargo.lock, Cargo.toml and key source paths. On error delete the partial clone and abort.

The excluded Android screenshot test images are not required for an x64 Windows source build. Rust crates are kept, including any apps/xtask workspace members. Review the exclusion if future upstream builds use the Android screenshot assets during Windows compilation.

## Compatibility strategy

The patcher can adjust when equivalence is **specific, known, checked, and unique**. For example, the earlier `self.poll_calendar()` call was removed from upstream's v0.14.0 UI lifecycle. b1r15 can instead place the Google response poll after the known `self.poll_graph()` call *in MailApp's per-frame logic*. It refuses duplicate or misplaced hooks. The rest of the source adaptations retain b1r14's strict matching and stop on unknown changes.

Avoid treating `git apply --3way`, fuzzy string substitutions or “ignore error” as guarantees of source compatibility. Git may resolve text while a new program structure no longer supports the behavior. Each build must pass all source checks, Rust compilation, packaging validation and actual functional testing before publication.

## What to test

- Verify long-path-safe checkout step succeeds on v0.14.0.
- Watch for **source adaptation** failures separately; those require a targeted patch review, not a long-path change.
- Verify both compiled executables and the C++ launcher are built from source.
- Verify native Google Calendar and Contacts add/edit/delete and that the redundant shortcut row stays removed while **Sync Google now** remains.
- Confirm portable Data persistence, 15-minute refresh, Gmail and signature icons.
- Test in a separate folder, and retain working b1r14 rollback.

### Commit guidance

Summary: `b1r15: prevent Windows long-path checkout failures and guard upstream hook changes`

Description: `Clone MailCraft tags without checkout, use repo-local Git longpaths and sparse exclusion for unrelated Android screenshot fixtures, verify tag/SHA and required Rust sources, recognize the audited v0.14 Google polling lifecycle hook, update workflow defaults and add regression tests. Preserve b1r14 native Google CRUD, Sync Google now, Gmail, signatures, portable Data and fail-closed source guards.`
