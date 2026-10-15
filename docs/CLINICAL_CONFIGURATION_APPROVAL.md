# ReHUB Institutional Clinical Configuration & Governance Approval

> **Institution:** Kenyan Residential Rehabilitation & Mental Health Institution  
> **System:** ReHUB (Rehabilitation Management System)  
> **Configuration Version:** `ARS-CLINICAL-CONFIG-1.0`  
> **Effective Date:** 2026-10-15  
> **Statutory Oversight:** Kenya Medical Practitioners and Dentists Council (KMPDC), Pharmacy and Poisons Board (PPB), National Authority for the Campaign Against Alcohol and Drug Abuse (NACADA)  

---

## 1. Executive Summary & Clinical Governance Statement

This document formally establishes the standardized clinical assessment instruments, diagnostic scoring cutoffs, clinical risk thresholds, observation frequencies, reassessment intervals, and crisis escalation protocols implemented in **ReHUB / ARS RMS**.

In residential rehabilitation and psychiatric care, clinical thresholds directly affect patient safety and life preservation. In accordance with institutional governance:
1. Automated clinical scoring assists, but **never replaces**, clinical judgment.
2. Keyword surveillance across unstructured clinical notes creates **surveillance review alerts only**; it does not replace or modify validated psychometric instruments.
3. Once approved, configuration version `ARS-CLINICAL-CONFIG-1.0` becomes immutable. Any future modifications require a formal revision (`ARS-CLINICAL-CONFIG-1.1` or `2.0`), leaving past assessment records tied to the historical configuration under which they were administered.

---

## 2. Approved Clinical Assessment Instruments & Rules

### 2.1 C-SSRS (Columbia-Suicide Severity Rating Scale)
- **Version:** Lifetime/Recent Clinical Screener v1.0
- **Source:** The Columbia Lighthouse Project (Columbia University / NIMH)
- **Scoring Method:** Categorical severity mapping (Levels 1 through 5) based on positive responses to suicidal ideation and suicidal behavior items. *Note: Summed numerical scoring is clinically invalid and strictly prohibited.*
- **Interpretation & Risk Thresholds:**
  - **Level 1 (Wish to be Dead):** `LOW_RISK`
  - **Level 2 (Non-Specific Active Suicidal Thoughts):** `MODERATE_RISK`
  - **Level 3 (Active Suicidal Ideation with Any Methods, Not Plan/Intent):** `MODERATE_RISK`
  - **Level 4 (Active Suicidal Ideation with Some Intent, Without Specific Plan):** `HIGH_RISK`
  - **Level 5 (Active Suicidal Ideation with Specific Plan and Intent):** `CRITICAL_RISK`
  - **Prior Suicidal Behavior within 3 months:** `CRITICAL_RISK`
- **Required Clinical Action:**
  - Levels 1–2: Routine counselling, weekly reassessment, safety plan.
  - Level 3: Multidisciplinary team review within 24 hours, restricted ground movement, 30-min nurse observation.
  - Levels 4–5: Immediate 1:1 continuous nursing observation, urgent psychiatrist review, removal of sharp objects and ligatures.
- **Automated Escalation:** Acute automated crisis alert (`CRITICAL`) broadcast to on-duty clinician and Medical Director with mandatory acknowledgment window (15 minutes).
- **Reassessment Interval:** Daily for high/critical; weekly for low/moderate.
- **Effective Date:** 2026-10-15

---

### 2.2 AUDIT (Alcohol Use Disorders Identification Test)
- **Version:** WHO AUDIT-10 (Core Instrument)
- **Source:** World Health Organization (WHO/MSD/MSB/01.6a)
- **Scoring Method:** 10 questions scored 0–4; total score range 0–40.
- **Interpretation & Risk Thresholds:**
  - **Zone I (Score 0–7):** Low risk / abstinence.
  - **Zone II (Score 8–15):** Hazardous alcohol use (Simple brief intervention).
  - **Zone III (Score 16–19):** Harmful alcohol use (Brief intervention plus counselling).
  - **Zone IV (Score 20–40):** Alcohol dependence / severe addiction (Comprehensive inpatient detoxification & rehabilitation).
- **Required Action:** Scores ≥ 20 trigger mandatory admission referral for medically monitored inpatient alcohol detoxification.
- **Reassessment Interval:** At admission intake (Day 0), mid-treatment (Day 45), and discharge readiness (Day 90).
- **Effective Date:** 2026-10-15

---

### 2.3 ASSIST (Alcohol, Smoking and Substance Involvement Screening Test)
- **Version:** WHO ASSIST v3.1
- **Source:** World Health Organization (WHO ASSIST Working Group)
- **Scoring Method:** Substance-specific Specific Substance Involvement (SSI) score calculated per drug class (Cannabis, Cocaine, Amphetamines, Inhalants, Sedatives, Hallucinogens, Opioids, Other).
- **Interpretation & Risk Thresholds:**
  - **Scores 0–3 (0–10 for alcohol):** Low risk.
  - **Scores 4–26 (11–26 for alcohol):** Moderate risk (Brief intervention indicated).
  - **Scores 27+:** High risk (Intensive residential treatment indicated).
- **Required Action:** Substance classes scoring ≥ 27 automatically populate in the resident's Master Substance History and Individualized Treatment Plan.
- **Reassessment Interval:** Admission and pre-discharge evaluation.
- **Effective Date:** 2026-10-15

---

### 2.4 CAGE Substance Abuse Questionnaire
- **Version:** 4-Item Clinical Screener
- **Source:** Ewing, J.A. (1984), *Detecting Alcoholism: The CAGE Questionnaire*, JAMA.
- **Scoring Method:** 1 point per affirmative answer (Cut down, Annoyed, Guilty, Eye-opener); range 0–4.
- **Interpretation:** Score ≥ 2 indicates clinically significant substance misuse requiring comprehensive clinical evaluation.
- **Effective Date:** 2026-10-15

