from flask import Blueprint, render_template, jsonify, request
from models.product import Product

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/")
def index():
    return render_template("customer/index.html")

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
