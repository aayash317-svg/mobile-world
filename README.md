# Mobile World Sales & Service — E-Commerce & Owner Dashboard

Production-ready, two-page web system built for **Mobile World Sales & Service** (Tamil Nadu, India). Built with **Python Flask**, **MySQL 8.0**, **vanilla JavaScript**, and **Chart.js**, featuring strict financial integrity, concurrency-safe inventory controls, Cash on Delivery (COD) accounting, an owner analytics dashboard, and an activity audit log.

---

## 1. Key URLs & Entry Points

| Page | URL | Access | Purpose |
| :--- | :--- | :--- | :--- |
| **Customer Storefront** | `http://localhost:5000/` | Public | Browse phones, accessories, repair services, manage cart, place COD orders |
| **Owner Dashboard** | `http://localhost:5000/admin/` | Authenticated | Live business KPIs, 7d/30d analytics, order fulfillment, stock management, audit trail |
| **Owner Login** | `http://localhost:5000/admin/login` | Public/Auth | Secure login portal with brute-force rate limiting and session security |

* **Demo Owner Credentials**:
  * **Username**: `admin`
  * **Password**: `admin123`

---

## 2. Architecture & Directory Structure

```text
mobile world/
├── app.py                      # Flask factory, route registration, auto-seeding
├── config.py                   # Environment configuration (MySQL + SQLite fallback)
├── requirements.txt            # Python dependencies (Flask, PyMySQL, SQLAlchemy, etc.)
├── .env                        # Local secrets & credentials (git-ignored)
├── .env.example                # Safe environment template
├── .gitignore                  # Git exclusions for secrets, venvs, and backups
├── backups/                    # Timestamped MySQL backup dumps (.sql)
├── models/
│   ├── __init__.py             # SQLAlchemy instance
│   ├── user.py                 # Owner user model with Werkzeug password hashing
│   ├── product.py              # Products with decimal pricing and inventory linkage
│   ├── order.py                # Order, OrderItem, Inventory, PaymentRecord, OrderStatusHistory
│   └── activity_log.py         # Auditable activity log table
├── routes/
│   ├── customer.py             # Public storefront & product search/filter APIs
│   ├── orders.py               # Order placement with server-side validation & idempotency
│   ├── admin.py                # Protected owner routes, rate limiting, and management APIs
│   └── analytics.py            # KPI aggregation & Chart.js data endpoints
├── services/
│   ├── inventory_service.py    # Atomic stock deduction & restoration with row locking
│   ├── order_service.py        # Order creation, status transitions, COD cash accounting
│   └── activity_service.py     # Centralized action & security audit logger
├── templates/
│   ├── customer/
│   │   └── index.html          # Responsive storefront showcasing real shop photos & COD checkout
│   └── admin/
│       ├── login.html          # Branded owner login with demo credentials
│       └── dashboard.html      # Responsive management portal with Chart.js analytics & modals
├── static/
│   ├── css/
│   │   ├── customer.css        # Modern, mobile-first retail styles
│   │   └── admin.css           # Clean, glassmorphic owner dashboard stylesheet
│   ├── js/
│   │   ├── customer.js         # Client-side cart, stock validation, and checkout
│   │   └── admin.js            # Chart.js charts, order transitions, and stock management
│   └── images/
│       ├── shop/               # Real Mobile World shop photos & branding logo
│       │   ├── logo.png        # Official MW Mobile World Sales & Service emblem logo
│       │   ├── storefront.jpg  # Real night exterior photo of shop
│       │   ├── repair_counter.jpg # Real interior technician bench & repair counter
│       │   ├── billing_desk.jpg   # Real billing & recharge desk
│       │   ├── accessories_shelves.jpg # Real accessories display wall
│       │   └── outdoor_kiosk.jpg       # Real illuminated outdoor kiosk
│       └── products/           # Crisp product vector assets
├── scripts/
│   ├── backup_db.py            # Automated MySQL backup utility with retention policy
│   ├── restore_db.py           # Safe restoration script targeting isolated test database
│   └── test_live_e2e.py        # Full live end-to-end integration test against MySQL
└── tests/
    └── test_all.py             # 11 automated pytest test suites covering all 6 phases
```

