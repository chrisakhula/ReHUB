# Phase 1 verification record

Verified locally on 5 October 2026 (Africa/Nairobi), using Python 3.10.11, Node 24.14.0 and an isolated PostgreSQL 18.6 cluster.

| Check | Result |
| --- | --- |
| Backend PostgreSQL integration suite | 21 passed |
| Frontend workflow suite | 6 passed |
| Strict TypeScript + Vite production build | Passed |
| Ruff check | Passed |
| Alembic upgrade to head | Passed |
| Alembic downgrade to base and re-upgrade, disposable test database | Passed |
| Alembic schema drift check | No new upgrade operations |
| Docker Compose configuration validation | Passed |
| npm dependency audit | Zero reported vulnerabilities |
| Browser login and authenticated staff list | Verified with a synthetic QA account |
| Phone-width offcanvas navigation | Verified at 390 × 844; viewport restored |

Backend coverage includes cookie flags, logout/replay rejection, refresh rotation/replay rejection, CSRF/origin checks, lockout persistence, forced password change, password change/revocation, direct permissions, denied access, prohibited clinical escalation, account creation/deactivation, duplicates, audit snapshots, PostgreSQL audit immutability, pagination, settings validation, roles/departments, one-time and expired resets, session idle/absolute expiry, facility boundaries and date ranges.

Frontend coverage includes login validation/success/failure, staff creation with role/password validation, role creation with mandatory reason, unauthenticated routing and first-login password-change routing. These are interaction tests using mocked HTTP services; they do not replace PostgreSQL integration tests or a complete browser end-to-end suite.

Saved UI evidence: [desktop staff list](screenshots/users-desktop.jpg), [phone navigation](screenshots/navigation-mobile.jpg), [desktop dashboard](screenshots/dashboard-desktop.jpg). All names/accounts are synthetic. The QA account is deactivated after verification and its sessions revoked; its record and audit history are retained.

Docker image builds and container startup were not run because the installed Docker engine is stopped. Nginx configuration has not been exercised in a running container. SMTP delivery is tested through an injected delivery function; a real mail-server round trip requires SMTP configuration. A Starlette test-client deprecation warning remains, while tests pass. Vite reports harmless third-party Zod annotation warnings and completes the production build.

No production deployment or clinical functionality is claimed. Follow the README deployment notes before using real institutional or health data.


## Integrated Phases 2-5 verification

Verified locally on 5 October 2026 (Africa/Nairobi).

| Check | Result |
| --- | --- |
| Full PostgreSQL suite | 50 passed |
| Frontend workflow tests | 14 passed |
| Strict TypeScript/Vite production build | Passed; code split by module/vendor |
| Ruff check | Passed |
| Alembic consistency | No new upgrade operations |
| npm audit | Zero reported vulnerabilities |
| Live same-origin API smoke | Synthetic registry/referral/screening/admission/consent/bed/activation/prescription/round generation passed |
| Browser medication workspace | Verified admission context, scheduled dose, oral route, ward/time controls and prescription state |

Expanded checks cover consent-controlled family communication/withdrawal, group attendance and private observations, programme attendance, nursing/handover/toxicology, private PDF/photo uploads, structural file rejection, PRN timing, allergy review, immutable care history, zero-variance counts, expired stock, pending intake amendments, intake-assigned caseload and used medicine identity protection. Frontend tests cover client creation, admission, treatment objectives, counselling dates, prescribing, eMAR outcomes and context/permission guards.

[Medication workspace evidence](screenshots/medication-phase5.jpg) uses only synthetic records. The temporary QA account is deactivated and sessions revoked after verification; the synthetic development client/admission/medicine records are retained to preserve audit history. Initial development accounts require first-login password changes.

The retained Starlette test-client deprecation warning does not affect passing tests. Third-party Zod annotation warnings remain in the successful build. Docker image/container execution, real SMTP, complete institutional end-to-end acceptance and production deployment are not verified. Complete the remaining phase/manual/production checklists before real health records are used.

## Password-change follow-up

Verified on 5 October 2026 (Africa/Nairobi). The reset administrator's temporary password was accepted by the live login and current-password check through the frontend proxy. The original seed password was rejected with the reported error. The live administrator's password was preserved during verification.

The form now identifies the account, explains that the current password is the temporary sign-in password after a reset, offers a visibility checkbox and sign-out, and focuses a rejected current-password field with guidance about old autofill. The proposed new password remains available for a corrected retry; passwords are not persisted by this UI.

| Check | Result |
| --- | --- |
| Frontend workflow suite | 17 passed |
| Targeted PostgreSQL forced-change regression | Passed; incorrect current password leaves credentials/session intact, correct replacement revokes all sessions and disables forced change |
| Strict TypeScript/Vite production build | Passed |
| Ruff on the changed backend test | Passed |
| Browser | Administrator sign-in, account/helper text, visibility toggle and sign-out control verified |

[Updated password-change form](screenshots/password-change-guidance.jpg) shows empty credential fields. Automated form submission/retry tests use synthetic credentials; the browser verification did not submit a new password for the live administrator.
