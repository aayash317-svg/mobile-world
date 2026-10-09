# Mobile World Sales & Service --- Two-Page Demo System Requirements

**Purpose:** Build a clean, working sample demo for the real Mobile
World Sales & Service shop. The system must have two separate entry
pages: a customer storefront and a private shop-owner dashboard.

## 1. Project goals

-   Present the shop's mobile phones and accessories professionally.
-   Let customers browse products, add items to a cart, and place Cash
    on Delivery (COD) orders.
-   Let the shop owner review orders, manage products and stock, and
    understand shop performance through charts.
-   Reuse the existing project structure, backend, database, and working
    features wherever possible.
-   Use the actual photos of the Mobile World shop provided by the
    owner. Do not replace them with unrelated stock photos.
-   Keep the demo honest: label sample/demo data clearly and do not
    claim unfinished integrations are complete.

## 2. The two page system

### Page A --- Customer Storefront

**Entry URL:** `/`

This is the public page for customers. It must not expose private owner
analytics or admin controls.

Required sections: 1. **Header/navigation** - Shop name: **MOBILE WORLD
SALES & SERVICE** - Logo or simple text logo - Home, Mobiles,
Accessories, Services, Contact - Search icon or search field - Cart
indicator with item count - Sign in / account option if accounts already
exist 2. **Hero section** - Use a real shop image supplied by the
owner. - Headline such as "Mobiles, Accessories & Service --- All in One
Place." - Short supporting text and a "Shop Products" call to action. 3.
**Product catalogue** - Product image, name, brand, price, and
stock/availability. - Categories: Mobile Phones, Accessories, and
Services if services are represented as catalogue items. - Search and
category filters. - Product details or a clear product card. -
Add-to-cart control with quantity handling. 4. **Cart** - Update
quantities and remove items. - Show subtotal, flat delivery fee, and
final total clearly. - Validate stock and quantity before order
placement. 5. **Checkout** - Customer name, phone number, delivery
address, and any required order notes. - Guest checkout should work;
account creation is optional. - Payment method for this demo: **Cash on
Delivery (COD)**. - State clearly that COD payment is collected on
delivery; do not mark the order as paid before collection. 6. **Order
confirmation** - Show an order number/reference and summary after the
server successfully creates the order. - Avoid displaying internal
database IDs or private admin details. 7. **Footer** - Shop name,
contact information only if provided by the owner, service information,
and basic policy links/placeholders.

### Page B --- Private Shop-Owner Dashboard

**Entry URL:** `/admin/`

This is a separate, private page for the owner. Protect it with
authentication. Hiding the link is not sufficient security.

#### B1. Overview cards

Show useful KPIs using actual database records when available: - Orders
in the selected period - Sales collected - COD amount awaiting
collection - Average order value - Products low in stock - Orders
awaiting processing

**Metric definitions:** - Separate placed order value from collected
revenue. - A COD order is not collected revenue until payment has
actually been received and recorded. - Cancelled/refunded orders should
be handled consistently and excluded from sales totals where
appropriate. - If demo data is used, label it clearly as **Sample
Data**.

#### B2. Analytics charts

Provide readable, responsive charts with titles, date ranges,
axes/legends, and empty states.

1.  **Sales trend (line chart):** daily collected sales over the last 7
    days. If showing order value instead, label it "Order Value," not
    "Collected Sales."
2.  **Orders by status (bar or doughnut chart):** pending, confirmed,
    processing, shipped/out for delivery, delivered, cancelled. Use the
    project's actual status names.
3.  **Top-selling products (bar chart):** based on order-item quantities
    from real order records.
4.  **Inventory health (bar chart or clear low-stock table):** available
    stock and low-stock products.
5.  **Payment summary (optional):** COD awaiting collection vs COD
    collected. Do not treat unpaid COD orders as revenue.

If the database has no real records, show an honest empty state such as
"No sales recorded yet," or show clearly labelled sample data for the
demo. Never fabricate live business results.

#### B3. Order management

-   List orders with order reference, date, customer, item count, total,
    payment method, payment state, and order status.
-   Search/filter by order reference, date, and status.
-   Open order details and view line items and delivery information.
-   Update order status through allowed transitions.
-   Record COD collection explicitly when payment is received.
-   Keep status and payment state as separate fields.

#### B4. Product and inventory management

