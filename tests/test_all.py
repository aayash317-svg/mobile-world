import os
import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app import create_app
from config import TestConfig
from models import db
from models.user import User
from models.customer import Customer, CustomerAddress, CustomerOTP, PasswordResetToken
from models.notification import CustomerNotification
from models.customer_activity import CustomerActivity
from models.price_alert import PriceDropAlert
from models.product import Product
from models.order import Inventory, Order, OrderItem, PaymentRecord
from models.activity_log import ActivityLog
from services.order_service import OrderService
from services.inventory_service import InventoryService
from services.customer_service import CustomerService

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()

        # Create Admin
        admin = User(username="admin", email="admin@test.com", role="owner")
        admin.set_password("admin123")
        db.session.add(admin)

        # Create Test Customer
        customer = Customer(
            name="Ramesh Kumar",
            email="ramesh@test.com",
            phone="9876543210",
            is_verified=True
        )
        customer.set_password("customer123")
        db.session.add(customer)

        # Create Test Products
        p1 = Product(
            sku="MW-TEST-001",
            name="OnePlus Nord CE 4 Test",
            brand="OnePlus",
            category="Mobile Phones",
            price=Decimal("25000.00"),
            mrp=Decimal("28000.00"),
            description="Test smartphone",
            image_url="/static/images/products/phone_oneplus.jpg",
            is_active=True
        )
        p2 = Product(
            sku="MW-TEST-002",
            name="67W GaN Charger Test",
            brand="Mobile World Gear",
            category="Accessories",
            price=Decimal("1200.00"),
            mrp=Decimal("1500.00"),
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

@pytest.fixture
def auth_customer(client, app):
    """Client authenticated with test customer session."""
    with app.app_context():
        cust = Customer.query.filter_by(email="ramesh@test.com").first()
        cust_id = cust.id
        cust_name = cust.name
        cust_email = cust.email

    with client.session_transaction() as sess:
        sess["customer_id"] = cust_id
        sess["customer_name"] = cust_name
        sess["customer_email"] = cust_email

    return client


# ==========================================================
# 1. AUTHENTICATION & SECURITY TESTS
# ==========================================================

def test_unauthorized_admin_api_rejected(client):
    """Unauthorized requests to private admin endpoints must return 401."""
    res = client.get("/api/admin/orders")
    assert res.status_code == 401
    assert "Authentication required" in res.get_json()["error"]

    res_dash = client.get("/admin/dashboard")
    assert res_dash.status_code == 302
    assert "/admin/login" in res_dash.headers["Location"]

def test_admin_login_success_and_logout(client):
    """Valid owner credentials successfully authenticate and grant session access."""
    login_res = client.post("/admin/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    assert login_res.get_json()["message"] == "Login successful"

    # Now authorized
    orders_res = client.get("/api/admin/orders")
    assert orders_res.status_code == 200

    # Logout
    logout_res = client.post("/admin/logout", json={})
    assert logout_res.status_code in (200, 302)

    # Back to unauthorized
    orders_res_after = client.get("/api/admin/orders")
    assert orders_res_after.status_code == 401

def test_admin_login_invalid_credentials(client):
    """Invalid admin credentials return 401 error."""
    res = client.post("/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert "Invalid username or password" in res.get_json()["error"]


# ==========================================================
# 2. CUSTOMER AUTHENTICATION & OTP FLOW
# ==========================================================

def test_customer_registration_and_otp_flow(client, app):
    """Register customer, receive OTP, verify and complete login."""
    reg_payload = {
        "name": "Kavitha M",
        "email": "kavitha@test.com",
        "phone": "9843212345",
        "password": "mypassword123",
        "confirm_password": "mypassword123",
        "address": "45 Cross Cut Road, Coimbatore",
        "pincode": "641012"
    }

    # Step 1: Initiate registration
    res_reg = client.post("/api/auth/register", json=reg_payload)
    assert res_reg.status_code == 200
    assert res_reg.get_json()["status"] == "otp_sent"

    # Retrieve generated OTP from DB
    with app.app_context():
        otp_record = CustomerOTP.query.filter_by(email="kavitha@test.com", is_used=False).first()
        assert otp_record is not None
        # Verify check_otp works on plain text
        # Since hash is stored, let's test invalid OTP first
        res_fail = client.post("/api/auth/verify-otp", json={"otp": "000000"})
        assert res_fail.status_code == 400
        assert "Incorrect" in res_fail.get_json()["error"]

        # Directly generate a known OTP for deterministic test
        CustomerOTP.query.filter_by(email="kavitha@test.com").delete()
        test_otp = CustomerOTP.create_otp(
            email="kavitha@test.com",
            plain_otp="123456",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            purpose="register"
        )
        db.session.add(test_otp)
        db.session.commit()

    # Step 2: Verify with correct OTP
    res_verify = client.post("/api/auth/verify-otp", json={"otp": "123456"})
    assert res_verify.status_code == 200
    assert res_verify.get_json()["customer"]["email"] == "kavitha@test.com"

    # Step 3: Verified customer can access their profile
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    assert res_me.get_json()["authenticated"] is True

def test_duplicate_registration_rejected(client):
    """Cannot register with already registered email or mobile number."""
    dup_email = {
        "name": "Another Ramesh",
        "email": "ramesh@test.com",  # Already exists
        "phone": "9999988888",
        "password": "password123",
        "confirm_password": "password123"
    }
    res = client.post("/api/auth/register", json=dup_email)
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]

def test_unauthenticated_checkout_rejected(client):
    """Unauthenticated users must be rejected from checkout with 401 redirect prompt."""
    payload = {
        "customer_name": "Guest",
        "customer_phone": "9876543210",
        "delivery_address": "Chennai",
        "items": [{"product_id": 1, "quantity": 1}]
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 401
    assert res.get_json()["require_auth"] is True


# ==========================================================
# 3. CHECKOUT & SERVER-SIDE VALIDATION TESTS
# ==========================================================

def test_server_calculates_price_ignoring_client_tampering(auth_customer, app):
    """Server must recalculate price from DB and NEVER trust prices in client payload."""
    with app.app_context():
        p = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = p.id

    # Client attempts to submit hacked price: ₹1.00 and hacked total: ₹1.00
    payload = {
        "customer_name": "Ramesh Test",
        "customer_phone": "9876543210",
        "delivery_address": "12 Gandhi Road, Chennai",
        "items": [{"product_id": prod_id, "quantity": 2, "price": 1.00, "total": 1.00}]
    }
    res = auth_customer.post("/api/orders", json=payload)
    assert res.status_code == 201

    data = res.get_json()["order"]
    # 2 * 1200 = 2400 subtotal + 50 delivery fee = 2450.00
    assert data["subtotal"] == 2400.00
    assert data["delivery_fee"] == 50.00
    assert data["total_amount"] == 2450.00
    assert data["payment_status"] == "Pending COD"

def test_checkout_invalid_details_rejected(auth_customer):
    """Missing or empty customer data must fail validation."""
    # Missing phone
    payload = {
        "customer_name": "Test User",
        "customer_phone": "",
        "delivery_address": "Test Street",
        "items": [{"product_id": 1, "quantity": 1}]
    }
    res = auth_customer.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "valid phone number" in res.get_json()["error"]

    # Empty items
    payload["customer_phone"] = "9876543210"
    payload["items"] = []
    res = auth_customer.post("/api/orders", json=payload)
    assert res.status_code == 400


# ==========================================================
# 4. CONCURRENCY & STOCK SAFETY TESTS
# ==========================================================

def test_out_of_stock_rejected(auth_customer, app):
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
    res = auth_customer.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "Insufficient stock" in res.get_json()["error"]

def test_two_purchases_competing_for_last_unit(auth_customer, app):
    """First buyer gets the last unit, second buyer gets an insufficient stock error."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="MW-TEST-001").first()
        prod_id = p1.id  # Exactly 1 in stock

    # Buyer 1 purchases unit 1
    res1 = auth_customer.post("/api/orders", json={
        "customer_name": "Customer 1",
        "customer_phone": "9876543210",
        "delivery_address": "Chennai",
        "items": [{"product_id": prod_id, "quantity": 1}]
    })
    assert res1.status_code == 201

    # Buyer 2 tries to purchase the same unit
    res2 = auth_customer.post("/api/orders", json={
        "customer_name": "Customer 2",
        "customer_phone": "9876543211",
        "delivery_address": "Madurai",
        "items": [{"product_id": prod_id, "quantity": 1}]
    })
    assert res2.status_code == 400
    assert "Insufficient stock" in res2.get_json()["error"]

def test_idempotency_prevents_duplicate_orders(auth_customer, app):
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

    res1 = auth_customer.post("/api/orders", json=payload)
    assert res1.status_code == 201
    ref1 = res1.get_json()["order"]["order_reference"]

    # Repeat submission
    res2 = auth_customer.post("/api/orders", json=payload)
    assert res2.status_code == 201
    ref2 = res2.get_json()["order"]["order_reference"]
    assert ref1 == ref2

    with app.app_context():
        p_after = Product.query.filter_by(sku="MW-TEST-002").first()
        assert p_after.stock == initial_stock - 1


# ==========================================================
# 5. ORDER STATUS TRANSITIONS & STOCK RESTORATION
# ==========================================================

def test_status_transitions_and_restoration_on_cancellation(client, auth_customer, app):
    """Cancelled and Returned orders must automatically restore reserved stock."""
    with app.app_context():
        p2 = Product.query.filter_by(sku="MW-TEST-002").first()
        prod_id = p2.id
        start_stock = p2.stock

    # Place order as customer
    res = auth_customer.post("/api/orders", json={
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

    # Progress through statuses
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Confirmed"})
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Packed"})
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Shipped"})

    # Cancel order -> restores stock
    client.patch(f"/api/admin/orders/{order_id}", json={"order_status": "Cancelled"})

    with app.app_context():
        assert Product.query.get(prod_id).stock == start_stock


# ==========================================================
# 6. PRICE DROP ALERT TRIGGER TEST
# ==========================================================

def test_price_drop_alert_triggered_on_admin_price_change(client, auth_customer, app):
    """When storeowner lowers product price, customer price drop alert is triggered."""
    with app.app_context():
        p = Product.query.filter_by(sku="MW-TEST-001").first()
        prod_id = p.id
        old_price = p.price  # 25000.00

    # Customer activates price alert
    res_alert = auth_customer.post("/api/customer/price-alerts", json={"product_id": prod_id, "target_price": 24000.00})
    assert res_alert.status_code == 201

    # Store owner logs in and reduces price to 23,999.00
    client.post("/admin/login", json={"username": "admin", "password": "admin123"})
    res_update = client.patch(f"/api/admin/products/{prod_id}", json={"price": 23999.00})
    assert res_update.status_code == 200

    # Customer should have received an in-app notification & activity log!
    with app.app_context():
        alert = PriceDropAlert.query.filter_by(product_id=prod_id).first()
        assert alert.is_triggered is True

        notifs = CustomerNotification.query.filter_by(type="price_drop").all()
        assert len(notifs) >= 1
        assert "Price Drop Alert" in notifs[0].title


# ==========================================================
# 7. AUTHORIZATION & IDOR ISOLATION TESTS
# ==========================================================

def test_customer_cannot_access_another_customers_address(auth_customer, app):
    """A customer must never be able to delete another customer's address (IDOR protection)."""
    with app.app_context():
        # Create other customer and their address
        other = Customer(name="Other Person", email="other@test.com", phone="9988776655")
        other.set_password("pass123")
        db.session.add(other)
        db.session.flush()

        other_addr = CustomerAddress(
            customer_id=other.id,
            full_name="Other",
            phone="9988776655",
            street_address="Private St",
            city="Salem",
            state="Tamil Nadu",
            pincode="636001"
        )
        db.session.add(other_addr)
        db.session.commit()
        other_addr_id = other_addr.id

    # Ramesh tries to delete Other Person's address
    res = auth_customer.delete(f"/api/customer/addresses/{other_addr_id}")
    assert res.status_code == 404
    assert "unauthorized" in res.get_json()["error"]


# ==========================================================
# 8. RATE LIMITING & SENSITIVE DATA TESTS
# ==========================================================

def test_rate_limiting_enforced_on_auth_endpoints(client):
    """Exceeding 5 login attempts within a 60 second window triggers HTTP 429 Too Many Requests."""
    from services.rate_limiter import limiter
    limiter.reset()

    # Fire 5 attempts (allowed)
    for _ in range(5):
        res = client.post("/api/auth/login", json={"identifier": "test@user.com", "password": "wrong"})
        assert res.status_code == 401

    # 6th attempt must be rejected with 429
    res_limited = client.post("/api/auth/login", json={"identifier": "test@user.com", "password": "wrong"})
    assert res_limited.status_code == 429
    assert "Too many requests" in res_limited.get_json()["error"]
    assert "Retry-After" in res_limited.headers

def test_password_recovery_flow(client, app):
    """Forgot password sends neutral response and reset token works securely."""
    # Step 1: Forgot password request
    res_forgot = client.post("/api/auth/forgot-password", json={"email": "ramesh@test.com"})
    assert res_forgot.status_code == 200
    assert "instructions have been sent" in res_forgot.get_json()["message"]

    # Step 2: Grab the generated token hash from DB
    with app.app_context():
        cust = Customer.query.filter_by(email="ramesh@test.com").first()
        token_entry = PasswordResetToken.query.filter_by(customer_id=cust.id, is_used=False).first()
        assert token_entry is not None
        # Create a deterministic plain token
        from werkzeug.security import generate_password_hash
        token_entry.token_hash = generate_password_hash("secure-reset-token-xyz")
        db.session.commit()

    # Step 3: Reset password
    res_reset = client.post("/api/auth/reset-password", json={
        "email": "ramesh@test.com",
        "token": "secure-reset-token-xyz",
        "new_password": "newpassword456",
        "confirm_password": "newpassword456"
    })
    assert res_reset.status_code == 200
    assert "successfully" in res_reset.get_json()["message"]

    # Step 4: Login with old password fails, new password succeeds
    from services.rate_limiter import limiter
    limiter.reset()
    res_old = client.post("/api/auth/login", json={"identifier": "ramesh@test.com", "password": "customer123"})
    assert res_old.status_code == 401

    res_new = client.post("/api/auth/login", json={"identifier": "ramesh@test.com", "password": "newpassword456"})
    assert res_new.status_code == 200
    assert res_new.get_json()["status"] == "otp_sent"


def test_product_detail_page_and_catalog_render(client):
    """Storefront index and individual product detail pages render with 200 OK without Jinja template errors."""
    # Test homepage catalog
    res_home = client.get("/")
    assert res_home.status_code == 200
    home_html = res_home.data.decode("utf-8")
    assert "Mobile World" in home_html

    # Test product detail page
    res_prod = client.get("/products/1")
    assert res_prod.status_code == 200
    prod_html = res_prod.data.decode("utf-8")
    assert "OnePlus Nord CE 4" in prod_html
    assert "phone_oneplus.jpg" in prod_html
    assert "Activate Alert" in prod_html