---

## 3. Implemented Phases & Features

### Phase 1 — Essential Security
* **Protected Admin Routes**: All `/admin/` and `/api/admin/*` endpoints strictly require authenticated sessions; unauthorized requests are rejected with HTTP 401 or redirected.
* **Password Hashing**: Passwords stored using Werkzeug secure password hashing (PBKDF2/SHA256).
* **Login Rate Limiting**: In-memory IP-based rate limiting (locks out after 5 consecutive failed attempts for 5 minutes).
* **Server-Side Validation**: Product prices, subtotal, flat delivery fee (₹50.00), and grand totals are calculated entirely on the server from MySQL records. Browser-tampered prices and totals are completely ignored.
* **Concurrency-Safe Stock Deduction**: Atomic stock deductions using database transactions with row-level locking (`with_for_update`) preventing race conditions and overselling.
* **Idempotency Protection**: Duplicate order submissions prevented via client-generated unique idempotency keys.
* **Separation of Concerns**: COD payment status (`Pending COD`, `Collected`) is strictly decoupled from order fulfillment status.

### Phase 2 — Order Management
* **Order Status Pipeline**: Full support for `Pending` $\rightarrow$ `Confirmed` $\rightarrow$ `Packed` $\rightarrow$ `Shipped` $\rightarrow$ `Delivered`, plus `Cancelled` and `Returned`.
* **Stock Restoration**: Transitioning an order to `Cancelled` or `Returned` automatically restores reserved stock back to the inventory in MySQL.
* **Audit History**: Every status transition is timestamped and recorded in `order_status_history`.
* **Customer Reference**: Unique, user-friendly order reference generated (e.g. `MW-20261009-00A9`).

### Phase 3 — Low-Stock Alerts
* **Configurable Thresholds**: Each product has a configurable `low_stock_threshold` in the `inventory` table.
* **Visual Warnings**: Low-stock products are highlighted with amber warning badges in both customer catalogue and owner dashboard.
* **Banner Notification**: A prominent alert banner appears on the owner dashboard listing products requiring reorder attention.
* **Direct Stock Adjustment**: Authorized owners can adjust available quantity and thresholds via the dashboard modal.

### Phase 4 — Sales Dashboard & Charts
* **Honest Accounting Rules**:
  * **Order Value**: Total monetary value of active placed orders.
  * **Delivered COD Value**: Value of packages successfully delivered.
  * **Collected Sales**: **Strictly cash recorded as physically collected** in `payment_records`. Uncollected COD is never counted as collected revenue!
  * **COD Awaiting Collection**: Outstanding cash to be collected from active shipments.
* **Chart.js Visualizations**:
  1. **Daily Collected Sales vs Order Value Trend** (Line chart with 7-day and 30-day view toggles).
  2. **Orders by Status Breakdown** (Doughnut chart).
  3. **Top-Selling Products by Volume** (Bar chart).
  4. **COD Cash Collection Summary** (Pie chart).

### Phase 5 — Admin Activity Log
* **Audit Trail Entity**: `activity_logs` table recording `timestamp`, `user_id`, `username`, `action`, `entity_type`, `entity_id`, `details`, and `ip_address`.
* **Tracked Events**: `ADMIN_LOGIN`, `ADMIN_LOGOUT`, `LOGIN_FAILED`, `ORDER_CREATED`, `ORDER_STATUS_CHANGED`, `COD_PAYMENT_COLLECTED`, `PRODUCT_CREATED`, `PRODUCT_UPDATED`, `STOCK_ADJUSTED`.
* **Dashboard Tab**: Real-time searchable activity log panel in the owner dashboard.

### Phase 6 — Database Backup & Recovery
* **Automated Backup**: `scripts/backup_db.py` uses `mysqldump` with `--single-transaction --quick` to create timestamped `.sql` backups in `backups/`.
* **Retention Policy**: Automatically rotates backups, retaining the 7 most recent files.
* **Safe Recovery**: `scripts/restore_db.py` safely restores backups into an isolated test database (`mobile_world_test_restore_db`), protecting the live production database from accidental overwrites.

