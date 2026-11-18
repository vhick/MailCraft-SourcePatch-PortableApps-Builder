# b1r8 Google Calendar + Contacts token-path correction

Observed: Both Calendar and Contacts showed the same hard-coded “New consent required” message after the user had already granted the needed permissions.

Root issue: The b1r6/b1r7 host maps every refresh failure to a consent error. The Google refresh endpoint does not take a new requested scope; the original authorization grant determines scopes.

Algorithm: use unexpired in-memory OAuth access token first, fallback to refresh only if expiring or Google API returns HTTP 401/403. Explicitly distinguish 401 vs 403 API errors after one renewal attempt. Never log access/refresh tokens, keys, or provider response bodies.

This is experimental and not proof that all three services work until live acceptance tests.
