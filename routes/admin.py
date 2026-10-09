import time
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.product import Product
from models.order import Order, Inventory
from services.order_service import OrderService
from services.inventory_service import InventoryService
from services.activity_service import ActivityService

admin_bp = Blueprint("admin", __name__)

# In-memory IP-based rate limiter for login attempts (5 attempts per 5 minutes)
LOGIN_ATTEMPTS = {}
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 300  # seconds

def check_rate_limit(ip: str):
    now = time.time()
    record = LOGIN_ATTEMPTS.get(ip)
    if not record:
        return True, 0
    count, first_time = record
    if now - first_time > LOCKOUT_TIME:
        # Reset window
        LOGIN_ATTEMPTS.pop(ip, None)
        return True, 0
    if count >= MAX_ATTEMPTS:
        remaining = int(LOCKOUT_TIME - (now - first_time))
        return False, remaining
    return True, 0

def record_failed_attempt(ip: str):
    now = time.time()
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = [1, now]
    else:
        LOGIN_ATTEMPTS[ip][0] += 1

def clear_attempts(ip: str):
    LOGIN_ATTEMPTS.pop(ip, None)


# --- Authentication Views & APIs ---

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        allowed, wait_seconds = check_rate_limit(ip)
        if not allowed:
            msg = f"Too many failed login attempts. Please wait {wait_seconds} seconds before trying again."
            if request.is_json:
                return jsonify({"error": msg}), 429
            flash(msg, "danger")
            return render_template("admin/login.html")

        data = request.get_json(silent=True) or request.form
        username = data.get("username", "").strip()
        password = data.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            clear_attempts(ip)
            login_user(user)
            ActivityService.log(
                action="ADMIN_LOGIN",
                entity_type="Auth",
                entity_id=user.id,
                details=f"Owner '{username}' successfully logged in",
                user_id=user.id,
                username=user.username
            )
            if request.is_json:
                return jsonify({"message": "Login successful", "redirect": url_for("admin.dashboard")})
            return redirect(url_for("admin.dashboard"))

        # Failed attempt
        record_failed_attempt(ip)
        ActivityService.log(
            action="LOGIN_FAILED",
            entity_type="Auth",
            details=f"Failed attempt for username '{username}' from IP {ip}",
            username=username or "Unknown"
        )

        error_msg = "Invalid username or password"
        if request.is_json:
            return jsonify({"error": error_msg}), 401
        flash(error_msg, "danger")

    return render_template("admin/login.html")


@admin_bp.route("/admin/logout", methods=["GET", "POST"])
@login_required
def logout():
    uname = current_user.username
    uid = current_user.id
    logout_user()
    ActivityService.log(
        action="ADMIN_LOGOUT",
        entity_type="Auth",
        entity_id=uid,
        details=f"Owner '{uname}' logged out",
        user_id=uid,
        username=uname
    )
    if request.is_json:
        return jsonify({"message": "Logged out successfully"})
    return redirect(url_for("admin.login"))


@admin_bp.route("/admin/")
@admin_bp.route("/admin/dashboard")
@login_required
def dashboard():
    return render_template("admin/dashboard.html", user=current_user)


# --- Protected Admin APIs ---

@admin_bp.route("/api/admin/orders", methods=["GET"])
@login_required
def get_orders():
    status = request.args.get("status")
    payment_status = request.args.get("payment_status")
    search = request.args.get("search")

    query = Order.query

    if status and status.lower() != "all":
        query = query.filter(Order.order_status == status)

    if payment_status and payment_status.lower() != "all":
        query = query.filter(Order.payment_status == payment_status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_reference.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_phone.ilike(search_term))
        )

    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict(include_items=True) for o in orders])


