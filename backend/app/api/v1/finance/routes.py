"""Finance ledger API routes."""

import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.permissions import require_permission
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
)
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
from app.services.finance import FinanceLedgerService, money

router = APIRouter(
    prefix="/finance",
    tags=["Finance"],
    dependencies=[Depends(require_permission("finance.view"))],
)


def meta(total: int, page: int, page_size: int) -> dict:
    return {"total": total, "page": page, "pages": math.ceil(total / page_size) if page_size else 1}


def iso(value):
    return value.isoformat() if value else None


def account_row(row: FinanceAccount) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "type": row.type,
        "normal_balance": row.normal_balance,
        "description": row.description,
        "is_active": row.is_active,
    }


def period_row(row: FinanceFiscalPeriod) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "start_date": iso(row.start_date),
        "end_date": iso(row.end_date),
        "status": row.status,
        "notes": row.notes,
    }


def journal_row(row: FinanceJournalEntry, include_lines: bool = False) -> dict:
    debit = sum((money(line.debit) for line in row.lines), money(0)) if row.lines else money(0)
    credit = sum((money(line.credit) for line in row.lines), money(0)) if row.lines else money(0)
    payload = {
        "id": str(row.id),
        "entry_date": iso(row.entry_date),
        "reference": row.reference,
        "description": row.description,
        "source_module": row.source_module,
        "posting_type": row.posting_type,
        "status": row.status,
        "total_debit": float(debit),
        "total_credit": float(credit),
    }
    if include_lines:
        payload["lines"] = [
            {
                "id": str(line.id),
                "account_id": str(line.account_id),
                "account_code": line.account.code if line.account else "",
                "account_name": line.account.name if line.account else "",
                "debit": float(line.debit),
                "credit": float(line.credit),
                "description": line.description,
            }
            for line in row.lines
        ]
    return payload


def supplier_invoice_row(row: FinanceSupplierInvoice) -> dict:
    return {
        "id": str(row.id),
        "supplier_id": str(row.supplier_id),
        "invoice_number": row.invoice_number,
        "invoice_date": iso(row.invoice_date),
        "due_date": iso(row.due_date),
        "invoice_type": row.invoice_type,
        "subtotal": float(row.subtotal),
        "tax_amount": float(row.tax_amount),
        "total_amount": float(row.total_amount),
        "status": row.status,
        "notes": row.notes,
    }


def page_records(query, page: int, page_size: int, serializer) -> dict:
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [serializer(item) for item in items], "meta": meta(total, page, page_size)}


def service(db: Session, request: Request, actor) -> FinanceLedgerService:
    return FinanceLedgerService(db, request, actor)


