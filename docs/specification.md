Build a complete, production-oriented Rehabilitation Management System for a Kenyan residential alcohol and substance-use rehabilitation institution.

The system should be designed specifically for rehabilitation workflows, not as a generic hospital management system.

The application must support the complete client journey:

Referral → Screening → Admission → Assessment → Clinical Care → Treatment Planning → Counselling and Rehabilitation → Nursing and Medication → Progress Review → Family Intervention → Discharge Planning → Discharge → Aftercare → Recovery Monitoring → Readmission where applicable.

The system must be modular, auditable, secure, responsive, maintainable, and designed for future expansion.

## 1. Mandatory Technology Stack

Use the following stack only for the main application:

### Backend
- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- PostgreSQL
- PostgreSQL UUID primary keys where appropriate
- REST API architecture
- JWT-based authentication using secure HTTP-only cookies where appropriate
- Argon2 or bcrypt password hashing
- Pytest for backend testing

### Frontend
- React
- TypeScript
- Vite
- React Router
- Bootstrap 5
- React Bootstrap where useful
- Axios or a well-structured native fetch service
- React Hook Form
- Zod for frontend validation
- TanStack Query for server state where appropriate

### Database
- PostgreSQL

### Deployment readiness
Structure the application so it can later be deployed using:
- Docker
- Docker Compose
- Nginx
- Linux server or cloud VM

Do not tightly couple the application to a specific cloud provider.

---

# 2. Design Philosophy

The system must look like a serious healthcare and institutional management platform.

Avoid AI-generated-looking design trends.

Do not use:

- Emojis
- Gradients
- Glassmorphism
- Excessive rounded cards
- Floating decorative shapes
- Neon colours
- Random illustrations
- Cartoon icons
- AI-generated artwork
- Oversized marketing-style headings
- Excessive shadows
- Excessive animations
- Decorative blobs
- Unnecessary motion effects
- Consumer-app styling
- Overly playful UI

Use:

- Clean Bootstrap layouts
- White, light grey, navy, dark blue, muted green, charcoal and restrained clinical colours
- Standard Bootstrap cards
- Clear tables
- Strong form hierarchy
- Professional typography
- Bootstrap Icons or another consistent professional icon library
- Clearly separated modules
- Responsive navigation
- Consistent spacing
- Accessible contrast
- Strong information hierarchy
- Institutional dashboard design

The visual language should resemble a professional hospital, clinic, ERP, EMR, or government institutional information system.

---

# 3. Application Name

Use a configurable system name.

Default:

ARS Rehabilitation Management System

Short name:

ARS RMS

The system name, institution logo, institution details and contact information should be configurable through Administration Settings.

---

# 4. Core Architectural Principles

Use a modular architecture.

Backend modules should be separated by business domain.

Suggested backend structure:

```text
backend/
    app/
        main.py
        core/
            config.py
            database.py
            security.py
            permissions.py
            exceptions.py
            logging.py

        models/
        schemas/
        services/
        repositories/
        api/
            v1/
                auth/
                users/
                clients/
                referrals/
                admissions/
                assessments/
                rehabilitation/
                clinical/
                nursing/
                medication/
                pharmacy/
                billing/
                inventory/
                residential/
                discharge/
                aftercare/
                incidents/
                compliance/
                reports/
                administration/

        audit/
        tests/
```

Frontend structure:

```text
frontend/
    src/
        api/
        auth/
        components/
        layouts/
        modules/
            dashboard/
            clients/
            referrals/
            admissions/
            assessments/
            rehabilitation/
            clinical/
            nursing/
            medication/
            pharmacy/
            billing/
            residential/
            inventory/
            discharge/
            aftercare/
            incidents/
            compliance/
            reports/
            administration/

        routes/
        hooks/
        types/
        schemas/
        utils/
        pages/
```

Do not place all backend logic inside route files.

Use:

Router → Service → Repository → Database

where appropriate.

---

# 5. Database Design Rules

Use PostgreSQL properly.

Use:

- UUID primary keys
- created_at
- updated_at
- created_by
- updated_by where appropriate
- soft deletion where business records must not disappear
- foreign keys
- indexes
- unique constraints
- check constraints where appropriate
- transaction-safe operations
- explicit enum strategy
- normalized database design

Do not physically delete:

- clinical notes
- medication administration records
- prescriptions
- financial transactions
- incidents
- consent records
- audit records
- discharge records

