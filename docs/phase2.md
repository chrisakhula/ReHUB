# Phase 2: Clients, intake and residential beds

## Scope and architecture

Phase 2 provides a permanent client registry, contacts, referrals, structured pre-admission screening, admission episodes, individual consent decisions, property custody and the Facility → Wing → Room → Bed hierarchy. Client records persist across admissions. An admission has its own number, care team, programme and workflow; creation also opens a separate EpisodeOfCare.

Writes follow Router → ClientService → ClientRepository → PostgreSQL. Intake uploads use the separate IntakeDocuments service. Facility scope is derived from the authenticated staff account; request bodies cannot choose another facility. Authentication, permission checks, CSRF validation and forced-password-change handling reuse Phase 1. Successful mutations and their audit events commit together through the request database transaction.

This document maps the implementation and its manual acceptance work. It does not establish readiness for real health data or replace the final integrated verification report.

## Database entities

| Entity / table | Purpose and constraints |
| --- | --- |
| Client / `clients` | Permanent master record: identity, demographic and location fields, health flags, optional photo reference, active/deceased state. Client number, national ID and passport are unique within a facility. |
| ClientContact / `client_contacts` | Next of kin, emergency, payer, authorised family, visitor and other contacts; relationship, contact details, active state and explicit contact authorisation. |
| ClientRevision / `client_revisions` | Historical registry snapshots with actor, timestamp and reason. Separate from the general audit log. |
| Referral / `referrals` | Client, referral source/date, referring person/organisation, reason, presenting problem, urgency, pre-admission notes and decision state. |
| Screening / `pre_admission_screenings` | Attributable clinical suitability record, risk levels, medical concerns, accommodation suitability, decision and mandatory reason. Multiple records preserve screening history. |
| Admission / `admissions` | Distinct numbered admission, referring record, timezone-aware date/time, admission type, programme/duration, assigned staff, rights/agreement acknowledgments, permission notes, requirements, allergies and risk flags. One open admission per client and one conversion per referral. |
| EpisodeOfCare / `episodes_of_care` | Separate care episode tied to the permanent client and admission. One episode per admission. |
| AdmissionStatusHistory / `admission_status_history` | Previous state, new state, reason and responsible actor for admission transitions. |
| Consent / `consents` | Separate decision for each consent type; text/version, grant or decline, date, expiry, witness, notes and withdrawal. Prior decisions remain available. |
| PropertyItem / `admission_property` | Belongings, valuables and prohibited items; quantity, storage, receipt/custodian, acknowledgment and one-time return. Positive quantity is constrained. |
| Wing / `wings` | Facility wing with unique facility name and active flag. |
| Room / `rooms` | Wing association, unique facility room name, optional sex restriction and active flag. |
| Bed / `beds` | Unique bed name within a room; constrained availability/occupancy status. |
| BedAssignment / `bed_assignments` | Admission-to-bed history with start/end and reason. Partial unique indexes enforce one current assignment per bed and admission. |
| IntakeDocument / `intake_documents` | Private client photo or referral PDF bytes, filename/type/size, category, version, confidentiality and upload attribution. Raw content is excluded from list metadata. |
| RecordNumber / `record_numbers` | Facility/kind/year counters. Facility-row locking serializes counter allocation, including first use. |
| ReferenceSeed / `reference_seeds` | Tracks applied domain reference seed versions without resetting institutional configuration. |

Business records carry UUID identifiers, facility association, creation/update timestamps and creator/updater fields. Numbers follow `ARS-YYYY-000001` and `ADM-YYYY-000001`. Searches, foreign keys and uniqueness use database indexes and constraints. Normal API operations do not delete these records.

## Migrations

Apply the complete linear migration chain with `alembic upgrade head` from `backend/`.

| Revision | Phase 2 contribution |
| --- | --- |
| `7e7f75ca5c6e` | Master registry, contacts, referrals, screening, admissions/episodes, consents/property, residential hierarchy/history and record counters. |
| `c109267ec439` | Private intake documents and client registry revisions. |
| `45ec2a926701` | Database history preservation: screening, status history, registry revisions and uploaded documents reject UPDATE/DELETE/TRUNCATE; mutable care tables reject destructive deletion/truncation. |

