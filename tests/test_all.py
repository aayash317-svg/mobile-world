import os
import json
import pytest
from decimal import Decimal
from app import create_app
from config import TestConfig
from models import db
from models.user import User
from models.product import Product
from models.order import Inventory, Order, OrderItem, PaymentRecord
from models.activity_log import ActivityLog
from services.order_service import OrderService
from services.inventory_service import InventoryService

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()

        # Create Admin
        admin = User(username="admin", email="admin@test.com", role="owner")
        admin.set_password("admin123")
        db.session.add(admin)

        # Create Test Products
        p1 = Product(
            sku="MW-TEST-001",
            name="OnePlus Nord CE 4 Test",
            brand="OnePlus",
            category="Mobile Phones",
            price=Decimal("25000.00"),
            description="Test smartphone",
            is_active=True
        )
        p2 = Product(
            sku="MW-TEST-002",
            name="67W GaN Charger Test",
            brand="Mobile World Gear",
            category="Accessories",
            price=Decimal("1200.00"),
            description="Test fast charger",
            is_active=True
        )
        db.session.add_all([p1, p2])
        db.session.flush()

        inv1 = Inventory(product_id=p1.id, quantity=1, low_stock_threshold=2)
        inv2 = Inventory(product_id=p2.id, quantity=10, low_stock_threshold=3)
        db.session.add_all([inv1, inv2])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()


# ==========================================================
# 1. AUTHENTICATION & SECURITY TESTS
# ==========================================================

def test_unauthorized_admin_api_rejected(client):
    """Unauthorized requests to private admin endpoints must return 401 or redirect."""
    res = client.get("/api/admin/orders")
    assert res.status_code == 401
    assert "Authentication required" in res.get_json()["error"]

    res_dash = client.get("/admin/dashboard")
    assert res_dash.status_code == 302
    assert "/admin/login" in res_dash.headers["Location"]