Where corrections are necessary, maintain the previous value or revision history.

---

# 6. Critical Domain Concept

Do not treat a person and an admission as the same object.

Create distinct entities such as:

- Client
- Referral
- Admission
- EpisodeOfCare
- BedAssignment
- TreatmentPlan
- Discharge
- AftercareCase
- Readmission

A single client may have multiple admissions over several years.

The client must retain one permanent Master Client Record.

---

# 7. Authentication and Security

Implement secure authentication.

Requirements:

- Login
- Logout
- Refresh token handling
- Password reset workflow
- Account activation/deactivation
- Force password change
- Failed login tracking
- Account lockout
- Session timeout
- Last login
- Optional future MFA architecture

Do not store plain-text passwords.

Use secure password hashing.

---

# 8. Role-Based Access Control

Implement granular RBAC.

Users may have:

- One or more roles
- Explicit permissions
- Department assignment
- Facility assignment if future multi-facility support is added

Initial roles:

- Super Administrator
- System Administrator
- Facility Administrator
- Medical Officer
- Clinical Officer
- Nurse
- Counsellor
- Psychologist
- Psychiatrist
- Social Worker
- Pharmacy Officer
- Finance Officer
- Receptionist
- Stores Officer
- HR Officer
- Management
- Auditor
- Read Only User

Permissions should follow:

resource.action

Examples:

```text
client.view
client.create
client.update

clinical.view
clinical.create_note

therapy.view
therapy.create_note

medication.prescribe
medication.administer

billing.view
billing.create_invoice

reports.financial
reports.clinical

users.manage
roles.manage
audit.view
```

The ICT administrator must not automatically have permission to read confidential psychotherapy records simply because they administer the system.

---

# 9. Audit Trail

Build auditing from the beginning.

Audit:

- login
- logout
- record creation
- record update
- status changes
- patient record access
- medication changes
- prescription changes
- billing adjustments
- discharge
- role changes
- permission changes
- document access
- exports
- sensitive record access

Audit records should capture:

- user
- timestamp
- action
- entity
- entity ID
- previous values where applicable
- new values
- IP address
- user agent
- reason where applicable

Audit records must be immutable to normal users.

---

# 10. Client Registry

Create a Master Client Registry.

Fields should include:

- unique client number
- first name
- middle name
- surname
- preferred name
- date of birth
- sex
- marital status
- nationality
- national ID number
- passport number where applicable
- phone number
- email
- county
- sub-county
- ward
- physical address
- occupation
- employer
- religion, only where institution policy requires and appropriate consent exists
- next of kin
- emergency contact
- referring institution
- photo, optional
- allergies
- known chronic conditions
- active status
- deceased status where applicable

Automatically generate a human-readable client number.

Example:

ARS-2026-000001

---

# 11. Referral Module

Support referrals from:

- Self
- Family
- Hospital
- Clinic
- Employer
- School
- Court
- Probation
- Police
- NACADA
- NGO
- Religious institution
- Community organization
- Other

Capture:

- referral date
- source
- referring person
- organization
- reason
- presenting problem
- referral documents
- urgency
- pre-admission notes
- decision

Referral status:

- New
- Screening
- Accepted
- Deferred
- Referred Elsewhere
- Declined
- Converted to Admission

---

# 12. Pre-Admission Screening

Create a structured screening workflow.

Capture:

- current intoxication
- withdrawal risk
- suicide risk
- self-harm risk
- violence risk
- psychosis
- severe medical condition
- pregnancy
- seizure history
- overdose history
- current medication
- communicable disease concerns
- accommodation suitability
- clinical suitability

Decision:

- Suitable for admission
- Medical stabilization required
- Psychiatric evaluation required
- External referral required
- Deferred
- Declined

Require reasons.

---

# 13. Admission Module

Admission should include:

- admission number
- client
- referral
- admission date
- admission time
- admission type
- accompanying person
- referring organization
- admission reason
- admission programme
- expected programme duration
- expected discharge date
- assigned counsellor
- assigned clinician
- assigned nurse where required
- room
- bed
- current status

Capture:

- personal belongings
- property inventory
- valuables
- prohibited items
- search record where policy permits
- consent forms
- client rights acknowledgment
- treatment agreement
- visitor permissions
- communication permissions
- dietary requirements
- allergies
- initial risk flags

