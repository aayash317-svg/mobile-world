import os
from decimal import Decimal
from flask import Flask, jsonify, redirect, url_for, request
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from models.product import Product
from models.order import Inventory, Order, OrderItem, PaymentRecord, OrderStatusHistory
from models.activity_log import ActivityLog
from routes.customer import customer_bp
from routes.orders import orders_bp
from routes.admin import admin_bp
from routes.analytics import analytics_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/admin/"):
            return jsonify({"error": "Authentication required. Please log in as owner."}), 401
        return redirect(url_for("admin.login"))

    # Register blueprints
    app.register_blueprint(customer_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)

    # Context processors & template helpers
    @app.context_processor
    def inject_shop_info():
        return {
            "shop_name": "Mobile World Sales & Service",
            "flat_delivery_fee": float(app.config.get("FLAT_DELIVERY_FEE", 50.00))
        }

    return app


def seed_database(app):
    with app.app_context():
        db.create_all()

        # 1. Create Default Admin if not exists
        admin_username = app.config.get("ADMIN_USERNAME", "admin")
        admin_password = app.config.get("ADMIN_PASSWORD", "admin123")
        existing_admin = User.query.filter_by(username=admin_username).first()
        if not existing_admin:
            admin = User(
                username=admin_username,
                email="owner@mobileworld.local",
                role="owner"
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            print(f"[Seed] Created admin account: {admin_username}")

        # 2. Seed Realistic Products if empty
        if Product.query.count() == 0:
            sample_products = [
                {
                    "sku": "MW-PH-001",
                    "name": "OnePlus Nord CE 4 (8GB / 128GB)",
                    "brand": "OnePlus",
                    "category": "Mobile Phones",
                    "price": Decimal("24999.00"),
                    "description": "Qualcomm Snapdragon 7 Gen 3, 100W SUPERVOOC charging, 50MP Sony LYT-600 OIS camera.",
                    "image_url": "/static/images/products/phone_oneplus.svg",
                    "stock": 8,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-PH-002",
                    "name": "Samsung Galaxy M35 5G (6GB / 128GB)",
                    "brand": "Samsung",
                    "category": "Mobile Phones",
                    "price": Decimal("16999.00"),
                    "description": "Monster 6000mAh battery, Exynos 1380 processor, 120Hz sAMOLED display with Corning Gorilla Glass Victus+.",
                    "image_url": "/static/images/products/phone_samsung.svg",
                    "stock": 12,
                    "low_threshold": 4
                },
                {
                    "sku": "MW-PH-003",
                    "name": "Redmi Note 13 5G (8GB / 256GB)",
                    "brand": "Xiaomi",
                    "category": "Mobile Phones",
                    "price": Decimal("18499.00"),
                    "description": "108MP ProLight camera, ultra-slim 120Hz AMOLED display, MediaTek Dimensity 6080.",
                    "image_url": "/static/images/products/phone_redmi.svg",
                    "stock": 5,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-PH-004",
                    "name": "Realme Narzo 70 Turbo 5G (6GB / 128GB)",
                    "brand": "Realme",
                    "category": "Mobile Phones",
                    "price": Decimal("14999.00"),
                    "description": "MediaTek Dimensity 7300 Energy 5G chip, stainless steel vapor cooling area, motorsport inspired design.",
                    "image_url": "/static/images/products/phone_realme.svg",
                    "stock": 2,  # Low stock test case
                    "low_threshold": 3
                },
                {
                    "sku": "MW-AC-001",
                    "name": "67W Super Fast Dual-Port GaN Charger",
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("1299.00"),
                    "description": "Compact GaN fast charger with USB-C and USB-A ports, surge protection, suitable for all smartphones.",
                    "image_url": "/static/images/products/charger.svg",
                    "stock": 25,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-AC-002",
                    "name": "Ultra-Tough Braided Type-C to Type-C Cable (1.5m)",
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("399.00"),
                    "description": "Heavy-duty nylon braided cable supporting 100W PD and fast data sync with reinforced stress joints.",
                    "image_url": "/static/images/products/cable.svg",
                    "stock": 40,
                    "low_threshold": 10
                },
                {
                    "sku": "MW-AC-003",
                    "name": "9D Curved Edge Tempered Glass Screen Guard",
                    "brand": "ArmorShield",
                    "category": "Accessories",
                    "price": Decimal("249.00"),
                    "description": "Edge-to-edge full coverage 9H hardness tempered glass with oleophobic anti-fingerprint coating.",
                    "image_url": "/static/images/products/glass.svg",
                    "stock": 35,
                    "low_threshold": 10
                },
                {
                    "sku": "MW-AC-004",
                    "name": "Magnetic Shockproof Armor Case with Kickstand",
                    "brand": "ArmorShield",
                    "category": "Accessories",
                    "price": Decimal("499.00"),
                    "description": "Military-grade dual-layer drop protection with integrated 360-degree rotating ring stand.",
                    "image_url": "/static/images/products/case.svg",
                    "stock": 18,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-SV-001",
                    "name": "Original Touch Display Replacement Service",
                    "brand": "Mobile World Service",
                    "category": "Services",
                    "price": Decimal("2199.00"),
                    "description": "Express 1-hour screen replacement using OEM grade displays. Includes 90-day touch warranty and free tempered glass installation.",
                    "image_url": "/static/images/products/service_screen.svg",
                    "stock": 99,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-SV-002",
                    "name": "High-Capacity Battery Replacement Service",
                    "brand": "Mobile World Service",
                    "category": "Services",
                    "price": Decimal("1499.00"),
                    "description": "Restore all-day battery life with certified high-efficiency cell replacement. 6 months warranty included.",
                    "image_url": "/static/images/products/service_battery.svg",
                    "stock": 99,
                    "low_threshold": 5
                }
            ]

            for item in sample_products:
                prod = Product(
                    sku=item["sku"],
                    name=item["name"],
                    brand=item["brand"],
                    category=item["category"],
                    price=item["price"],
                    description=item["description"],
                    image_url=item["image_url"],
                    is_active=True
                )
                db.session.add(prod)
                db.session.flush()

                inv = Inventory(
                    product_id=prod.id,
                    quantity=item["stock"],
                    low_stock_threshold=item["low_threshold"]
                )
                db.session.add(inv)

            db.session.commit()
            print(f"[Seed] Populated {len(sample_products)} catalogue items and inventory records.")

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        try:
            seed_database(app)
        except Exception as e:
            print(f"Database setup error: {e}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
