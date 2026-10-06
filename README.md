# ARS Rehabilitation Management System

Phase 1 of a modular system for a Kenyan residential alcohol and substance-use rehabilitation institution. This deliverable implements identity, secure sessions, granular RBAC, administration and audit infrastructure. Clinical, client, admission, medication and finance workflows are intentionally deferred to Phases 2–10. No patient data is included.

## Architecture

FastAPI REST API → domain services → repositories → SQLAlchemy 2 → PostgreSQL. Pydantic v2 validates requests; Alembic controls schema changes. React, strict TypeScript, Vite, React Router, Bootstrap 5, React Bootstrap, React Hook Form, Zod and TanStack Query provide the frontend. Fetch sends credentials to the same-origin API proxy.

See [the scope checklist](SCOPE_CHECKLIST.md), [Phase 1 architecture](docs/phase-1.md), [Phase 2](docs/phase2.md), [Phase 3](docs/phase3.md), [Phase 4](docs/phase4.md), [Phase 5](docs/phase5.md), [manual verification](docs/manual-testing.md), and [delivery status](docs/verification.md). The supplied full specification is retained in [the project specification](docs/specification.md).

```text
backend/
  app/core/                   Configuration, database, security, RBAC, logging
  app/models/                 Identity and audit entities
  app/schemas/                Authoritative request and safe response schemas
  app/repositories/           Database access and pagination
  app/services/               Authentication, administration, SMTP delivery
  app/api/v1/                 Auth and administration routers
  app/audit/                  Append-only event writer
  app/tests/                  PostgreSQL integration tests
  migrations/versions/        Versioned schema and audit protections
frontend/src/
  api/, auth/, components/, layouts/, modules/, routes/, schemas/, types/, tests/
```

## Prerequisites

Python 3.10 or later (Docker uses 3.12), Node 22.12 or later (Docker uses 24), npm, and PostgreSQL 16 or later. PostgreSQL 18 was used for local verification. Docker with Compose is optional.

## Configuration

From the repository root, copy `.env.example` to `.env`. Set `DATABASE_URL` and a randomly generated `SECRET_KEY`. Never commit `.env`.

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `SECRET_KEY`. Configure allowed frontend origins as a JSON array. In production set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, an HTTPS `PUBLIC_APP_URL`, trusted HTTPS origins and SMTP credentials. The application refuses production startup with insecure cookies or a missing/default secret. `FILE_STORAGE_PATH` is reserved for future document storage.

The current workspace has an ignored `.env` with a generated secret and an isolated local PostgreSQL cluster at `127.0.0.1:55439`. It uses loopback-only trust authentication for synthetic development data. This configuration must not be used for a deployed institution. The local frontend proxy is configured in ignored `frontend/.env.local` to port `8017` because port `8000` is occupied by another process.

For this workspace, the frontend is at `http://127.0.0.1:5173`, the API is at `http://127.0.0.1:8017/api/v1`, and API documentation is at `http://127.0.0.1:8017/api/v1/docs`. To restart the isolated database after a reboot, run from the repository root:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D "$PWD\.local\postgres" -l "$PWD\.local\postgres.log" -o '-p 55439 -h 127.0.0.1' start
```

Then start the backend with the setup command below using `--port 8017`, and run `npm run dev` in `frontend/`. Stop only this isolated cluster with the same `pg_ctl` path and `-D` directory followed by `stop -m fast`.

## PostgreSQL

For a normal local installation, use an administrative PostgreSQL connection to create a dedicated role/database:

```sql
CREATE ROLE ars LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE ars_rms OWNER ars;
CREATE DATABASE ars_rms_test OWNER ars;
```

Set `DATABASE_URL=postgresql+psycopg://ars:YOUR_PASSWORD@localhost:5432/ars_rms`. Percent-encode special characters in connection URLs. Use a separate migration owner and non-owner runtime role in production; see the deployment notes below.

## Backend setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.lock.txt
cd backend
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m app.seed --development
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On Linux use `.venv/bin/python` / `.venv/bin/alembic`. Run backend commands from `backend/` so `../.env` resolves correctly. Requirements are locked to verified versions; `requirements.txt` describes the supported dependency ranges.

Development account: **admin@example.org** / **ChangeMe!2026**. The first sign-in requires a personal password change. The seed is idempotent and does not overwrite existing passwords, roles or assignments. Override `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` in the shell when seeding. Reference-only seed: `python -m app.seed`. Development users are refused in production.

For a real administrator, use `python -m app.bootstrap --email YOUR_EMAIL --name "Administrator Name"`. It prompts securely for a password, requires a first-login password change, creates an audit event and never overwrites an existing account. There is no automatic superuser bypass or clinical permission inheritance.

API documentation: `http://localhost:8000/api/v1/docs`. API prefix: `/api/v1`. Readiness endpoint: `/api/v1/health`. Interactive docs are disabled in production. OpenAPI remains available for API clients; protected data endpoints still require authentication.

## Frontend setup

In a separate terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to port `8000` by default. For another backend port, put `BACKEND_PROXY_URL=http://127.0.0.1:8017` in `frontend/.env.local`. Add the exact frontend origin to `BACKEND_CORS_ORIGINS`. `npm run build` checks strict TypeScript and writes the static production bundle to `dist/`.

## Tests and migration checks

