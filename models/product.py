from datetime import datetime
from decimal import Decimal
from . import db

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    brand = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)  # Mobile Phones, Accessories, Services
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    inventory = db.relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", back_populates="product")

    @property
    def stock(self):
        return self.inventory.quantity if self.inventory else 0

    @property
    def low_stock_threshold(self):
        return self.inventory.low_stock_threshold if self.inventory else 5

    @property
    def is_low_stock(self):
        if not self.inventory:
            return True
        return self.inventory.quantity <= self.inventory.low_stock_threshold and self.inventory.quantity > 0

    @property
    def is_out_of_stock(self):
        if not self.inventory:
            return True
        return self.inventory.quantity <= 0

    def to_dict(self, include_inventory=True):
        data = {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "description": self.description,
            "price": float(self.price),
            "price_formatted": f"₹{self.price:,.2f}",
            "image_url": self.image_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_inventory:
            data.update({
                "stock": self.stock,
                "low_stock_threshold": self.low_stock_threshold,
                "is_low_stock": self.is_low_stock,
                "is_out_of_stock": self.is_out_of_stock,
            })
        return data