-   Add/edit/deactivate products.
-   Store product name, brand, category, price, image, description, SKU
    or unique identifier, and active state.
-   Show stock on hand and a configurable low-stock threshold.
-   Validate prices and stock quantities on the server.
-   Prevent ordering more units than are available.
-   Show clear warnings for low-stock and out-of-stock products.

#### B5. Owner access and navigation

-   Owner login/logout.
-   Dashboard navigation: Overview, Analytics, Orders, Products,
    Inventory, Settings.
-   Only authenticated and authorized owner/admin users can access
    private APIs and pages.
-   Never place passwords, secret keys, or database credentials in
    frontend JavaScript.

## 3. URL and page separation

Keep these two main entry points easy to find and demonstrate:

  -----------------------------------------------------------------------
  Page              URL               Audience          Main purpose
  ----------------- ----------------- ----------------- -----------------
  Customer          `/`               Public customers  Browse products
  Storefront                                            and place COD
                                                        orders

  Owner Dashboard   `/admin/`         Authenticated     View performance,
                                      shop owner        manage orders,
                                                        products, and
                                                        stock
  -----------------------------------------------------------------------

If the existing project uses different routes or a separate frontend
development port, keep its current routing convention and document the
final customer and owner URLs in the README. Do not create two links
that accidentally open the same page.

## 4. Data and backend expectations

-   Inspect the existing codebase before editing. Reuse existing routes,
    models, database schema, and working UI where practical.

-   Use server-side validation for checkout, stock, price, order totals,
    and admin actions.

-   Calculate the final price on the server from trusted product prices
    and the configured flat delivery fee. Do not trust totals submitted
    by the browser.

-   Create an order and reserve/decrement stock safely so two customers
    cannot oversell the same item.

-   Protect order creation against accidental duplicate submissions
    where practical.

-   Keep order status separate from payment status.

-   Use real database records for owner analytics whenever possible.

-   Add an analytics endpoint if needed, for example:
    `GET /api/admin/analytics/summary?range=7d`

-   Example response shape (illustrative only; calculate actual values
    in the backend):

    ``` json
    {
      "range": "7d",
      "ordersCount": 0,
      "collectedSales": 0,
      "codAwaitingCollection": 0,
      "averageOrderValue": 0,
      "ordersByStatus": [],
      "dailyCollectedSales": [],
      "topProducts": [],
      "lowStockProducts": []
    }
    ```

-   If the existing backend cannot support a feature before the demo,
    document the limitation instead of presenting a fake working
    feature.

## 5. Actual shop photos and visual design

-   Use the owner's supplied Mobile World storefront, shelves, phones,
    accessories, repair-counter, and cases photos where relevant.
-   Suggested placements:
    -   Storefront exterior photo: customer hero/banner.
    -   Phone/accessory shelves: catalogue/category sections.
    -   Repair counter: services section, if the shop offers repairs.
    -   Product photos: individual product cards only when the image
        actually matches the product.
-   Do not present a shop photo as if it were a specific product image.
-   Visual direction: modern, trustworthy, mobile-first retail design;
    readable text, strong contrast, clear product prices, accessible
    buttons, consistent spacing, and responsive layouts.
-   Use lightweight transitions only where useful; keep cart and
    checkout quick and accessible.
-   Optimize images for fast loading and add meaningful alt text.

## 6. Suggested project structure

Adapt this to the existing project rather than forcing a rewrite:

``` text
mobile-world/
├── customer/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── admin/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── assets/
│   └── shop-photos/
├── backend/
│   ├── routes/
│   ├── models/
│   └── services/
└── README.md
```

If the current project already has a working frontend/backend structure,
preserve it and map these responsibilities onto its existing folders.

## 7. Minimum data entities

Reuse current database models if present. Otherwise, the system will
generally need:

-   **Product:** ID, name, brand, category, description, price, image,
    SKU, active state.
-   **Inventory:** product ID, quantity available, low-stock threshold,
    updated timestamp.
-   **Order:** reference, customer/contact/delivery details, status,
    payment method, payment state, subtotal, delivery fee, total,
    timestamps.
-   **Order item:** order ID, product ID, product-name/price snapshot,
    quantity, line total.
-   **Owner/admin:** credentials stored securely and role/authorization
    information.
-   **Payment/collection record:** amount, method, collection time, and
    staff/owner action where applicable.

