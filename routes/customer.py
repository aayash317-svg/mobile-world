from decimal import Decimal
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from models import db
from models.product import Product
from models.order import Order
from models.customer import Customer, CustomerAddress
from models.notification import CustomerNotification
from models.customer_activity import CustomerActivity
from models.price_alert import PriceDropAlert
from services.auth_guard import get_current_customer, customer_required, check_ownership
from services.customer_service import CustomerService

customer_bp = Blueprint("customer", __name__)

# ==========================================
# PUBLIC STOREFRONT & PRODUCTS
# ==========================================

@customer_bp.route("/")
def index():
    return render_template("customer/index.html")

@customer_bp.route("/products/<int:product_id>")
def product_detail_view(product_id):
    product = Product.query.filter_by(id=product_id, is_active=True).first_or_404()
    related = Product.query.filter(
        Product.id != product.id,
        Product.category == product.category,
        Product.is_active == True
    ).limit(4).all()
    return render_template("customer/product_detail.html", product=product, related=related)

@customer_bp.route("/checkout")
def checkout_view():
    customer = get_current_customer()
    return render_template("customer/checkout.html", customer=customer)

@customer_bp.route("/order-confirmation/<order_reference>")
def order_confirmation_view(order_reference):
    order = Order.query.filter_by(order_reference=order_reference).first_or_404()
    # If user is logged in, verify ownership or allow confirmation page for the newly placed order
    customer = get_current_customer()
    return render_template("customer/order_confirmation.html", order=order, customer=customer)

@customer_bp.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    brand = request.args.get("brand")
    search = request.args.get("search")

    query = Product.query.filter_by(is_active=True)

    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(category))

    if brand and brand.lower() != "all":
        query = query.filter(Product.brand.ilike(brand))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) |
            (Product.brand.ilike(search_term)) |
            (Product.description.ilike(search_term))
        )

    products = query.order_by(Product.id.asc()).all()
    return jsonify([p.to_dict() for p in products])

@customer_bp.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = Product.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product.to_dict())


# ==========================================
# CUSTOMER ACCOUNT HUB (PROTECTED)
# ==========================================

@customer_bp.route("/account")
@customer_required
def account_hub():
    customer = get_current_customer()
    recent_orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).limit(3).all()
    unread_notifs = CustomerNotification.query.filter_by(customer_id=customer.id, is_read=False).count()
    active_alerts = PriceDropAlert.query.filter_by(customer_id=customer.id, is_active=True).count()
    return render_template(
        "customer/account_hub.html",
        customer=customer,
        recent_orders=recent_orders,
        unread_notifs=unread_notifs,
        active_alerts=active_alerts
    )

@customer_bp.route("/account/orders")
@customer_required
def account_orders():
    customer = get_current_customer()
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/account_orders.html", customer=customer, orders=orders)

@customer_bp.route("/account/addresses")
@customer_required
def account_addresses():
    customer = get_current_customer()
    addresses = CustomerAddress.query.filter_by(customer_id=customer.id).order_by(CustomerAddress.is_default.desc()).all()
    return render_template("customer/account_addresses.html", customer=customer, addresses=addresses)

@customer_bp.route("/account/notifications")
@customer_required
def account_notifications():
    customer = get_current_customer()
    notifications = CustomerNotification.query.filter_by(customer_id=customer.id).order_by(CustomerNotification.created_at.desc()).all()
    return render_template("customer/account_notifications.html", customer=customer, notifications=notifications)

@customer_bp.route("/account/activity")
@customer_required
def account_activity():
    customer = get_current_customer()
    activities = CustomerActivity.query.filter_by(customer_id=customer.id).order_by(CustomerActivity.created_at.desc()).limit(50).all()
    return render_template("customer/account_activity.html", customer=customer, activities=activities)

@customer_bp.route("/account/price-alerts")
@customer_required
def account_price_alerts():
    customer = get_current_customer()
    alerts = PriceDropAlert.query.filter_by(customer_id=customer.id).order_by(PriceDropAlert.created_at.desc()).all()
    return render_template("customer/account_price_alerts.html", customer=customer, alerts=alerts)

@customer_bp.route("/account/security")
@customer_required
def account_security():
    customer = get_current_customer()
    return render_template("customer/account_security.html", customer=customer)


# ==========================================
# CUSTOMER DATA APIS (OWNERSHIP ENFORCED)
# ==========================================