Admission statuses:

- Pending
- Active
- On Leave
- Hospitalized
- AWOL
- Discharge Pending
- Discharged
- Transferred
- Deceased

---

# 14. Consent Management

Create proper consent records.

Consent types:

- Treatment
- Medication
- Information sharing
- Family communication
- Photography
- Media
- Research
- Laboratory testing
- Telemedicine
- Release of medical information
- Other

Capture:

- client
- admission
- consent type
- consent text/version
- granted
- declined
- date
- expiry
- withdrawal date
- witness
- notes

Do not use one generic consent checkbox.

---

# 15. Substance Use Assessment

Support multiple substances per client.

Substances should be configurable.

Initial examples:

- Alcohol
- Cannabis
- Tobacco
- Nicotine
- Heroin
- Other opioids
- Cocaine
- Prescription opioids
- Benzodiazepines
- Amphetamines
- Methamphetamine
- Inhalants
- Hallucinogens
- Synthetic drugs
- Other

For every substance capture:

- first use age
- regular use age
- frequency
- quantity
- route
- duration
- last use
- typical pattern
- maximum use
- withdrawal symptoms
- tolerance
- overdose
- previous quit attempts
- longest abstinence
- previous treatment
- consequences
- current status

---

# 16. Screening Instruments Framework

Build a configurable assessment engine.

Do not hard-code the application around only one assessment.

Allow administrators to configure structured assessment tools.

Initial support should allow implementation of:

- AUDIT
- ASSIST
- CAGE
- DAST
- PHQ-9
- GAD-7
- suicide-risk assessment
- withdrawal assessment
- relapse-risk assessment

Each instrument should support:

- questions
- response options
- scoring
- calculated score
- score interpretation
- risk level
- completion date
- completed by
- historical score comparison

Display score trends.

---

# 17. Biopsychosocial Assessment

Build a comprehensive assessment divided into:

## Biological
- health history
- chronic illness
- medication
- sleep
- nutrition
- disability
- physical complaints

## Psychological
- psychiatric history
- mood
- anxiety
- trauma
- cognition
- suicide risk
- self-harm
- previous psychiatric admissions

## Social
- family
- relationships
- housing
- employment
- education
- finances
- peers
- support systems

## Substance Use
- substance history
- triggers
- consequences
- dependency indicators

## Legal
- court cases
- probation
- legal obligations

## Occupational
- skills
- work history
- employability

## Spiritual
Only when clinically and institutionally appropriate.

Allow draft, completed and reviewed states.

---

# 18. Risk Assessment

Create structured risk records for:

- suicide
- self-harm
- aggression
- violence
- absconding
- relapse
- overdose
- falls
- seizure
- withdrawal complication
- exploitation
- abuse
- medical deterioration

Risk levels:

- Low
- Moderate
- High
- Critical

High and Critical risks should generate dashboard alerts.

Every risk record should include:

- risk factors
- protective factors
- intervention
- assigned staff
- review date
- status

---

# 19. Treatment Planning

Create individualized treatment plans.

Each plan should contain:

- presenting problem
- diagnosis/problem area
- treatment goal
- measurable objectives
- interventions
- responsible professional
- start date
- target date
- review date
- outcome
- status

Plan states:

- Draft
- Active
- Under Review
- Revised
- Completed
- Cancelled

Maintain version history.

Never overwrite an old plan without preserving the prior version.

---

# 20. Case Management

Each admission should have:

- primary case manager
- assigned counsellor
- multidisciplinary team where applicable

Case manager dashboard should show:

- assigned clients
- overdue assessments
- treatment plans due
- upcoming reviews
- missed therapy sessions
- family meetings due
- discharge preparation
- aftercare follow-ups
- active risk alerts

---

# 21. Counselling and Therapy

Support:

- Individual counselling
- Group counselling
- Family therapy
- Psychoeducation
- Addiction counselling
- Cognitive behavioural interventions
- Relapse prevention
- Trauma interventions
- Motivational interviewing
- Occupational therapy
- Spiritual support where applicable
- Peer support

Session record:

- admission
- session type
- therapist
- date
- start time
- end time
- objective
- session summary
- intervention
- client response
- progress
- homework
- risk concerns
- next session

Psychotherapy notes should support stricter access permissions than general clinical notes.

---

# 22. Group Therapy

Create group sessions.

Group session should include:

- title
- type
- topic
- facilitator
- co-facilitator
- date
- duration
- location
- objectives

Allow multiple residents to be marked:

- Present
- Absent
- Excused
- Refused
- Late

Allow private individual observations per participant.

---

# 23. Rehabilitation Programme

Create programme schedules.

Support:

- daily programme
- weekly programme
- activity categories
- recurring activities
- attendance

Examples:

- Morning routine
- Group therapy
- Psychoeducation
- Life skills
- Occupational activity
- Physical exercise
- Recreation
- Spiritual programme
- AA/NA meeting
- Family programme

Attendance should contribute to the client's progress history.

---

# 24. Clinical Module

Support:

- clinical encounters
- medical history
- physical examination
- diagnoses
- problem list
- allergies
- vital signs
- clinician notes
- medical orders
- investigations
- referrals
- follow-up
- emergency clinical events

Each clinical encounter should identify the responsible clinician.

---

# 25. Nursing Module

Create a nursing dashboard.

Display:

- currently admitted residents
- high-risk patients
- observations due
- medication due
- new admissions
- incidents
- residents outside facility
- handover items

Support:

- nursing assessment
- nursing notes
- vitals
- observation chart
- sleep
- appetite
- mood
- hygiene
- withdrawal symptoms
- pain
- interventions
- escalation
- shift handover

Every nursing note should be timestamped and attributable.

---

# 26. Medication Prescribing

Allow authorized clinicians only to prescribe.

Prescription fields:

- client
- admission
- medication
- generic name
- brand name if relevant
- formulation
- strength
- dose
- route
- frequency
- start date
- stop date
- PRN status
- indication
- instructions
- prescriber

Prescription status:

- Draft
- Active
- Suspended
- Discontinued
- Completed

Maintain prescription change history.

---

# 27. eMAR

Implement Electronic Medication Administration Record.

Display medications due by:

- patient
- ward
- medication round
- scheduled time

Capture:

- medication
- prescribed dose
- actual dose
- route
- scheduled time
- administration time
- administered by
- status
- reason

Statuses:

- Given
- Refused
- Omitted
- Held
- Not Available
- Patient Away
- PRN

Any omitted or refused medication should require a reason.

---

# 28. Pharmacy

Create:

- medication catalogue
- suppliers
- batches
- expiry dates
- purchase receipts
- dispensing
- ward stock
- returns
- adjustments
- damaged stock
- expired stock
- stock counts
- reorder levels

Track every stock movement.

Use batch-level inventory.

Provide expiry alerts.

---

# 29. Laboratory and Investigations

Support:

- investigation requests
- laboratory requests
- specimen date
- laboratory provider
- test
- result
- reference range
- abnormal flag
- clinician review
- external PDF attachment

Allow the module to function even if tests are performed externally.

---

# 30. Toxicology Testing

Create a dedicated drug-testing module.

Capture:

- client
- admission
- test date
- reason
- sample type
- substances tested
- result per substance
- confirmatory test
- staff
- client acknowledgement
- follow-up action

Allow longitudinal trend review.

---

# 31. Residential Bed Management

Model:

Facility → Wing → Room → Bed

Bed statuses:

- Available
- Occupied
- Reserved
- Cleaning
- Maintenance
- Unavailable

Support:

- bed assignment
- transfer
- transfer reason
- bed history
- occupancy reports

---

# 32. Resident Movement

Track where every resident currently is.

Movement types:

- In Facility
- Hospital
- Court
- Home Visit
- Approved Leave
- External Activity
- AWOL
- Returned
- Transferred
- Discharged

Capture departure and expected return.

Flag residents overdue for return.

---

# 33. Visitors

Create:

- approved visitor registry
- visitor relationship
- permission status
- visit booking
- check-in
- check-out
- items brought in
- staff authorization
- notes
- visit incidents

---

# 34. Family Management

Distinguish:

- next of kin
- emergency contact
- payer
- authorized family member
- visitor

Track:

- consent to communicate
- information-sharing limitations
- family sessions
- family conferences
- family education
- discharge planning involvement

---

# 35. Incident Management

Support incident categories:

- Violence
- Aggression
- Self-harm
- Suicide attempt
- Absconding
- Attempted absconding
- Substance possession
- Contraband
- Medication error
- Fall
- Injury
- Medical emergency
- Abuse allegation
- Safeguarding concern
- Property damage
- Sexual misconduct
- Security incident
- Other

