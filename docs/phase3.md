# Phase 3: Assessments and rehabilitation

Phase 3 adds admission-linked assessment, rehabilitation, treatment planning, case coordination and family intervention workflows. The permanent client record remains in Phase 2; every care record identifies the admission to which it belongs.

## Architecture and files

The request path is `FastAPI router → RehabilitationService → RehabilitationRepository → PostgreSQL`. The repository extends the shared `CareRepository` for facility-scoped clients, admissions and staff. The service performs scoring, state validation, revision checks, consent checks and safe audit recording. Writes use the request transaction supplied by `get_db`.

| Layer | File |
| --- | --- |
| Database models | `backend/app/models/rehabilitation.py` |
| Assessment reference catalogue | `backend/app/models/assessment_types.py` |
| Authoritative input schemas | `backend/app/schemas/rehabilitation.py` |
| Repository | `backend/app/repositories/rehabilitation.py` |
| Domain service | `backend/app/services/rehabilitation.py` |
| Versioned API | `backend/app/api/v1/rehabilitation/routes.py` |
| Seed data and role supplements | `backend/app/seed_care.py` |
| Assessment workspace | `frontend/src/modules/assessments/AssessmentsPage.tsx` |
| Structured scoring and trends | `frontend/src/modules/assessments/ScorePanel.tsx` |
| Assessment field definitions | `frontend/src/modules/assessments/resources.ts` |
| Rehabilitation workspace | `frontend/src/modules/rehabilitation/RehabilitationPage.tsx` |
| Rehabilitation field definitions | `frontend/src/modules/rehabilitation/resources.ts` |
| Shared care components and types | `frontend/src/modules/care/` |

## Database entities

Care entities use UUID primary keys, facility foreign keys, timestamps and actor attribution. Records belonging to residents also reference `admissions.id`. Instruments and substances are facility-specific; the assessment type catalogue contains common reference names.

| Entity / table | Purpose |
| --- | --- |
| `Substance` / `rehab_substances` | Configurable substance catalogue, initially 15 substances |
| `SubstanceHistory` / `substance_histories` | Per-substance use ages, frequency, quantity, route, duration, last use, pattern, withdrawal, tolerance, overdose, abstinence, treatment and consequences |
| `AssessmentType` / `assessment_types` | Nine common assessment names and implementation purpose |
| `AssessmentInstrument` / `assessment_instruments` | Immutable question, option, scoring and interpretation configuration by code and version |
| `InstrumentAssessment` / `instrument_assessments` | Answers, calculated total/domain scores, interpretation, risk level, completion time and staff |
| `BiopsychosocialAssessment` / `biopsychosocial_assessments` | Biological, psychological, social, substance, legal, occupational and optional spiritual sections |
| `RiskAssessment` / `risk_assessments` | Structured risk type, level, factors, protective factors, intervention, assigned staff, review date and status |
| `TreatmentPlan` / `treatment_plans` | Versioned problems, goals, measurable objectives, interventions, responsibility, dates, outcome and state |
| `CaseAssignment` / `case_assignments` | Case manager, counsellor, multidisciplinary team and assessment/family/discharge preparation due dates |
| `TherapySession` / `therapy_sessions` | Attributable individual/family/other therapy records, scheduling, progress, interventions and restricted psychotherapy classification |
| `GroupSession` / `group_sessions` | Group title, topic, type, facilitators, time, duration, location and objectives |
| `GroupAttendance` / `group_attendances` | Participant attendance and separately permission-protected private observations |
| `ProgrammeActivity` / `programme_activities` | One-off, daily and weekly activities with programme, location and facilitator |
| `ProgrammeAttendance` / `programme_attendances` | Per-admission attendance for a specific activity occurrence |
| `FamilyCommunication` / `family_communications` | Consent-linked contact, method, purpose, shared information, outcome and next meeting |

