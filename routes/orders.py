from flask import Blueprint, request, jsonify, session
from services.order_service import OrderService
from services.auth_guard import get_current_customer
from services.rate_limiter import rate_limit

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/api/orders", methods=["POST"])
@rate_limit(limit=10, window_seconds=60)
def place_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body. JSON payload expected."}), 400

    customer = get_current_customer()
    if not customer:
        return jsonify({
            "error": "Authentication required. Please sign in to place an order.",
            "require_auth": True,
            "redirect": "/signin?next=/checkout"
        }), 401

    customer_name = data.get("customer_name") if data.get("customer_name") is not None else customer.name
    customer_phone = data.get("customer_phone") if data.get("customer_phone") is not None else customer.phone
    customer_email = data.get("customer_email") if data.get("customer_email") is not None else customer.email
    delivery_address = data.get("delivery_address")
    order_notes = data.get("order_notes")
    items = data.get("items")
    idempotency_key = data.get("idempotency_key")

    try:
        order = OrderService.create_order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            items_payload=items,
            order_notes=order_notes,
            customer_email=customer_email,
            idempotency_key=idempotency_key,
            customer_id=customer.id
        )
        return jsonify({
            "message": "Order placed successfully via Cash on Delivery",
            "order": order.to_dict(include_items=True),
            "redirect": f"/order-confirmation/{order.order_reference}"
        }), 201

    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to process order: {str(e)}"}), 500
