from datetime import datetime
from decimal import Decimal
import uuid
from . import db

ALLOWED_ORDER_STATUSES = [
    "Pending",
    "Confirmed",
    "Packed",
    "Shipped",
    "Delivered",
    "Cancelled",
    "Returned"
]

ALLOWED_PAYMENT_STATUSES = [
    "Pending COD",
    "Collected",
    "Refunded"
]

class Inventory(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=5, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = db.relationship("Product", back_populates="inventory")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "low_stock_threshold": self.low_stock_threshold,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_reference = db.Column(db.String(32), unique=True, nullable=False, index=True)
    idempotency_key = db.Column(db.String(128), unique=True, nullable=True, index=True)
    
    # Customer Details
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False, index=True)
    customer_email = db.Column(db.String(150), nullable=True)
    delivery_address = db.Column(db.Text, nullable=False)
    order_notes = db.Column(db.Text, nullable=True)

    # Statuses (Strictly Decoupled)
    # Order status: Pending, Confirmed, Packed, Shipped, Delivered, Cancelled, Returned
    order_status = db.Column(db.String(50), default="Pending", nullable=False, index=True)
    # Payment status: Pending COD, Collected, Refunded
    payment_status = db.Column(db.String(50), default="Pending COD", nullable=False, index=True)
    payment_method = db.Column(db.String(50), default="COD", nullable=False)

    # Monetary values (Decimal safe)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(10, 2), default=Decimal("50.00"), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer = db.relationship("Customer", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("PaymentRecord", back_populates="order", cascade="all, delete-orphan")
    history = db.relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusHistory.created_at.desc()")

    @staticmethod
    def generate_reference():
        prefix = datetime.utcnow().strftime("%Y%m%d")
        rand_code = uuid.uuid4().hex[:4].upper()
        return f"MW-{prefix}-{rand_code}"

    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "order_reference": self.order_reference,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email,
            "delivery_address": self.delivery_address,
            "order_notes": self.order_notes,
            "order_status": self.order_status,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "subtotal": float(self.subtotal),
            "delivery_fee": float(self.delivery_fee),
            "total_amount": float(self.total_amount),
            "subtotal_formatted": f"₹{self.subtotal:,.2f}",
            "delivery_fee_formatted": f"₹{self.delivery_fee:,.2f}",
            "total_amount_formatted": f"₹{self.total_amount:,.2f}",
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p") if self.created_at else None,
            "created_at_iso": self.created_at.isoformat() if self.created_at else None,
            "item_count": sum(item.quantity for item in self.items),
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
            data["payments"] = [p.to_dict() for p in self.payments]
            data["history"] = [h.to_dict() for h in self.history]
        return data


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    
    product_name_snapshot = db.Column(db.String(255), nullable=False)
    unit_price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name_snapshot,
            "unit_price": float(self.unit_price_snapshot),
            "unit_price_formatted": f"₹{self.unit_price_snapshot:,.2f}",
            "quantity": self.quantity,
            "line_total": float(self.line_total),
            "line_total_formatted": f"₹{self.line_total:,.2f}",
        }


class PaymentRecord(db.Model):
    __tablename__ = "payment_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), default="Cash on Delivery", nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    recorded_by = db.Column(db.String(100), default="Shop Owner", nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    order = db.relationship("Order", back_populates="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "amount": float(self.amount),
            "amount_formatted": f"₹{self.amount:,.2f}",
            "payment_method": self.payment_method,
            "collected_at": self.collected_at.strftime("%d %b %Y, %I:%M %p") if self.collected_at else None,
            "recorded_by": self.recorded_by,
            "notes": self.notes
        }


class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    previous_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    changed_by = db.Column(db.String(100), default="System", nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    order = db.relationship("Order", back_populates="history")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p") if self.created_at else None
        }
