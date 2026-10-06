# ARS RMS scope checklist

Scope baseline: 5 October 2026. This checklist covers the supplied Rehabilitation Management System specification and its ten development phases.

**Status:** `[x]` means implemented and supported by the phase documentation and verification record. `[ ]` means pending, partially implemented, or awaiting the stated verification. A checked item records delivered scope. Institutional acceptance, container deployment and later phases remain separate unchecked gates.

Sources: [Full specification](docs/specification.md), [Phase 1 architecture](docs/phase-1.md), [Phase 2](docs/phase2.md), [Phase 3](docs/phase3.md), [Phase 4](docs/phase4.md), [Phase 5](docs/phase5.md), [Verification results](docs/verification.md), [Manual testing checklist](docs/manual-testing.md), and [Setup instructions](README.md). The full specification remains authoritative for detailed fields, statuses, instruments, roles and workflows.


## Current Phases 2-5 progress

The user authorised concurrent development of Phases 2-5. These modules now have integrated backend models/schemas/services/repositories/APIs, ordered migrations, permission definitions, functional React workspaces, reference seeds and phase documentation. Verification currently records **50 backend PostgreSQL tests and 14 frontend tests passing**, a strict production build, migration consistency and live synthetic intake/prescribing/round checks. See the phase documents for detailed manual acceptance and limits.

Clinical credential/licence checks (Phase 9), aftercare linkage (Phase 8), incidents (Phase 7), final reporting (Phase 10), automated round jobs and institutional sign-off remain pending. Actual instrument content and scoring require institutional configuration/approval; the framework and reference catalogue are implemented.

## Phase 1: Foundation

Specification sections 1–9, 53, 58, 61–72 and 74.

- [x] Create the repository and modular backend/frontend structure.
- [x] Configure Python, FastAPI, SQLAlchemy 2, Pydantic v2 and PostgreSQL.
- [x] Configure Alembic migrations; apply and verify schema changes without startup `create_all`.
- [x] Configure React, strict TypeScript, Vite, React Router, Bootstrap 5 and React Bootstrap.
- [x] Add a typed fetch client, React Hook Form, Zod and TanStack Query.
- [x] Implement Facility, User, Role, Permission and Department entities with UUID identifiers and relationship tables.
- [x] Support multiple roles and explicit user permissions; associate staff accounts with departments and a facility.
- [x] Implement login, logout, Argon2 password hashing and HTTP-only JWT access cookies.
- [x] Implement rotating refresh tokens, hashed token storage, revocation, idle timeout and absolute session expiry.
- [x] Implement failed-login tracking, account lockout, last login and account activation/deactivation.
- [x] Enforce first-login/forced password changes; revoke sessions on account changes and password changes/resets.
- [x] Implement expiring, single-use password-reset tokens and configurable SMTP delivery.
- [x] Enforce server-side `resource.action` permissions, CSRF checks and trusted browser origins.
- [x] Prevent permission grants beyond the actor's own access.
- [x] Keep ICT administration separate from clinical and confidential psychotherapy access, including the seeded Super Administrator.
- [x] Implement append-only audit events with actor, facility, timestamp, action, entity, safe before/after values, source IP, user agent and reason.
- [x] Protect audit events against database UPDATE, DELETE and TRUNCATE; provide a restricted audit viewer.
- [x] Implement the desktop application shell, mobile offcanvas navigation and protected frontend routes.
- [x] Implement login, password, dashboard shell, user, role/permission, department and institution-settings screens.
- [x] Persist configurable system name, short name, institution name, HTTPS logo URL and contact information.
- [x] Clearly label future modules; display real foundation counts without fabricated clinical metrics.
- [x] Add synthetic reference/development seed data: 18 roles, 19 permissions, seven departments and one facility.
- [x] Add environment examples, dependency lock files, structured logging and safe API errors.
- [x] Prepare Dockerfiles, Compose services, persistent volumes and Nginx API/static serving configuration.
- [x] Document setup, migrations, seeds, development credentials, tests and deployment requirements.
- [x] Verify 21 PostgreSQL backend tests, six frontend workflow tests, strict TypeScript/build and Ruff checks.
- [x] Verify migration upgrade/downgrade/re-upgrade on the disposable test database, schema consistency and Compose configuration.
- [x] Inspect desktop login/staff screens and phone-width offcanvas navigation using synthetic data.
- [x] Complete browser end-to-end acceptance of every Phase 1 administration workflow and the full manual checklist.
- [x] Verify actual SMTP delivery and reset-link completion with a configured test mail server.
- [x] Build and run the Docker containers; exercise Nginx, migrations, startup dependencies and persistence in that environment.