Capture:

- date/time
- location
- people involved
- witnesses
- severity
- narrative
- immediate action
- treatment
- escalation
- investigation
- corrective action
- reviewer
- closure

Submitted incidents should not be destructively edited.

Use addendum/correction mechanisms.

---

# 36. Safeguarding

Create a restricted-access safeguarding module.

Support:

- vulnerable adults
- minors
- physical abuse
- sexual abuse
- neglect
- exploitation
- emotional abuse
- financial abuse
- other safeguarding concerns

Limit access through explicit permissions.

---

# 37. Complaints and Grievances

Track:

- complaint number
- complainant
- client
- category
- date
- description
- assigned staff
- investigation
- corrective action
- outcome
- resolution date

Status:

- Open
- Assigned
- Under Investigation
- Action Required
- Resolved
- Closed

---

# 38. Discharge Planning

Discharge planning should begin before discharge.

Capture:

- discharge readiness
- treatment goals achieved
- unresolved risks
- medications
- relapse-prevention plan
- accommodation
- family support
- employment
- education
- support groups
- appointments
- external referrals
- emergency plan
- discharge summary

Require mandatory elements before final discharge.

---

# 39. Discharge

Discharge types:

- Completed Programme
- Against Advice
- Transferred
- Medical Referral
- Administrative Discharge
- Absconded
- Deceased
- Other

Capture:

- discharge date/time
- discharge type
- reason
- destination
- clinician approval
- counsellor summary
- medications
- follow-up plan
- next appointment
- documentation

---

# 40. Aftercare

Maintain an active recovery record after discharge.

Schedule follow-ups such as:

- 7 days
- 30 days
- 90 days
- 180 days
- 365 days

Allow institution configuration.

Capture:

- contacted
- unsuccessful contact
- abstinence
- lapse
- relapse
- employment
- education
- housing
- family relations
- medication adherence
- support-group participation
- mental wellbeing
- physical wellbeing
- referral
- readmission

---

# 41. Relapse Management

Create structured relapse events.

Capture:

- relapse date
- substance
- trigger
- circumstance
- severity
- consequences
- protective factors
- immediate intervention
- clinical review
- treatment-plan revision
- readmission decision

Do not simply close aftercare when relapse occurs.

---

# 42. Billing

Support rehabilitation programme billing.

Create:

- services
- packages
- price lists
- invoices
- invoice items
- payments
- receipts
- discounts
- refunds
- credits
- write-offs
- outstanding balances
- statements

Payment methods:

- Cash
- M-Pesa
- Bank Transfer
- Card
- Cheque
- Insurance
- Sponsor
- Other

Separate:

Client

from:

Payer

---

# 43. Sponsors and Payers

Support:

- Self
- Parent
- Family
- Employer
- Insurance
- NGO
- Government
- County
- Church
- Corporate sponsor
- Other

A payer may sponsor multiple clients.

A client may have multiple payers.

---

# 44. M-Pesa Architecture

Prepare billing architecture for future M-Pesa integration.

Do not hard-code payment confirmation.

Create appropriate structures for:

- transaction reference
- phone number
- amount
- timestamp
- payer
- invoice
- reconciliation status

---

# 45. Inventory and Stores

Support non-medical inventory.

Categories:

- Food
- Toiletries
- Cleaning supplies
- Bedding
- Uniforms
- Office supplies
- Counselling materials
- Maintenance items
- Kitchen items
- Other

Workflow:

Purchase Request → Approval → Purchase Order → Goods Received → Store → Issue

Support:

- supplier
- item
- unit
- stock level
- reorder level
- batch
- expiry
- stock issue
- stock return
- adjustment
- stock count
- variance

---

# 46. Nutrition

Support:

- meal plans
- special diets
- allergies
- diabetic diets
- vegetarian diets
- other medical diets
- daily resident headcount
- kitchen requirements

---

# 47. Staff Management

Create staff profiles.

Capture:

- employee number
- name
- department
- designation
- qualifications
- professional body
- licence number
- licence expiry
- employment status
- joining date
- contact information

Support professional credential expiry alerts.

---

# 48. Staff Rostering

Support:

- departments
- shifts
- staff schedules
- leave
- availability
- coverage

Provide daily staff roster views.

---

# 49. Compliance

Create compliance registers.

Examples:

- NACADA accreditation
- Facility licences
- County licences
- Fire certificates
- Public health certificates
- Pharmacy-related licences where applicable
- ODPC compliance records
- Professional licences
- Insurance certificates
- Internal policies
- Inspection reports

Capture:

- document type
- reference
- issuing authority
- issue date
- expiry date
- attachment
- responsible person
- status

Generate alerts at configurable intervals such as:

90 days
60 days
30 days
14 days
7 days

---

# 50. Document Management

Allow documents to be uploaded and attached to:

- client
- referral
- admission
- assessment
- clinical encounter
- billing record
- incident
- compliance record
- staff member

Store metadata:

- document category
- uploaded by
- upload date
- confidentiality level
- version
- description

Do not expose direct unsafe filesystem paths.

---

# 51. Data Protection

Design for compliance with Kenyan data-protection expectations for sensitive health information.

Implement:

- role-based access
- least privilege
- encrypted transport
- secure credentials
- audit trails
- session timeout
- restricted exports
- configurable retention policies
- consent tracking
- data-access logging
- account deactivation
- secure backups
- anonymized reporting
- confidentiality classification

Prepare the architecture for future:

- data access requests
- correction requests
- retention workflows
- breach register
- consent withdrawal

---

# 52. Reports

Create reporting modules.

## Clinical
- active patients
- diagnoses
- risk levels
- medication
- referrals
- clinical outcomes

## Rehabilitation
- admissions
- substance trends
- therapy attendance
- programme attendance
- treatment-plan completion
- discharge outcomes
- relapse

## Aftercare
- follow-up completion
- abstinence
- relapse
- readmission
- employment
- family reintegration

## Financial
- revenue
- invoices
- payments
- outstanding balances
- debt ageing
- payment methods
- sponsor balances

## Residential
- bed occupancy
- average length of stay
- movements
- admissions
- discharge

## Compliance
- licence expiry
- incidents
- complaints
- audits
- corrective actions

Allow filtering by:

- date range
- gender
- age
- programme
- substance
- admission status
- discharge type
- clinician
- counsellor

Reports should support export to CSV and PDF architecture.

---

# 53. Dashboard

Create dashboards tailored to user roles.

## Management Dashboard

Display:

- current residents
- available beds
- occupancy percentage
- admissions today
- discharges today
- expected discharges
- active high-risk cases
- programme attendance
- pending incidents
- outstanding balances
- compliance expiries
- treatment reviews overdue

## Counsellor Dashboard

Display:

- assigned clients
- sessions today
- missed sessions
- treatment-plan reviews
- discharge plans
- follow-ups
- active risks

## Nursing Dashboard

Display:

- medications due
- observations due
- high-risk clients
- new admissions
- shift handover
- incidents

## Finance Dashboard

Display:

- invoices
- today's collections
- unpaid invoices
- debt ageing
- sponsor balances

Use clean Bootstrap metric cards.

Do not use decorative gradient dashboards.

---

# 54. Notifications

Implement internal notifications.

Examples:

- assessment overdue
- treatment review due
- medication due
- discharge documentation incomplete
- follow-up due
- compliance certificate expiring
- stock below reorder level
- drug batch expiring
- client overdue from leave
- incident assigned

Notifications should support:

- unread/read
- severity
- link to record
- created date
- user-specific delivery

---

# 55. Internal Tasks

Create a task module.

Tasks may link to:

- client
- admission
- incident
- discharge
- compliance
- inventory

Fields:

- title
- description
- assigned to
- priority
- due date
- status
- related record
- comments

Statuses:

- Open
- In Progress
- Blocked
- Completed
- Cancelled

---

# 56. Search

Implement global search.

Search should support:

- client name
- client number
- admission number
- national ID
- phone number

Do not expose confidential note text through global search unless authorized.

---

# 57. Pagination and Filtering

Every major list must support server-side:

- pagination
- filtering
- sorting
- date ranges
- search

Do not load entire large tables into the browser.

---

# 58. API Standards

Use API prefix:

```text
/api/v1/
```

Use consistent JSON responses.

Implement:

- proper HTTP status codes
- validation errors
- domain errors
- authorization errors
- pagination metadata
- exception handlers

Generate FastAPI OpenAPI documentation.

Protect sensitive endpoints.

---

# 59. Validation

Backend validation is authoritative.

Frontend validation improves usability but must never replace backend validation.

