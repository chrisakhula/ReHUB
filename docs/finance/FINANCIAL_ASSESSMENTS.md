# Pre-Admission Financial Assessments

## 1. Purpose
The Financial Assessment captures the commercial background and payer viability of prospective clients during referral and pre-admission intake before clinical admission activation.

## 2. Reference Standard
- Reference Prefix: `FAS-YYYY-NNNNN` (e.g. `FAS-2026-00001`)
- Stored on table: `billing_financial_assessments`

## 3. Data Schema
| Field | Type | Description |
|---|---|---|
| `client_id` | UUID | Client master identifier |
| `reference_code` | String(50) | Unique human-readable assessment code |
| `proposed_programme` | String(150) | Inpatient / outpatient rehabilitation programme |
| `expected_length_of_stay_days` | Integer | Anticipated duration of treatment |
| `expected_admission_date` | Date | Target admission date |
| `primary_payer_type` | Enum | `SELF`, `FAMILY`, `EMPLOYER`, `CORPORATE`, `INSURANCE`, `NGO`, `CHURCH`, `GOVERNMENT`, `OTHER` |
| `primary_payer_name` | String(150) | Name of primary financial guarantor |
| `secondary_payer_type` | Enum | Optional secondary coverage |
| `sponsor_id` | UUID | Reference to registered Sponsor organization |
| `estimated_programme_cost` | Numeric(12,2) | Projected gross programme cost |
| `deposit_required` | Numeric(12,2) | Upfront admission deposit requirement |
| `credit_terms` | String(100) | Payment term agreements (e.g. 30_DAYS) |
| `installment_preference` | String(100) | Preferred installment schedule |
| `discount_eligibility` | Numeric(5,2) | Verified discount eligibility percentage |
| `authorization_limit` | Numeric(12,2) | Max credit limit approved |
| `financial_notes` | Text | Commercial notes (no clinical details) |

## 4. Privacy Boundary
Assessments capture solely commercial viability, insurance pre-authorizations, and sponsor guarantees. No clinical narratives, diagnostic speculation, or substance use histories are stored in financial assessments.