Never store plaintext passwords. Use the existing framework's secure
password hashing and session/authentication mechanism.

## 8. Demo flow

### Customer demo

1.  Open `/`.
2.  Show the real shop branding and photos.
3.  Search or filter for a phone/accessory.
4.  Add an item to the cart and change quantity.
5.  Show subtotal + flat delivery fee + total.
6.  Place a COD order using test customer details.
7.  Show the order confirmation and reference.

### Owner demo

1.  Open `/admin/` in a separate tab.
2.  Log in as the owner.
3.  Show overview KPIs and their date range.
4.  Explain each chart and whether it uses real or clearly labelled
    sample data.
5.  Open the new customer order.
6.  Update the order status.
7.  Demonstrate product/stock management.
8.  If COD collection recording exists, show how collected payment is
    recorded; otherwise state it is not yet implemented.

## 9. Before-demo checklist

-   [ ] Both entry pages open separately and work.
-   [ ] Customer page works on mobile and desktop.
-   [ ] Owner dashboard is protected by authentication.
-   [ ] Real shop photos are used in relevant sections.
-   [ ] At least one complete COD order is tested end-to-end.
-   [ ] The same order appears in the owner dashboard.
-   [ ] Totals and delivery fee are correct.
-   [ ] Charts are populated from real data or labelled sample data.
-   [ ] Empty states are handled.
-   [ ] No broken images, console errors, or dead navigation links.
-   [ ] No credentials or secrets are exposed in frontend code.
-   [ ] Demo data and unfinished features are clearly disclosed.

## 10. Production work that must not be misrepresented as complete

Before taking real customer orders at scale, verify and test: - Database
transactions and concurrent stock reservation. - Duplicate order
prevention/idempotency. - Cancellation and stock restoration rules. -
Secure owner authentication, session expiry, and authorization on every
private API. - Input validation, rate limiting, and protection against
common web attacks. - Backup and restore procedures, logs, and
monitoring. - Privacy handling for customer names, phone numbers, and
addresses. - COD collection reconciliation and refund/cancellation
workflows. - Online payment gateway, verified server-side webhooks, and
refund handling if online payments are later introduced. -
Delivery/fulfilment workflow and clear customer policies.

Do not claim online payments are integrated in this demo unless a real
gateway has been implemented and tested end-to-end.

## 11. Implementation instructions for the coding agent

1.  Read this file fully.
2.  Inspect the existing repository and report the current framework,
    routes, database, and features before making changes.
3.  Preserve the working customer storefront, admin dashboard, and COD
    checkout.
4.  Implement the two distinct page experiences: public `/` and private
    `/admin/`.
5.  Connect the admin charts to actual database-derived analytics.
6.  Use the real shop images already supplied in the project; ask for
    missing files rather than substituting unrelated stock images.
7.  Test one COD order from customer checkout through appearance in the
    owner dashboard.
8.  Test mobile responsiveness, stock validation, navigation, and admin
    access restrictions.
9.  Do not rewrite the entire project unless a concrete technical reason
    is found.
10. Update README with setup steps, demo accounts (never real secrets),
    both page URLs, implemented features, known limitations, and test
    results.
11. Provide a final summary listing changed files, test
    commands/results, what works, and what remains unfinished.

## 12. Definition of done for this demo

The demo is ready when: - Customers can browse products and successfully
place a COD order. - The owner can sign in on a separate dashboard page
and see/manage that order. - The dashboard shows understandable charts
and KPIs based on actual records or explicitly labelled sample data. -
The two page URLs are documented and visibly distinct. - Actual shop
branding/photos are used where available. - Known limitations are
documented honestly.


---

# 13. Confirmed technology stack

The current project stack is:

- **Frontend:** HTML5, CSS3, vanilla JavaScript.
- **Backend:** Python + Flask.
- **Database:** MySQL.
- **Dashboard charts:** Chart.js.
- **Version control:** Git + GitHub.
- **Testing:** pytest, plus browser-based end-to-end testing.

Use the existing Flask/MySQL integration wherever it already works. Use Flask-SQLAlchemy only if compatible with the current codebase and if it improves maintainability; do not migrate the whole application just to adopt it.

