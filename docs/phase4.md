# Phase 4: Clinical, nursing and investigations

Phase 4 implements specification sections 24, 25, 29 and 30. It builds on the permanent client registry and admission episodes from Phase 2, and uses Phase 1 authentication, facility boundaries, database permissions, CSRF protection and request transactions. Medication rounds are provided by Phase 5.

## Architecture and implementation map

| Layer | Location | Responsibility |
| --- | --- | --- |
| Models | `backend/app/models/clinical.py` | UUID records, admission/client links, responsible staff, note revisions, laboratory results and private PDF bytes. |
| Schemas | `backend/app/schemas/clinical.py` | Typed inputs, bounded narratives, timezone-aware timestamps, vital-sign ranges, allowed states and duplicate substance validation. |
| Repository | `backend/app/repositories/clinical.py` | Facility-scoped care access, ordered revision/result history and attachment metadata projection. |
| Shared repository | `backend/app/repositories/care.py` | Current-admission write checks, historical admission reads, active same-facility staff validation and pagination. |
| Services | `backend/app/services/clinical.py` | Attribution, initial snapshots, optimistic correction versions, allergy synchronization, order completion, laboratory review, PDF validation and nursing worklists. |
| Router | `backend/app/api/v1/clinical/routes.py` | Distinct clinical, nursing and laboratory permission checks, metadata-only audit events and authenticated PDF download. |
| Frontend | `frontend/src/modules/clinical/` | Clinical care, laboratory and toxicology workspaces and domain form definitions. |
| Nursing frontend | `frontend/src/modules/nursing/NursingPage.tsx` | Notes, observation history, escalation, handover and nursing summary. |
| Shared frontend | `frontend/src/modules/care/` | Admission context, typed Bootstrap forms, React Hook Form, Zod, query caching, pagination, record details and revision history. |

The Phase 4 schema migration is `d0846c43e92e_phase_4_clinical_nursing_and_.py`, following the Phase 3 migration. `45ec2a926701_preserve_care_history.py` adds PostgreSQL triggers that reject deletion and truncation of care records, and also reject updates to immutable history tables. Normal writes use the existing database transaction dependency, so domain changes and their audit events commit together.

## Records and workflows

| Record | Scope and behavior |
| --- | --- |
| `clinical_encounters` | Admission-linked encounters with responsible clinician, presentation, medical history, examination, diagnosis, assessment, plan, follow-up and emergency response. Emergency encounters require documented action. |
| `clinical_note_revisions` | Full snapshots for encounters and nursing notes. The initial record is version 1; corrections append a new version and reason. Unique entity/version constraints and a locked source record prevent duplicate versions. |
| `clinical_problems` | Permanent client problem list, optional admission link, diagnosis/code/onset and active/resolved status with resolution and responsible editor. |
| `clinical_allergies` | Permanent client allergen, reaction, severity and status. Active substances synchronize with `Client.allergies` for prescribing review. Inactive or erroneous entries retain their history. |
| `clinical_vitals` | Timestamped blood pressure, pulse, respiration, temperature, oxygen saturation, weight, height, glucose and pain. At least one measurement is required; blood pressure requires both values and systolic greater than diastolic. |
| `clinical_orders` | Medical, investigation, referral, follow-up and observation orders with priority, destination, due time, completion/cancellation reason and completion note. Closed orders cannot be closed again. |
| `nursing_notes` | Timestamped assessments and notes attributed to their author, with shift, interventions, escalation recipient, high-risk flag and observation due time. Corrections use the shared revision mechanism. |
| `nursing_observations` | Historical sleep, appetite, mood, hygiene, withdrawal symptoms/score, pain, interventions, escalation and next observation time. Observations remain immutable. |
| `nursing_handovers` | Shift/date summary, outstanding tasks, priority and optional resident context. A receiving staff member acknowledges an item once; actor and time are retained. |
| `clinical_lab_requests` | External or internal provider, investigation, indication, specimen type/date and priority. The module does not require an in-house laboratory. |
| `clinical_lab_results` | Result text, units, reference range, abnormal flag and clinician review. Result corrections append a new result with a reason; previous results remain available. Review targets the current result and cannot be repeated on the same result. |
| `clinical_lab_attachments` | Private database-held PDF bytes, safe filename, size and SHA-256, linked to an investigation. List responses contain metadata only. |
| `clinical_toxicology_tests` | Admission/client, time, reason, sample type, per-substance result/concentration, confirmatory test/result, testing staff, acknowledgement and follow-up. Duplicate substance names in a test are rejected. |

