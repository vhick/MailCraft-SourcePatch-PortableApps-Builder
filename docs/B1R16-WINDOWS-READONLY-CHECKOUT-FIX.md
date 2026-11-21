# MailCraft Enhanced Builder b1r16 — Windows readonly Git-object cleanup

## Exact failure examined

User GitHub Actions upload: `logs_121490042715.zip`, run on November 21, 2026.
Requested upstream `v0.14.0`, package revision `b1r15`, `Publish=true`. The workflow **did not get beyond Python unit tests**. The `test_commit_mismatch_refuses_source` case intentionally passed a nonexistent `ffffffff…` SHA to the checkout helper. The Git checkout correctly refused the nonexistent object, but failure cleanup called plain `shutil.rmtree(destination)` and raised `PermissionError: [WinError 5] Access is denied` for a read-only file under `.git/objects/00/`. This turned an intentional rejection into a test error.

No source patching, Rust compile, packaging, or installer acceptance occurred in the uploaded run; do not infer v0.14.0 compatibility or user-data safety from this result.

## b1r16 repair (small and fail-closed)

- Before creating upstream work-tree files, peel the fetched Git tag to its commit and compare it to the resolver's immutable SHA. If different, raise an explanatory `RuntimeError` without attempting `git checkout` of a false commit.
- On any failed clone/checkout, remove **only** the new temporary upstream checkout using `shutil.rmtree(onexc=...)`. On `PermissionError` it clears read-only file attributes and retries only the failed removal operation (Python 3.12 supported), including protected `.git` object files. Does not use admin permissions, registry edits, machine-wide Git configuration, or broad `ignore_errors=True`.
- If a file is actually locked or an ACL prevents removal, preserve the original source error and append cleanup details as an exception note. Such errors are not silently ignored.
- A Windows-only path-length workaround from b1r15 is left intact. No Google integration, portable data paths, signature, launch, or package scripts are changed.
- Earlier unit tests no longer hard-code a specific builder revision; they check the `b<N>r<N>` revision format. Future package revision increments therefore do not cause the same test-suite failure.

Python documentation: https://docs.python.org/3.12/library/shutil.html#shutil.rmtree (see `onexc` and Windows read-only files example).

## Test coverage

- `tests/test_b1r15_checkout.py` now confirms wrong commit is rejected *before* any Git checkout and that the partial clone disappears.
- `tests/test_b1r16_windows_cleanup.py` covers read-only file retry, unrelated errors still propagated, persistent access denial still propagated, and isolation of unrelated portable user files.
- Historical Google native-form CRUD/sync, source-drift, signature preview and portability tests continue unchanged except that six workflow assertions use revision-agnostic checks.

Local result: **61 Python unit tests passed**. Unit tests do not constitute a Windows build or live Google authentication/write test.

## Recommended initial workflow input

| Input | Value |
| --- | --- |
| upstream_version | `v0.14.0` |
| package_revision | `b1r16` |
| compact_signature_preview | `true` |
| signature_picture_button | `true` |
| google_calendar_contacts | `true` |
| google_two_way_edit | `true` |
| google_native_forms | `true` |
| publish | **`false`** |

On success verify installed native Google Calendar/Contacts add/edit/delete, manual **Sync Google Now**, automatic 15-minute refresh, Gmail, signature image preview, and persistence in portable `Data`. Compare any changes on Google's web interfaces. Retain working b1r14 and its independent Data backup until everything has been validated. If a later patch stage fails against 0.14.0, it is a separate compatibility issue: share new run logs, not guessed bypasses.
