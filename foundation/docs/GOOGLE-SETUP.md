# Google Cloud configuration, once native integration exists

Account used for email in MailCraft: your Google Workspace address.
Cloud project can remain owned by a separate personal Gmail account; it must use the **External** OAuth audience if outside the Workspace organization. A Workspace-owned **Internal** project is preferable for permanent company operation when available and authorized.

## Do this only when the enhanced MailCraft build actually supports Google Calendar / Contacts

1. Sign in to https://console.cloud.google.com/ and select the existing MailCraft Desktop OAuth project.
2. Open **APIs & Services > Library**. Enable **Google Calendar API**.
3. Return to **Library**. Enable **People API**.
4. Open **Google Auth Platform > Data Access**. Add these **read-only** scopes alongside the existing Gmail scope:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/contacts.readonly`
5. Keep `https://mail.google.com/`, `openid`, and `email` for the existing MailCraft email functionality. Do not replace those with Calendar/Contacts scopes.
6. Make sure your Workspace account is an OAuth test user if the Cloud project is External / Testing.
7. The Google Workspace administrator might need to approve the new requested scopes in **Admin Console > Security > Access and data control > API controls**.
8. On a **new** Gmail account, grant all three services in the Google browser consent flow. For an **existing** MailCraft account, reauthorize once to grant the new Calendar and Contacts permissions; the old token does not automatically gain extra scopes.
9. If the user declines Calendar or Contacts permission, Gmail must still connect and send/receive normally; the other two should show clear disconnected status.

Never publish a public app or grant 'Trusted' status without the organization's security review. Google External/Testing Gmail grants normally have a 7-day refresh-token expiration unless a qualifying exception applies. This is different from the People API *sync token*, which also expires periodically and requires a fresh full contact sync. For a verified long-term business use case, choose a company-owned Internal Cloud project where policy permits.

Sources:
- https://developers.google.com/workspace/calendar/api/auth
- https://developers.google.com/people/api/rest/v1/people.connections/list
- https://developers.google.com/identity/protocols/oauth2/resources/granular-permissions
- https://developers.google.com/identity/protocols/oauth2/production-readiness/overview