Migration `4947cd5f55ab_phase_3_assessments_treatment_and_.py` introduces the rehabilitation tables after Phase 2. Migration `12af82d0ece9_assessment_type_reference_catalogue.py` adds the common assessment type catalogue. Migration `45ec2a926701_preserve_care_history.py` adds PostgreSQL triggers preventing update, deletion or truncation of immutable clinical histories and preventing deletion/truncation of retained operational records. Apply the full migration chain through `alembic upgrade head`.

Foreign keys link instruments, substances, sessions, attendance, contacts and consents to their corresponding records. Unique `supersedes_id` constraints prevent two revisions from replacing the same record. The service locks records being revised and rejects stale revision requests.

## Assessment engine and validation

`InstrumentIn` accepts questions with unique keys, explicit response values, numerical scores, optional score domains and optional alert answers. Questions can be excluded from calculated scores while remaining required in the completed assessment. Total and domain score bands must cover the possible score range without gaps or overlaps. Unknown answers, unanswered questions and extra question keys are rejected. Calculated results come from the server.

Every instrument change creates a new version. A completed assessment keeps its original instrument foreign key, so later configuration changes preserve its answers and calculation basis. Scoring completion records identify the completing user. A configured alert answer raises the assessment risk to at least High; High/Critical calculated results create a safe audit alert event.

The seed catalogue contains AUDIT, ASSIST, CAGE, DAST, PHQ-9, GAD-7, suicide-risk, withdrawal and relapse-risk assessment names. Institution-approved questions, response options, scoring rules and interpretations must be entered by a user holding `assessment.configure` before an instrument can be completed. Seed names do not constitute clinically validated instrument implementations. No real client data or invented clinical threshold templates are seeded.

The remaining Pydantic schemas enforce bounded narrative fields, valid enumerated values, UUID relationships and explicit revision reasons. Substance ages are ordered and checked against the client age. Biopsychosocial assessments require all six core sections for completion; review follows completion. Treatment plans enforce start/review/target chronology and measurable objective dates. Completed plans require an outcome and completed objectives. Therapy sessions require an end after the start, completed-session summary/intervention and a subsequent next-session time.

## History, case worklists and privacy

Substance histories, biopsychosocial records, risks, plans, case assignments, therapy sessions and attendance use append-only revisions. Submit a new record containing `supersedes_id` and `correction_reason`. The default list shows current records; `current_only=false` includes retained versions. Treatment plan `root_id` identifies the plan lineage and `version` increases on each revision. Completed/cancelled plans are terminal. No clinical delete API is provided.

An assignment updates the admission's primary case manager and assigned counsellor while preserving the preceding assignment record. The assigned-caseload endpoint lists the current user's cases, overdue assessment dates, treatment reviews, missed sessions, upcoming scheduled sessions, active risks, family meeting dates and discharge preparation dates. Risk/plan/session information is included only when the user holds its corresponding read permission. Aftercare integration remains a Phase 8 responsibility; the endpoint explicitly reports `aftercare_available=false`.

General therapy reads require `therapy.view`. Confidential sessions additionally require `psychotherapy.view`; unauthorized list queries exclude confidential rows before pagination, and direct access is refused. Creating restricted notes additionally requires `psychotherapy.create_note`. A confidential record cannot be revised into a general note. Group participant observations are omitted from responses without `psychotherapy.view`; adding them requires the restricted note permission.

Family communication requires a granted `FAMILY_COMMUNICATION` consent for the same client/admission, valid consent dates, no withdrawal, a current authorized contact and explicit staff confirmation that sharing remains within the consent scope. The server validates these relationships and dates. The scope itself is recorded as consent text and admission communication instructions; the staff confirmation is necessary because scope is not a machine-readable list of permitted information categories. The workflow records communication that occurred; it does not send email, messages or calls.

All reads and major writes are audited. Audit payloads contain identifiers, classification/state or version information; assessment answers and therapy narratives are not copied into the audit stream. Facility scope and granular permissions are enforced on the server, independently of visible UI actions. ICT administration grants no automatic access to these care records.

## API and permissions

