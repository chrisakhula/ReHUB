"""Finance ledger service."""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import audit
from app.models.finance import (
    FinanceAccount,
    FinanceCashReconciliation,
    FinanceExpenseCategory,
    FinanceExpenseVoucher,
    FinanceFiscalPeriod,
    FinanceJournalEntry,
    FinanceJournalLine,
    FinancePaymentReconciliation,
    FinanceSupplier,
    FinanceSupplierInvoice,
    FinanceSupplierInvoiceItem,
    FinanceSupplierPayment,
)
from app.models.identity import utcnow
from app.schemas.finance import (
    AccountIn,
    CashReconciliationIn,
    ExpenseCategoryIn,
    ExpenseVoucherIn,
    FiscalPeriodIn,
    ManualJournalIn,
    PaymentReconciliationIn,
    SupplierIn,
    SupplierInvoiceIn,
    SupplierPaymentIn,
)

DEFAULT_ACCOUNTS = [
    ("1000", "Cash on hand", "ASSET", "DEBIT"),
    ("1010", "M-Pesa control account", "ASSET", "DEBIT"),
    ("1020", "Card settlement account", "ASSET", "DEBIT"),
    ("1030", "Bank account", "ASSET", "DEBIT"),
    ("1100", "Inventory and supplies", "ASSET", "DEBIT"),
    ("1200", "Accounts receivable", "ASSET", "DEBIT"),
    ("1210", "Input VAT receivable", "ASSET", "DEBIT"),
    ("2000", "Accounts payable", "LIABILITY", "CREDIT"),
    ("2100", "VAT payable", "LIABILITY", "CREDIT"),
    ("2200", "Client deposits", "LIABILITY", "CREDIT"),
    ("3000", "Accumulated fund", "EQUITY", "CREDIT"),
    ("4000", "Programme revenue", "REVENUE", "CREDIT"),
    ("4100", "Consultation revenue", "REVENUE", "CREDIT"),
    ("4200", "Pharmacy revenue", "REVENUE", "CREDIT"),
    ("4300", "Cash overage income", "REVENUE", "CREDIT"),
    ("5000", "Direct care cost of services", "COGS", "DEBIT"),
    ("5100", "Pharmacy cost of goods sold", "COGS", "DEBIT"),
    ("6000", "General operating expense", "EXPENSE", "DEBIT"),
    ("6100", "Utilities expense", "EXPENSE", "DEBIT"),
    ("6200", "Staff welfare expense", "EXPENSE", "DEBIT"),
    ("6300", "Repairs and maintenance", "EXPENSE", "DEBIT"),
    ("6400", "Clinical supplies expense", "EXPENSE", "DEBIT"),
    ("6500", "Inventory wastage expense", "EXPENSE", "DEBIT"),
    ("6600", "Cash shortage expense", "EXPENSE", "DEBIT"),
]

DEFAULT_EXPENSE_CATEGORIES = {
    "Utilities": "6100",
    "Staff welfare": "6200",
    "Repairs and maintenance": "6300",
    "Clinical supplies": "6400",
    "General operations": "6000",
}

PAYMENT_ACCOUNT_BY_METHOD = {
    "CASH": "1000",
    "MPESA": "1010",
    "M-PESA": "1010",
    "CARD": "1020",
    "BANK": "1030",
    "TRANSFER": "1030",
}


def money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def normal_balance_for(account_type: str) -> str:
    return "DEBIT" if account_type in {"ASSET", "EXPENSE", "COGS"} else "CREDIT"