New admission-linked care requires status `ACTIVE`, `ON_LEAVE`, `HOSPITALIZED`, `AWOL` or `DISCHARGE_PENDING`. Historical records can be read. New encounter, note, observation and toxicology times must fall after admission and cannot be future dated. Input timestamps require an explicit timezone. The frontend enters and displays care times in Africa/Nairobi.

Clinical/nursing corrections retain the original record, author and snapshot. A correction includes `expected_version`; an outdated edit returns HTTP 409 and requires reloading. Corrections may retain historical admission context without reopening that admission. The latest snapshot is used for normal list/detail rendering; the history panel exposes all snapshots, actors, times and reasons to permitted readers.

## Permissions and routes

Permissions are checked on the server from current database grants. Frontend action visibility uses the same permission codes. ICT administration has no implicit clinical access.

| Permission | Actions |
| --- | --- |
| `clinical.view` | Read encounters, problem list, allergies, vitals and orders; read encounter revisions. |
| `clinical.create_note` | Create/correct encounters, record problems/allergies and change problem/allergy status. Responsible clinicians must also hold this permission. |
| `clinical.record_vitals` | Record vital signs; granted to clinical officers/medical officers and nurses by the care role supplements. |
| `clinical.manage_orders` | Create/close medical orders and review the latest laboratory result. |
| `nursing.view` | Read nursing notes, observations, handover and dashboard; read nursing revisions. |
| `nursing.record` | Record/correct nursing notes, record observations and create/acknowledge handover. |
| `lab.view` | Read laboratory requests/results, toxicology and trend history; download private laboratory PDFs. |
| `lab.order` | Request investigations. |
| `lab.result` | Record/correct investigation results, attach external PDFs and record toxicology tests. |

All paths below are relative to `/api/v1`.

| Paths | Operations |
| --- | --- |
| `/clinical/encounters` | GET paginated records; POST encounter. |
| `/clinical/encounters/{id}/revisions` | GET revision history; POST correction with expected version and reason. |
| `/clinical/problems`, `/clinical/allergies` | GET/POST; PATCH `/{id}` for audited status changes. |
| `/clinical/vitals` | GET/POST. |
| `/clinical/orders` | GET/POST; PATCH `/{id}` to complete or cancel. |
| `/nursing/notes` | GET/POST; GET/POST `/{id}/revisions`. |
| `/nursing/observations` | GET/POST. |
| `/nursing/handovers` | GET/POST; POST `/{id}/acknowledge`. |
| `/nursing/dashboard` | GET paginated current-resident context and derived worklists. |
| `/lab/requests` | GET/POST; POST `/{id}/results`; POST `/{id}/attachments`. |
| `/lab/results/{id}/review` | POST clinician review of the current result. |
| `/lab/attachments/{id}` | GET permission-checked private PDF download. |
| `/toxicology/tests` | GET/POST; filter by `client_id` for history across admission episodes. |
| `/toxicology/trends` | GET paginated per-substance result history for an `admission_id`. |
| `/care/options` | GET searched, paginated admission context and active staff choices; resolves a selected historical admission by ID. |

List responses use `{items, meta: {page, page_size, total}}`. Admission/client filters are validated within the actor's facility. Unauthorized permissions return HTTP 403; inaccessible IDs return HTTP 404. Dates and sort options use shared care pagination validation. Sensitive list/history/download events log access metadata without copying clinical narratives into audit snapshots.

## Frontend behavior

The pages are `/clinical`, `/nursing`, `/laboratory` and `/toxicology`. Each uses the established restrained Bootstrap design, labelled controls, inline creation/action forms, paginated tables, readable record details, and explicit loading/error/empty/success states. The admission is shareable through `?admission_id=...`; staff use client/admission labels rather than entering UUIDs. Client-wide problem/allergy tabs inherit the client from the selected episode.

Clinical encounters and nursing notes show correction actions and expandable revision history. Laboratory actions record a result, review the latest result, attach a file and download its private PDF. Toxicology captures a repeating list of substances with one result per substance. Historical observations/vitals are available as tables; these measurements are not interpreted automatically.

