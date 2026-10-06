import type { Field } from "./types";
import { nowEAT, todayEAT } from "./validation";

export const text = (
  name: string,
  label: string,
  required = false,
  section?: string,
): Field => ({ name, label, required, section });
export const note = (
  name: string,
  label: string,
  required = false,
  section?: string,
): Field => ({ name, label, required, section, type: "textarea" });
export const choice = (
  name: string,
  label: string,
  options: string[],
  required = true,
  defaultValue?: string,
  section?: string,
): Field => ({
  name,
  label,
  options,
  required,
  type: "select",
  default: defaultValue ?? (required ? options[0] : undefined),
  section,
});
export const check = (
  name: string,
  label: string,
  section?: string,
  defaultValue = false,
): Field => ({ name, label, type: "checkbox", default: defaultValue, section });
export const number = (
  name: string,
  label: string,
  required = false,
  min?: number,
  max?: number,
  section?: string,
): Field => ({ name, label, type: "number", required, min, max, section });
export const date = (
  name: string,
  label: string,
  required = false,
  section?: string,
): Field => ({
  name,
  label,
  type: "date",
  required,
  default: required ? todayEAT : undefined,
  section,
});
export const stamp = (
  name: string,
  label: string,
  required = false,
  section?: string,
): Field => ({
  name,
  label,
  type: "datetime-local",
  required,
  default: required ? nowEAT : undefined,
  section,
  help: "East Africa Time (UTC+3)",
});
export const lookup = (
  name: string,
  label: string,
  source: string,
  required = true,
  section?: string,
  labelKeys?: string[],
): Field => ({
  name,
  label,
  type: "lookup",
  source,
  required,
  section,
  labelKeys,
});
export const staff = (
  name: string,
  label: string,
  required = false,
  section?: string,
): Field =>
  lookup(name, label, "/intake/staff", required, section, ["full_name"]);
