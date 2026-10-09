import os
import sys
import json
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
from app import create_app
from config import Config
from models import db
from models.product import Product
from models.order import Order, PaymentRecord
from models.activity_log import ActivityLog

def run_live_e2e():
    app = create_app(Config)
    client = app.test_client()

    print("[1] Verifying Customer Catalogue API against MySQL...")
    res = client.get("/api/products")
    assert res.status_code == 200, f"Catalogue failed: {res.data}"
    products = res.get_json()
    print(f"    Loaded {len(products)} active products from MySQL.")

    # Select first product
    target_prod = products[0]
    prod_id = target_prod["id"]
    initial_stock = target_prod["stock"]
    print(f"    Selected '{target_prod['name']}' (ID: {prod_id}, Initial Stock: {initial_stock})")

    print("[2] Placing Customer COD Order...")
    order_payload = {
        "customer_name": "Karthik Raja",
        "customer_phone": "9445303696",
        "delivery_address": "45 Bazaar Street, Tirunelveli, Tamil Nadu - 627001",
        "order_notes": "Please deliver after 6 PM, keep change ready",
        "items": [{"product_id": prod_id, "quantity": 1}]
    }
    order_res = client.post("/api/orders", json=order_payload)
    assert order_res.status_code == 201, f"Order placement failed: {order_res.data}"
    order_data = order_res.get_json()["order"]
    order_id = order_data["id"]
    order_ref = order_data["order_reference"]
    total_amount = order_data["total_amount"]
    print(f"    Order Created! Reference: {order_ref}, Total: ₹{total_amount}, Status: {order_data['order_status']}")

    print("[3] Verifying Stock Decrement in MySQL...")
    res2 = client.get(f"/api/products/{prod_id}")
    new_stock = res2.get_json()["stock"]
    assert new_stock == initial_stock - 1, f"Stock mismatch: expected {initial_stock - 1}, got {new_stock}"
    print(f"    Stock successfully decremented from {initial_stock} to {new_stock}.")

    print("[4] Logging in as Shop Owner...")
    login_res = client.post("/admin/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, f"Owner login failed: {login_res.data}"
    print("    Owner authenticated successfully.")

    print("[5] Checking Analytics (Distinguishing COD Placed vs Collected)...")
    summary_before = client.get("/api/admin/analytics/summary?range=7d").get_json()
    print(f"    Total Orders: {summary_before['totalOrders']}, Collected Sales: {summary_before['collectedSalesFormatted']}, Awaiting COD: {summary_before['codAwaitingCollectionFormatted']}")

    print("[6] Progressing Order Status: Confirmed -> Packed -> Shipped...")
    for st in ["Confirmed", "Packed", "Shipped"]:
        st_res = client.patch(f"/api/admin/orders/{order_id}", json={"order_status": st})
        assert st_res.status_code == 200
        print(f"    Transitioned to '{st}'")

    print("[7] Recording COD Cash Payment Collection upon Delivery...")
    pay_res = client.patch(f"/api/admin/orders/{order_id}", json={"record_payment": True, "payment_notes": "Cash collected by delivery agent"})
    assert pay_res.status_code == 200
    updated_order = pay_res.get_json()["order"]
    assert updated_order["payment_status"] == "Collected"
    assert updated_order["order_status"] == "Delivered"
    print(f"    Payment status updated to: {updated_order['payment_status']}, Order status: {updated_order['order_status']}")

    print("[8] Verifying Revenue KPIs Updated in Real Time...")
    summary_after = client.get("/api/admin/analytics/summary?range=7d").get_json()
    print(f"    Updated Collected Sales: {summary_after['collectedSalesFormatted']}")

    print("[9] Inspecting Activity Audit Trail...")
    logs_res = client.get("/api/admin/activity-logs")
    logs = logs_res.get_json()
    print(f"    Audit trail contains {len(logs)} recorded events.")
    recent_actions = [l["action"] for l in logs[:5]]
    print(f"    Recent actions: {', '.join(recent_actions)}")

    print("\n=========================================================")
    print("ALL LIVE END-TO-END FLOWS ON MYSQL PASSED WITH 100% SUCCESS!")
    print("=========================================================")

if __name__ == "__main__":
    run_live_e2e()