@customer_bp.route("/api/customer/profile", methods=["GET", "PUT"])
@customer_required
def api_customer_profile():
    customer = get_current_customer()
    if request.method == "GET":
        return jsonify(customer.to_dict())

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()

    if not name or len(name) < 2:
        return jsonify({"error": "Valid name is required."}), 400
    if not phone or len(phone) < 10:
        return jsonify({"error": "Valid 10-digit phone number is required."}), 400

    # Check phone uniqueness if modified
    if phone != customer.phone:
        existing = Customer.query.filter(Customer.phone == phone, Customer.id != customer.id).first()
        if existing:
            return jsonify({"error": "This phone number is already registered to another account."}), 400

    customer.name = name
    customer.phone = phone
    db.session.commit()

    CustomerService.log_activity(
        customer_id=customer.id,
        event_type="PROFILE_UPDATED",
        title="Profile Updated",
        description="Updated name and phone contact details"
    )

    return jsonify({"message": "Profile updated successfully.", "customer": customer.to_dict()})

@customer_bp.route("/api/customer/change-password", methods=["POST"])
@customer_required
def api_change_password():
    customer = get_current_customer()
    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not customer.check_password(current_password):
        return jsonify({"error": "Current password is incorrect."}), 400

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match."}), 400

    customer.set_password(new_password)
    db.session.commit()

    CustomerService.log_activity(
        customer_id=customer.id,
        event_type="PASSWORD_CHANGED",
        title="Password Changed",
        description="Changed password via security settings"
    )
    CustomerService.create_notification(
        customer_id=customer.id,
        type="security",
        title="Password Changed",
        message="Your account password was updated successfully from security settings.",
        link_url="/account/security"
    )

    return jsonify({"message": "Password changed successfully."})

@customer_bp.route("/api/customer/addresses", methods=["GET", "POST"])
@customer_required
def api_customer_addresses():
    customer = get_current_customer()

    if request.method == "GET":
        addresses = CustomerAddress.query.filter_by(customer_id=customer.id).order_by(CustomerAddress.is_default.desc()).all()
        return jsonify([a.to_dict() for a in addresses])

    # POST: Add new address
    data = request.get_json() or {}
    full_name = data.get("full_name") or customer.name
    phone = data.get("phone") or customer.phone
    street_address = data.get("street_address", "").strip()
    city = data.get("city", "Coimbatore").strip()
    state = data.get("state", "Tamil Nadu").strip()
    pincode = data.get("pincode", "641012").strip()
    landmark = data.get("landmark", "").strip()
    is_default = bool(data.get("is_default", False))

    if not street_address or not pincode:
        return jsonify({"error": "Street address and pincode are required."}), 400

    if is_default or CustomerAddress.query.filter_by(customer_id=customer.id).count() == 0:
        CustomerAddress.query.filter_by(customer_id=customer.id).update({"is_default": False})
        is_default = True

    new_addr = CustomerAddress(
        customer_id=customer.id,
        full_name=full_name,
        phone=phone,
        street_address=street_address,
        city=city,
        state=state,
        pincode=pincode,
        landmark=landmark or None,
        is_default=is_default
    )
    db.session.add(new_addr)
    db.session.commit()

    CustomerService.log_activity(
        customer_id=customer.id,
        event_type="ADDRESS_ADDED",
        title="Delivery Address Added",
        description=f"Added address: {street_address}, {pincode}"
    )

    return jsonify({"message": "Address saved successfully.", "address": new_addr.to_dict()}), 201

@customer_bp.route("/api/customer/addresses/<int:address_id>", methods=["DELETE"])
@customer_required
def api_delete_address(address_id):
    customer = get_current_customer()
    addr = CustomerAddress.query.filter_by(id=address_id, customer_id=customer.id).first()
    if not addr:
        return jsonify({"error": "Address not found or unauthorized access."}), 404

    db.session.delete(addr)
    db.session.commit()
    return jsonify({"message": "Address removed successfully."})

@customer_bp.route("/api/customer/addresses/<int:address_id>/default", methods=["PUT"])
@customer_required
def api_set_default_address(address_id):
    customer = get_current_customer()
    addr = CustomerAddress.query.filter_by(id=address_id, customer_id=customer.id).first()
    if not addr:
        return jsonify({"error": "Address not found or unauthorized access."}), 404

    CustomerAddress.query.filter_by(customer_id=customer.id).update({"is_default": False})
    addr.is_default = True
    db.session.commit()
    return jsonify({"message": "Default address updated.", "address": addr.to_dict()})