All paths below are beneath `/api/v1/rehabilitation`. Resource endpoints support `GET` lists, `GET /{record_id}` and `POST` creation. Revisions also use `POST`; there are no destructive update/delete endpoints for clinical histories.

| Resource | Read permission | Create/revise permission |
| --- | --- | --- |
| `/substances` | `assessment.view` | `assessment.configure` |
| `/substance-histories` | `assessment.view` | `assessment.record` |
| `/instruments` | `assessment.view` | `assessment.configure` |
| `/scores` | `assessment.view` | `assessment.record` |
| `/biopsychosocial` | `assessment.view` | `assessment.record` |
| `/risks` | `risk.view` | `risk.record` |
| `/treatment-plans` | `treatment_plan.view` | `treatment_plan.manage` |
| `/cases` | `case_management.view` | `treatment_plan.manage` |
| `/sessions` | `therapy.view` and restricted access where applicable | `therapy.create_note` and restricted access where applicable |
| `/groups` | `therapy.view` | `therapy.create_note` |
| `/programme` | `programme.view` | `programme.manage` |
| `/family-communications` | `family.view` | `family.record` |

Additional endpoints:

- `GET /assessment-types`: common assessment type names (`assessment.view`).
- `GET /score-trends`: historical scores for an admission, optionally filtered by instrument (`assessment.view`).
- `GET /risk-alerts`: current active High/Critical risk assessments (`risk.view`).
- `GET /case-dashboard`: the current user's assigned caseload (`case_management.view`).
- `GET /programme/schedule?from_date=...&to_date=...`: expanded scheduled occurrences, with a maximum 93-day period (`programme.view`).
- `GET/POST /groups/{record_id}/attendance`: group participants; read uses `therapy.view`, write uses `therapy.create_note`, and private observations have the additional psychotherapy permissions.
- `GET/POST /programme/{record_id}/attendance`: occurrence attendance using `programme.view`/`programme.manage`.

List endpoints return `{items, meta: {page, page_size, total}}`. Supported query parameters include `page`, `page_size` (maximum 100), `q`, `sort`, `direction`, `start`, `end`, `status`, `admission_id` and `current_only`. Date filters use Nairobi calendar boundaries. Search targets record labels/types rather than confidential narrative content. The schedule response paginates source activities before expansion and reports source activity totals.

The care seed adds appropriate permissions to Counsellor, Psychologist, Psychiatrist, clinical and social-work roles through an explicit, version-marked reference update. Psychotherapy permission remains restricted to the relevant professional roles. Existing administrative roles are not implicitly elevated into clinical readers.

## Frontend workflow

The `/assessments` workspace contains admission selection, structured instrument completion, score history/trends, substance histories, grouped biopsychosocial forms, risk assessment, High/Critical risk lists and instrument configuration. Instrument questions, options and bands use repeatable typed fields instead of raw JSON entry.

The `/rehabilitation` workspace contains treatment plans with repeatable measurable objectives, counselling records, case assignments, assigned caseload, groups/participant attendance, recurring programme activities/attendance and family intervention. The shared care components provide responsive Bootstrap tables, search/date/sort controls, pagination, record details, sectioned forms and permission-aware actions. React Hook Form and Zod provide frontend validation; server validation remains authoritative. API requests use the shared cookie/CSRF-aware `api` and `save` functions, with TanStack Query for server state and invalidation after writes.

## Automated checks

Phase 3 integration checks are in `backend/app/tests/test_care_workflows.py` and `backend/app/tests/test_care_safeguards.py`. They cover synthetic instrument scoring and invalid answers, treatment revision preservation, confidential session filtering/direct-access rejection, consent withdrawal, authorized contacts, group private observation redaction and programme attendance. Shared tests cover facility isolation, retained clinical history and administrative permission separation.

Use the dedicated PostgreSQL test database described in the root README. From `backend`, run `python -m pytest app/tests/test_care_workflows.py app/tests/test_care_safeguards.py`. Frontend verification uses the existing `npm test -- --run` and `npm run build` commands. Results and any outstanding validation are recorded in the project verification document; this architecture document does not imply that its manual checklist has been executed.