Optional supporting packages, subject to the existing environment:
- **Flask-Login** for owner sessions if an equivalent secure login system does not already exist.
- **Flask-Migrate** for controlled database schema migrations if the project uses SQLAlchemy.
- **Flask-WTF or equivalent CSRF protection** for cookie-authenticated state-changing forms.
- **pytest** for backend and business-rule tests.

Inspect current dependency versions first. Choose maintained, compatible versions and avoid blind upgrades that could break the demo.

# 14. Recommended target folder structure

Adapt the structure below to the repository as it exists; do not move files or restructure the project unless needed.

```text
mobile-world/
├── app.py
├── config.py
├── requirements.txt
├── .env                  # Local secrets; never commit
├── .gitignore
├── models/
│   ├── product.py
│   ├── order.py
│   └── user.py
├── routes/
│   ├── customer.py
│   ├── orders.py
│   ├── admin.py
│   └── analytics.py
├── services/
│   ├── order_service.py
│   └── inventory_service.py
├── templates/
│   ├── customer/
│   │   └── index.html
│   └── admin/
│       ├── login.html
│       └── dashboard.html
├── static/
│   ├── css/
│   │   ├── customer.css
│   │   └── admin.css
│   ├── js/
│   │   ├── customer.js
│   │   └── admin.js
│   └── images/
│       └── shop/
├── migrations/
└── tests/
```

This is a target example only. Preserve the project's current organization if it already separates templates, static assets, routes, and database logic appropriately.

# 15. Recommended Flask API endpoints