---

### 2.5 DAST-10 (Drug Abuse Screening Test)
- **Version:** DAST-10 Brief Clinical Instrument
- **Source:** Skinner, H.A. (1982), Addiction Research Foundation.
- **Scoring Method:** 1 point per affirmative response (except question 3 which is reversed); score range 0–10.
- **Interpretation & Risk Thresholds:**
  - **Score 0:** None (No intervention).
  - **Score 1–2:** Low level (Monitoring).
  - **Score 3–5:** Moderate level (Outpatient or residential rehabilitation).
  - **Score 6–8:** Substantial level (Inpatient residential rehabilitation).
  - **Score 9–10:** Severe level (Intensive inpatient clinical treatment).
- **Effective Date:** 2026-10-15

---

### 2.6 PHQ-9 (Patient Health Questionnaire - 9)
- **Version:** PHQ-9 Standard
- **Source:** Kroenke, K., Spitzer, R.L., Williams, J.B. (2001).
- **Scoring Method:** 9 questions scored 0–3; total score 0–27.
- **Interpretation & Risk Thresholds:**
  - **1–4:** Minimal depression.
  - **5–9:** Mild depression.
  - **10–14:** Moderate depression.
  - **15–19:** Moderately severe depression.
  - **20–27:** Severe depression.
  - **Question 9 (Thoughts of death/suicide) > 0:** Mandates immediate clinical suicide risk assessment irrespective of total score.
- **Reassessment Interval:** Bi-weekly during inpatient rehabilitation.
- **Effective Date:** 2026-10-15

---

### 2.7 GAD-7 (Generalized Anxiety Disorder 7)
- **Version:** GAD-7 Standard
- **Source:** Spitzer, R.L., Kroenke, K., et al. (2006).
- **Scoring Method:** 7 questions scored 0–3; total score 0–21.
- **Interpretation & Risk Thresholds:**
  - **0–4:** Minimal anxiety.
  - **5–9:** Mild anxiety.
  - **10–14:** Moderate anxiety.
  - **15–21:** Severe anxiety.
- **Effective Date:** 2026-10-15

---

### 2.8 Withdrawal & Detoxification Management
- **Instruments:**
  - **CIWA-Ar** (Alcohol Withdrawal): Range 0–67. Score ≥ 10 triggers pharmacological detoxification protocol. Score ≥ 15 triggers hourly nursing vitals and acute clinical review.
  - **COWS** (Clinical Opiate Withdrawal Scale): Score 5–12 (mild), 13–24 (moderate), 25–36 (moderately severe), >36 (severe withdrawal).
- **Observation Frequency:**
  - Active acute withdrawal: Vitals and checks every 2 to 4 hours.
  - Stable residential phase: Routine nursing shift checks (morning, evening, night).
  - Crisis / 1:1 Observation: Continuous line-of-sight monitoring.

---

### 2.9 Admission, Reassessment & Discharge Readiness Rules
1. **Admission Clearance:** Resident must have negative medical emergency red flags (vital instability, severe delirium tremens, acute psychosis requiring involuntary psychiatric commitment) or clinician medical sign-off.
2. **Reassessment Intervals:** Psychometric battery administered at Intake (Day 0–3), Mid-Treatment (Day 45), and Pre-Discharge (Day 80–90).
3. **Discharge Readiness Criteria:**
   - Clinical stability confirmed by treating Medical Officer.
   - 100% negative toxicology panel on random screens over previous 30 days.
   - Comprehensive relapse prevention and safe recovery accommodation plan verified.
   - Documented family conference completed.
   - Formal aftercare schedule locked (Day 7, 30, 90, 180, 365).

---

## 3. C-SSRS & Crisis Surveillance Distinction Protocol

To ensure patient safety and avoid false reassurance:
1. **Surveillance Keyword Scanner:** Automated background scanning of clinical notes, shift handovers, and therapy records matches high-risk clinical keywords.
2. **Negation Safety:** Phrases such as *"Client denies suicidal ideation"* or *"no intent to harm self"* are filtered out by negation logic.
3. **Review Flag Only:** Positively matched keywords produce a `CLINICAL_REVIEW_REQUIRED` surveillance flag. The system strictly prohibits recording this as a formal suicide assessment score. A qualified clinician must administer the formal C-SSRS screener to establish clinical risk.

---

## 4. Formal Approval & Attributable Sign-Off

The clinical protocols, psychometric cutoffs, escalation response timers, and observation schedules documented in version `ARS-CLINICAL-CONFIG-1.0` have been reviewed against national guidelines (NACADA, Ministry of Health Kenya) and are hereby approved for institutional operation.

### Institutional Medical Authority:

| Sign-Off Attribute | Formal Institutional Record |
| :--- | :--- |
| **Institution Name** | ARS Residential Rehabilitation & Healthcare Institution |
| **Configuration Version** | `ARS-CLINICAL-CONFIG-1.0` |
| **Approving Clinician** | [Awaiting Institutional Medical Director Seal & Signature] |
| **Professional Title** | Medical Director / Consultant Psychiatrist |
| **Regulatory Registration** | KMPDC Reg. No. [Pending Medical Council Registration Entry] |
| **Clinical Decision** | **PENDING FORMAL PHYSICAL/DIGITAL SIGNATURE** |
| **Effective Date** | 2026-10-15 |

### Technical Verification Attestation:
- **System Administrator:** Cleophas (Lead Systems Engineer)
- **Verification Date:** 2026-10-14
- **Technical Status:** Configured, validated, and ready for deployment upon clinical signature.