export const reason: Field = note("reason", "Reason for action", true);
export const revisionReason: Field = note(
  "correction_reason",
  "Reason for revision",
  true,
);
export const strings = (
  name: string,
  label: string,
  section?: string,
): Field => ({
  name,
  label,
  type: "strings",
  section,
  help: "Enter one value per line.",
});
export const clientField = lookup(
  "client_id",
  "Client",
  "/clients",
  true,
  "Client",
  ["client_number", "first_name", "surname"],
);
export const admissionField = lookup(
  "admission_id",
  "Admission",
  "/admissions",
  true,
  "Admission",
  ["admission_number", "client_name"],
);
export const sex = ["MALE", "FEMALE", "INTERSEX", "UNSPECIFIED"];
export const levels = ["LOW", "MODERATE", "HIGH", "CRITICAL"];
export const attendance = ["PRESENT", "ABSENT", "EXCUSED", "REFUSED", "LATE"];
export const clientFields: Field[] = [
  text("first_name", "First name", true, "Identity"),
  text("middle_name", "Middle name", false, "Identity"),
  text("surname", "Surname", true, "Identity"),
  text("preferred_name", "Preferred name", false, "Identity"),
  date("date_of_birth", "Date of birth", true, "Identity"),
  choice("sex", "Sex", sex, true, "UNSPECIFIED", "Identity"),
  text("marital_status", "Marital status", false, "Identity"),
  {
    ...text("nationality", "Nationality", true, "Identity"),
    default: "Kenyan",
  },
  text("national_id", "National ID", false, "Identity"),
  text("passport_number", "Passport number", false, "Identity"),
  text("phone", "Phone number", false, "Contact & location"),
  text("email", "Email address", false, "Contact & location"),
  text("county", "County", false, "Contact & location"),
  text("sub_county", "Sub-county", false, "Contact & location"),
  text("ward", "Ward", false, "Contact & location"),
  note("physical_address", "Physical address", false, "Contact & location"),
  text("occupation", "Occupation", false, "Social & health"),
  text("employer", "Employer", false, "Social & health"),
  text(
    "referring_institution",
    "Referring institution",
    false,
    "Social & health",
  ),
  strings("allergies", "Allergies", "Social & health"),
  strings("chronic_conditions", "Chronic conditions", "Social & health"),
  text(
    "religion",
    "Religion (policy and consent required)",
    false,
    "Optional & status",
  ),
  check(
    "religion_policy_required",
    "Institution policy requires religion",
    "Optional & status",
  ),
  check(
    "religion_consent",
    "Explicit consent to record religion",
    "Optional & status",
  ),
  check("active", "Active client", "Optional & status", true),
  check("deceased", "Deceased", "Optional & status"),
];
export const contactFields: Field[] = [
  choice("kind", "Contact type", [
    "NEXT_OF_KIN",
    "EMERGENCY",
    "PAYER",
    "AUTHORIZED_FAMILY",
    "VISITOR",
    "OTHER",
  ]),
  text("name", "Contact name", true),
  text("relationship", "Relationship", true),
  text("phone", "Phone number", true),
  text("email", "Email address"),
  note("address", "Address"),
  check("authorized_contact", "Authorised family contact"),
  check("active", "Active contact", undefined, true),
];
export const referralFields: Field[] = [
  clientField,
  date("referral_date", "Referral date", true),
  choice("source", "Referral source", [
    "SELF",
    "FAMILY",
    "HOSPITAL",
    "CLINIC",
    "EMPLOYER",
    "SCHOOL",
    "COURT",
    "PROBATION",
    "POLICE",
    "NACADA",
    "NGO",
    "RELIGIOUS_INSTITUTION",
    "COMMUNITY_ORGANIZATION",
    "OTHER",
  ]),
  text("referring_person", "Referring person"),
  text("organization", "Organisation"),
  choice("urgency", "Urgency", ["ROUTINE", "URGENT", "EMERGENCY"]),
  note("reason", "Referral reason", true),
  note("presenting_problem", "Presenting problem", true),
  note("pre_admission_notes", "Pre-admission notes"),
];
export const screeningFields: Field[] = [
  check("current_intoxication", "Currently intoxicated", "Risks"),
  ...["withdrawal", "suicide", "self_harm", "violence"].map((n) =>
    choice(
      `${n}_risk`,
      `${n.replaceAll("_", " ")} risk`,
      levels,
      true,
      "LOW",
      "Risks",
    ),
  ),
  ...[
    "psychosis",
    "severe_medical_condition",
    "pregnancy",
    "seizure_history",
    "overdose_history",
  ].map((n) => check(n, n.replaceAll("_", " "), "Medical concerns")),
  note("current_medication", "Current medication", false, "Medical concerns"),
  note(
    "communicable_disease_concerns",
    "Communicable disease concerns",
    false,
    "Medical concerns",
  ),
  check("accommodation_suitable", "Accommodation suitable", "Decision", true),
  check("clinically_suitable", "Clinically suitable", "Decision", true),
  choice(
    "decision",
    "Screening decision",
    [
      "SUITABLE",
      "MEDICAL_STABILIZATION",
      "PSYCHIATRIC_EVALUATION",
      "EXTERNAL_REFERRAL",
      "DEFERRED",
      "DECLINED",
    ],
    true,
    "SUITABLE",
    "Decision",
  ),
  note("reason", "Decision reason", true, "Decision"),
];
export const admissionFields: Field[] = [
  clientField,
  lookup(
    "referral_id",
    "Accepted referral",
    "/referrals?status=ACCEPTED",
    true,
    "Admission",
    ["source", "organization", "id"],
  ),
  stamp("admission_date", "Admission date and time", true, "Admission"),
  choice(
    "admission_type",
    "Admission type",
    ["VOLUNTARY", "COURT_ORDERED", "READMISSION", "TRANSFER"],
    true,
    "VOLUNTARY",
    "Admission",
  ),
  text("accompanying_person", "Accompanying person", false, "Admission"),
  text("referring_organization", "Referring organisation", false, "Admission"),
  note("reason", "Admission reason", true, "Admission"),
  text("programme", "Programme", true, "Programme & staff"),
  {
    ...number(
      "expected_duration_days",
      "Expected programme days",
      true,
      1,
      1095,
      "Programme & staff",
    ),
    default: 90,
  },
  date(
    "expected_discharge_date",
    "Expected discharge date",
    false,
    "Programme & staff",
  ),
  ...[
    "assigned_counsellor_id",
    "assigned_clinician_id",
    "assigned_nurse_id",
    "primary_case_manager_id",
  ].map((n) => staff(n, n.replaceAll("_", " "), false, "Programme & staff")),
  check(
    "client_rights_acknowledged",
    "Client rights acknowledged",
    "Rights & requirements",
  ),
  check(
    "treatment_agreement",
    "Treatment agreement acknowledged",
    "Rights & requirements",
  ),
  note(
    "visitor_permissions",
    "Visitor permissions",
    false,
    "Rights & requirements",
  ),
  note(
    "communication_permissions",
    "Communication permissions",
    false,
    "Rights & requirements",
  ),
  note(
    "dietary_requirements",
    "Dietary requirements",
    false,
    "Rights & requirements",
  ),
  strings("allergies", "Admission allergies", "Rights & requirements"),
  strings("risk_flags", "Initial risk flags", "Rights & requirements"),
  check("search_permitted", "Search is permitted by policy", "Search record"),
  note("search_record", "Search record", false, "Search record"),
];
export const consentFields: Field[] = [
  choice("consent_type", "Consent type", [
    "TREATMENT",
    "MEDICATION",
    "INFORMATION_SHARING",
    "FAMILY_COMMUNICATION",
    "PHOTOGRAPHY",
    "MEDIA",
    "RESEARCH",
    "LABORATORY_TESTING",
    "TELEMEDICINE",
    "RELEASE_MEDICAL_INFORMATION",
    "OTHER",
  ]),
  note("consent_text", "Consent text", true),
  text("version", "Text version", true),
  choice("decision", "Decision", ["GRANTED", "DECLINED"]),
  stamp("consent_date", "Consent date", true),
  stamp("expires_at", "Expiry date"),
  text("witness", "Witness", true),
  note("notes", "Notes"),
];
export const propertyFields: Field[] = [
  text("description", "Description", true),
  choice("category", "Property category", [
    "BELONGINGS",
    "VALUABLES",
    "PROHIBITED",
  ]),
  { ...number("quantity", "Quantity", true, 1, 100000), default: 1 },
  text("storage_location", "Storage location"),
  text("client_acknowledgment", "Client acknowledgment", true),
];