Intervening revisions implement Phases 3–5 and their references. Application startup does not create or alter tables. Database administrators remain responsible for controlling privileged schema access.

## Backend implementation

| Layer | Files and responsibilities |
| --- | --- |
| Models | `backend/app/models/clients.py`: registry/intake/residential entities and constraints. |
| Schemas | `backend/app/schemas/clients.py`: Pydantic v2 inputs, literal choices, lengths, date rules, suitability and search-policy validation; explicit mapped-column serialization. |
| Repository | `backend/app/repositories/clients.py`: facility-scoped listing, identifiers, transactional numbering, current-bed lookup and open-admission checks. Reuses `repositories/care.py` for scoped record/staff access. |
| Services | `backend/app/services/clients.py`: referral/admission state machines, consent replacement/withdrawal, custody, assignment and transfer. `services/intake_documents.py`: validated private uploads and versions. |
| Routes | `backend/app/api/v1/clients/routes.py` and `documents.py`: permission-specific HTTP endpoints, paginated lists, access audit and binary downloads. |
| Seed | `backend/app/seed_clients.py`: granular permission catalogue, integrated by the development seed/bootstrap flow. No real client records are seeded. |

Lists return `items` and `meta` (`page`, `page_size`, `total`). Major lists support server pagination, search, allowlisted sorting and date filters; workflow lists expose status filtering. The page size is bounded at 100. Validation errors use the shared structured error response. Sensitive note bodies and document content are kept out of the general audit event snapshots; historical client details remain in the permission-protected client revision table.

## Workflow rules

Referral sources cover self/family, clinical institutions, employer/school, legal agencies, NACADA, NGO, religious/community organisations and other sources. Screening records capture intoxication, withdrawal/suicide/self-harm/violence risk, psychosis, serious medical concerns, pregnancy, seizure/overdose history, medication, communicable disease concerns and suitability.

Only a suitable completed screening accepts a referral. Unsuitable accommodation/clinical suitability, critical risks, acute medical concerns or psychosis cannot be recorded as suitable. Evaluation/stabilization decisions defer the referral; external referral and decline produce their corresponding states. Every screening and manual state change requires a reason.

Admission requires this client's accepted referral, an active living client, no existing open admission and valid staff selections from the same facility. Referral conversion, admission creation, number allocation and episode creation occur in one transaction.

Activation of a pending residential admission requires rights acknowledgment, treatment agreement, a current granted Treatment consent and a bed. Current care states are Active, On Leave, Hospitalized, AWOL and Discharge Pending. Manual transitions cannot finalize Discharged, Transferred or Deceased: final discharge belongs to Phase 8. On-leave/hospitalized/AWOL residents retain their bed.

Consent types include Treatment, Medication, Information Sharing, Family Communication, Photography, Media, Research, Laboratory Testing, Telemedicine, Release of Medical Information and Other. A replacement decision cannot silently overwrite a current grant; withdraw it first. Grant/decline, consent text/version, witness, expiry and withdrawal remain distinct fields and actions.

Bed assignment locks the admission and affected beds, checks wing/room activity and room suitability, then records a current assignment. Transfers end the old assignment before creating the new one, preserve history and put the old bed into Cleaning. Occupied beds cannot be made available by directly changing their status. Pending admissions can release an assignment; current residents transfer beds or await the future final discharge workflow.

Property records retain receipt information and acknowledgment. Return is an attributable action requiring a reason and cannot be repeated.

## API and permissions

All paths below have the `/api/v1` prefix.