Validate:

- date rules
- required clinical fields
- status transitions
- duplicate records
- authorization
- medication constraints
- billing totals
- admission/discharge logic

---

# 60. Workflow State Machines

Where appropriate, enforce valid state transitions.

Example admission:

```text
PENDING
    ↓
ACTIVE
    ↓
DISCHARGE_PENDING
    ↓
DISCHARGED
```

Do not allow arbitrary status changes that break business logic.

Use similar controls for:

- referrals
- prescriptions
- treatment plans
- incidents
- invoices
- compliance items
- discharge

---

# 61. Frontend Layout

Create a standard application shell.

Desktop:

```text
-----------------------------------------------------
Top Navbar
-----------------------------------------------------
Sidebar | Main Content
        |
        |
-----------------------------------------------------
```

Sidebar sections:

Dashboard

Clients

Referrals

Admissions

Assessments

Rehabilitation

Clinical

Nursing

Medication

Pharmacy

Residential Care

Billing

Inventory

Discharge

Aftercare

Incidents

Reports

Compliance

Administration

Collapse submenus where appropriate.

On mobile, use Bootstrap offcanvas navigation.

---

# 62. Forms

Forms should use consistent Bootstrap structure.

Use:

- labels above controls
- helper text where appropriate
- inline validation feedback
- required field indicators
- logical field grouping
- fieldsets or cards for long assessments

Do not create a 100-field form on one uninterrupted page.

Use tabs, steps or sections for complex workflows.

---

# 63. Tables

Use professional Bootstrap tables.

Include:

- search
- filters
- pagination
- sorting
- status badges
- row actions

Avoid excessive colour.

Use status colour consistently.

---

# 64. Accessibility

Ensure:

- semantic HTML
- keyboard usability
- visible focus states
- labels for all inputs
- adequate contrast
- ARIA attributes where required
- error messages understandable without relying solely on colour

---

# 65. Responsive Design

Support:

- desktop
- laptop
- tablet
- mobile

Clinical forms and dashboards should remain usable on tablets.

---

# 66. Testing

Backend tests should cover:

- authentication
- permissions
- admissions
- medication
- billing
- discharge
- audit trail
- status transitions

Frontend testing should cover critical workflows.

At minimum, create tests for:

- login
- creating a client
- admitting a client
- creating treatment plan
- recording counselling session
- prescribing medication
- administering medication
- generating invoice
- discharging client

---

# 67. Database Migrations

Use Alembic.

Do not manually modify production database schema.

Every schema change must have a migration.

---

# 68. Seed Data

Create development seed data for:

- roles
- permissions
- departments
- substances
- medication routes
- payment methods
- incident categories
- common assessment types
- sample facility
- sample users

Never include real patient information in seed files.

---

# 69. Logging

Implement structured backend logging.

Capture:

- application errors
- authentication issues
- unexpected exceptions
- integration failures

Do not log:

- passwords
- tokens
- full sensitive clinical notes
- confidential personal information unnecessarily

---

# 70. Configuration

Use environment variables.

Create:

```text
.env.example
```

Include:

```text
DATABASE_URL
SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
ENVIRONMENT
BACKEND_CORS_ORIGINS
FILE_STORAGE_PATH
```

Do not commit secrets.

---

# 71. Docker

Prepare:

```text
docker-compose.yml
```

Services:

- backend
- frontend
- postgres
- nginx if required

Development configuration should remain straightforward.

---

# 72. Documentation

Create:

```text
README.md
```

Include:

- project overview
- architecture
- prerequisites
- environment setup
- PostgreSQL setup
- backend setup
- frontend setup
- migrations
- seed data
- starting development servers
- running tests
- Docker instructions
- default development user
- API documentation location

---

# 73. Development Approach

Do not attempt to implement the entire system in one monolithic step.

Develop it in structured phases.

## Phase 1: Foundation

Build:

- project structure
- PostgreSQL connection
- FastAPI app
- React app
- authentication
- users
- roles
- permissions
- departments
- audit infrastructure
- application shell
- navigation

## Phase 2: Client and Admissions

Build:

- client registry
- contacts
- referrals
- screening
- admission
- consent
- rooms
- beds

## Phase 3: Assessments and Rehabilitation

Build:

- substance assessment
- biopsychosocial assessment
- risk assessment
- treatment plans
- case management
- individual therapy
- group therapy
- programme attendance