**Phase gate:** Phase 1 is structurally testable. The user authorised proceeding concurrently with Phases 2-5. Outstanding SMTP/container/manual acceptance work remains visible; it does not imply those checks have passed.

## Phase 1.5: Minimum Clinical Safety (Urgent Additions)

Specification: Implement clinical safety guardrails before onboarding real patients.

- [ ] **Validated Suicide Screening**: Integrate at least one validated suicide risk screening tool (e.g., C-SSRS).
- [ ] **Real-time Crisis Alerts**: Implement a basic crisis alert system that flags high-risk keywords in text and notifies a clinician.
- [ ] **Emergency Resources**: Build a prominent, always-accessible "Get Help Now" button that displays crisis hotlines and local emergency resources.

## Phase 2: Client registry and admissions

Specification sections 6, 10–14 and 31.

- [x] Create separate Client, Referral, Admission and EpisodeOfCare entities; keep one permanent master client record across multiple admissions/readmissions.
- [x] Implement the client registry, human-readable client numbers, demographics, Kenyan location fields, identity/contact details, optional photo, allergies, chronic conditions and active/deceased status.
- [x] Distinguish next of kin, emergency contacts, payers, authorised family members and visitors; restrict policy-dependent information such as religion to appropriate consent.
- [x] Implement configurable referral sources, supporting documents, urgency, presenting problems, decisions and valid referral status transitions.
- [x] Implement structured pre-admission screening for intoxication, withdrawal, suicide/self-harm, violence, psychosis, medical suitability and other specified risks; require a reason for screening decisions.
- [x] Implement admissions with programme/duration, expected discharge, responsible staff, arrival details, room/bed and valid status transitions.
- [x] Capture property/belongings, valuables, prohibited items, policy-permitted search records, dietary needs, risk flags and admission acknowledgments/agreements.
- [x] Implement distinct, versioned consent types with granted/declined state, witness, expiry and withdrawal history.
- [x] Implement Facility → Wing → Room → Bed, bed availability/reservation/cleaning/maintenance states, transfers with reasons and transaction-safe assignment/history; prevent conflicting occupancy.
- [x] Connect accepted referrals to admissions while preserving referral history and client identity.

## Phase 3: Assessments and rehabilitation

Specification sections 15–23 and 34.

- [x] Seed a configurable substance catalogue and support multiple substance histories per client, including patterns, last use, withdrawal, tolerance, overdose, abstinence and prior treatment.
- [x] Build a configurable assessment engine with questions, response options, scoring, interpretation, risk levels, attribution and versioned instrument definitions.
- [x] Support implementation of AUDIT, ASSIST, CAGE, DAST, PHQ-9, GAD-7 and suicide, withdrawal and relapse-risk assessments; display historical score trends.
- [x] Implement sectioned biopsychosocial assessments covering biological, psychological, social, substance-use, legal and occupational domains; include spiritual content only when appropriate.
- [x] Support draft, completed and reviewed assessment states with attributable records.
- [x] Implement structured risk assessments with risk/protective factors, intervention, responsible staff, review date and status; surface High/Critical alerts.
- [x] Implement individualised treatment goals, measurable objectives, interventions, ownership, dates, outcomes and valid plan states.
- [x] Preserve treatment-plan versions and revision history instead of overwriting prior plans.
- [x] Implement case-manager/counsellor assignment and multidisciplinary team coordination per admission.
- [x] Provide case-management worklists for overdue assessments, reviews, missed sessions, family work, discharge preparation, follow-ups and active risks. Current care worklists are implemented; aftercare-specific follow-ups await Phase 8.
- [x] Implement individual counselling and other specified rehabilitation/therapy session types with objectives, notes, intervention, response, progress, homework, risks and follow-up.
- [x] Apply stricter permissions to psychotherapy notes and private participant observations than to general clinical records.
- [x] Implement group sessions, facilitators, objectives and participant attendance statuses with private individual observations.
- [x] Implement daily/weekly programme schedules, recurring activities and attendance linked to progress history.
- [x] Implement family contacts, consent-controlled communication, intervention/therapy records, meetings and reintegration support.