class FinanceLedgerService:
    def __init__(self, db: Session, request: Request | None, actor):
        self.db = db
        self.request = request
        self.actor = actor
        self.facility_id = actor.facility_id

    def event(self, action: str, entity, new: dict | None = None, reason: str = ""):
        if self.request is None:
            return
        audit(
            self.db,
            self.request,
            action,
            entity.__class__.__name__,
            self.actor,
            getattr(entity, "id", None),
            new=new,
            reason=reason,
        )

    def account_by_code(self, code: str) -> FinanceAccount:
        account = self.db.scalar(
            select(FinanceAccount).where(
                FinanceAccount.facility_id == self.facility_id,
                FinanceAccount.code == code,
                FinanceAccount.is_active.is_(True),
            )
        )
        if not account:
            raise HTTPException(422, f"Finance account {code} is not configured")
        return account

    def account_by_id(self, account_id: UUID) -> FinanceAccount:
        account = self.db.get(FinanceAccount, account_id)
        if not account or account.facility_id != self.facility_id or not account.is_active:
            raise HTTPException(422, "Finance account is not available")
        return account

    def payment_account(self, method: str, account_id: UUID | None = None) -> FinanceAccount:
        if account_id:
            return self.account_by_id(account_id)
        code = PAYMENT_ACCOUNT_BY_METHOD.get(method.upper())
        if not code:
            raise HTTPException(422, "Choose a payment account for this payment method")
        return self.account_by_code(code)

    def validate_period(
        self, posting_date: date, allow_locked: bool = False
    ) -> FinanceFiscalPeriod:
        period = self.db.scalar(
            select(FinanceFiscalPeriod).where(
                FinanceFiscalPeriod.facility_id == self.facility_id,
                FinanceFiscalPeriod.start_date <= posting_date,
                FinanceFiscalPeriod.end_date >= posting_date,
            )
        )
        if not period:
            raise HTTPException(422, "Posting date does not fall within a configured fiscal period")
        if period.status == "CLOSED":
            raise HTTPException(409, f"Fiscal period {period.name} is closed")
        if period.status == "LOCKED" and not allow_locked:
            raise HTTPException(409, f"Fiscal period {period.name} is locked")
        return period

    def seed_defaults(self) -> dict:
        created_accounts = 0
        for code, name, account_type, balance in DEFAULT_ACCOUNTS:
            existing = self.db.scalar(
                select(FinanceAccount).where(
                    FinanceAccount.facility_id == self.facility_id,
                    FinanceAccount.code == code,
                )
            )
            if existing:
                continue
            self.db.add(
                FinanceAccount(
                    facility_id=self.facility_id,
                    code=code,
                    name=name,
                    type=account_type,
                    normal_balance=balance,
                    system_account=True,
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
            )
            created_accounts += 1
        self.db.flush()

        created_categories = 0
        for name, code in DEFAULT_EXPENSE_CATEGORIES.items():
            existing = self.db.scalar(
                select(FinanceExpenseCategory).where(
                    FinanceExpenseCategory.facility_id == self.facility_id,
                    FinanceExpenseCategory.name == name,
                )
            )
            if existing:
                continue
            account = self.account_by_code(code)
            self.db.add(
                FinanceExpenseCategory(
                    facility_id=self.facility_id,
                    name=name,
                    account_id=account.id,
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
            )
            created_categories += 1

        today = date.today()
        period = self.db.scalar(
            select(FinanceFiscalPeriod).where(
                FinanceFiscalPeriod.facility_id == self.facility_id,
                FinanceFiscalPeriod.start_date <= today,
                FinanceFiscalPeriod.end_date >= today,
            )
        )
        created_period = False
        if not period:
            period = FinanceFiscalPeriod(
                facility_id=self.facility_id,
                name=f"FY {today.year}",
                start_date=date(today.year, 1, 1),
                end_date=date(today.year, 12, 31),
                status="OPEN",
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
            self.db.add(period)
            created_period = True

        self.db.flush()
        self.event(
            "finance.seeded",
            period,
            new={
                "accounts": created_accounts,
                "expense_categories": created_categories,
                "fiscal_period_created": created_period,
            },
        )
        return {
            "created_accounts": created_accounts,
            "created_expense_categories": created_categories,
            "created_current_period": created_period,
        }

    def create_account(self, data: AccountIn) -> FinanceAccount:
        account = FinanceAccount(
            facility_id=self.facility_id,
            code=data.code.strip(),
            name=data.name.strip(),
            type=data.type,
            normal_balance=data.normal_balance or normal_balance_for(data.type),
            description=data.description,
            is_active=data.is_active,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(account)
        self.db.flush()
        self.event("finance.account_created", account, new={"code": account.code})
        return account

    def create_fiscal_period(self, data: FiscalPeriodIn) -> FinanceFiscalPeriod:
        period = FinanceFiscalPeriod(
            facility_id=self.facility_id,
            name=data.name,
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(period)
        self.db.flush()
        self.event("finance.fiscal_period_created", period, new={"name": period.name})
        return period

    def set_period_status(self, period_id: UUID, status: str) -> FinanceFiscalPeriod:
        period = self.db.get(FinanceFiscalPeriod, period_id)
        if not period or period.facility_id != self.facility_id:
            raise HTTPException(404, "Fiscal period not found")
        period.status = status
        period.updated_by = self.actor.id
        if status == "LOCKED":
            period.locked_by = self.actor.id
            period.locked_at = utcnow()
        if status == "CLOSED":
            period.closed_by = self.actor.id
            period.closed_at = utcnow()
        self.db.flush()
        self.event("finance.fiscal_period_status_changed", period, new={"status": status})
        return period

    def post_journal(
        self,
        *,
        entry_date: date,
        reference: str,
        description: str,
        source_module: str,
        posting_type: str,
        source_id: str | None,
        lines: Iterable[dict],
        status: str = "POSTED",
        allow_locked: bool = False,
    ) -> FinanceJournalEntry | None:
        self.validate_period(entry_date, allow_locked=allow_locked)
        if source_id:
            existing = self.db.scalar(
                select(FinanceJournalEntry).where(
                    FinanceJournalEntry.facility_id == self.facility_id,
                    FinanceJournalEntry.source_module == source_module,
                    FinanceJournalEntry.source_id == source_id,
                    FinanceJournalEntry.posting_type == posting_type,
                )
            )
            if existing:
                return existing

        prepared = []
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        for line in lines:
            account = (
                self.account_by_id(line["account_id"])
                if line.get("account_id")
                else self.account_by_code(line["account_code"])
            )
            debit = money(line.get("debit"))
            credit = money(line.get("credit"))
            if debit and credit:
                raise HTTPException(422, "A journal line cannot have both debit and credit")
            if not debit and not credit:
                continue
            prepared.append((account, debit, credit, line.get("description") or description))
            total_debit += debit
            total_credit += credit

        if not prepared:
            return None
        if total_debit != total_credit:
            raise HTTPException(422, f"Journal is unbalanced: {total_debit} != {total_credit}")

        entry = FinanceJournalEntry(
            facility_id=self.facility_id,
            entry_date=entry_date,
            reference=reference,
            description=description,
            source_module=source_module,
            source_id=source_id,
            posting_type=posting_type,
            status=status,
            posted_at=utcnow() if status == "POSTED" else None,
            approved_by=self.actor.id if status == "POSTED" else None,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(entry)
        self.db.flush()
        for account, debit, credit, line_description in prepared:
            self.db.add(
                FinanceJournalLine(
                    journal_entry_id=entry.id,
                    account_id=account.id,
                    debit=debit,
                    credit=credit,
                    description=line_description,
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
            )
        self.db.flush()
        self.event(
            "finance.journal_posted",
            entry,
            new={"reference": reference, "debit": str(total_debit), "credit": str(total_credit)},
        )
        return entry

    def create_manual_journal(self, data: ManualJournalIn) -> FinanceJournalEntry:
        return self.post_journal(
            entry_date=data.entry_date,
            reference=data.reference or f"MANUAL-{datetime.utcnow().timestamp():.0f}",
            description=data.description,
            source_module="FINANCE",
            source_id=None,
            posting_type="MANUAL",
            status="DRAFT",
            lines=[line.model_dump() for line in data.lines],
        )

    def approve_journal(self, journal_id: UUID) -> FinanceJournalEntry:
        journal = self.db.scalar(
            select(FinanceJournalEntry)
            .options(selectinload(FinanceJournalEntry.lines))
            .where(
                FinanceJournalEntry.id == journal_id,
                FinanceJournalEntry.facility_id == self.facility_id,
            )
        )
        if not journal:
            raise HTTPException(404, "Journal not found")
        if journal.status not in {"DRAFT", "SUBMITTED"}:
            raise HTTPException(409, f"Journal status is {journal.status}")
        self.validate_period(journal.entry_date)
        debit = sum((money(line.debit) for line in journal.lines), Decimal("0.00"))
        credit = sum((money(line.credit) for line in journal.lines), Decimal("0.00"))
        if debit != credit:
            raise HTTPException(422, "Journal is unbalanced")
        journal.status = "POSTED"
        journal.approved_by = self.actor.id
        journal.posted_at = utcnow()
        journal.updated_by = self.actor.id
        self.db.flush()
        self.event("finance.journal_approved", journal, new={"status": journal.status})
        return journal

    def reverse_journal(self, journal_id: UUID) -> FinanceJournalEntry:
        original = self.db.scalar(
            select(FinanceJournalEntry)
            .options(selectinload(FinanceJournalEntry.lines))
            .where(
                FinanceJournalEntry.id == journal_id,
                FinanceJournalEntry.facility_id == self.facility_id,
            )
        )
        if not original:
            raise HTTPException(404, "Journal not found")
        if original.status != "POSTED":
            raise HTTPException(409, "Only posted journals can be reversed")
        original.status = "REVERSED"
        original.updated_by = self.actor.id
        reversal = self.post_journal(
            entry_date=date.today(),
            reference=f"REV-{original.reference}",
            description=f"Reversal of {original.reference}",
            source_module=original.source_module,
            source_id=str(original.id),
            posting_type="REVERSAL",
            lines=[
                {
                    "account_id": line.account_id,
                    "debit": line.credit,
                    "credit": line.debit,
                    "description": f"Reversal of {original.reference}",
                }
                for line in original.lines
            ],
        )
        reversal.reversed_entry_id = original.id
        self.db.flush()
        self.event("finance.journal_reversed", original, new={"reversal_id": str(reversal.id)})
        return reversal

    def create_expense_category(self, data: ExpenseCategoryIn) -> FinanceExpenseCategory:
        category = FinanceExpenseCategory(
            facility_id=self.facility_id,
            name=data.name,
            description=data.description,
            account_id=self.account_by_id(data.account_id).id,
            is_active=data.is_active,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(category)
        self.db.flush()
        return category

    def create_expense(self, data: ExpenseVoucherIn) -> FinanceExpenseVoucher:
        voucher = FinanceExpenseVoucher(
            facility_id=self.facility_id,
            expense_category_id=data.expense_category_id,
            amount=money(data.amount),
            payment_method=data.payment_method,
            payment_account_id=data.payment_account_id,
            paid_to=data.paid_to,
            reference=data.reference,
            description=data.description,
            expense_date=data.expense_date,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(voucher)
        self.db.flush()
        self.event("finance.expense_created", voucher, new={"amount": str(voucher.amount)})
        return voucher

    def approve_expense(self, voucher_id: UUID) -> FinanceExpenseVoucher:
        voucher = self.db.get(FinanceExpenseVoucher, voucher_id)
        if not voucher or voucher.facility_id != self.facility_id:
            raise HTTPException(404, "Expense voucher not found")
        if voucher.status == "APPROVED":
            raise HTTPException(409, "Expense voucher is already approved")
        category = self.db.get(FinanceExpenseCategory, voucher.expense_category_id)
        payment_account = self.payment_account(voucher.payment_method, voucher.payment_account_id)
        self.post_journal(
            entry_date=voucher.expense_date,
            reference=voucher.reference or f"EXP-{str(voucher.id)[:8]}",
            description=voucher.description or f"Expense: {category.name}",
            source_module="EXPENSE",
            source_id=str(voucher.id),
            posting_type="EXPENSE",
            lines=[
                {"account_id": category.account_id, "debit": voucher.amount, "credit": 0},
                {"account_id": payment_account.id, "debit": 0, "credit": voucher.amount},
            ],
        )
        voucher.status = "APPROVED"
        voucher.approved_by = self.actor.id
        voucher.approved_at = utcnow()
        voucher.updated_by = self.actor.id
        self.db.flush()
        return voucher

    def create_supplier(self, data: SupplierIn) -> FinanceSupplier:
        supplier = FinanceSupplier(
            facility_id=self.facility_id,
            **data.model_dump(),
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(supplier)
        self.db.flush()
        return supplier

    def create_supplier_invoice(self, data: SupplierInvoiceIn) -> FinanceSupplierInvoice:
        supplier = self.db.get(FinanceSupplier, data.supplier_id)
        if not supplier or supplier.facility_id != self.facility_id:
            raise HTTPException(422, "Supplier is not available")
        invoice = FinanceSupplierInvoice(
            facility_id=self.facility_id,
            supplier_id=data.supplier_id,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            invoice_type=data.invoice_type,
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(invoice)
        self.db.flush()

        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        for item in data.items:
            self.account_by_id(item.account_id)
            line_total = money(item.quantity * item.unit_cost - item.discount)
            tax_amount = money(line_total * item.tax_rate / Decimal("100"))
            subtotal += line_total
            tax_total += tax_amount
            self.db.add(
                FinanceSupplierInvoiceItem(
                    supplier_invoice_id=invoice.id,
                    account_id=item.account_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    discount=item.discount,
                    tax_rate=item.tax_rate,
                    line_total=line_total,
                    tax_amount=tax_amount,
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
            )
        invoice.subtotal = money(subtotal)
        invoice.tax_amount = money(tax_total)
        invoice.total_amount = money(subtotal + tax_total)
        self.db.flush()
        self.event(
            "finance.supplier_invoice_created",
            invoice,
            new={"invoice_number": invoice.invoice_number, "total": str(invoice.total_amount)},
        )
        return invoice

    def approve_supplier_invoice(self, invoice_id: UUID) -> FinanceSupplierInvoice:
        invoice = self.db.scalar(
            select(FinanceSupplierInvoice)
            .options(selectinload(FinanceSupplierInvoice.items))
            .where(
                FinanceSupplierInvoice.id == invoice_id,
                FinanceSupplierInvoice.facility_id == self.facility_id,
            )
        )
        if not invoice:
            raise HTTPException(404, "Supplier invoice not found")
        if invoice.status == "APPROVED":
            raise HTTPException(409, "Supplier invoice is already approved")
        lines = [
            {
                "account_id": item.account_id,
                "debit": item.line_total,
                "credit": 0,
                "description": item.description,
            }
            for item in invoice.items
        ]
        if money(invoice.tax_amount) > 0:
            lines.append(
                {
                    "account_code": "1210",
                    "debit": invoice.tax_amount,
                    "credit": 0,
                    "description": "Input VAT",
                }
            )
        lines.append(
            {
                "account_code": "2000",
                "debit": 0,
                "credit": invoice.total_amount,
                "description": "Accounts payable",
            }
        )
        self.post_journal(
            entry_date=invoice.invoice_date,
            reference=invoice.invoice_number,
            description=f"Supplier invoice {invoice.invoice_number}",
            source_module="SUPPLIER_INVOICE",
            source_id=str(invoice.id),
            posting_type="SUPPLIER_INVOICE",
            lines=lines,
        )
        invoice.status = "APPROVED"
        invoice.approved_by = self.actor.id
        invoice.approved_at = utcnow()
        invoice.updated_by = self.actor.id
        self.db.flush()
        return invoice

    def pay_supplier_invoice(
        self, invoice_id: UUID, data: SupplierPaymentIn
    ) -> FinanceSupplierPayment:
        invoice = self.db.get(FinanceSupplierInvoice, invoice_id)
        if not invoice or invoice.facility_id != self.facility_id:
            raise HTTPException(404, "Supplier invoice not found")
        paid = money(
            self.db.scalar(
                select(func.coalesce(func.sum(FinanceSupplierPayment.amount), 0)).where(
                    FinanceSupplierPayment.supplier_invoice_id == invoice_id
                )
            )
        )
        balance = money(invoice.total_amount) - paid
        amount = money(data.amount)
        if amount > balance:
            raise HTTPException(422, f"Payment exceeds outstanding balance {balance}")
        payment_account = self.account_by_id(data.payment_account_id)
        payment = FinanceSupplierPayment(
            supplier_invoice_id=invoice_id,
            amount=amount,
            payment_method=data.payment_method,
            payment_account_id=payment_account.id,
            payment_reference=data.payment_reference,
            payment_date=data.payment_date,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(payment)
        self.db.flush()
        self.post_journal(
            entry_date=data.payment_date,
            reference=data.payment_reference or f"PAY-{invoice.invoice_number}",
            description=f"Supplier payment {invoice.invoice_number}",
            source_module="SUPPLIER_PAYMENT",
            source_id=str(payment.id),
            posting_type="SUPPLIER_PAYMENT",
            lines=[
                {"account_code": "2000", "debit": amount, "credit": 0},
                {"account_id": payment_account.id, "debit": 0, "credit": amount},
            ],
        )
        invoice.status = "PAID" if amount >= balance else "PARTIAL"
        self.db.flush()
        return payment

    def create_cash_reconciliation(
        self, data: CashReconciliationIn
    ) -> FinanceCashReconciliation:
        variance = money(data.counted_cash - data.expected_cash)
        recon = FinanceCashReconciliation(
            facility_id=self.facility_id,
            period_date=data.period_date,
            cashier_name=data.cashier_name,
            opening_cash=money(data.opening_cash),
            expected_cash=money(data.expected_cash),
            counted_cash=money(data.counted_cash),
            variance=variance,
            reviewed_by=self.actor.id,
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(recon)
        self.db.flush()
        if variance < 0:
            self.post_journal(
                entry_date=data.period_date,
                reference=f"CASH-{str(recon.id)[:8]}",
                description="Cash reconciliation shortage",
                source_module="CASH_RECONCILIATION",
                source_id=str(recon.id),
                posting_type="CASH_SHORTAGE",
                lines=[
                    {"account_code": "6600", "debit": abs(variance), "credit": 0},
                    {"account_code": "1000", "debit": 0, "credit": abs(variance)},
                ],
            )
        elif variance > 0:
            self.post_journal(
                entry_date=data.period_date,
                reference=f"CASH-{str(recon.id)[:8]}",
                description="Cash reconciliation overage",
                source_module="CASH_RECONCILIATION",
                source_id=str(recon.id),
                posting_type="CASH_OVERAGE",
                lines=[
                    {"account_code": "1000", "debit": variance, "credit": 0},
                    {"account_code": "4300", "debit": 0, "credit": variance},
                ],
            )
        return recon

    def create_payment_reconciliation(
        self, data: PaymentReconciliationIn
    ) -> FinancePaymentReconciliation:
        recon = FinancePaymentReconciliation(
            facility_id=self.facility_id,
            method=data.method,
            period_date=data.period_date,
            system_total=money(data.system_total),
            statement_total=money(data.statement_total),
            variance=money(data.statement_total - data.system_total),
            missing_references=data.missing_references,
            duplicate_references=data.duplicate_references,
            checked_by=self.actor.id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(recon)
        self.db.flush()
        return recon

    def trial_balance(self, start: date | None = None, end: date | None = None) -> dict:
        query = (
            self.db.query(
                FinanceAccount.id,
                FinanceAccount.code,
                FinanceAccount.name,
                FinanceAccount.type,
                FinanceAccount.normal_balance,
                func.coalesce(func.sum(FinanceJournalLine.debit), 0).label("debit"),
                func.coalesce(func.sum(FinanceJournalLine.credit), 0).label("credit"),
            )
            .outerjoin(FinanceJournalLine, FinanceJournalLine.account_id == FinanceAccount.id)
            .outerjoin(
                FinanceJournalEntry,
                FinanceJournalEntry.id == FinanceJournalLine.journal_entry_id,
            )
            .filter(FinanceAccount.facility_id == self.facility_id)
            .filter(or_(FinanceJournalEntry.status == "POSTED", FinanceJournalEntry.id.is_(None)))
        )
        if start:
            query = query.filter(
                or_(FinanceJournalEntry.entry_date >= start, FinanceJournalEntry.id.is_(None))
            )
        if end:
            query = query.filter(
                or_(FinanceJournalEntry.entry_date <= end, FinanceJournalEntry.id.is_(None))
            )
        rows = query.group_by(FinanceAccount.id).order_by(FinanceAccount.code).all()

        items = []
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        for row in rows:
            debit = money(row.debit)
            credit = money(row.credit)
            balance = debit - credit if row.normal_balance == "DEBIT" else credit - debit
            items.append(
                {
                    "id": str(row.id),
                    "code": row.code,
                    "name": row.name,
                    "type": row.type,
                    "debit": float(debit),
                    "credit": float(credit),
                    "balance": float(balance),
                }
            )
            total_debit += debit
            total_credit += credit
        return {
            "items": items,
            "totals": {"debit": float(total_debit), "credit": float(total_credit)},
        }

    def profit_and_loss(self, start: date | None = None, end: date | None = None) -> dict:
        tb = self.trial_balance(start, end)
        sections = defaultdict(list)
        totals = defaultdict(Decimal)
        for item in tb["items"]:
            if item["type"] not in {"REVENUE", "COGS", "EXPENSE"}:
                continue
            amount = money(item["balance"])
            sections[item["type"]].append(item)
            totals[item["type"]] += amount
        gross_profit = totals["REVENUE"] - totals["COGS"]
        net_profit = gross_profit - totals["EXPENSE"]
        return {
            "income": sections["REVENUE"],
            "cogs": sections["COGS"],
            "expenses": sections["EXPENSE"],
            "totals": {
                "income": float(totals["REVENUE"]),
                "cogs": float(totals["COGS"]),
                "gross_profit": float(gross_profit),
                "expenses": float(totals["EXPENSE"]),
                "net_profit": float(net_profit),
            },
        }

    def balance_sheet(self, as_of: date | None = None) -> dict:
        tb = self.trial_balance(end=as_of)
        sections = defaultdict(list)
        totals = defaultdict(Decimal)
        retained = Decimal("0.00")
        for item in tb["items"]:
            amount = money(item["balance"])
            if item["type"] in {"REVENUE", "COGS", "EXPENSE"}:
                retained += amount if item["type"] == "REVENUE" else -amount
                continue
            sections[item["type"]].append(item)
            totals[item["type"]] += amount
        return {
            "assets": sections["ASSET"],
            "liabilities": sections["LIABILITY"],
            "equity": sections["EQUITY"],
            "totals": {
                "assets": float(totals["ASSET"]),
                "liabilities": float(totals["LIABILITY"]),
                "equity": float(totals["EQUITY"]),
                "retained_earnings": float(retained),
            },
        }
