# b1r3 Preview-only acceptance checklist

1. Preserve working b1r2 and original stable repo; build b1r3 in a separate enhanced repo with publish OFF.
2. Verify `v0.13.0` and exact pinned source identity; ensure both source patch steps succeed; inspect GitHub compilation logs.
3. Back up `Data` and launch the experimental ZIP in a fresh folder without sharing a writable MailCraft profile.
4. Compose with the original HTML signature; verify the **Load signature pictures** button appears. Before click, remote icon placeholders remain, with b1r2 compact horizontal geometry.
5. Click the button. Icons8 HTTPS 22x22 icons should load if the source host permits. Verify no more than twelve icon fetches can occur and other received email remains blocked.
6. Hide icons and verify placeholders return without changing the signature HTML.
7. Send to Gmail; verify seven original social icons, links and compact footer stay exactly as before.
8. Check that a received HTML marketing email with remote pictures remains blocked unless separately authorized.
9. Test offline and unavailable remote image: no crash; fallback placeholders.
10. Verify normal Google OAuth sign-in/reconnect; do not write credentials in logs or release.

If any stage fails, do not distribute this experimental release. Disable `signature_picture_button` (b1r2 behavior), or use your confirmed b1r2 build. No claim of completed Windows integration testing is made by this kit.