| Endpoint family | Operations / permission |
| --- | --- |
| `/clients`, `/clients/{id}` | List/detail: `client.view`; register: `client.create`; demographics update: `client.update`. |
| `/clients/{id}/contacts` | Read: `client.view`; create/update contacts: `client.update`. |
| `/clients/{id}/history` | Read registry revisions: `client.view`. |
| `/clients/{id}/photo` | Private photo upload: `client.update`. |
| `/referrals`, `/referrals/{id}` | Read: `referral.view`; create: `referral.create`; status action: `referral.update`. |
| `/referrals/{id}/screenings` | Read history: `screening.view`; complete screening: `screening.create`. |
| `/referrals/{id}/documents` | Read metadata: `referral.view`; attach PDF: `referral.create`. |
| `/admissions`, `/admissions/{id}` | Read: `admission.view`; create admission: `admission.create`; status action: `admission.update`. |
| `/admissions/{id}/assignments` | Assign/reassign care team: `admission.assign`. |
| `/admissions/{id}/history` | Read status history: `admission.view`. |
| `/admissions/{id}/consents`, `/consents/{id}/withdraw` | Read: `consent.view`; record decision: `consent.create`; withdraw: `consent.withdraw`. |
| `/admissions/{id}/property`, `/property/{id}/return` | Read inventory: `admission.view`; custody actions: `admission.property`. |
| `/residential/wings`, `/residential/rooms`, `/residential/beds` | Read: `residential.view`; create hierarchy/bed availability: `residential.manage`. |
| `/residential/occupancy` | Occupancy summary: `residential.view`. |
| `/admissions/{id}/bed`, `/admissions/{id}/bed/release` | Bed assignment/transfer/release: `residential.assign`. |
| `/admissions/{id}/bed-history` | Read assignment history: `residential.view`. |
| `/intake/staff` | Paginated active staff identifiers for assignment: `admission.view`. |
| `/intake/documents/{id}` | Download private photo/PDF: `client.view`, additionally `referral.view` for referral files. |

There are 19 Phase 2 permission codes. None is implied by ICT account-management access. Roles and explicit grants must be configured for institutional responsibilities. There is no unrestricted superuser shortcut.

## Frontend

| Route / page | Working interactions |
| --- | --- |
| `/clients` / `ClientsPage` | Search/register clients; grouped identity, location, health and optional/status fields; demographic updates with reason; registry history; contact registration/update; private photo upload/download; links to referral/admission history. |
| `/referrals` / `ReferralsPage` | Referral registration, status actions, structured screening, historical screenings and private PDF attachments. |
| `/admissions` / `AdmissionsPage` | Admission creation with programme/staff/rights/requirements groups; status, care-team and bed actions; tabs for consent, property, bed and status histories; admission links to later care modules. |
| `/residential` / `ResidentialPage` | Wings/rooms/beds tabs, creation, status filtering and permissible bed-availability actions. |

Shared `modules/care/ResourcePanel`, `RecordForm` and `HistoryPanel` provide tables, filters, paginated/searchable lookups, grouped fieldsets, loading/error/empty states, details and mutations. Field definitions live in `modules/care/fields.ts`; `validation.ts` builds Zod validation; React Hook Form handles form state. `types.ts` describes entities, form values, fields and actions. HTTP requests use the shared typed `api`/`save` client with cookies, CSRF and error handling. Backend validation remains authoritative. Permission checks hide unavailable actions and prevent denied resource requests.

## Verification evidence and limits

Automated coverage is in `backend/app/tests/test_care_workflows.py`, `test_care_safeguards.py` and `frontend/src/tests/care-workflows.test.tsx`. Intake scenarios cover registration/duplicates, accepted-referral admission, activation prerequisites, bed conflict/transfer history, private PDF/photo access, version history and denied ICT access. Related tests exercise valid consent/authorised-contact family communication and withdrawal. Frontend interaction tests cover creating a permanent client and submitting grouped admission data. These tests are not a full browser end-to-end suite. Consult the final verification record for executed commands and results.

Remaining limitations at the time of this review:

- Pending admission acknowledgments are recorded at creation. The current update API reassigns staff but does not amend rights/agreement flags or programme details; an admission created with missing acknowledgment cannot yet be corrected into an activatable record. A reasoned intake-amendment workflow is needed.
- `ClientUpdate.reason` currently allows more characters than the registry revision column. Reasons over 500 characters need a schema/column alignment before acceptance is complete.
- Intake file checks enforce size, extension, signature and a small PDF active-content denylist. They do not provide comprehensive PDF parsing, image decoding/re-encoding, malware scanning or external viewer safety. Files are authenticated, returned as attachments and use shared no-store/nosniff headers, but content-safety guarantees must remain limited.
- Contact authorisation and communication permission scope are institution-entered data. Consent text and communication notes do not form a normalized recipient-specific permission policy; staff must check the actual consent scope before disclosure.
- Ward/bed reservation is an availability state, with no named reservation owner or expiry workflow. Wing/room records can be created but do not yet have dedicated amendment/deactivation screens.
- Occupancy is available through the API; the residential page currently focuses on bed tables rather than a separate report/export. Its wing/admission display fields need API/UI alignment where those labels are absent from the response.
- Final discharge, cancellation/readmission decisions and episode closure are later-phase workflows. There are no final discharge controls in Phase 2.
- Uploaded documents are stored privately in PostgreSQL. Storage lifecycle, retention policy, backup/restore proof, antivirus integration and the broader document-management subsystem require operational and later-phase work.

## Manual acceptance checklist

Use synthetic records and separate staff accounts with narrow permissions. Unchecked items below are acceptance steps, not claims of completed browser verification.

- [ ] Register a client with required identity/date/sex fields; confirm an automatically allocated client number and retained master record.
- [ ] Reject future date of birth, duplicate national ID/passport and religion without both policy indication and consent.
- [ ] Update demographics with a reason; inspect the previous/new registry versions without copying personal narratives into the general audit log.
- [ ] Register next-of-kin/emergency contacts; update active/authorised status and verify the relationship and phone persist.
- [ ] Create each relevant referral source/urgency, then record a screening with all risk/medical/suitability fields and a reason.
- [ ] Reject suitable decisions with critical risk, acute medical/psychotic concerns or unsuitable accommodation; verify deferred/evaluation/external/declined paths preserve screening history.
- [ ] Upload a valid private referral PDF and client JPEG/PNG; verify metadata/version, correct download, size/type rejection and access audit.
- [ ] Deny cross-facility client/referral/document/admission/bed identifiers and deny ICT accounts without explicit care permissions.
- [ ] Create an admission from the selected client's accepted referral; verify a distinct admission number, conversion state and EpisodeOfCare.
- [ ] Reject duplicate open admissions, already-converted or other-client referrals, future dates and inactive/other-facility staff assignments.
- [ ] Attempt activation before consent/rights/agreement/bed; verify rejection. With prerequisites recorded, activate and inspect immutable status history.
- [ ] Record granted and declined decisions separately for applicable consent types; reject invalid expiry/future dates; withdraw a grant with a reason; preserve the original consent text/version.
- [ ] Receive belongings, valuables and prohibited items with quantity/storage/acknowledgment; return once with attribution; reject a second return.
- [ ] Create wing → room → beds; check room restrictions and reject inactive/unsuitable accommodation.
- [ ] Attempt competing assignments to one bed; confirm only one succeeds. Transfer a resident and verify old assignment end, old bed Cleaning, new bed Occupied and historical reason.
- [ ] Reject making an occupied bed Available directly; retain assignments during leave/hospitalization/AWOL.
- [ ] Verify client/referral/admission/bed list search, pagination, sort and date/status filters across multiple pages.
- [ ] Review forms/tables at phone and tablet widths, keyboard-only navigation, labels, inline errors and denied-action visibility.
- [ ] Resolve the review limitations above, then run the integrated PostgreSQL suite, frontend interaction suite, build, migration/schema checks and browser workflow acceptance before real institutional use.


## Integrated review corrections

Pending intake acknowledgments and requirements can be amended through `PUT /admissions/{id}/intake`; the original and amended snapshots remain in `admission_intake_revisions` and can be read at `/admissions/{id}/intake/history`. Current admissions retain their required acknowledgments. Operational reasons are bounded to the audit/revision column lengths. Bed rows include wing, room and admission identifiers. Private uploads use structural PDF parsing and decoded/re-encoded image validation, not only signatures. Clinical account lifecycle changes preserve privileges without giving ICT permission to read the records.