def test_admin_login_success_and_logout(client):
    """Valid credentials successfully authenticate and grant session access."""
    login_res = client.post("/admin/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    assert login_res.get_json()["message"] == "Login successful"

    # Now authorized
    orders_res = client.get("/api/admin/orders")
    assert orders_res.status_code == 200

    # Logout (supports both json 200 and redirect 302)
    logout_res = client.post("/admin/logout", json={})
    assert logout_res.status_code in (200, 302)

    # Back to unauthorized
    orders_res_after = client.get("/api/admin/orders")
    assert orders_res_after.status_code == 401

def test_admin_login_invalid_credentials(client):
    """Invalid credentials return 401 error."""
    res = client.post("/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert "Invalid username or password" in res.get_json()["error"]


# ==========================================================
# 2. CHECKOUT & SERVER-SIDE VALIDATION TESTS
# ==========================================================

def test_server_calculates_price_ignoring_client_tampering(client, app):
    """Server must recalculate price from DB and NEVER trust prices in client payload."""
    with app.app_context():
        p = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = p.id
        trusted_price = p.price  # 1200.00

    # Client attempts to submit hacked price: ₹1.00 and hacked total: ₹1.00
    payload = {
        "customer_name": "Ramesh Test",
        "customer_phone": "9876543210",
        "delivery_address": "12 Gandhi Road, Chennai",
        "items": [{"product_id": prod_id, "quantity": 2, "price": 1.00, "total": 1.00}]
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201

    data = res.get_json()["order"]
    # 2 * 1200 = 2400 subtotal + 50 delivery fee = 2450.00
    assert data["subtotal"] == 2400.00
    assert data["delivery_fee"] == 50.00
    assert data["total_amount"] == 2450.00
    assert data["payment_status"] == "Pending COD"

def test_checkout_invalid_details_rejected(client):
    """Missing or empty customer data must fail validation."""
    # Missing phone
    payload = {
        "customer_name": "Test User",
        "customer_phone": "",
        "delivery_address": "Test Street",
        "items": [{"product_id": 1, "quantity": 1}]
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "valid phone number" in res.get_json()["error"]

    # Empty items
    payload["customer_phone"] = "9876543210"
    payload["items"] = []
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400


# ==========================================================
# 3. CONCURRENCY & STOCK SAFETY TESTS
# ==========================================================

def test_out_of_stock_rejected(client, app):
    """Requesting more units than available stock must be rejected."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="MW-TEST-001").first()
        prod_id = p1.id  # Only 1 unit in stock

    payload = {
        "customer_name": "Buyer 1",
        "customer_phone": "9876543210",
        "delivery_address": "Anna Nagar",
        "items": [{"product_id": prod_id, "quantity": 5}]
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "Insufficient stock" in res.get_json()["error"]

def test_two_purchases_competing_for_last_unit(client, app):
    """First buyer gets the last unit, second buyer gets an insufficient stock error."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="MW-TEST-001").first()
        prod_id = p1.id  # Exactly 1 in stock

    # Buyer 1 purchases unit 1
    res1 = client.post("/api/orders", json={
        "customer_name": "Customer 1",
        "customer_phone": "9876543210",
        "delivery_address": "Chennai",
        "items": [{"product_id": prod_id, "quantity": 1}]
    })
    assert res1.status_code == 201

    # Buyer 2 tries to purchase the same unit
    res2 = client.post("/api/orders", json={
        "customer_name": "Customer 2",
        "customer_phone": "9876543211",
        "delivery_address": "Madurai",
        "items": [{"product_id": prod_id, "quantity": 1}]
    })
    assert res2.status_code == 400
    assert "Insufficient stock" in res2.get_json()["error"]

def test_idempotency_prevents_duplicate_orders(client, app):
    """Submitting duplicate order with same idempotency key returns original order without double decrement."""
    with app.app_context():
        p2 = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = p2.id
        initial_stock = p2.stock

    idem_key = "MW-UNIQUE-IDEMP-KEY-999"
    payload = {
        "customer_name": "Same Buyer",
        "customer_phone": "9876543210",
        "delivery_address": "Salem",
        "idempotency_key": idem_key,
        "items": [{"product_id": prod_id, "quantity": 1}]
    }

    res1 = client.post("/api/orders", json=payload)
    assert res1.status_code == 201
    ref1 = res1.get_json()["order"]["order_reference"]

    # Repeat submission
    res2 = client.post("/api/orders", json=payload)
    assert res2.status_code == 201
    ref2 = res2.get_json()["order"]["order_reference"]
    assert ref1 == ref2

    with app.app_context():
        p_after = Product.query.filter_by(sku="MW-TEST-002").first()
        assert p_after.stock == initial_stock - 1  # Decremented only once!


# ==========================================================
# 4. ORDER STATUS TRANSITIONS & STOCK RESTORATION TESTS
# ==========================================================

def test_status_transitions_and_restoration_on_cancellation(client, app):
    """Cancelled and Returned orders must automatically restore reserved stock."""
    with app.app_context():
        p2 = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = p2.id
        start_stock = p2.stock

    # Place order
    res = client.post("/api/orders", json={
        "customer_name": "Order Cancel Test",
        "customer_phone": "9876543210",
        "delivery_address": "Coimbatore",
        "items": [{"product_id": prod_id, "quantity": 3}]
    })
    order_id = res.get_json()["order"]["id"]

    with app.app_context():
        assert Product.query.get(prod_id).stock == start_stock - 3

    # Log in as admin
    client.post("/admin/login", json={"username": "admin", "password": "admin123"})

    # Progress through statuses: Confirmed -> Packed -> Shipped
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Confirmed"})
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Packed"})
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Shipped"})

    # Now Cancel order
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Cancelled"})

    # Stock must be fully restored!
    with app.app_context():
        assert Product.query.get(prod_id).stock == start_stock


# ==========================================================
# 5. COD ACCOUNTING & ANALYTICS INTEGRITY TESTS
# ==========================================================

def test_cod_not_counted_as_revenue_until_collected(client, app):
    """Unpaid COD orders must NOT be counted as collected sales."""
    client.post("/admin/login", json={"username": "admin", "password": "admin123"})

    # Initial analytics
    res_init = client.get("/api/admin/analytics/summary?range=7d").get_json()
    assert res_init["collectedSales"] == 0.0

    # Place an active COD order for ₹1,250
    with app.app_context():
        prod_id = Product.query.filter_by(sku="MW-TEST-002").first().id

    res_order = client.post("/api/orders", json={
        "customer_name": "Cash Buyer",
        "customer_phone": "9876543210",
        "delivery_address": "Trichy",
        "items": [{"product_id": prod_id, "quantity": 1}]
    })
    order_data = res_order.get_json()["order"]
    order_id = order_data["id"]
    order_total = order_data["total_amount"]  # 1200 + 50 = 1250

    # Check analytics: Placed order value is ₹1250, but Collected Sales is still ₹0.00!
    res_analytics = client.get("/api/admin/analytics/summary?range=7d").get_json()
    assert res_analytics["collectedSales"] == 0.0
    assert res_analytics["codAwaitingCollection"] == order_total

    # Now owner records cash collection
    client.patch(f"/api/admin/orders/{order_id}", json={"record_payment": True})

    # Now collected sales must equal ₹1250 and codAwaitingCollection drops to ₹0.00!
    res_final = client.get("/api/admin/analytics/summary?range=7d").get_json()
    assert res_final["collectedSales"] == order_total
    assert res_final["codAwaitingCollection"] == 0.0


# ==========================================================
# 6. ACTIVITY AUDIT TRAIL TESTS
# ==========================================================

def test_activity_log_records_owner_actions(client, app):
    """Important actions must be logged in ActivityLog."""
    client.post("/admin/login", json={"username": "admin", "password": "admin123"})

    with app.app_context():
        prod = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = prod.id

    # Adjust stock
    client.patch(f"/api/admin/inventory/{prod_id}", json={"stock": 15, "low_stock_threshold": 4})

    # Fetch logs
    res_logs = client.get("/api/admin/activity-logs")
    assert res_logs.status_code == 200
    logs = res_logs.get_json()
    assert len(logs) > 0

    actions = [l["action"] for l in logs]
    assert "ADMIN_LOGIN" in actions
    assert "STOCK_ADJUSTED" in actions
