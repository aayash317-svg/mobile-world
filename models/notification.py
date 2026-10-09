from datetime import datetime
from . import db

class CustomerNotification(db.Model):
    __tablename__ = "customer_notifications"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(50), default="order", nullable=False)  # order, repair, price_drop, security, store
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    customer = db.relationship("Customer", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "link_url": self.link_url,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%d %b, %I:%M %p") if self.created_at else None,
            "created_at_iso": self.created_at.isoformat() if self.created_at else None
        }
