from flask import Blueprint, request, jsonify
from services.order_service import OrderService

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/api/orders", methods=["POST"])
def place_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body. JSON payload expected."}), 400

    customer_name = data.get("customer_name")
    customer_phone = data.get("customer_phone")
    customer_email = data.get("customer_email")
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
            idempotency_key=idempotency_key
        )
        return jsonify({
            "message": "Order placed successfully via Cash on Delivery",
            "order": order.to_dict(include_items=True)
        }), 201

    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to process order. Please check stock and try again."}), 500
