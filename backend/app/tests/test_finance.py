import pytest
import uuid
from datetime import date

def post(client, url, json_data):
    response = client.post(f"/api/v1{url}", json=json_data)
    assert response.status_code in (200, 201), f"{response.status_code}: {response.text}"
    return response.json()

def test_finance_seed(clinical_client):
    # Seed
    res = clinical_client.post("/api/v1/finance/seed")
    assert res.status_code == 200
    data = res.json()
    assert "created_accounts" in data
    
def test_finance_account_creation(clinical_client):
    account_code = f"80{uuid.uuid4().hex[:2]}"
    account = post(clinical_client, "/finance/accounts", {
        "code": account_code,
        "name": "Test Bank Account",
        "type": "ASSET",
        "normal_balance": "DEBIT",
        "description": "A test bank account",
        "is_active": True
    })
    assert account["code"] == account_code
    assert account["type"] == "ASSET"

    accounts = clinical_client.get("/api/v1/finance/accounts").json()
    assert any(a["code"] == account_code for a in accounts["items"])

def test_finance_expense_and_journal(clinical_client):
    # Seed first to get default categories
    clinical_client.post("/api/v1/finance/seed")
    
    categories = clinical_client.get("/api/v1/finance/expense-categories").json()["items"]
    if not categories:
        pytest.skip("No expense categories found")
    
    cat = categories[0]
    
    expense = post(clinical_client, "/finance/expenses", {
        "expense_category_id": cat["id"],
        "amount": 1500.50,
        "payment_method": "CASH",
        "paid_to": "Test Vendor",
        "reference": f"EXP-{uuid.uuid4().hex[:6]}",
        "description": "Test expense",
        "expense_date": date.today().isoformat()
    })
    assert expense["amount"] == 1500.50
    assert expense["status"] == "DRAFT"
    
    # Approve expense
    approved = post(clinical_client, f"/finance/expenses/{expense['id']}/approve", {})
    assert approved["status"] == "APPROVED"
    
    # Check if journal was created
    journals = clinical_client.get("/api/v1/finance/journals").json()["items"]
    # The journal reference should match or contain the expense reference
    journal = next((j for j in journals if j["source_module"] == "EXPENSE"), None)
    assert journal is not None
    assert journal["status"] == "POSTED"
    
def test_supplier_invoice(clinical_client):
    # Create supplier
    supplier = post(clinical_client, "/finance/suppliers", {
        "name": f"Test Supplier {uuid.uuid4().hex[:4]}",
        "contact_person": "John Doe",
        "phone": "1234567890",
        "is_active": True
    })
    
    accounts = clinical_client.get("/api/v1/finance/accounts").json()["items"]
    expense_account = next((a for a in accounts if a["type"] == "EXPENSE"), None)
    if not expense_account:
        pytest.skip("No expense account found")

    invoice = post(clinical_client, "/finance/supplier-invoices", {
        "supplier_id": supplier["id"],
        "invoice_number": f"INV-{uuid.uuid4().hex[:6]}",
        "invoice_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "invoice_type": "DIRECT_EXPENSE",
        "items": [
            {
                "account_id": expense_account["id"],
                "description": "Services rendered",
                "quantity": 1,
                "unit_cost": 5000,
                "discount": 0,
                "tax_rate": 16
            }
        ]
    })
    
    assert invoice["status"] == "SUBMITTED"
    assert invoice["subtotal"] == 5000
    
    # Approve invoice
    approved = post(clinical_client, f"/finance/supplier-invoices/{invoice['id']}/approve", {})
    assert approved["status"] == "APPROVED"