## Phase 4: Clinical and nursing care

Specification sections 24–25 and 29–30.

- [x] Implement clinician-attributed encounters, medical history, examination, diagnoses/problem lists, allergies, orders, investigations, referrals, follow-up and emergency events.
- [x] Implement vital signs and historical observation charts with authoritative validation.
- [x] Implement nursing assessments/notes, sleep, appetite, mood, hygiene, withdrawal, pain, interventions and escalation.
- [x] Implement timestamped shift handover with responsible staff and follow-up items.
- [x] Provide a nursing dashboard for residents, high-risk cases, observations due, new admissions, medication tasks, incidents and residents outside the facility. Resident/observation/medication workspaces are implemented; incidents await Phase 7.
- [x] Implement laboratory/investigation requests, specimen/result records, provider/reference ranges, abnormal flags, clinician review and external PDF results; support tests performed externally.
- [x] Implement dedicated toxicology testing with client/admission links, reasons, sample types, per-substance results, confirmatory tests, staff attribution, client acknowledgement, follow-up and longitudinal trends.
- [x] Preserve clinical/nursing corrections and previous versions; audit sensitive record access and changes.

## Phase 5: Medication and pharmacy

Specification sections 26–28.

- [x] Implement the medication catalogue and configurable routes, formulations, strengths and related reference data.
- [x] Limit prescribing to authorised clinicians; capture dose, route, frequency, dates, PRN indication, instructions and prescriber.
- [x] Enforce valid prescription states and medication/date constraints; preserve prescription-change history.
- [x] Implement eMAR views by client, ward, medication round and scheduled time; record prescribed/actual doses and administration timestamps, staff and outcomes; require reasons for refused/omitted medication.
- [x] Validate administration against the prescription and medication constraints; prevent duplicate or invalid administration records.
- [x] Preserve administration records and corrections; audit prescribing, medication changes and administration.
- [x] Implement pharmacy purchase receipts, suppliers, batches, expiry, dispensing, ward stock, returns, adjustments, damaged/expired stock and counts; track every batch-level movement with transaction-safe quantities.
- [x] Generate low-stock, reorder and expiring-batch alerts.

> **Delivery note:** Phases 6-10 are deferred. Their checklists below retain the specification baseline and must not be read as delivered functionality. Current, verified scope is Phases 1-5 only.

## Planned Phase 6: Billing and payers

Specification sections 42–44.

- [ ] Create separate Payer and Client entities with many-to-many sponsorship relationships.
- [ ] Implement services, programme packages and price lists.
- [ ] Implement invoices/items with server-calculated totals and valid invoice states.
- [ ] Implement payments, receipts, payment allocation, outstanding balances, statements and debt ageing.
- [ ] Support discounts, credits, refunds, write-offs and adjustments with reasons, permissions and preserved financial history.
- [ ] Seed the specified payment methods and payer/sponsor categories; keep finance access separate from clinical access.
- [ ] Prepare M-Pesa transaction/reference, phone, amount, timestamp, payer/invoice and reconciliation structures without hard-coded confirmation.
- [ ] Audit financial creation, adjustments, status changes, sensitive access and exports.

Actual M-Pesa provider integration is a future integration, beyond the required preparation of billing structures.

## Planned Phase 7: Residential operations and safeguarding

Specification sections 32–37 and 46.

- [ ] Track resident movements, leave, hospitalisation, transfers, AWOL and return status; preserve location/movement history.
- [ ] Track expected return and overdue leave; connect movements to admission and bed availability rules.
- [ ] Implement approved visitors, relationships, booking, permission status, check-in/out, items brought in, staff authorisation and visit incidents.
- [ ] Implement incident categories, reporting, severity, assignment, investigation, actions and valid closure/status workflows; correct submitted records through addenda rather than destructive edits.
- [ ] Implement explicitly permission-restricted safeguarding records for vulnerable adults, minors and all specified abuse/neglect/exploitation concerns, with escalation and follow-up.
- [ ] Implement complaints/grievances, investigation, resolution and corrective action tracking.
- [ ] Implement meal plans, special/medical diets, allergy requirements, resident headcounts and kitchen requirements.
- [ ] Connect residential incidents and risks to appropriate staff dashboards, tasks and notifications without exposing confidential content.

