from datetime import datetime
from decimal import Decimal
from . import db

class PriceDropAlert(db.Model):
    __tablename__ = "price_drop_alerts"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    initial_price = db.Column(db.Numeric(10, 2), nullable=False)
    target_price = db.Column(db.Numeric(10, 2), nullable=True)  # Alert when drops below target, or any drop if null
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_triggered = db.Column(db.Boolean, default=False, nullable=False)
    triggered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    customer = db.relationship("Customer", back_populates="price_alerts")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "Product",
            "product_image": self.product.image_url if self.product else "",
            "current_price": float(self.product.price) if self.product else float(self.initial_price),
            "current_price_formatted": f"₹{self.product.price:,.2f}" if self.product else "",
            "initial_price": float(self.initial_price),
            "initial_price_formatted": f"₹{self.initial_price:,.2f}",
            "target_price": float(self.target_price) if self.target_price else None,
            "target_price_formatted": f"₹{self.target_price:,.2f}" if self.target_price else "Any Drop",
            "is_active": self.is_active,
            "is_triggered": self.is_triggered,
            "triggered_at": self.triggered_at.strftime("%d %b %Y") if self.triggered_at else None,
            "created_at": self.created_at.strftime("%d %b %Y") if self.created_at else None
        }
