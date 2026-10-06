# Phase 1 manual verification

Use synthetic staff data in a development database. Do not load patient data.

1. Start PostgreSQL, apply migrations, seed development data, start backend and frontend. Verify `/api/v1/health` returns healthy.
2. On a fresh development seed, sign in as `admin@example.org` / `ChangeMe!2026`. For an existing or reset account, use its current credentials; seeding does not replace passwords. Confirm the first-login password-change page identifies the signed-in account and administration endpoints return 403 until changed.
3. Enter the same temporary password used to sign in in **Current password**, then choose a different new password with at least 12 characters. Check that **Show current password** toggles visibility. Submit an incorrect current password first: its field must receive focus and explain how to replace an old autofilled password while preserving the new password for retry. Retry with the correct temporary password, confirm all existing sessions are revoked, and sign in again. Verify **Sign out** also works before completing a required password change.
4. Open Dashboard. Confirm counts come from real foundation records and no resident/clinical values are shown.
5. Create a synthetic user with an active department and Auditor role. Confirm the account appears after searching its name/email.
6. Verify duplicate email creation returns a visible error and short passwords produce inline validation feedback.
7. Edit the account, supply a change reason, deactivate it. Confirm existing sessions are revoked and login fails. Reactivate it and require a password change.
8. Create a role with audit.view and a reason. Edit it and verify the changed permissions. Clinical permission checkboxes must be disabled for the ICT administrator; direct API escalation attempts must return 403.
9. Create/edit/deactivate a department. Confirm inactive departments are not available for new staff assignments.
10. Change institution name, short name, contact details and an HTTPS logo URL. Reload and confirm the shell reflects saved identity. A non-HTTPS logo must be rejected.
11. Inspect audit events. Search actions and apply EAT date filters. Expand a staff-change event and verify actor, previous/new safe fields and reason. Confirm no password hashes or tokens are present.
12. Sign in as an Auditor after changing the temporary password. Confirm user/role/settings menus are absent and direct administration requests return 403.
13. In developer tools, remove `X-CSRF-Token` from an authenticated POST; expect 403. Confirm access/refresh cookies are HTTP-only and Strict SameSite. Production cookies must also be Secure.
14. Submit five incorrect passwords. Confirm the account is locked for 15 minutes and failed attempts are audited.
15. Let a session idle past 30 minutes. Confirm protected access/refresh returns 401 and the UI returns to sign in.
16. With a test SMTP service configured, request a reset for a synthetic account, use the emailed fragment-token link and verify one-time use plus invalid/expired link rejection. Unknown and known accounts must get the same public response.
17. Test keyboard-only navigation, focus indicators, form labels, inline errors and skip link. At phone/tablet widths, verify Offcanvas navigation, wrapping content and independently scrollable tables.
18. Sign out, reload and confirm cached administrative data is not accessible.

Future clinical workflow tests are deferred to the phases where those modules exist. They are not represented by placeholder tests.
