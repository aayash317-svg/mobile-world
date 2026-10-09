from datetime import datetime
from . import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)  # Order, Product, Inventory, Auth
    entity_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M:%S %p") if self.created_at else None,
            "created_at_iso": self.created_at.isoformat() if self.created_at else None
        }