@router.post("/seed")
def seed_finance(
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return service(db, request, actor).seed_defaults()


@router.get("/accounts")
def accounts(
    page: int = 1,
    page_size: int = Query(20, le=100),
    q: str = "",
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceAccount).filter(FinanceAccount.facility_id == actor.facility_id)
    if q:
        query = query.filter(
            or_(
                FinanceAccount.code.ilike(f"%{q}%"),
                FinanceAccount.name.ilike(f"%{q}%"),
            )
        )
    return page_records(query.order_by(FinanceAccount.code), page, page_size, account_row)


@router.post("/accounts", status_code=201)
def create_account(
    data: AccountIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return account_row(service(db, request, actor).create_account(data))


@router.get("/fiscal-periods")
def fiscal_periods(
    page: int = 1,
    page_size: int = Query(20, le=100),
    status: str = "",
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceFiscalPeriod).filter(
        FinanceFiscalPeriod.facility_id == actor.facility_id
    )
    if status:
        query = query.filter(FinanceFiscalPeriod.status == status)
    return page_records(
        query.order_by(FinanceFiscalPeriod.start_date.desc()), page, page_size, period_row
    )


@router.post("/fiscal-periods", status_code=201)
def create_fiscal_period(
    data: FiscalPeriodIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return period_row(service(db, request, actor).create_fiscal_period(data))


@router.post("/fiscal-periods/{period_id}/lock")
def lock_fiscal_period(
    period_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return period_row(service(db, request, actor).set_period_status(period_id, "LOCKED"))


@router.post("/fiscal-periods/{period_id}/close")
def close_fiscal_period(
    period_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return period_row(service(db, request, actor).set_period_status(period_id, "CLOSED"))


@router.post("/fiscal-periods/{period_id}/reopen")
def reopen_fiscal_period(
    period_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    return period_row(service(db, request, actor).set_period_status(period_id, "OPEN"))


@router.get("/journals")
def journals(
    page: int = 1,
    page_size: int = Query(20, le=100),
    q: str = "",
    status: str = "",
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = (
        db.query(FinanceJournalEntry)
        .options(selectinload(FinanceJournalEntry.lines))
        .filter(FinanceJournalEntry.facility_id == actor.facility_id)
    )
    if q:
        query = query.filter(
            or_(
                FinanceJournalEntry.reference.ilike(f"%{q}%"),
                FinanceJournalEntry.description.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(FinanceJournalEntry.status == status)
    if start:
        query = query.filter(FinanceJournalEntry.entry_date >= start)
    if end:
        query = query.filter(FinanceJournalEntry.entry_date <= end)
    return page_records(
        query.order_by(FinanceJournalEntry.entry_date.desc()), page, page_size, journal_row
    )


@router.post("/journals", status_code=201)
def create_manual_journal(
    data: ManualJournalIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    journal = service(db, request, actor).create_manual_journal(data)
    db.refresh(journal, attribute_names=["lines"])
    return journal_row(journal, include_lines=True)


@router.get("/journals/{journal_id}")
def journal_detail(
    journal_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    journal = db.scalar(
        select(FinanceJournalEntry)
        .options(selectinload(FinanceJournalEntry.lines).selectinload(FinanceJournalLine.account))
        .where(
            FinanceJournalEntry.id == journal_id,
            FinanceJournalEntry.facility_id == actor.facility_id,
        )
    )
    return journal_row(journal, include_lines=True)


@router.post("/journals/{journal_id}/approve")
def approve_journal(
    journal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.approve")),
):
    return journal_row(service(db, request, actor).approve_journal(journal_id))


@router.post("/journals/{journal_id}/reverse")
def reverse_journal(
    journal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.approve")),
):
    return journal_row(service(db, request, actor).reverse_journal(journal_id))


@router.get("/expense-categories")
def expense_categories(
    page: int = 1,
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceExpenseCategory).filter(
        FinanceExpenseCategory.facility_id == actor.facility_id
    )
    return page_records(
        query.order_by(FinanceExpenseCategory.name),
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
            "account_id": str(row.account_id),
            "is_active": row.is_active,
        },
    )


@router.post("/expense-categories", status_code=201)
def create_expense_category(
    data: ExpenseCategoryIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.configure")),
):
    row = service(db, request, actor).create_expense_category(data)
    return {"id": str(row.id), "name": row.name, "account_id": str(row.account_id)}


@router.get("/expenses")
def expenses(
    page: int = 1,
    page_size: int = Query(20, le=100),
    status: str = "",
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceExpenseVoucher).filter(
        FinanceExpenseVoucher.facility_id == actor.facility_id
    )
    if status:
        query = query.filter(FinanceExpenseVoucher.status == status)
    return page_records(
        query.order_by(FinanceExpenseVoucher.expense_date.desc()),
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "expense_date": iso(row.expense_date),
            "expense_category_id": str(row.expense_category_id),
            "amount": float(row.amount),
            "payment_method": row.payment_method,
            "paid_to": row.paid_to,
            "reference": row.reference,
            "status": row.status,
        },
    )


@router.post("/expenses", status_code=201)
def create_expense(
    data: ExpenseVoucherIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    row = service(db, request, actor).create_expense(data)
    return {"id": str(row.id), "amount": float(row.amount), "status": row.status}


@router.post("/expenses/{voucher_id}/approve")
def approve_expense(
    voucher_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.approve")),
):
    row = service(db, request, actor).approve_expense(voucher_id)
    return {"id": str(row.id), "status": row.status}


@router.get("/suppliers")
def suppliers(
    page: int = 1,
    page_size: int = Query(20, le=100),
    q: str = "",
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceSupplier).filter(FinanceSupplier.facility_id == actor.facility_id)
    if q:
        query = query.filter(FinanceSupplier.name.ilike(f"%{q}%"))
    return page_records(
        query.order_by(FinanceSupplier.name),
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "name": row.name,
            "contact_person": row.contact_person,
            "phone": row.phone,
            "tax_pin": row.tax_pin,
            "is_active": row.is_active,
        },
    )


@router.post("/suppliers", status_code=201)
def create_supplier(
    data: SupplierIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    row = service(db, request, actor).create_supplier(data)
    return {"id": str(row.id), "name": row.name}


@router.get("/supplier-invoices")
def supplier_invoices(
    page: int = 1,
    page_size: int = Query(20, le=100),
    status: str = "",
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceSupplierInvoice).filter(
        FinanceSupplierInvoice.facility_id == actor.facility_id
    )
    if status:
        query = query.filter(FinanceSupplierInvoice.status == status)
    return page_records(
        query.order_by(FinanceSupplierInvoice.invoice_date.desc()),
        page,
        page_size,
        supplier_invoice_row,
    )


@router.post("/supplier-invoices", status_code=201)
def create_supplier_invoice(
    data: SupplierInvoiceIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    return supplier_invoice_row(service(db, request, actor).create_supplier_invoice(data))


@router.post("/supplier-invoices/{invoice_id}/approve")
def approve_supplier_invoice(
    invoice_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.approve")),
):
    return supplier_invoice_row(service(db, request, actor).approve_supplier_invoice(invoice_id))


@router.post("/supplier-invoices/{invoice_id}/pay")
def pay_supplier_invoice(
    invoice_id: UUID,
    data: SupplierPaymentIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    row = service(db, request, actor).pay_supplier_invoice(invoice_id, data)
    return {"id": str(row.id), "amount": float(row.amount), "status": row.status}


@router.get("/cash-reconciliations")
def cash_reconciliations(
    page: int = 1,
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinanceCashReconciliation).filter(
        FinanceCashReconciliation.facility_id == actor.facility_id
    )
    return page_records(
        query.order_by(FinanceCashReconciliation.period_date.desc()),
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "period_date": iso(row.period_date),
            "cashier_name": row.cashier_name,
            "expected_cash": float(row.expected_cash),
            "counted_cash": float(row.counted_cash),
            "variance": float(row.variance),
            "status": row.status,
        },
    )


@router.post("/cash-reconciliations", status_code=201)
def create_cash_reconciliation(
    data: CashReconciliationIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    row = service(db, request, actor).create_cash_reconciliation(data)
    return {"id": str(row.id), "variance": float(row.variance), "status": row.status}


@router.get("/payment-reconciliations")
def payment_reconciliations(
    page: int = 1,
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.view")),
):
    query = db.query(FinancePaymentReconciliation).filter(
        FinancePaymentReconciliation.facility_id == actor.facility_id
    )
    return page_records(
        query.order_by(FinancePaymentReconciliation.period_date.desc()),
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "method": row.method,
            "period_date": iso(row.period_date),
            "system_total": float(row.system_total),
            "statement_total": float(row.statement_total),
            "variance": float(row.variance),
            "status": row.status,
        },
    )


@router.post("/payment-reconciliations", status_code=201)
def create_payment_reconciliation(
    data: PaymentReconciliationIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.edit")),
):
    row = service(db, request, actor).create_payment_reconciliation(data)
    return {"id": str(row.id), "variance": float(row.variance), "status": row.status}


@router.get("/reports/general-ledger")
def general_ledger(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reports")),
):
    rows = db.scalars(
        select(FinanceJournalEntry)
        .options(selectinload(FinanceJournalEntry.lines).selectinload(FinanceJournalLine.account))
        .where(
            FinanceJournalEntry.facility_id == actor.facility_id,
            FinanceJournalEntry.status == "POSTED",
        )
        .order_by(FinanceJournalEntry.entry_date.desc())
    ).all()
    filtered = [
        row
        for row in rows
        if (start is None or row.entry_date >= start) and (end is None or row.entry_date <= end)
    ]
    return {"items": [journal_row(row, include_lines=True) for row in filtered]}


@router.get("/reports/trial-balance")
def trial_balance(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reports")),
):
    return service(db, request, actor).trial_balance(start, end)


@router.get("/reports/profit-and-loss")
def profit_and_loss(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reports")),
):
    return service(db, request, actor).profit_and_loss(start, end)


@router.get("/reports/balance-sheet")
def balance_sheet(
    request: Request,
    as_of: date | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reports")),
):
    return service(db, request, actor).balance_sheet(as_of)
