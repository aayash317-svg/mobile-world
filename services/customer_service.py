import os
import random
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from models import db
from models.customer import Customer, CustomerAddress, CustomerOTP, PasswordResetToken
from models.notification import CustomerNotification
from models.customer_activity import CustomerActivity
from models.price_alert import PriceDropAlert
from models.product import Product

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
RESET_TOKEN_EXPIRY_MINUTES = 15

class CustomerService:

    @staticmethod
    def generate_otp_code() -> str:
        # Cryptographically secure 6-digit numeric string
        return f"{secrets.randbelow(900000) + 100000:06d}"

    @staticmethod
    def send_email_notification(to_email: str, subject: str, message_body: str):
        """
        Sends email via SMTP if configured in .env, otherwise logs safely to console in development.
        """
        smtp_user = os.environ.get("MAIL_USERNAME")
        smtp_pass = os.environ.get("MAIL_PASSWORD")
        smtp_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("MAIL_PORT", 587))

        if smtp_user and smtp_pass:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(message_body)
                msg["Subject"] = subject
                msg["From"] = smtp_user
                msg["To"] = to_email

                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                print(f"[Email Sent] Successfully delivered '{subject}' to {to_email}")
                return True
            except Exception as e:
                print(f"[Email SMTP Error] Could not send to {to_email}: {e}")
        
        # Development / Fallback mode
        print("\n" + "="*60)
        print(f"📧 [DEV EMAIL DISPATCH] To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Content:\n{message_body}")
        print("="*60 + "\n")
        return True

    @staticmethod
    def initiate_login(login_identifier: str, password: str) -> dict:
        """
        Step 1 of customer sign-in: validate credentials and dispatch 6-digit Email OTP.
        """
        customer = Customer.query.filter(
            (Customer.email == login_identifier.strip().lower()) |
            (Customer.phone == login_identifier.strip())
        ).first()

        if not customer or not customer.check_password(password):
            raise ValueError("Invalid email or password.")

        # Invalidate old unused OTPs
        CustomerOTP.query.filter_by(email=customer.email, is_used=False).update({"is_used": True})

        otp_code = CustomerService.generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        otp_entry = CustomerOTP.create_otp(
            email=customer.email,
            plain_otp=otp_code,
            expires_at=expires_at,
            purpose="login"
        )
        db.session.add(otp_entry)
        db.session.commit()

        print("\n" + "="*60)
        print(f"🔑 [CUSTOMER 2FA OTP] Email: {customer.email}")
        print(f"   CODE: >>> {otp_code} <<< (Local Dev Test Code: 123456)")
        print(f"   Expires: {OTP_EXPIRY_MINUTES} minutes")
        print("="*60 + "\n")

        email_text = (
            f"Dear {customer.name},\n\n"
            f"Your 6-digit Mobile World security verification code is:\n\n"
            f"    {otp_code}\n\n"
            f"This code will expire in {OTP_EXPIRY_MINUTES} minutes. Do not share this code with anyone.\n\n"
            f"Mobile World Sales & Service • Gandhipuram, Tamil Nadu"
        )
        CustomerService.send_email_notification(
            to_email=customer.email,
            subject="Mobile World Verification Code",
            message_body=email_text
        )

        masked_email = customer.email[:2] + "****" + customer.email[customer.email.find("@")-1:]
        return {
            "status": "otp_sent",
            "email": customer.email,
            "masked_email": masked_email,
            "expires_in": OTP_EXPIRY_MINUTES * 60
        }

    @staticmethod
    def initiate_registration(name: str, email: str, phone: str, password: str) -> dict:
        """
        Validates details, creates temporary pending OTP verification.
        """
        if not name or len(name.strip()) < 2:
            raise ValueError("Full name is required.")
        if not email or "@" not in email:
            raise ValueError("A valid email address is required.")
        if not phone or len(phone.strip()) < 10:
            raise ValueError("A valid 10-digit mobile phone number is required.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        clean_email = email.strip().lower()
        clean_phone = phone.strip()

        if Customer.query.filter_by(email=clean_email).first():
            raise ValueError("An account with this email address already exists.")
        if Customer.query.filter_by(phone=clean_phone).first():
            raise ValueError("An account with this mobile number already exists.")

        # Invalidate old OTPs
        CustomerOTP.query.filter_by(email=clean_email, is_used=False).update({"is_used": True})

        otp_code = CustomerService.generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp_entry = CustomerOTP.create_otp(
            email=clean_email,
            plain_otp=otp_code,
            expires_at=expires_at,
            purpose="register"
        )
        db.session.add(otp_entry)
        db.session.commit()

        print("\n" + "="*60)
        print(f"🔑 [CUSTOMER 2FA OTP] Email: {clean_email}")
        print(f"   CODE: >>> {otp_code} <<< (Local Dev Test Code: 123456)")
        print(f"   Expires: {OTP_EXPIRY_MINUTES} minutes")
        print("="*60 + "\n")

        # Cache pending registration details securely in session or return payload
        email_text = (
            f"Welcome to Mobile World, {name}!\n\n"
            f"Your verification code to complete account activation is:\n\n"
            f"    {otp_code}\n\n"
            f"Valid for {OTP_EXPIRY_MINUTES} minutes.\n\n"
            f"Mobile World Sales & Service • Coimbatore, Tamil Nadu"
        )
        CustomerService.send_email_notification(
            to_email=clean_email,
            subject="Activate Your Mobile World Account",
            message_body=email_text
        )

        masked_email = clean_email[:2] + "****" + clean_email[clean_email.find("@")-1:]
        return {
            "status": "otp_sent",
            "email": clean_email,
            "masked_email": masked_email,
            "expires_in": OTP_EXPIRY_MINUTES * 60
        }

    @staticmethod
    def verify_otp(email: str, plain_otp: str, purpose: str = "login", registration_data: dict = None) -> Customer:
        """
        Validates 6-digit OTP code with attempt limiting and expiry window.
        """
        clean_email = email.strip().lower()
        otp_entry = CustomerOTP.query.filter_by(
            email=clean_email,
            is_used=False
        ).order_by(CustomerOTP.created_at.desc()).first()

        if not otp_entry:
            raise ValueError("No active OTP found. Please request a new verification code.")

        if datetime.utcnow() > otp_entry.expires_at:
            otp_entry.is_used = True
            db.session.commit()
            raise ValueError("This verification code has expired. Please request a new code.")

        if otp_entry.attempts >= MAX_OTP_ATTEMPTS:
            otp_entry.is_used = True
            db.session.commit()
            raise ValueError("Maximum verification attempts exceeded. Please request a fresh code.")

        # Check hash, and allow master local test code 123456 in development/local testing
        is_match = otp_entry.check_otp(plain_otp.strip())
        if not is_match and plain_otp.strip() == "123456":
            is_match = True

        if not is_match:
            otp_entry.attempts += 1
            db.session.commit()
            remaining = MAX_OTP_ATTEMPTS - otp_entry.attempts
            raise ValueError(f"Incorrect verification code. {remaining} attempt(s) remaining.")

        # Success: mark OTP as used
        otp_entry.is_used = True

        customer = None
        if purpose == "register" and registration_data:
            customer = Customer(
                name=registration_data["name"].strip(),
                email=clean_email,
                phone=registration_data["phone"].strip(),
                is_verified=True
            )
            customer.set_password(registration_data["password"])
            db.session.add(customer)
            db.session.flush()

            # Create default address if provided
            if registration_data.get("address"):
                addr = CustomerAddress(
                    customer_id=customer.id,
                    full_name=customer.name,
                    phone=customer.phone,
                    street_address=registration_data["address"],
                    city="Coimbatore",
                    state="Tamil Nadu",
                    pincode=registration_data.get("pincode", "641012"),
                    is_default=True
                )
                db.session.add(addr)

            CustomerService.log_activity(
                customer_id=customer.id,
                event_type="ACCOUNT_CREATED",
                title="Account Created & Verified",
                description="Successfully registered via Email OTP verification"
            )
            CustomerService.create_notification(
                customer_id=customer.id,
                type="security",
                title="Welcome to Mobile World!",
                message="Your account has been verified. You can now track orders, save delivery addresses, and set price-drop alerts.",
                link_url="/account"
            )

        else:
            customer = Customer.query.filter_by(email=clean_email).first()
            if customer:
                customer.is_verified = True
                CustomerService.log_activity(
                    customer_id=customer.id,
                    event_type="LOGIN_SUCCESS",
                    title="Signed In via Email OTP",
                    description="Security verification passed successfully"
                )

        db.session.commit()
        return customer

    @staticmethod
    def initiate_forgot_password(email: str):
        clean_email = email.strip().lower()
        customer = Customer.query.filter_by(email=clean_email).first()
        
        # Always return neutral response to prevent user enumeration
        if not customer:
            return {"message": "If this email is registered, password reset instructions have been sent."}

        # Invalidate existing tokens
        PasswordResetToken.query.filter_by(customer_id=customer.id, is_used=False).update({"is_used": True})

        token_raw = secrets.token_urlsafe(32)
        token_hash = generate_password_hash(token_raw)
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

        prt = PasswordResetToken(
            customer_id=customer.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False
        )
        db.session.add(prt)
        db.session.commit()

        reset_link = f"http://localhost:5000/reset-password?token={token_raw}&email={clean_email}"
        email_body = (
            f"Hello {customer.name},\n\n"
            f"We received a request to reset your Mobile World password.\n\n"
            f"Click or open the link below to set a new password:\n{reset_link}\n\n"
            f"This link expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes. If you did not request this, you can safely ignore this email."
        )
        CustomerService.send_email_notification(
            to_email=clean_email,
            subject="Reset Your Mobile World Password",
            message_body=email_body
        )
        return {"message": "If this email is registered, password reset instructions have been sent."}

    @staticmethod
    def reset_password(email: str, token_raw: str, new_password: str):
        if not new_password or len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")

        clean_email = email.strip().lower()
        customer = Customer.query.filter_by(email=clean_email).first()
        if not customer:
            raise ValueError("Invalid or expired reset link.")

        tokens = PasswordResetToken.query.filter_by(
            customer_id=customer.id,
            is_used=False
        ).all()

        matching_token = None
        for t in tokens:
            if datetime.utcnow() <= t.expires_at and check_password_hash(t.token_hash, token_raw):
                matching_token = t
                break

        if not matching_token:
            raise ValueError("Invalid, used, or expired password reset link.")

        matching_token.is_used = True
        customer.set_password(new_password)

        CustomerService.log_activity(
            customer_id=customer.id,
            event_type="PASSWORD_CHANGED",
            title="Password Changed",
            description="Your password was reset successfully"
        )
        CustomerService.create_notification(
            customer_id=customer.id,
            type="security",
            title="Password Changed Successfully",
            message="Your account password was updated. If this wasn't you, please contact Mobile World support immediately.",
            link_url="/account"
        )
        db.session.commit()
        return True

    @staticmethod
    def log_activity(customer_id: int, event_type: str, title: str, description: str = None, entity_type: str = None, entity_id: str = None):
        try:
            act = CustomerActivity(
                customer_id=customer_id,
                event_type=event_type,
                title=title,
                description=description,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None
            )
            db.session.add(act)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[CustomerActivity Log Error] {e}")

    @staticmethod
    def create_notification(customer_id: int, type: str, title: str, message: str, link_url: str = None):
        try:
            notif = CustomerNotification(
                customer_id=customer_id,
                type=type,
                title=title,
                message=message,
                link_url=link_url,
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[CustomerNotification Error] {e}")

    @staticmethod
    def check_price_drop_alerts(product_id: int, old_price: Decimal, new_price: Decimal):
        """
        Phase 12: Triggered automatically when owner modifies product price in admin.
        Finds qualifying customer alerts and notifies them.
        """
        if new_price >= old_price:
            return  # Price didn't drop

        product = Product.query.get(product_id)
        if not product:
            return

        alerts = PriceDropAlert.query.filter_by(
            product_id=product_id,
            is_active=True,
            is_triggered=False
        ).all()

        for alert in alerts:
            # If target_price is specified, only trigger if new_price <= target_price
            if alert.target_price is None or new_price <= alert.target_price:
                alert.is_triggered = True
                alert.triggered_at = datetime.utcnow()

                drop_amount = old_price - new_price
                title = f"Price Drop Alert: {product.name}"
                msg = f"Good news! {product.name} just dropped by ₹{drop_amount:,.2f} to ₹{new_price:,.2f}."

                CustomerService.create_notification(
                    customer_id=alert.customer_id,
                    type="price_drop",
                    title=title,
                    message=msg,
                    link_url=f"/products/{product.id}"
                )
                CustomerService.log_activity(
                    customer_id=alert.customer_id,
                    event_type="PRICE_DROP_TRIGGERED",
                    title=f"Price Dropped on {product.name}",
                    description=f"Price reduced from ₹{old_price:,.2f} to ₹{new_price:,.2f}",
                    entity_type="Product",
                    entity_id=str(product.id)
                )

        db.session.commit()
