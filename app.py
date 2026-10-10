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
from models.customer import Customer, CustomerAddress, CustomerOTP, PasswordResetToken
from models.notification import CustomerNotification
from models.customer_activity import CustomerActivity
from models.price_alert import PriceDropAlert
from routes.customer import customer_bp
from routes.auth import auth_bp
from routes.orders import orders_bp
from routes.admin import admin_bp
from routes.analytics import analytics_bp
from services.auth_guard import get_current_customer

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
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)

    # Context processors & template helpers
    @app.context_processor
    def inject_shop_info():
        customer = get_current_customer()
        unread_notifs = 0
        if customer:
            try:
                unread_notifs = CustomerNotification.query.filter_by(customer_id=customer.id, is_read=False).count()
            except Exception:
                unread_notifs = 0
        return {
            "shop_name": "Mobile World Sales & Service",
            "flat_delivery_fee": float(app.config.get("FLAT_DELIVERY_FEE", 50.00)),
            "current_customer": customer,
            "unread_notif_count": unread_notifs
        }

    # Auto-initialize and seed database on startup (skip in automated test suite)
    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                db.create_all()
                seed_database(app)
            except Exception as e:
                print(f"[Init] Initial DB setup note: {e}")
                if "mysql" in str(app.config.get("SQLALCHEMY_DATABASE_URI", "")):
                    print("[Database Fallback] Falling back to SQLite for cloud deployment.")
                    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(Config.BASE_DIR, 'mobile_world.db')}"
                    db.init_app(app)
                    try:
                        db.create_all()
                        seed_database(app)
                    except Exception as inner_e:
                        print(f"[Fallback Error] {inner_e}")

    return app


