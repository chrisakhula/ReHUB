# Financial Documents, PDFs & Structured Exports

## 1. Document Engine Architecture
Official financial documents are rendered server-side using `FinancialDocumentPdfBuilder` with configurable institutional branding:
```
Financial Entity
      ↓
Document Data Mapper
      ↓
PDF Builder (ReportLab / Direct Engine)
      ↓
Branded Stream (A4 / A5)
      ↓
Client Download / Browser Print Preview
```

## 2. Branding Configuration
Branding parameters are centrally managed and not hard-coded:
- Official Institution Name: `ARMS REHUB REHABILITATION CENTRE`
- Address: `P.O. Box 45210-00100, Nairobi, Kenya`
- Phone & Email: `+254 700 000 000`, `finance@rehub.local`
- Tax / KRA PIN: `P051234567Z`
- M-Pesa Paybill / Bank settlement details included in official document footers.

## 3. Documents Generated
| Document | Format | Reference Code | Use Case |
|---|---|---|---|
| Quotation / Cost Estimate | A4 | `EST-YYYY-NNNNN` | Commercial pre-admission quote |
| Financial Agreement | A4 | `FAG-YYYY-NNNNN` | Contractual fee agreement |
| Client Invoice | A4 | `INV-YYYY-NNNNN` | Formal billing request |
| Payment Receipt | A5 | `RCT-YYYY-NNNNN` | Proof of payment settlement |
| Client Account Statement | A4 | Subledger Snapshot | Transaction history & balance |
| Discharge Financial Clearance | A4 | `CLR-YYYY-NNNNN` | Exit financial certificate |
| Resident Funds Statement | A4 | `RFA-YYYY-NNNNN` | Pocket money custodial statement |

## 4. Structured Spreadsheet Exports (CSV & XLSX)
Server-side report generator `FinancialSpreadsheetExporter` produces structured CSV and Excel (`.xlsx`) files for:
- Accounts Receivable (AR) Aging Report
- Daily Collections Register (Cash, M-Pesa, Bank, Card)
- Client Account Balances
- Resident Funds Trust Liability Subledger
- Sponsor Balances & Statements
- Refunds & Reversals Register

### Export Audit Logging
Every file generated is logged to `billing_export_audits`:
- `user_id`
- `export_format`: `CSV`, `XLSX`, `PDF`, `PRINT`
- `report_type`
- `filter_parameters`
- `timestamp`
- `facility_id`