Use the existing route naming conventions where possible. These endpoints are a suggested API contract, not a requirement to duplicate existing routes.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/products` | List active products |
| `GET` | `/api/products/<id>` | Get product details |
| `POST` | `/api/orders` | Validate and place a COD order |
| `GET` | `/api/admin/analytics/summary?range=7d` | Return dashboard KPIs and chart data |
| `GET` | `/api/admin/orders` | List owner-visible orders |
| `PATCH` | `/api/admin/orders/<id>` | Perform validated order-status/payment-collection actions |
| `POST` | `/api/admin/products` | Create a product |
| `PATCH` | `/api/admin/products/<id>` | Update product details |
| `PATCH` | `/api/admin/inventory/<id>` | Adjust stock securely |

Every private `/api/admin/*` route must enforce authentication and authorization on the server. Frontend hiding or an obscure URL is not access control. Validate request bodies and return appropriate error responses.

# 16. Data model and business rules

Reuse the current MySQL schema and models where possible. The logical entities normally needed are:

- **Products:** name, brand, category, description, price, image path/URL, SKU, active state.
- **Inventory:** product ID, quantity available, low-stock threshold, updated timestamp.
- **Users/admins:** securely hashed credentials and role/authorization information.
- **Orders:** unique order reference, customer/contact/delivery details, order status, payment method, payment status, subtotal, delivery fee, total, timestamps.
- **Order items:** order ID, product ID, product-name and unit-price snapshot, quantity, line total.
- **Payment/collection records:** amount, method, collection time, and responsible owner/staff action where appropriate.

Required rules:
1. Calculate price, subtotal, flat delivery fee, and final total on the server using trusted database prices. Never trust browser-submitted totals.
2. Validate product IDs, quantities, product availability, and stock on the server.
3. Use a database transaction and suitable row locking or conditional stock updates to prevent concurrent orders from overselling stock.
4. Keep order status and payment status separate.
5. COD is not collected revenue until the owner records that the money was received.
6. Prevent duplicate orders from repeated checkout submissions where practical, using an idempotency key or another reliable duplicate-submission strategy.
7. Define and test cancellation rules, including when reserved stock is restored.
8. Never store plaintext passwords or expose database credentials, session secrets, or API secrets in frontend JavaScript or Git.
9. Use decimal-safe monetary types in the database and backend; avoid floating-point arithmetic for money.

# 17. Owner dashboard analytics definitions

The dashboard should show, where supported by real database records:

- Orders placed during the selected period.
- Collected sales, based on recorded payment collection.
- COD amount awaiting collection.
- Average order value, with its calculation clearly defined.
- Orders awaiting processing.
- Order counts by status.
- Top-selling products based on order-item quantities.
- Low-stock and out-of-stock products.

Chart requirements:
1. **Sales trend:** daily collected sales for the selected range, such as the last 7 days. If charting order totals instead, title it “Order Value,” not “Collected Sales.”
2. **Orders by status:** use actual status values from the current application.
3. **Top products:** aggregate real order-item records and define whether cancelled orders are excluded.
4. **Inventory health:** show available stock and low-stock thresholds.
5. **COD collection summary:** distinguish awaiting collection from collected amounts.

Use Chart.js with responsive layouts, readable labels, date ranges, legends, accessible colors, loading states, error states, and empty states. If there is no data, show an honest empty state such as “No sales recorded yet.” Sample/demo data must be visibly labelled and must not be mixed into actual business figures.

# 18. Security and reliability requirements

- Require secure owner authentication and authorization on every private page/API.
- Store password hashes using a suitable password-hashing method; never plaintext.
- Protect cookie-authenticated state-changing requests against CSRF.
- Validate and normalize user input on the server.
- Use parameterized database queries or the ORM safely; never concatenate untrusted input into SQL.
- Keep `.env` and secret files out of Git; provide a safe `.env.example` with placeholders.
- Configure session cookies securely in production and use HTTPS in deployment.
- Apply sensible login/order rate limits and safe error messages where appropriate.
- Avoid logging passwords, session tokens, or unnecessary customer personal information.
- Provide database backup and restore guidance before production use.
- Test transaction failures, invalid quantities, duplicate submissions, unauthorized admin requests, and stock conflicts.

# 19. Implementation sequence

1. **Inspect and back up:** review the current repository, routes, templates, JavaScript, database schema, dependencies, and existing COD flow. Create a Git commit or backup before changes.
2. **Preserve the customer experience:** improve the existing storefront, real shop photos, responsive layout, catalogue, cart, and checkout without breaking working features.
3. **Secure the owner portal:** verify login/session handling and protect every admin API.
4. **Connect analytics:** add or adapt a Flask endpoint that aggregates actual MySQL records, then render those results with Chart.js.
5. **Verify shared data:** place a test COD order as a customer and confirm it appears in the owner dashboard with the correct totals and inventory state.
6. **Test and document:** check mobile responsiveness, empty states, order validation, duplicate submission behavior, permissions, and server/browser errors. Document setup, routes, test results, and remaining limitations.

# 20. Exact instruction for Antigravity

Read this requirements file completely. Inspect my existing Mobile World Sales & Service repository before changing anything.

The confirmed stack is HTML5, CSS3, vanilla JavaScript, Python + Flask, and MySQL. Use Chart.js for the owner dashboard graphs. Preserve the existing database integration and working features. Use Flask-SQLAlchemy, Flask-Login, Flask-Migrate, or CSRF-related packages only when appropriate for the current project and compatible with its existing code.

Implement two distinct page experiences:
1. Public customer storefront at `/`.
2. Secure shop-owner dashboard at `/admin/`.

Connect both pages to the same Flask application and MySQL data. Preserve the working customer storefront, admin dashboard, and Cash on Delivery checkout. Use the actual Mobile World shop photos already supplied in the project.

Implement or improve product browsing, search, cart, checkout, server-side order-total and stock validation, owner order management, product/inventory management, and responsive Chart.js analytics. Dashboard analytics must use actual database records; clearly label any sample data. Keep order status separate from payment status, and do not count COD as collected revenue until collection is recorded.

Protect every admin API on the server, keep secrets out of Git, and preserve the existing database schema wherever possible. Do not rebuild the whole project or add unnecessary frameworks. Inspect dependencies before changing versions.

Before finishing, test one complete COD order from customer checkout through to the owner dashboard. Verify order totals, stock behavior, authentication/authorization, mobile responsiveness, and browser/server errors. Update the README with setup instructions, environment variables, both page URLs, tests run, implemented features, and remaining limitations.

At the end, report the files changed, the tests and results, what works, and what remains unfinished. Do not claim online payments or unfinished security features are complete.

# 21. Updated definition of done

The demo is ready when:
- The customer storefront and owner dashboard are distinct and accessible at documented URLs.
- A customer can successfully place a COD order.
- The owner can sign in and see/manage that same order.
- Product prices, delivery fee, order totals, and stock are validated by the backend.
- Charts use real data or are clearly marked as sample data.
- Private admin APIs reject unauthenticated and unauthorized access.
- The site works on desktop and mobile with no known critical console/server errors.
- Setup steps, test results, and known limitations are documented.