@admin_bp.route("/api/admin/orders/<int:order_id>", methods=["PATCH"])
@login_required
def update_order(order_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body expected"}), 400

    new_status = data.get("order_status")
    record_payment = data.get("record_payment")
    payment_notes = data.get("payment_notes")
    status_notes = data.get("status_notes")

    try:
        updated_order = None
        if new_status:
            updated_order = OrderService.update_order_status(
                order_id=order_id,
                new_status=new_status,
                changed_by=current_user.username,
                notes=status_notes
            )

        if record_payment:
            OrderService.record_cod_payment(
                order_id=order_id,
                recorded_by=current_user.username,
                notes=payment_notes
            )
            updated_order = Order.query.get(order_id)

        if not updated_order:
            updated_order = Order.query.get_or_404(order_id)

        return jsonify({
            "message": "Order updated successfully",
            "order": updated_order.to_dict(include_items=True)
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to update order: {str(e)}"}), 500


@admin_bp.route("/api/admin/products", methods=["POST"])
@login_required
def create_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body expected"}), 400

    name = data.get("name")
    brand = data.get("brand")
    category = data.get("category")
    price = data.get("price")
    sku = data.get("sku")
    stock = int(data.get("stock", 0))
    low_threshold = int(data.get("low_stock_threshold", 5))
    image_url = data.get("image_url", "")
    description = data.get("description", "")

    if not name or not brand or not category or price is None or not sku:
        return jsonify({"error": "Missing required fields (name, brand, category, price, sku)"}), 400

    try:
        price_decimal = Decimal(str(price))
        product = Product(
            name=name.strip(),
            brand=brand.strip(),
            category=category.strip(),
            price=price_decimal,
            sku=sku.strip(),
            image_url=image_url.strip(),
            description=description.strip(),
            is_active=True
        )
        db.session.add(product)
        db.session.flush()

        inventory = Inventory(
            product_id=product.id,
            quantity=stock,
            low_stock_threshold=low_threshold
        )
        db.session.add(inventory)
        db.session.commit()

        ActivityService.log(
            action="PRODUCT_CREATED",
            entity_type="Product",
            entity_id=product.id,
            details=f"Created '{product.name}' (SKU: {product.sku}), Price: ₹{price_decimal}, Stock: {stock}",
            user_id=current_user.id,
            username=current_user.username
        )

        return jsonify({"message": "Product created successfully", "product": product.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/api/admin/products/<int:product_id>", methods=["PATCH"])
@login_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body expected"}), 400

    try:
        changes = []
        if "name" in data and data["name"].strip() != product.name:
            changes.append(f"name: {product.name} -> {data['name']}")
            product.name = data["name"].strip()
        if "brand" in data and data["brand"].strip() != product.brand:
            product.brand = data["brand"].strip()
        if "category" in data and data["category"].strip() != product.category:
            product.category = data["category"].strip()
        if "price" in data:
            new_p = Decimal(str(data["price"]))
            if new_p != product.price:
                changes.append(f"price: ₹{product.price} -> ₹{new_p}")
                product.price = new_p
        if "description" in data:
            product.description = data["description"].strip()
        if "image_url" in data:
            product.image_url = data["image_url"].strip()
        if "is_active" in data:
            product.is_active = bool(data["is_active"])
            changes.append(f"active: {product.is_active}")

        if "stock" in data:
            new_stock = int(data["stock"])
            low_th = int(data.get("low_stock_threshold", product.low_stock_threshold))
            old_qty = product.stock
            InventoryService.adjust_stock(product.id, new_stock, low_th)
            changes.append(f"stock: {old_qty} -> {new_stock}")

        db.session.commit()

        if changes:
            ActivityService.log(
                action="PRODUCT_UPDATED",
                entity_type="Product",
                entity_id=product.id,
                details=f"Updated '{product.name}': {', '.join(changes)}",
                user_id=current_user.id,
                username=current_user.username
            )

        return jsonify({"message": "Product updated successfully", "product": product.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/api/admin/inventory/<int:product_id>", methods=["PATCH"])
@login_required
def adjust_inventory(product_id):
    data = request.get_json()
    if not data or "stock" not in data:
        return jsonify({"error": "'stock' quantity is required"}), 400

    try:
        product = Product.query.get_or_404(product_id)
        old_stock = product.stock
        new_stock = int(data["stock"])
        low_threshold = data.get("low_stock_threshold")
        if low_threshold is not None:
            low_threshold = int(low_threshold)

        inv = InventoryService.adjust_stock(product_id, new_stock, low_threshold)

        ActivityService.log(
            action="STOCK_ADJUSTED",
            entity_type="Inventory",
            entity_id=product.id,
            details=f"Adjusted '{product.name}' stock from {old_stock} to {new_stock} (threshold: {inv.low_stock_threshold})",
            user_id=current_user.id,
            username=current_user.username
        )

        return jsonify({"message": "Inventory updated", "inventory": inv.to_dict()})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/api/admin/activity-logs", methods=["GET"])
@login_required
def get_activity_logs():
    limit = int(request.args.get("limit", 50))
    logs = ActivityService.get_recent_logs(limit=limit)
    return jsonify([l.to_dict() for l in logs])