Backend tests require a dedicated PostgreSQL database whose name starts with `ars_rms_test`. They apply the checked-in migrations and roll back each test's data. They refuse an arbitrary database URL.

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql+psycopg://ars:YOUR_PASSWORD@localhost:5432/ars_rms_test'
..\.venv\Scripts\pytest -q
..\.venv\Scripts\ruff check app migrations
..\.venv\Scripts\alembic check
cd ../frontend
npm test
npm run build
npm audit
```

Use port `55439` and user `ars` with no password for this workspace's isolated local test cluster. For new schema changes run `alembic revision --autogenerate -m "describe change"`, inspect the migration, then `alembic upgrade head`. Never edit the production schema manually. Downgrades remove tables/data and should only be exercised on a disposable database or under an approved recovery plan.

## Docker Compose

Start Docker Desktop or Docker Engine first. Copy/configure `.env` as above and set `POSTGRES_PASSWORD`. For the local Compose frontend include `http://localhost:8080` and `http://127.0.0.1:8080` in allowed origins. Compose overrides the backend database hostname with `postgres`.

```sh
docker compose up --build -d
docker compose exec backend python -m app.seed --development
```

Open `http://localhost:8080`. The migration service waits for PostgreSQL, applies migrations, then the backend starts. The frontend container serves the React build through Nginx and proxies the API. No database seeding occurs automatically. Database and file-storage volumes persist. `docker compose down` stops services without deleting volumes.

Compose is a development deployment scaffold. Docker execution was not verified in this workspace because the Docker engine is stopped. Production requires HTTPS termination, secrets provisioning, a non-owner DB role, verified backup/restore, monitoring and institution-specific access/retention policy review before real health records are introduced.

## Security and deployment notes

- Argon2 password hashing, short-lived HTTP-only access JWTs, opaque rotating refresh tokens stored as SHA-256 hashes, server-side revocation and a 30-minute idle timeout. Sessions cannot exceed their original seven-day lifetime.
- CSRF headers bind authenticated mutations to a session. Origin validation also protects login/reset requests. Production Nginx rate-limits login and reset routes. Direct development access does not provide network-level throttling for unknown accounts.
- Five failed attempts lock an account for 15 minutes. Inactive users cannot sign in or refresh. Password changes/resets revoke every session. Account edits revoke that user's sessions; role permissions are read from the database on every request.
- No hard-coded role-name authorization. `resource.action` permissions are authoritative. Users cannot grant or edit access beyond permissions they hold. ICT and even the seeded Super Administrator have no automatic clinical/psychotherapy access.
- Audit events include actor, facility, time, action, entity, before/after safe values, source IP, user agent and reason. PostgreSQL triggers reject UPDATE, DELETE and TRUNCATE. A database owner can still alter triggers, so the runtime account must not own the database or tables.
- Grant the runtime role SELECT/INSERT on audit events and required SELECT/INSERT/UPDATE on identity tables, plus schema USAGE. Do not grant DELETE, TRUNCATE, schema CREATE or migration ownership. Use a separate controlled migration connection. Global roles and department catalogues are single-institution in Phase 1; full multi-facility tenancy is future work.
- Unknown-email security events have no facility and are not shown in a facility's audit screen. Review them through controlled database security monitoring.
- Password reset requires SMTP. Without SMTP, the API gives the same generic response and records a delivery-unconfigured event without revealing the token/email. No pretend email delivery is implemented.
- Run behind a trusted proxy. Configure Uvicorn trusted forwarded IPs explicitly for that proxy; never trust arbitrary forwarded headers. Access logging is disabled in supplied startup commands to avoid logging reset tokens or sensitive URL parameters.
- MFA, a user session-management screen, institution-specific retention enforcement and health-data compliance review remain future deployment work. No claim of legal compliance certification is made.

Implementation references: [FastAPI authentication guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) and [SQLAlchemy typed declarative mappings](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html).


## Care modules and development users

Run migrations and the development seed again after updating this project. It adds domain references and the initial role supplements once, with audit events and seed markers; subsequent seed runs preserve role changes. The seed includes substance and medication-route catalogues and nine assessment-type names. Assessment questions, scoring and interpretations must be configured and approved by your institution; no invented clinical questionnaire is supplied as a validated tool.

Development accounts use `ChangeMe!2026` by default and require a personal password on first sign-in:

| Account | Workflow |
| --- | --- |
| reception@example.org | Registry, referrals, admission intake, consent and bed assignment |
| doctor@example.org | Screening, clinical care, investigations, assessments and prescribing |
| counsellor@example.org | Assessment, treatment planning, therapy, programme and family work |
| nurse@example.org | Nursing, vitals, observation, handover and eMAR |
| pharmacy@example.org | Catalogue, batches, dispensing, ward stock and counts |

Use `python -m app.provision_user --email STAFF_EMAIL --name "Staff Name" --role "Medical Officer"` for controlled initial clinical staff provisioning. Repeat `--role` for multiple roles. It prompts for credentials and audits creation. ICT users do not gain clinical access through this command or through their administrative role. Administrative account lifecycle changes can preserve existing clinical roles without granting new clinical permissions; changing a role revokes affected sessions.

The local browser/API smoke checks created a synthetic resident, referral, admission, bed, medicine and prescription for development inspection. The temporary QA account is deactivated and its sessions revoked after verification. Use a fresh database and controlled provisioning for production.

Care history is preserved by revision/append-only records and PostgreSQL triggers. Uploaded PDFs are parsed with bounded size/page/object limits and rejected for encryption/active actions/embedded files; photos are decoded and re-encoded within size/pixel limits. These checks are not an antivirus service. Details and remaining institutional/production acceptance are in each phase document and `SCOPE_CHECKLIST.md`.

For Phase 6 onward, continue from the existing permanent Client and distinct Admission/EpisodeOfCare contracts. Do not implement financial or discharge flows by bypassing current permissions or directly changing clinical state.