The nursing API derives high-risk, observations due, newly admitted and outside-facility lists from the resident page. Outside-facility statuses are leave, hospitalization and AWOL. Explicit nursing flags and active structured High/Critical risk assessments drive its high-risk indication. Unclassified intake flags remain available in the admission record. The medication link opens Phase 5 rounds. Facility-wide resident total is separate from page-derived worklists; those lists must not be interpreted as facility-wide totals.

## Private PDF handling

An attachment uses JSON base64 transport and a 5 MB decoded size limit. Filenames allow a bounded set of characters and a `.pdf` suffix. The shared file validator parses PDF structure, bounds file/page/object sizes, rejects encryption, active actions and embedded files, and the service computes a hash. Content stays inside the facility-scoped database record; no filesystem paths or public URLs are returned. Downloads require `lab.view`, create an access audit event, use attachment disposition and send a sandbox content-security policy.

This is bounded private document storage and structural/action validation. It does not provide antivirus scanning or integration with an external document-verification service. Provider values, reference ranges and abnormal flags are recorded by authorized staff, not inferred by an analyzer or automated clinical rules engine.

## Validation and manual acceptance checklist

Integration coverage is in `backend/app/tests/test_care_workflows.py` and `backend/app/tests/test_care_safeguards.py`, including encounter revision preservation, invalid/valid vitals, external laboratory result/review, nursing observation/handover, toxicology, database history protection, facility boundaries and audit payload confidentiality. Execution results belong in `docs/verification.md`; this document does not assert that the checklist below has been performed.

- [ ] Sign in as a permitted clinician. Select an active admission by name/number, save an encounter and confirm clinician/time/client/admission attribution.
- [ ] Record an emergency encounter without response details and confirm validation prevents saving; add the emergency response and save.
- [ ] Correct an encounter with a reason. Confirm version 1 is readable and unchanged, and the ordinary record shows version 2. Submit the old expected version again and confirm HTTP 409.
- [ ] Confirm a clinician and a nurse can record vitals using their assigned permission. Reject an empty set, a missing blood-pressure pair, invalid SpO2 and pain outside 0–10.
- [ ] Record a problem and mark it resolved with a reason. Confirm its original diagnosis remains and resolution metadata is shown.
- [ ] Record an allergy. Confirm it appears in the client record and prescribing review; deactivate it with a reason and confirm history is retained.
- [ ] As a nurse, record an assessment, interventions and escalation. Correct the note and inspect both versions and authors.
- [ ] Record sleep/appetite/mood/hygiene/withdrawal/pain observations. Confirm history retains each observation and next-due time updates the worklist.
- [ ] Create a shift handover with outstanding tasks; acknowledge it as the receiving user and confirm a second acknowledgement is rejected.
- [ ] Verify the nursing resident total and page-scoped worklists with more than one page of synthetic residents, including leave/hospital/AWOL statuses and a newly admitted resident.
- [ ] Request an external investigation, record specimen/result/reference range/flag and perform clinician review. Append a corrected result with a reason and confirm the earlier result remains visible.
- [ ] Upload a small PDF and download it as an authorized user. Reject malformed base64, non-PDF content, unsafe filenames, recognized active-content markers and a decoded file above 5 MB.
- [ ] Attempt attachment access and clinical record access using an ICT-only account and another-facility user; confirm denial without exposing content.
- [ ] Record a multi-substance toxicology test with acknowledgement and follow-up. Reject duplicate substances and inspect historical tests by admission and permanent client.
- [ ] Confirm closed admissions reject new care records while previous records and correction history remain readable.
- [ ] Inspect audit metadata for creation, correction, result review and sensitive reads; confirm full notes/results are absent.
- [ ] Inspect mobile/tablet views, keyboard focus, form errors and responsive tables.
- [ ] Open medication rounds from nursing and confirm real Phase 5 due medication data is available to appropriately permitted nurses.

## Scope boundaries

Incident management is scheduled for Phase 7. The dashboard reports incident integration as unavailable instead of inventing a count. Laboratory integration is manual and accommodates external providers. Clinical vitals, observations, toxicology and note histories are permanent records; specialized chart visualization, analyzer connectivity and automated clinical interpretation are not part of this implementation. The dedicated trend endpoint is admission-scoped; permanent-client history is available through the toxicology list's client filter.