## Manual testing checklist

Use synthetic clients and an active admission. Test with a Counsellor account, a Psychologist/Psychiatrist account holding restricted note permissions, an ICT administrator and a staff account at another facility.

- [ ] Confirm ICT users receive authorization errors for direct assessment/therapy APIs and cannot access confidential care through the navigation or global search.
- [ ] Search/select a synthetic admission and confirm the same permanent client remains distinct from the selected admission.
- [ ] Record histories for at least two substances with different patterns; revise one and verify the preceding history remains retrievable.
- [ ] Reject reversed use ages, future last-use dates and ages exceeding the client's age.
- [ ] Configure a synthetic instrument with two questions, score options and contiguous bands; reject duplicate keys, invalid alert values, gaps and overlapping score bands.
- [ ] Complete the instrument, compare the calculated score with the configured options and verify staff/time attribution; reject missing and unknown answers.
- [ ] Create a new instrument version and verify previous assessments remain linked to the original configuration. Inspect trend labels/filtering when scoring scales differ between versions.
- [ ] Save a biopsychosocial draft, complete its six core sections, then review through a reasoned revision; confirm the preceding versions remain available.
- [ ] Record an active High/Critical risk and verify it appears in the risk-alert list; revise it to Resolved and confirm it leaves the active alert list while history remains.
- [ ] Create an Active treatment plan with a measurable objective and responsible professional; revise it to Under Review and verify increased version/history.
- [ ] Reject inconsistent plan dates and completion without completed objectives/outcome; verify terminal plan states cannot be arbitrarily reopened.
- [ ] Assign case manager/counsellor/team, set an overdue assessment and upcoming review/family dates, and confirm the assigned worklist uses the current user.
- [ ] Record and revise an individual session with summary, intervention, progress and next appointment; verify its complete record remains available.
- [ ] Create a restricted psychotherapy note. Confirm a general Counsellor can neither list/read it nor reclassify it; confirm the restricted professional can read it.
- [ ] Create a group and mark synthetic participants Present, Absent, Excused, Refused or Late. Verify duplicate attendance requires a reasoned revision.
- [ ] Add a private participant observation with the restricted permission and verify its text is omitted from ordinary therapy responses.
- [ ] Create daily and weekly activities; inspect scheduled occurrences and record attendance on valid occurrences. Reject invalid occurrence dates, future attendance and mismatched programmes.
- [ ] Create an authorized family contact and granted family communication consent; record a scope-confirmed communication. Reject unrelated contacts, wrong consent types, unconfirmed scope, expiry and withdrawal.
- [ ] Inspect audit entries after sensitive reads/writes and confirm record references/actors exist without copied clinical narratives.
- [ ] Confirm another facility's identifiers return no accessible care records and cannot be supplied as staff, client, consent or session references.
- [ ] Check desktop/tablet/mobile layouts, labelled controls, keyboard focus, empty/error states, pagination and sectioned long forms.
- [ ] Verify clinical revisions survive restart and PostgreSQL prevents destructive mutation/deletion of retained histories.

## Boundaries for later phases

Discharge execution, aftercare follow-ups and recovery monitoring belong to Phase 8. Cross-domain management reports, CSV/PDF export and quality analytics belong to Phase 10. Phase 3 provides record-linked due dates, worklists, scores, risk lists and attendance history on which those modules can build.


## Integrated review corrections

Family communication locks the consent and authorised contact while validating and recording the event. Scores cannot precede admission; group attendance cannot precede admission or be recorded for a future group; completed sessions cannot be in the future. Staff assignments check relevant care permissions. Score trends filter by the selected instrument version so different scoring configurations are not presented as one comparable series. The assigned-case dashboard also includes admissions assigned during intake when a structured case profile has not yet been created, and flags that setup requirement. Daily/weekly programme schedules and attendance history are available in the workspace. Aftercare-specific follow-ups remain deferred to Phase 8.