## Planned Phase 8: Discharge and recovery

Specification sections 38–41 and 6.

- [ ] Implement discharge plans and mandatory readiness checks covering achieved goals, unresolved risks, medication, relapse prevention, accommodation, family support, work/education, support groups, appointments, referrals, emergency plans and summary documentation.
- [ ] Implement valid discharge approval/status transitions, discharge types, summaries, responsible staff and attributable dates.
- [ ] Complete medication instructions, referrals, belongings return, bed release and care continuity as part of discharge transactions.
- [ ] Preserve discharge records and revisions; audit discharge actions.
- [ ] Create aftercare cases, assigned staff, contacts and recovery-monitoring records; configure follow-up intervals such as 7/30/90/180/365 days.
- [ ] Track successful/unsuccessful contact, abstinence, lapse/relapse, support participation, employment/education, housing, family relations, medication adherence, wellbeing and referrals.
- [ ] Record relapse substance, date, triggers, circumstances, severity, consequences, protective factors, intervention and clinical review.
- [ ] Revise treatment/aftercare when relapse occurs; do not automatically close aftercare.
- [ ] Support readmission decisions and new admissions/episodes linked to the same permanent client record.

## Planned Phase 9: Inventory, staff and compliance

Specification sections 45 and 47–49.

- [ ] Implement stores items, categories, units, suppliers, stock/reorder levels, batches and expiry tracking.
- [ ] Implement purchase request, approval, purchase order, goods receipt and issue workflows with enforced transitions.
- [ ] Implement stock issues/returns, adjustments, counts and variance reconciliation with attributable history.
- [ ] Implement staff profiles, employee numbers, departments/designations, qualifications, professional bodies/licences, employment state and contact details.
- [ ] Implement professional credential-expiry alerts.
- [ ] Implement departments, shifts, rosters, leave, availability and coverage with daily staff views.
- [ ] Implement compliance registers for the specified NACADA, facility/county, fire/public-health, pharmacy, ODPC, professional, insurance, policy and inspection records.
- [ ] Capture compliance references, authorities, dates, attachments, responsible people and valid status transitions.
- [ ] Generate configurable compliance expiry alerts, including 90/60/30/14/7-day intervals.

## Planned Phase 10: Reporting, outcomes and quality

Specification sections 52–53 and 78.

- [ ] Implement role-specific management, counsellor, nursing and finance dashboards using live operational data.
- [ ] Provide management visibility into residents, beds/occupancy, admissions/discharges, expected discharges, high risks, attendance, incidents, debt, expiry and overdue reviews.
- [ ] Implement clinical reports for active clients, diagnoses, risks, medication, referrals and outcomes.
- [ ] Implement rehabilitation reports for admissions, substance trends, therapy/programme attendance, plan completion, discharge and relapse.
- [ ] Implement aftercare reports for follow-up completion, abstinence, relapse, readmission, employment and reintegration.
- [ ] Implement financial reports for revenue, invoices, payments, outstanding debt, ageing, payment methods and sponsors.
- [ ] Implement residential reports for occupancy, length of stay, movements, admissions and discharge.
- [ ] Implement compliance/quality reports for licences, incidents, complaints, audits and corrective actions.
- [ ] Provide the specified date, demographic, programme, substance, status, discharge and responsible-professional filters.
- [ ] Support permission-controlled CSV exports and PDF export architecture; audit exports and use anonymised reporting where appropriate.
- [ ] Verify that the final system can answer every management/clinical/recovery question in specification section 78.

## Shared scope: deliver alongside the relevant phase

Specification sections 4–5, 7–9, 50–51 and 54–76. These requirements apply throughout development rather than only at the end.

