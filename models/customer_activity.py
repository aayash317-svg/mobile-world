from datetime import datetime
from . import db

class CustomerActivity(db.Model):
    __tablename__ = "customer_activities"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # ORDER_PLACED, ORDER_UPDATED, PROFILE_UPDATED, ADDRESS_ADDED, SECURITY
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    entity_type = db.Column(db.String(50), nullable=True)  # Order, Address, Profile
    entity_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    customer = db.relationship("Customer", back_populates="activities")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p") if self.created_at else None,
            "created_at_iso": self.created_at.isoformat() if self.created_at else None
        }
