# Phase 1 architecture and delivery map

## Scope

This phase establishes identity, administration and security infrastructure. It does not implement client records or admissions. A Client and an Admission will be distinct entities in Phase 2; no identity user model is reused as a patient record.

## Database entities

| Entity | Purpose |
| --- | --- |
| Facility | Institution identity, branding and contacts; future facility association |
| Department | Staff organisation with activation state |
| User | UUID identity, password hash, active state, forced password change, lockout and last login |
| Role | Named explicit permission set |
| Permission | Unique resource.action catalogue, including reserved future module permissions |
| UserRole / RolePermission / UserPermission | Normalised many-to-many assignments |
| AuthSession | Revocable session, hashed refresh and CSRF tokens, idle/absolute expiry |
| PasswordReset | Hashed, expiring, single-use reset token |
| AuditEvent | Immutable record with safe changes, actor, source and facility |

Identity records carry creation/update timestamps and creator/updater UUIDs. Users/departments are deactivated, never deleted through the API. UUIDs use native PostgreSQL UUID columns through SQLAlchemy's `Uuid` type. Unique constraints, relationship foreign keys, search indexes and nonnegative login-count constraint are present. Timestamps are timezone-aware; the UI displays East Africa Time.

## Migrations

1. `34852fabf912`: identity tables, associations, sessions and audit.
2. `9b420e3b6c10`: update/delete/truncate protection for audit, login-count constraint.
3. `395301858dbd`: facility association and audit index.

No `create_all` at application startup. Both development setup and tests run Alembic. Audit history predating facility tagging is preserved rather than rewritten.

## Backend layers

`schemas/identity.py` defines request validation and safe account responses. `repositories/identity.py` resolves selections, duplicates and paginated queries. `services/auth.py` handles credential/session workflows; `services/administration.py` validates permission grants and writes safe audit snapshots. Route files handle HTTP concerns and delegate writes to services. Aggregated read-only views use SQLAlchemy in the administration router; future reporting queries can move to domain repositories as they grow.

`core/permissions.py` validates tokens, active accounts, session expiry, CSRF and forced password changes. Permissions are evaluated from current database assignments, without wildcard superuser exceptions. `audit/service.py` is the reusable event writer. Mutations and their audit event share a transaction; rejected login counters/audit explicitly commit before returning 401.

## API map

| Path | Operations | Permission |
| --- | --- | --- |
| `/auth/login`, `/auth/request-reset`, `/auth/reset-password` | POST | Public, validated, trusted-origin browser requests |
| `/auth/refresh` | POST | Refresh cookie and session CSRF |
| `/auth/me` | GET | Current session |
| `/auth/logout`, `/auth/change-password` | POST | Current session and CSRF |
| `/users` | GET, POST | users.manage |
| `/users/{id}` | PUT | users.manage plus grant limits |
| `/roles` | GET | roles.manage or users.manage |
| `/roles`, `/roles/{id}` | POST, PUT | roles.manage plus grant limits |
| `/permissions` | GET | roles.manage or users.manage |
| `/departments` | GET | Current session |
| `/departments`, `/departments/{id}` | POST, PUT | departments.manage |
| `/settings` | GET | Current session, own facility |
| `/settings` | PUT | settings.manage |
| `/audit` | GET | audit.view, facility scope |
| `/dashboard` | GET | Current session, permission-filtered counts |

Errors use `{"error":{"message": "...", "fields": [...]}}`; lists return `items` and `meta` with page/page_size/total. Page size is bounded at 100. Accounts support search, status filter and allowlisted sort; audit supports action search and dates. Delete endpoints intentionally do not exist. Permission definitions are code-owned; administrators compose roles and direct assignments instead of inventing ineffective endpoint permission codes.

## Frontend map

Login, forgot/reset/change password; permission-filtered dashboard; user search/create/edit; roles and permissions; departments; append-only audit inspection; institution settings. Protected routes distinguish missing authentication from denied authorization. A forced password change redirects before normal app access.

Reusable `PageHeader`, `ErrorNotice`, `Loading`, `Pagination`, `Empty` and `FormField` components provide consistent Bootstrap interactions. Typed API functions centralise credentials, CSRF, refresh and errors. React Hook Form with Zod validates forms; backend validation remains authoritative. The shell provides desktop sidebar, Bootstrap Offcanvas mobile navigation and a keyboard skip link.

System/short/institution names, contacts and HTTPS logo URL are persisted in facility settings. Planned modules are explanatory navigation text, never inert links pretending to work. No clinical dashboard metrics are fabricated.

## Seed data

18 required role names, 19 explicit/reserved permissions, seven departments, one synthetic facility and an opt-in development administrator. Substance, medication, payment and assessment reference catalogues are deferred until their domain models exist. Seed runs do not replace changed permission assignments.

## Future phases

| Phase | Next deliverable |
| --- | --- |
| 2 | Permanent client record, contacts, referrals, screening, admissions, consent, rooms and beds |
| 3 | Assessment engine, substance/biopsychosocial/risk assessments, versioned treatment plans and therapy |
| 4 | Clinical encounters, diagnoses, vitals, nursing, handover and laboratory |
| 5 | Prescriptions, eMAR, pharmacy, batches, dispensing and expiry alerts |
| 6 | Payers, programme billing, invoices, payments, statements and M-Pesa integration structures |
| 7 | Movements, visitors, incidents, safeguarding and nutrition |
| 8 | Discharge readiness, discharge, aftercare, relapse and readmission |
| 9 | Stores, procurement, compliance, credentials and licences |
| 10 | Role-specific clinical/operational dashboards, reports, outcomes, audits and exports |

Continue only after reviewing this Phase 1 foundation. Clinical note revisions, sensitive access logging and confidential psychotherapy restrictions will be built with their actual domain entities.