## Phase 4: Clinical and Nursing

Build:

- clinical encounters
- diagnosis
- vitals
- nursing notes
- observations
- handover
- laboratory

## Phase 5: Medication and Pharmacy

Build:

- medication catalogue
- prescriptions
- eMAR
- pharmacy inventory
- dispensing
- batch tracking
- expiry alerts

## Phase 6: Billing

Build:

- services
- packages
- invoices
- payments
- sponsors
- statements
- debt ageing

## Phase 7: Residential Operations

Build:

- movements
- visitors
- incidents
- safeguarding
- nutrition

## Phase 8: Discharge and Recovery

Build:

- discharge planning
- discharge
- aftercare
- relapse
- readmission

## Phase 9: Inventory and Compliance

Build:

- stores
- procurement
- compliance
- credentials
- licences

## Phase 10: Reporting and Quality

Build:

- dashboards
- reports
- outcome analysis
- audits
- corrective actions
- exports

---

# 74. First Deliverable

Start by implementing Phase 1 only.

Before implementing business modules:

1. Create the repository structure.
2. Create backend and frontend projects.
3. Configure PostgreSQL.
4. Configure SQLAlchemy.
5. Configure Alembic.
6. Configure FastAPI.
7. Configure React, TypeScript and Bootstrap.
8. Implement User, Role, Permission and Department models.
9. Implement authentication.
10. Implement RBAC.
11. Implement audit infrastructure.
12. Implement the base application layout.
13. Create login page.
14. Create dashboard shell.
15. Create user-management screens.
16. Create role and permission management.
17. Create seed data.
18. Write tests.
19. Write README instructions.

Do not move to Phase 2 until Phase 1 is structurally clean and testable.

---

# 75. Coding Standards

Use:

- clear naming
- type hints in Python
- TypeScript strict mode
- modular components
- reusable form components
- reusable table components
- reusable API clients
- domain services
- database transactions
- documented complex business logic

Avoid:

- giant files
- duplicated code
- business logic inside React components
- SQL directly inside route handlers
- hard-coded IDs
- hard-coded user roles
- magic numbers
- untyped TypeScript
- `any` unless absolutely unavoidable

---

# 76. Critical Quality Rules

At all times:

1. Preserve patient confidentiality.
2. Preserve historical clinical data.
3. Do not allow destructive modification of audit-sensitive records.
4. Enforce authorization server-side.
5. Keep UI professional and institutional.
6. Avoid unnecessary visual effects.
7. Use PostgreSQL constraints where appropriate.
8. Use backend validation as authoritative.
9. Keep each module independent but interoperable.
10. Design for future multi-facility support.
11. Keep the API versioned.
12. Maintain clean migration history.
13. Make all major actions auditable.
14. Do not mix billing permissions with clinical permissions.
15. Do not give ICT users automatic access to confidential clinical information.

---

# 77. Expected Output for Each Development Phase

For every phase you implement, provide:

1. Architecture summary
2. New database entities
3. Migration files
4. Pydantic schemas
5. Repository layer
6. Service layer
7. API routes
8. Permission definitions
9. React pages
10. React reusable components
11. TypeScript types
12. API service functions
13. Frontend validation
14. Tests
15. Seed-data updates
16. README updates
17. Manual testing checklist

When writing code, produce complete working files rather than incomplete snippets whenever practical.

Do not create placeholder functionality that appears to work but does nothing.

---

# 78. Final Product Goal

The final system should allow management to confidently answer:

- Who is currently admitted?
- Where is every resident?
- Which beds are available?
- Who is high risk?
- Which assessments are overdue?
- What treatment plan does each client have?
- Which counselling sessions have occurred?
- Which medications are prescribed?
- Which medications have been administered?
- Which incidents occurred?
- Which residents are approaching discharge?
- What aftercare is due?
- Who has relapsed or been readmitted?
- What money is owed?
- What payments have been received?
- Which licences are expiring?
- Which staff credentials are expiring?
- What are our rehabilitation outcomes?
- Is every sensitive action auditable?

The finished platform should feel like a serious Kenyan rehabilitation institution's operational system, combining:

Electronic Client Record + Clinical Care + Rehabilitation Case Management + Medication Management + Residential Operations + Billing + Compliance + Recovery Outcome Tracking.

Begin with Phase 1 and build the foundation correctly before progressing to other phases.