---

## 4. Setup & Running Instructions

### Prerequisites
* Python 3.11+
* MySQL Server 8.0 running locally on port 3306

### Quick Setup

1. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure MySQL Database**:
   Verify your `.env` file credentials:
   ```env
   DB_TYPE=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=mobile_world_db
   DB_USER=mobile_user
   DB_PASSWORD=MobileWorld@2026
   SECRET_KEY=mobile-world-secure-secret-key-2026-production-ready
   FLAT_DELIVERY_FEE=50.00
   PORT=5000
   ```

4. **Initialize & Seed Database**:
   ```powershell
   python -c "from app import create_app, seed_database; app = create_app(); seed_database(app);"
   ```

5. **Start Application Server**:
   ```powershell
   python app.py
   ```
   * Open Storefront: `http://localhost:5000/`
   * Open Owner Dashboard: `http://localhost:5000/admin/` (Login: `admin` / `admin123`)

---

## 5. Automated Tests & Verification

### Running the Pytest Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v tests/test_all.py
```
**Test Results**:
* `test_unauthorized_admin_api_rejected` — **PASSED**
* `test_admin_login_success_and_logout` — **PASSED**
* `test_admin_login_invalid_credentials` — **PASSED**
* `test_server_calculates_price_ignoring_client_tampering` — **PASSED**
* `test_checkout_invalid_details_rejected` — **PASSED**
* `test_out_of_stock_rejected` — **PASSED**
* `test_two_purchases_competing_for_last_unit` — **PASSED**
* `test_idempotency_prevents_duplicate_orders` — **PASSED**
* `test_status_transitions_and_restoration_on_cancellation` — **PASSED**
* `test_cod_not_counted_as_revenue_until_collected` — **PASSED**
* `test_activity_log_records_owner_actions` — **PASSED**

*Result: 11 passed in 2.41s.*

### Running Live MySQL End-to-End Test
```powershell
python scripts/test_live_e2e.py
```
*Result: Verified full order placement, stock decrement, status transitions, cash collection, KPI updates, and activity audit trail on local MySQL 8.0.*

---

## 6. Backup & Restoration Procedures

### Creating a Database Backup
```powershell
python scripts/backup_db.py
```
*Output: Generates `backups/mobile_world_backup_YYYYMMDD_HHMMSS.sql` with automatic 7-day retention rotation.*

### Testing Restoration (Isolated Test Database)
```powershell
python scripts/restore_db.py mobile_world_test_restore_db
```
*Safety Note: To protect live production data, the script rejects any attempt to overwrite `mobile_world_db` unless `--force-production` is explicitly passed.*

---

## 7. Status Summary of Features

| Phase | Feature | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Secure Admin Login | **Completed** | Sessions, Werkzeug hashing, lockout rate-limiting |
| **Phase 1** | Server-Side Checkout & Pricing | **Completed** | Decimal-safe math, browser tampering immune |
| **Phase 1** | Concurrency Stock Reservation | **Completed** | Row-level locking with atomic rollback |
| **Phase 2** | Order Management & Pipeline | **Completed** | Pending, Confirmed, Packed, Shipped, Delivered, Cancelled, Returned |
| **Phase 2** | Stock Restoration on Cancellation | **Completed** | Automatically triggered on Cancelled or Returned |
| **Phase 3** | Low-Stock Threshold Alerts | **Completed** | Configurable per product with dashboard alert banner |
| **Phase 4** | Sales Dashboard & Chart.js | **Completed** | 7d/30d trends, strict separation of placed vs. collected cash |
| **Phase 5** | Admin Activity Audit Log | **Completed** | Log table tracking all admin & order mutations |
| **Phase 6** | Backup & Recovery Scripts | **Completed** | Timestamped dumps & test recovery script |
| **Phase 7** | WhatsApp / SMS Order Alerts | *Planned for Production* | Ready for Twilio / Gupshup webhook integration |
| **Phase 7** | Google Maps Shop Location Embed | *Planned for Production* | Ready for verified Google Business profile embed |