@customer_bp.route("/api/customer/orders", methods=["GET"])
@customer_required
def api_customer_orders():
    customer = get_current_customer()
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict(include_items=True) for o in orders])

@customer_bp.route("/api/customer/notifications", methods=["GET"])
@customer_required
def api_customer_notifications():
    customer = get_current_customer()
    notifs = CustomerNotification.query.filter_by(customer_id=customer.id).order_by(CustomerNotification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifs])

@customer_bp.route("/api/customer/notifications/<int:notification_id>/read", methods=["POST"])
@customer_required
def api_mark_notification_read(notification_id):
    customer = get_current_customer()
    notif = CustomerNotification.query.filter_by(id=notification_id, customer_id=customer.id).first()
    if not notif:
        return jsonify({"error": "Notification not found or access denied."}), 404

    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Notification marked as read."})

@customer_bp.route("/api/customer/notifications/mark-all-read", methods=["POST"])
@customer_required
def api_mark_all_notifications_read():
    customer = get_current_customer()
    CustomerNotification.query.filter_by(customer_id=customer.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read."})

@customer_bp.route("/api/customer/activity", methods=["GET"])
@customer_required
def api_customer_activity():
    customer = get_current_customer()
    limit = int(request.args.get("limit", 50))
    acts = CustomerActivity.query.filter_by(customer_id=customer.id).order_by(CustomerActivity.created_at.desc()).limit(limit).all()
    return jsonify([a.to_dict() for a in acts])

@customer_bp.route("/api/customer/price-alerts", methods=["GET", "POST"])
@customer_required
def api_customer_price_alerts():
    customer = get_current_customer()

    if request.method == "GET":
        alerts = PriceDropAlert.query.filter_by(customer_id=customer.id).order_by(PriceDropAlert.created_at.desc()).all()
        return jsonify([a.to_dict() for a in alerts])

    # POST: create price alert
    data = request.get_json() or {}
    product_id = data.get("product_id")
    target_price = data.get("target_price")

    if not product_id:
        return jsonify({"error": "Product ID is required."}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found."}), 404

    # Check if existing active alert exists
    existing = PriceDropAlert.query.filter_by(
        customer_id=customer.id,
        product_id=product.id,
        is_active=True
    ).first()

    if existing:
        if target_price:
            existing.target_price = Decimal(str(target_price))
            db.session.commit()
        return jsonify({"message": "Price alert already active for this product.", "alert": existing.to_dict()})

    target_price_dec = Decimal(str(target_price)) if target_price else None
    alert = PriceDropAlert(
        customer_id=customer.id,
        product_id=product.id,
        target_price=target_price_dec,
        initial_price=product.price,
        is_active=True
    )
    db.session.add(alert)
    db.session.commit()

    CustomerService.log_activity(
        customer_id=customer.id,
        event_type="PRICE_ALERT_CREATED",
        title=f"Price Alert Created: {product.name}",
        description=f"Alert set for price drop below ₹{target_price_dec or product.price:,.2f}",
        entity_type="Product",
        entity_id=str(product.id)
    )

    return jsonify({"message": f"Price drop alert created for {product.name}!", "alert": alert.to_dict()}), 201

@customer_bp.route("/api/customer/price-alerts/<int:alert_id>", methods=["DELETE"])
@customer_required
def api_delete_price_alert(alert_id):
    customer = get_current_customer()
    alert = PriceDropAlert.query.filter_by(id=alert_id, customer_id=customer.id).first()
    if not alert:
        return jsonify({"error": "Alert not found or unauthorized access."}), 404

    db.session.delete(alert)
    db.session.commit()
    return jsonify({"message": "Price alert deleted."})

@customer_bp.route("/api/customer/price-alerts/<int:alert_id>/toggle", methods=["POST"])
@customer_required
def api_toggle_price_alert(alert_id):
    customer = get_current_customer()
    alert = PriceDropAlert.query.filter_by(id=alert_id, customer_id=customer.id).first()
    if not alert:
        return jsonify({"error": "Alert not found or unauthorized access."}), 404

    alert.is_active = not alert.is_active
    db.session.commit()
    return jsonify({"message": f"Alert {'resumed' if alert.is_active else 'paused'}.", "alert": alert.to_dict()})
