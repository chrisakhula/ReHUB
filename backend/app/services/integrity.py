"""Billing-to-GL Financial Integrity Diagnostic Service.

Provides comprehensive diagnostic reconciliation between business transactions
(invoices, payments, write-offs, credit notes) and General Ledger journal lines.
Strictly non-destructive: Detects and reports anomalies without modifying historical data.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.money import money
from app.models.billing import Invoice, Payment, WriteOff, CreditNote
from app.models.finance import FinanceJournalEntry, FinanceJournalLine, FinanceAccount
from app.schemas.billing import BillingGlIntegrityReport, IntegrityRecord


class BillingGlIntegrityService:
    def __init__(self, db: Session, facility_id: Optional[UUID] = None):
        self.db = db
        if not facility_id:
            from app.models.identity import Facility
            self.facility_id = self.db.scalar(select(Facility.id))
        else:
            self.facility_id = facility_id

    def scan_all(self) -> BillingGlIntegrityReport:
        records: list[IntegrityRecord] = []
        matched = 0
        mismatches = 0
        missing_journals = 0
        duplicate_journals = 0

        # 1. Scan Invoices (issued, partial, paid, written_off)
        invoices = self.db.scalars(
            select(Invoice).filter(
                Invoice.facility_id == self.facility_id,
                Invoice.status.in_(("ISSUED", "PARTIAL", "PAID", "WRITTEN_OFF")),
            )
        ).all()

        for inv in invoices:
            if inv.total_amount == Decimal("0.00"):
                continue

            entries = self.db.scalars(
                select(FinanceJournalEntry).filter(
                    FinanceJournalEntry.facility_id == self.facility_id,
                    FinanceJournalEntry.source_module == "BILLING_INVOICE",
                    FinanceJournalEntry.source_id == str(inv.id),
                    FinanceJournalEntry.status == "POSTED",
                )
            ).all()

            if len(entries) == 0:
                missing_journals += 1
                records.append(
                    IntegrityRecord(
                        entity_type="INVOICE",
                        reference=inv.invoice_number,
                        source_id=str(inv.id),
                        billing_amount=inv.total_amount,
                        gl_amount=Decimal("0.00"),
                        difference=inv.total_amount,
                        status="MISSING_JOURNAL",
                        details=f"Invoice {inv.invoice_number} is {inv.status} in Billing, but has no posted GL journal entry.",
                    )
                )
            elif len(entries) > 1:
                duplicate_journals += 1
                total_gl_dr = Decimal("0.00")
                for entry in entries:
                    for line in entry.lines:
                        if line.account.code == "1200":
                            total_gl_dr += line.debit
                records.append(
                    IntegrityRecord(
                        entity_type="INVOICE",
                        reference=inv.invoice_number,
                        source_id=str(inv.id),
                        billing_amount=inv.total_amount,
                        gl_amount=total_gl_dr,
                        difference=inv.total_amount - total_gl_dr,
                        status="DUPLICATE_JOURNAL",
                        details=f"Invoice {inv.invoice_number} has {len(entries)} posted GL journal entries.",
                    )
                )
            else:
                entry = entries[0]
                gl_debit = Decimal("0.00")
                for line in entry.lines:
                    if line.account.code == "1200":
                        gl_debit += line.debit
                diff = inv.total_amount - gl_debit
                if diff == Decimal("0.00"):
                    matched += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="INVOICE",
                            reference=inv.invoice_number,
                            source_id=str(inv.id),
                            billing_amount=inv.total_amount,
                            gl_amount=gl_debit,
                            difference=Decimal("0.00"),
                            status="MATCHED",
                            details="Balanced with AR (1200) debit.",
                        )
                    )
                else:
                    mismatches += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="INVOICE",
                            reference=inv.invoice_number,
                            source_id=str(inv.id),
                            billing_amount=inv.total_amount,
                            gl_amount=gl_debit,
                            difference=diff,
                            status="MISMATCH",
                            details=f"Billing amount ({inv.total_amount}) != GL posted AR debit ({gl_debit}).",
                        )
                    )

        # 2. Scan Payments (completed)
        payments = self.db.scalars(
            select(Payment).filter(
                Payment.facility_id == self.facility_id,
                Payment.status == "COMPLETED",
            )
        ).all()

        for pay in payments:
            entries = self.db.scalars(
                select(FinanceJournalEntry).filter(
                    FinanceJournalEntry.facility_id == self.facility_id,
                    FinanceJournalEntry.source_module == "BILLING_PAYMENT",
                    FinanceJournalEntry.source_id == str(pay.id),
                    FinanceJournalEntry.status == "POSTED",
                )
            ).all()

            if len(entries) == 0:
                missing_journals += 1
                records.append(
                    IntegrityRecord(
                        entity_type="PAYMENT",
                        reference=pay.transaction_reference,
                        source_id=str(pay.id),
                        billing_amount=pay.amount,
                        gl_amount=Decimal("0.00"),
                        difference=pay.amount,
                        status="MISSING_JOURNAL",
                        details=f"Payment {pay.transaction_reference} has no posted GL journal entry.",
                    )
                )
            elif len(entries) > 1:
                duplicate_journals += 1
                total_gl_cr = Decimal("0.00")
                for entry in entries:
                    for line in entry.lines:
                        if line.account.code == "1200":
                            total_gl_cr += line.credit
                records.append(
                    IntegrityRecord(
                        entity_type="PAYMENT",
                        reference=pay.transaction_reference,
                        source_id=str(pay.id),
                        billing_amount=pay.amount,
                        gl_amount=total_gl_cr,
                        difference=pay.amount - total_gl_cr,
                        status="DUPLICATE_JOURNAL",
                        details=f"Payment {pay.transaction_reference} has {len(entries)} posted GL journal entries.",
                    )
                )
            else:
                entry = entries[0]
                gl_credit = Decimal("0.00")
                for line in entry.lines:
                    if line.account.code == "1200":
                        gl_credit += line.credit
                diff = pay.amount - gl_credit
                if diff == Decimal("0.00"):
                    matched += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="PAYMENT",
                            reference=pay.transaction_reference,
                            source_id=str(pay.id),
                            billing_amount=pay.amount,
                            gl_amount=gl_credit,
                            difference=Decimal("0.00"),
                            status="MATCHED",
                            details="Balanced with AR (1200) credit.",
                        )
                    )
                else:
                    mismatches += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="PAYMENT",
                            reference=pay.transaction_reference,
                            source_id=str(pay.id),
                            billing_amount=pay.amount,
                            gl_amount=gl_credit,
                            difference=diff,
                            status="MISMATCH",
                            details=f"Payment amount ({pay.amount}) != GL posted AR credit ({gl_credit}).",
                        )
                    )

        # 3. Scan Write-Offs (posted or approved)
        writeoffs = self.db.scalars(
            select(WriteOff).filter(
                WriteOff.facility_id == self.facility_id,
                WriteOff.status.in_(("APPROVED", "POSTED")),
            )
        ).all()

        for wo in writeoffs:
            entries = self.db.scalars(
                select(FinanceJournalEntry).filter(
                    FinanceJournalEntry.facility_id == self.facility_id,
                    FinanceJournalEntry.source_module == "BILLING_WRITEOFF",
                    FinanceJournalEntry.source_id == str(wo.id),
                    FinanceJournalEntry.status == "POSTED",
                )
            ).all()

            if len(entries) == 0:
                missing_journals += 1
                records.append(
                    IntegrityRecord(
                        entity_type="WRITEOFF",
                        reference=wo.reference_code or str(wo.id),
                        source_id=str(wo.id),
                        billing_amount=wo.amount,
                        gl_amount=Decimal("0.00"),
                        difference=wo.amount,
                        status="MISSING_JOURNAL",
                        details=f"Write-off {wo.reference_code} has no posted GL bad debt journal.",
                    )
                )
            else:
                entry = entries[0]
                gl_bad_debt = Decimal("0.00")
                for line in entry.lines:
                    if line.account.code == "6000":
                        gl_bad_debt += line.debit
                diff = wo.amount - gl_bad_debt
                if diff == Decimal("0.00"):
                    matched += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="WRITEOFF",
                            reference=wo.reference_code or str(wo.id),
                            source_id=str(wo.id),
                            billing_amount=wo.amount,
                            gl_amount=gl_bad_debt,
                            difference=Decimal("0.00"),
                            status="MATCHED",
                            details="Balanced with Bad Debt (6000) debit.",
                        )
                    )
                else:
                    mismatches += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="WRITEOFF",
                            reference=wo.reference_code or str(wo.id),
                            source_id=str(wo.id),
                            billing_amount=wo.amount,
                            gl_amount=gl_bad_debt,
                            difference=diff,
                            status="MISMATCH",
                            details=f"Write-off amount ({wo.amount}) != GL Bad Debt debit ({gl_bad_debt}).",
                        )
                    )

        # 4. Scan Credit Notes (posted or approved)
        credit_notes = self.db.scalars(
            select(CreditNote).filter(
                CreditNote.facility_id == self.facility_id,
                CreditNote.status.in_(("APPROVED", "POSTED")),
            )
        ).all()

        for cn in credit_notes:
            entries = self.db.scalars(
                select(FinanceJournalEntry).filter(
                    FinanceJournalEntry.facility_id == self.facility_id,
                    FinanceJournalEntry.source_module == "CREDIT_NOTE",
                    FinanceJournalEntry.source_id == str(cn.id),
                    FinanceJournalEntry.status == "POSTED",
                )
            ).all()

            if len(entries) == 0:
                missing_journals += 1
                records.append(
                    IntegrityRecord(
                        entity_type="CREDIT_NOTE",
                        reference=cn.credit_number,
                        source_id=str(cn.id),
                        billing_amount=cn.amount,
                        gl_amount=Decimal("0.00"),
                        difference=cn.amount,
                        status="MISSING_JOURNAL",
                        details=f"Credit Note {cn.credit_number} has no posted GL revenue adjustment journal.",
                    )
                )
            else:
                entry = entries[0]
                gl_rev_adj = Decimal("0.00")
                for line in entry.lines:
                    if line.account.code in ("4000", "4010"):
                        gl_rev_adj += line.debit
                diff = cn.amount - gl_rev_adj
                if diff == Decimal("0.00"):
                    matched += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="CREDIT_NOTE",
                            reference=cn.credit_number,
                            source_id=str(cn.id),
                            billing_amount=cn.amount,
                            gl_amount=gl_rev_adj,
                            difference=Decimal("0.00"),
                            status="MATCHED",
                            details="Balanced with Revenue debit.",
                        )
                    )
                else:
                    mismatches += 1
                    records.append(
                        IntegrityRecord(
                            entity_type="CREDIT_NOTE",
                            reference=cn.credit_number,
                            source_id=str(cn.id),
                            billing_amount=cn.amount,
                            gl_amount=gl_rev_adj,
                            difference=diff,
                            status="MISMATCH",
                            details=f"Credit Note amount ({cn.amount}) != GL Revenue debit ({gl_rev_adj}).",
                        )
                    )

        total_checked = len(invoices) + len(payments) + len(writeoffs) + len(credit_notes)

        return BillingGlIntegrityReport(
            facility_id=self.facility_id,
            scanned_at=datetime.now(timezone.utc),
            invoices_checked=len(invoices),
            payments_checked=len(payments),
            writeoffs_checked=len(writeoffs),
            credit_notes_checked=len(credit_notes),
            total_records=total_checked,
            matched=matched,
            mismatches=mismatches,
            missing_journals=missing_journals,
            duplicate_journals=duplicate_journals,
            records=records,
        )
