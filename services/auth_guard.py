from functools import wraps
from flask import session, request, jsonify, redirect, url_for, g
from flask_login import current_user
from models.customer import Customer

def get_current_customer() -> Customer | None:
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    # Cache per-request on g
    if not hasattr(g, "current_customer") or g.current_customer is None or getattr(g.current_customer, "id", None) != customer_id:
        g.current_customer = Customer.query.get(customer_id)
    return g.current_customer

def customer_required(f):
    """
    Decorator ensuring an authenticated customer session exists.
    Enforces authorization boundaries so customers only access their own resources.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        customer = get_current_customer()
        if not customer:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Authentication required. Please sign in to your Mobile World account."}), 401
            return redirect(url_for("auth.signin_view", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def check_ownership(resource_owner_id: int) -> bool:
    """
    Checks if the currently authenticated customer owns the requested resource.
    Prevents IDOR (Insecure Direct Object Reference).
    """
    customer = get_current_customer()
    if not customer:
        return False
    return customer.id == resource_owner_id

def admin_required(f):
    """
    Decorator strictly enforcing store owner privileges.
    Returns 401 if not logged in, 403 if logged in but not owner.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Authentication required. Please log in as owner."}), 401
            return redirect(url_for("admin.login"))
        if getattr(current_user, "role", None) != "owner":
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Access forbidden. Store owner privileges required."}), 403
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated_function