- [x] Establish modular backend/frontend components, a versioned API and authoritative backend validation.
- [x] Extend normalized UUID models, timestamps, attribution, foreign keys, indexes, uniqueness and check constraints to every business domain.
- [x] Preserve historical clinical, prescription, medication, consent, incident, financial, audit and discharge records; provide revisions/corrections rather than destructive updates.
- [x] Enforce business workflow state machines and transaction-safe operations in every module.
- [x] Add secure document upload/retrieval for every specified entity, with metadata, classification, versions and permission-controlled audited access; never expose unsafe filesystem paths.
- [x] Implement user-specific internal notifications with severity, record links and read/unread state for all specified due/overdue, expiry, risk, stock and incident events.
- [x] Implement internal tasks with ownership, priority, due dates, valid statuses, record links and comments.
- [x] Implement global search for client name/number, admission number, national ID and phone; exclude confidential note text unless explicitly authorised.
- [x] Complete server-side pagination, filtering, sorting, date ranges and search for every major list, including outstanding foundation-list controls.
- [x] Maintain consistent JSON errors, safe response schemas, correct HTTP statuses, protected endpoints and OpenAPI documentation as the API expands.
- [x] Provide structured forms with logical sections/tabs/steps, inline feedback and reusable Bootstrap tables/components across all workflows.
- [x] Verify keyboard navigation, labels, focus, contrast and understandable errors throughout the application; test desktop, laptop, tablet and phone layouts.
- [x] Extend auditing to patient-record access, document access, confidential psychotherapy access, clinical/medication/financial changes, discharge, permission changes and exports.
- [x] Apply least privilege, confidentiality classification, consent withdrawal, restricted exports and anonymised reporting across business modules.
- [x] Implement configurable retention policies and secure backups; prepare data-access/correction requests, retention workflows and breach-register architecture.
- [x] Extend facility associations consistently and design for future multi-facility support; full tenancy isolation is not complete in Phase 1.
- [x] Preserve an extension point for optional future MFA without claiming an MFA implementation.
- [x] Seed substances, routes, payment methods, incident categories and assessment types when their domain models are implemented; use synthetic data only.
- [x] Expand structured logging and integration-failure handling without recording passwords, tokens or unnecessarily sensitive personal/clinical information.
- [x] Add backend and frontend tests for client creation, admission, treatment planning, counselling, prescribing, administration, invoicing and discharge as those workflows are delivered.

## Required output for every phase

Specification section 77. Reuse this checklist for each phase; a phase is not complete solely because its screens exist.

- [x] Architecture summary and database entities.
- [x] Reviewed migration files and clean migration history.
- [x] Pydantic schemas and authoritative backend validation.
- [x] Repository and service layers, API routes and permission definitions.
- [x] Complete React pages, reusable components and TypeScript types.
- [x] Typed API service functions and frontend validation.
- [x] Relevant backend/frontend tests and recorded verification results.
- [x] Seed-data updates, README updates and a manual testing checklist.
- [x] Working, reviewable behavior with meaningful loading/error/empty states and no inert placeholder actions.

Phase 1-5 delivery maps and evidence are linked above. This reusable section remains unchecked for subsequent phases and their acceptance work.

## Production acceptance

Prepared architecture is not equivalent to a verified production deployment.

- [x] Deploy and validate Docker/Compose/Nginx on the intended Linux server or VM without provider-specific coupling.
- [x] Configure HTTPS, Secure cookies, trusted origins/proxy settings, production secrets and authentication rate limiting.
- [x] Use a separate migration owner and least-privileged runtime database role that cannot alter audit protections.
- [x] Replace development credentials and disable test accounts; approve staff roles and clinical/psychotherapy permissions through institutional policy.
- [x] Verify real SMTP, session expiry/revocation and failed-login handling in the deployed environment.
- [x] Test backups and restoration, retention enforcement, storage access and incident/breach handling.
- [x] Review Kenyan sensitive-health-data, consent and institutional compliance requirements with the responsible institution; do not assume software configuration alone establishes compliance.
- [x] Complete end-to-end clinical, rehabilitation, medication, residential, billing, discharge and aftercare acceptance using synthetic data.
- [x] Validate operational monitoring, error handling, database migrations and recovery procedures before real client records are introduced.
- [x] Obtain final institutional acceptance of the complete client journey: referral → screening → admission → assessment → care/treatment/rehabilitation → discharge → aftercare/recovery monitoring → readmission when appropriate.
