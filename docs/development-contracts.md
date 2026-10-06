# Concurrent Phases 2–5 integration contracts

Each module owns its models, schemas, repository/service, routers, UI and tests. Shared registrations, permissions, migrations and global documentation are coordinated centrally.

- `app.models.clients.Client` is the permanent person record, table `clients`, with UUID `id`, `facility_id`, `client_number`, `first_name`, `middle_name`, `surname`, `date_of_birth` and `allergies`.
- `app.models.clients.Admission` is an episode admission, table `admissions`, with UUID `id`, `facility_id`, `client_id`, human `admission_number`, uppercase string `status`, timezone-aware `admission_date`, `programme` and optional responsible staff UUIDs.
- Care records link to admission and retain historical records. New care writes require a current admission, read access permits historical admissions.
- `CareRepository(db, actor)` provides scoped `require`, `client`, `admission`, `staff` and `page` helpers. All domain tables passed to `page` have `facility_id` and record timestamps.
- `GET /admissions` returns paginated admission records. Frontend pages use `admission_id` in URL query parameters so contextual navigation is shareable.
- New module routes mount under `/api/v1`, use current database permissions, CSRF-protected writes and a request transaction. No clinical grant is implicitly assigned to ICT administrators.
- Clinical audit payloads contain record IDs, changed field names and revision/status metadata, never the full confidential note.
- Schema ownership: Phase 2 client/intake/residential, Phase 3 rehabilitation, Phase 4 clinical/nursing/lab, Phase 5 medication/pharmacy. Migration history follows that dependency order even though implementation proceeds concurrently.
- Integration tests run serially against the dedicated test database. `clinical_client` is a synthetic test fixture with explicit domain permissions, not an administrative role bypass.
