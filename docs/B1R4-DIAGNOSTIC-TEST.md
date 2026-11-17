# b1r4 manual signature image diagnosis

1. Keep the **original** stable portable builder and a separate Data folder. Backup your b1r3 Data first.
2. Build with `upstream_version=v0.13.0`, `package_revision=b1r4`, `compact_signature_preview=true`, `signature_picture_button=true`, `publish=false`.
3. Open a new message with the original HTML signature. Click **Load signature pictures** exactly once. The button should become **Hide signature pictures**.
4. Read the added status line: counts for images attempted/finished, loading, successful, and failed; error text when a request fails.
5. If the status reports failure, copy the error text (do not share OAuth secrets) and compare whether the seven Icons8 icons appear. You can click Hide then Load to retry.
6. Send one test message to Gmail and confirm the outgoing signature is identical to b1r3. If anything else breaks, roll back immediately and do not install over the stable Data folder.

This is a diagnostic UI release, not a guarantee the host fetches Icons8 assets. The actual Windows Rust build and real network fetching cannot be tested in this environment. It does not request remote pictures automatically, does not store account secrets, and does not add Google Contacts or Calendar synchronization.
