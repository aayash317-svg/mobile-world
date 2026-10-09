from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.order_service import OrderService

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/admin/analytics/summary", methods=["GET"])
@login_required
def get_analytics_summary():
    range_param = request.args.get("range", "7d")
    days = 7
    if range_param.endswith("d"):
        try:
            days = int(range_param[:-1])
        except ValueError:
            days = 7
    elif range_param.isdigit():
        days = int(range_param)

    summary = OrderService.get_analytics_summary(days=days)
    return jsonify(summary)
