import os
import sys
import shutil
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.product import Product
from models.order import Inventory

brain_dir = r"C:\Users\aayas\.gemini\antigravity-ide\brain\0b0a7e03-37aa-411a-a396-51f72edc7922"
target_dir = r"d:\mobile world\static\images\products"

copies = [
    ("service_screen_repair_1791634897534.jpg", "service_screen.jpg"),
    ("service_battery_repair_1791634921574.jpg", "service_battery.jpg"),
    ("phone_vivo_v30e_1791634947761.jpg", "phone_vivo.jpg"),
    ("phone_iphone15_black_1791634990377.jpg", "phone_iphone.jpg"),
    ("earbuds_tws_anc_1791635014032.jpg", "earbuds.jpg"),
    ("powerbank_20000mah_1791635044559.jpg", "powerbank.jpg"),
    ("smartwatch_amoled_1791635072356.jpg", "smartwatch.jpg"),
]

for src, dst in copies:
    src_path = os.path.join(brain_dir, src)
    dst_path = os.path.join(target_dir, dst)
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print(f"Copied {src} -> {dst}")
    else:
        print(f"Missing {src}")

app = create_app()
with app.app_context():
    p9 = db.session.get(Product, 9)
    if p9:
        p9.image_url = "/static/images/products/service_screen.jpg"
        print("Updated Product 9 image_url")
    p10 = db.session.get(Product, 10)
    if p10:
        p10.image_url = "/static/images/products/service_battery.jpg"
        print("Updated Product 10 image_url")

    new_products = [
        {
            "sku": "MW-VIVO-V30E",
            "name": "Vivo V30e 5G (8GB / 256GB)",
            "brand": "Vivo",
            "category": "Mobile Phones",
            "description": "Studio Quality Aura Light Portrait, 3D Curved AMOLED Display, 5500mAh Battery with 44W FlashCharge in Silk Green finish.",
            "price": Decimal("27999.00"),
            "mrp": Decimal("32999.00"),
            "ram": "8GB",
            "storage": "256GB",
            "color": "Silk Green",
            "warranty_months": 12,
            "image_url": "/static/images/products/phone_vivo.jpg",
            "stock": 14,
        },
        {
            "sku": "MW-APL-IP15-BLK",
            "name": "Apple iPhone 15 (128GB - Black)",
            "brand": "Apple",
            "category": "Mobile Phones",
            "description": "Dynamic Island, 48MP Main Camera with 2x Telephoto, Color-infused Glass and Aluminum Design, USB-C Connectivity.",
            "price": Decimal("69900.00"),
            "mrp": Decimal("79900.00"),
            "ram": "6GB",
            "storage": "128GB",
            "color": "Black",
            "warranty_months": 12,
            "image_url": "/static/images/products/phone_iphone.jpg",
            "stock": 8,
        },
        {
            "sku": "MW-AUDIO-TWS-ANC",
            "name": "True Wireless ANC Active Noise-Cancelling Earbuds",
            "brand": "SoundWave Pro",
            "category": "Accessories",
            "description": "Hybrid 35dB Active Noise Cancellation, Quad Mics for Crystal Clear Calling, 38 Hours Playtime, IPX5 Water Resistance.",
            "price": Decimal("2499.00"),
            "mrp": Decimal("4999.00"),
            "ram": None,
            "storage": None,
            "color": "Charcoal Black",
            "warranty_months": 12,
            "image_url": "/static/images/products/earbuds.jpg",
            "stock": 25,
        },
        {
            "sku": "MW-PWR-20K-65W",
            "name": "20000mAh 65W PD Ultra-Fast Power Bank with LED",
            "brand": "Mobile World Gear",
            "category": "Accessories",
            "description": "65W Power Delivery laptop & smartphone fast charging, precision digital percentage screen, aircraft-safe multi-protect safety chip.",
            "price": Decimal("2199.00"),
            "mrp": Decimal("3499.00"),
            "ram": None,
            "storage": None,
            "color": "Titanium Gray",
            "warranty_months": 12,
            "image_url": "/static/images/products/powerbank.jpg",
            "stock": 20,
        },
        {
            "sku": "MW-WCH-AMOLED-PRO",
            "name": 'Aura Pro 1.43" AMOLED Bluetooth Calling Smartwatch',
            "brand": "Mobile World Gear",
            "category": "Accessories",
            "description": "1000 Nits Ultra-Bright AMOLED Display, Functional Rotating Crown, 24/7 Heart & SpO2 Tracker, 120+ Sports Modes.",
            "price": Decimal("2899.00"),
            "mrp": Decimal("5999.00"),
            "ram": None,
            "storage": None,
            "color": "Brushed Steel",
            "warranty_months": 12,
            "image_url": "/static/images/products/smartwatch.jpg",
            "stock": 18,
        },
    ]

    for item in new_products:
        existing = Product.query.filter_by(sku=item["sku"]).first()
        if not existing:
            p = Product(
                sku=item["sku"],
                name=item["name"],
                brand=item["brand"],
                category=item["category"],
                description=item["description"],
                price=item["price"],
                mrp=item["mrp"],
                ram=item["ram"],
                storage=item["storage"],
                color=item["color"],
                warranty_months=item["warranty_months"],
                image_url=item["image_url"],
                is_active=True,
            )
            db.session.add(p)
            db.session.flush()
            inv = Inventory(product_id=p.id, quantity=item["stock"], low_stock_threshold=5)
            db.session.add(inv)
            print(f"Created new product {p.id}: {p.name} with stock {item['stock']}")
        else:
            existing.image_url = item["image_url"]
            print(f"Updated existing product {existing.id} image_url")

    db.session.commit()
    print("All products committed to database successfully!")