def seed_database(app):
    with app.app_context():
        db.create_all()

        # 1. Create or sync Default Admin
        admin_username = app.config.get("ADMIN_USERNAME", "admin")
        admin_password = app.config.get("ADMIN_PASSWORD", "MobileWorld@2026")
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
        else:
            existing_admin.set_password(admin_password)
            db.session.commit()

        # 2. Seed Default Demo Customer if not exists
        existing_cust = Customer.query.filter_by(email="ramesh@test.com").first()
        if not existing_cust:
            cust = Customer(
                name="Ramesh Kumar",
                email="ramesh@test.com",
                phone="9876543210",
                is_verified=True
            )
            cust.set_password("password123")
            db.session.add(cust)
            db.session.flush()

            addr = CustomerAddress(
                customer_id=cust.id,
                full_name="Ramesh Kumar",
                phone="9876543210",
                street_address="45, Cross Cut Road, Gandhipuram",
                city="Coimbatore",
                state="Tamil Nadu",
                pincode="641012",
                is_default=True
            )
            db.session.add(addr)
            db.session.commit()
            print("[Seed] Created demo customer account: ramesh@test.com")
        else:
            existing_cust.set_password("password123")
            db.session.commit()

        # 2. Seed Realistic Products if empty
        if Product.query.count() == 0:
            sample_products = [
                {
                    "sku": "MW-PH-001",
                    "name": "OnePlus Nord CE 4 (8GB / 128GB)",
                    "brand": "OnePlus",
                    "category": "Mobile Phones",
                    "price": Decimal("24999.00"),
                    "mrp": Decimal("26999.00"),
                    "description": "Qualcomm Snapdragon 7 Gen 3, 100W SUPERVOOC charging, 50MP Sony LYT-600 OIS camera.",
                    "image_url": "/static/images/products/phone_oneplus.jpg",
                    "stock": 8,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-PH-002",
                    "name": "Samsung Galaxy M35 5G (6GB / 128GB)",
                    "brand": "Samsung",
                    "category": "Mobile Phones",
                    "price": Decimal("16999.00"),
                    "mrp": Decimal("19999.00"),
                    "description": "Monster 6000mAh battery, Exynos 1380 processor, 120Hz sAMOLED display with Corning Gorilla Glass Victus+.",
                    "image_url": "/static/images/products/phone_samsung.jpg",
                    "stock": 12,
                    "low_threshold": 4
                },
                {
                    "sku": "MW-PH-003",
                    "name": "Redmi Note 13 5G (8GB / 256GB)",
                    "brand": "Xiaomi",
                    "category": "Mobile Phones",
                    "price": Decimal("18499.00"),
                    "mrp": Decimal("20999.00"),
                    "description": "108MP ProLight camera, ultra-slim 120Hz AMOLED display, MediaTek Dimensity 6080.",
                    "image_url": "/static/images/products/phone_redmi.jpg",
                    "stock": 5,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-PH-004",
                    "name": "Realme Narzo 70 Turbo 5G (6GB / 128GB)",
                    "brand": "Realme",
                    "category": "Mobile Phones",
                    "price": Decimal("14999.00"),
                    "mrp": Decimal("16999.00"),
                    "description": "MediaTek Dimensity 7300 Energy 5G chip, stainless steel vapor cooling area, motorsport inspired design.",
                    "image_url": "/static/images/products/phone_realme.jpg",
                    "stock": 2,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-VIVO-V30E",
                    "name": "Vivo V30e 5G (8GB / 256GB)",
                    "brand": "Vivo",
                    "category": "Mobile Phones",
                    "price": Decimal("27999.00"),
                    "mrp": Decimal("32999.00"),
                    "description": "Studio Quality Aura Light Portrait, 3D Curved AMOLED Display, 5500mAh Battery with 44W FlashCharge.",
                    "image_url": "/static/images/products/phone_vivo.jpg",
                    "stock": 14,
                    "low_threshold": 3
                },
                {
                    "sku": "MW-APL-IP15-BLK",
                    "name": "Apple iPhone 15 (128GB - Black)",
                    "brand": "Apple",
                    "category": "Mobile Phones",
                    "price": Decimal("69900.00"),
                    "mrp": Decimal("79900.00"),
                    "description": "Dynamic Island, 48MP Main Camera with 2x Telephoto, Color-infused Glass and Aluminum Design, USB-C Connectivity.",
                    "image_url": "/static/images/products/phone_iphone.jpg",
                    "stock": 8,
                    "low_threshold": 2
                },
                {
                    "sku": "MW-AC-001",
                    "name": "67W Super Fast Dual-Port GaN Charger",
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("1299.00"),
                    "mrp": Decimal("1999.00"),
                    "description": "Compact GaN fast charger with USB-C and USB-A ports, surge protection, suitable for all smartphones.",
                    "image_url": "/static/images/products/charger.jpg",
                    "stock": 25,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-AC-002",
                    "name": "Ultra-Tough Braided Type-C to Type-C Cable (1.5m)",
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("399.00"),
                    "mrp": Decimal("699.00"),
                    "description": "Heavy-duty nylon braided cable supporting 100W PD and fast data sync with reinforced stress joints.",
                    "image_url": "/static/images/products/cable.jpg",
                    "stock": 40,
                    "low_threshold": 10
                },
                {
                    "sku": "MW-AC-003",
                    "name": "9D Curved Edge Tempered Glass Screen Guard",
                    "brand": "ArmorShield",
                    "category": "Accessories",
                    "price": Decimal("249.00"),
                    "mrp": Decimal("499.00"),
                    "description": "Edge-to-edge full coverage 9H hardness tempered glass with oleophobic anti-fingerprint coating.",
                    "image_url": "/static/images/products/glass.jpg",
                    "stock": 35,
                    "low_threshold": 10
                },
                {
                    "sku": "MW-AC-004",
                    "name": "Magnetic Shockproof Armor Case with Kickstand",
                    "brand": "ArmorShield",
                    "category": "Accessories",
                    "price": Decimal("499.00"),
                    "mrp": Decimal("899.00"),
                    "description": "Military-grade dual-layer drop protection with integrated 360-degree rotating ring stand.",
                    "image_url": "/static/images/products/case.jpg",
                    "stock": 18,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-AUDIO-TWS-ANC",
                    "name": "True Wireless ANC Active Noise-Cancelling Earbuds",
                    "brand": "SoundWave Pro",
                    "category": "Accessories",
                    "price": Decimal("2499.00"),
                    "mrp": Decimal("4999.00"),
                    "description": "Hybrid 35dB Active Noise Cancellation, Quad Mics for Crystal Clear Calling, 38 Hours Playtime.",
                    "image_url": "/static/images/products/earbuds.jpg",
                    "stock": 25,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-PWR-20K-65W",
                    "name": "20000mAh 65W PD Ultra-Fast Power Bank with LED",
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("2199.00"),
                    "mrp": Decimal("3499.00"),
                    "description": "65W Power Delivery laptop & smartphone fast charging, precision digital percentage screen.",
                    "image_url": "/static/images/products/powerbank.jpg",
                    "stock": 20,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-WCH-AMOLED-PRO",
                    "name": 'Aura Pro 1.43" AMOLED Bluetooth Calling Smartwatch',
                    "brand": "Mobile World Gear",
                    "category": "Accessories",
                    "price": Decimal("2899.00"),
                    "mrp": Decimal("5999.00"),
                    "description": "1000 Nits Ultra-Bright AMOLED Display, Functional Rotating Crown, 24/7 Heart & SpO2 Tracker.",
                    "image_url": "/static/images/products/smartwatch.jpg",
                    "stock": 18,
                    "low_threshold": 4
                },
                {
                    "sku": "MW-SV-001",
                    "name": "Original Touch Display Replacement Service",
                    "brand": "Mobile World Service",
                    "category": "Services",
                    "price": Decimal("2199.00"),
                    "mrp": Decimal("2999.00"),
                    "description": "Express 1-hour screen replacement using OEM grade displays. Includes 90-day touch warranty and free tempered glass installation.",
                    "image_url": "/static/images/products/service_screen.jpg",
                    "stock": 99,
                    "low_threshold": 5
                },
                {
                    "sku": "MW-SV-002",
                    "name": "High-Capacity Battery Replacement Service",
                    "brand": "Mobile World Service",
                    "category": "Services",
                    "price": Decimal("1499.00"),
                    "mrp": Decimal("1999.00"),
                    "description": "Restore all-day battery life with certified high-efficiency cell replacement. 6 months warranty included.",
                    "image_url": "/static/images/products/service_battery.jpg",
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
                    mrp=item.get("mrp"),
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
