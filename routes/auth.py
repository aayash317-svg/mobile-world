import time
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db
from models.customer import Customer
from services.customer_service import CustomerService
from services.rate_limiter import rate_limit
from services.auth_guard import get_current_customer

auth_bp = Blueprint("auth", __name__)

# --- HTML Views ---

@auth_bp.route("/signin", methods=["GET"])
def signin_view():
    if get_current_customer():
        next_url = request.args.get("next") or url_for("customer.account_hub")
        return redirect(next_url)
    return render_template("customer/signin.html", next=request.args.get("next", ""))

@auth_bp.route("/register", methods=["GET"])
def register_view():
    if get_current_customer():
        return redirect(url_for("customer.account_hub"))
    return render_template("customer/register.html", next=request.args.get("next", ""))

@auth_bp.route("/verify-otp", methods=["GET"])
def verify_otp_view():
    purpose = session.get("pending_otp_purpose")
    email = session.get("pending_otp_email")
    if not email:
        return redirect(url_for("auth.signin_view"))
    
    masked_email = email[:2] + "****" + email[email.find("@")-1:]
    return render_template(
        "customer/verify_otp.html",
        email=email,
        masked_email=masked_email,
        purpose=purpose or "login",
        next=request.args.get("next", "")
    )

@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_view():
    return render_template("customer/forgot_password.html")

@auth_bp.route("/reset-password", methods=["GET"])
def reset_password_view():
    token = request.args.get("token", "")
    email = request.args.get("email", "")
    if not token or not email:
        return render_template("customer/reset_password.html", error="Invalid or missing reset link parameters.")
    return render_template("customer/reset_password.html", token=token, email=email)


# --- JSON APIs with Rate Limiting ---

@auth_bp.route("/api/auth/login", methods=["POST"])
@rate_limit(limit=5, window_seconds=60)
def api_login():
    data = request.get_json() or {}
    identifier = data.get("identifier") or data.get("email") or ""
    password = data.get("password") or ""

    if not identifier.strip() or not password:
        return jsonify({"error": "Please enter both your email/phone and password."}), 400

    try:
        res = CustomerService.initiate_login(identifier, password)
        # Store temporary verification state in session
        session["pending_otp_email"] = res["email"]
        session["pending_otp_purpose"] = "login"
        session["pending_otp_timestamp"] = time.time()
        session["pending_otp_next"] = data.get("next", "")

        return jsonify({
            "message": "Verification code sent to your registered email.",
            "status": "otp_sent",
            "masked_email": res["masked_email"],
            "redirect": url_for("auth.verify_otp_view", next=data.get("next", ""))
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Unable to sign in. Please try again."}), 500


@auth_bp.route("/api/auth/register", methods=["POST"])
@rate_limit(limit=5, window_seconds=60)
def api_register():
    data = request.get_json() or {}
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    address = data.get("address", "")
    pincode = data.get("pincode", "")

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    try:
        res = CustomerService.initiate_registration(name, email, phone, password)
        session["pending_otp_email"] = res["email"]
        session["pending_otp_purpose"] = "register"
        session["pending_otp_reg_data"] = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": password,
            "address": address,
            "pincode": pincode
        }
        session["pending_otp_timestamp"] = time.time()
        session["pending_otp_next"] = data.get("next", "")

        return jsonify({
            "message": "Account validation started. 6-digit verification code sent to your email.",
            "status": "otp_sent",
            "masked_email": res["masked_email"],
            "redirect": url_for("auth.verify_otp_view", next=data.get("next", ""))
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Registration failed. Please check inputs and try again."}), 500


@auth_bp.route("/api/auth/verify-otp", methods=["POST"])
@rate_limit(limit=10, window_seconds=60)
def api_verify_otp():
    data = request.get_json() or {}
    otp = data.get("otp", "").strip()
    email = session.get("pending_otp_email")
    purpose = session.get("pending_otp_purpose", "login")

    if not email:
        return jsonify({"error": "No pending verification session. Please sign in or register first."}), 400

    if not otp or len(otp) != 6:
        return jsonify({"error": "Please enter all 6 digits of the verification code."}), 400

    reg_data = session.get("pending_otp_reg_data") if purpose == "register" else None

    try:
        customer = CustomerService.verify_otp(
            email=email,
            plain_otp=otp,
            purpose=purpose,
            registration_data=reg_data
        )

        if not customer:
            return jsonify({"error": "Verification failed."}), 400

        # Authenticate customer session
        session["customer_id"] = customer.id
        session["customer_name"] = customer.name
        session["customer_email"] = customer.email

        # Clean pending OTP session variables
        next_dest = session.pop("pending_otp_next", "") or url_for("customer.account_hub")
        session.pop("pending_otp_email", None)
        session.pop("pending_otp_purpose", None)
        session.pop("pending_otp_reg_data", None)
        session.pop("pending_otp_timestamp", None)

        return jsonify({
            "message": "Verification successful!",
            "customer": customer.to_dict(),
            "redirect": next_dest
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An error occurred during verification. Please try again."}), 500


@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
@rate_limit(limit=2, window_seconds=60)
def api_resend_otp():
    email = session.get("pending_otp_email")
    purpose = session.get("pending_otp_purpose", "login")

    if not email:
        return jsonify({"error": "No pending verification found."}), 400

    try:
        customer = Customer.query.filter_by(email=email).first()
        name = customer.name if customer else (session.get("pending_otp_reg_data", {}).get("name", "Customer"))

        otp_code = CustomerService.generate_otp_code()
        from datetime import datetime, timedelta
        from models.customer import CustomerOTP
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        # Invalidate old OTPs
        CustomerOTP.query.filter_by(email=email, is_used=False).update({"is_used": True})

        otp_entry = CustomerOTP.create_otp(
            email=email,
            plain_otp=otp_code,
            expires_at=expires_at,
            purpose=purpose
        )
        db.session.add(otp_entry)
        db.session.commit()

        email_text = (
            f"Dear {name},\n\n"
            f"Your new 6-digit Mobile World verification code is:\n\n"
            f"    {otp_code}\n\n"
            f"Valid for 5 minutes.\n\n"
            f"Mobile World Sales & Service • Coimbatore, Tamil Nadu"
        )
        CustomerService.send_email_notification(
            to_email=email,
            subject="New Mobile World Verification Code",
            message_body=email_text
        )

        return jsonify({"message": "A new verification code has been dispatched to your email."}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to resend code: {str(e)}"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST", "GET"])
def api_logout():
    customer = get_current_customer()
    if customer:
        CustomerService.log_activity(
            customer_id=customer.id,
            event_type="LOGOUT",
            title="Signed Out",
            description="Ended session safely"
        )
    session.pop("customer_id", None)
    session.pop("customer_name", None)
    session.pop("customer_email", None)
    if request.is_json:
        return jsonify({"message": "Signed out successfully", "redirect": url_for("customer.index")})
    return redirect(url_for("customer.index"))


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
@rate_limit(limit=3, window_seconds=60)
def api_forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"error": "Please provide a valid registered email address."}), 400

    res = CustomerService.initiate_forgot_password(email)
    return jsonify(res), 200


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
@rate_limit(limit=5, window_seconds=60)
def api_reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    token = data.get("token", "").strip()
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    try:
        CustomerService.reset_password(email, token, new_password)
        return jsonify({
            "message": "Password reset successfully. You can now sign in with your new password.",
            "redirect": url_for("auth.signin_view")
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to reset password. Please request a new reset link."}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    customer = get_current_customer()
    if not customer:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "customer": customer.to_dict()
    }), 200
