from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    preferred_store = db.Column(db.String(150), default="Gandhipuram Cross Cut Rd, CBE", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    addresses = db.relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="customer")
    notifications = db.relationship("CustomerNotification", back_populates="customer", cascade="all, delete-orphan")
    activities = db.relationship("CustomerActivity", back_populates="customer", cascade="all, delete-orphan")
    price_alerts = db.relationship("PriceDropAlert", back_populates="customer", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "is_verified": self.is_verified,
            "preferred_store": self.preferred_store,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CustomerAddress(db.Model):
    __tablename__ = "customer_addresses"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    street_address = db.Column(db.Text, nullable=False)
    landmark = db.Column(db.String(150), nullable=True)
    city = db.Column(db.String(100), default="Coimbatore", nullable=False)
    state = db.Column(db.String(100), default="Tamil Nadu", nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    address_type = db.Column(db.String(20), default="Home", nullable=False)  # Home, Work
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    customer = db.relationship("Customer", back_populates="addresses")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "street_address": self.street_address,
            "landmark": self.landmark,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "address_type": self.address_type,
            "is_default": self.is_default
        }


class CustomerOTP(db.Model):
    __tablename__ = "customer_otps"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(50), default="login", nullable=False)  # login, register, reset
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def check_otp(self, plain_otp: str) -> bool:
        return check_password_hash(self.otp_hash, plain_otp)

    @classmethod
    def create_otp(cls, email: str, plain_otp: str, expires_at: datetime, purpose="login"):
        return cls(
            email=email,
            otp_hash=generate_password_hash(plain_otp),
            purpose=purpose,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
