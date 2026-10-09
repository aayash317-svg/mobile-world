from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from models import db
from models.order import Order, OrderItem, PaymentRecord, Inventory, OrderStatusHistory, ALLOWED_ORDER_STATUSES
from models.product import Product
from services.inventory_service import InventoryService
from services.activity_service import ActivityService

class OrderService:

    @staticmethod
    def create_order(
        customer_name: str,
        customer_phone: str,
        delivery_address: str,
        items_payload: list,
        order_notes: str = None,
        customer_email: str = None,
        idempotency_key: str = None,
        customer_id: int = None
    ) -> Order:
        """
        Creates a new COD order with server-side calculation and concurrency-safe stock deduction.
        """
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name is required.")
        if not customer_phone or len(customer_phone.strip()) < 7:
            raise ValueError("A valid phone number is required.")
        if not delivery_address or not delivery_address.strip():
            raise ValueError("Delivery address is required.")
        if not items_payload or len(items_payload) == 0:
            raise ValueError("Order must contain at least one item.")

        if idempotency_key:
            existing = Order.query.filter_by(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        flat_delivery_fee = current_app.config.get("FLAT_DELIVERY_FEE", Decimal("50.00"))
        calculated_subtotal = Decimal("0.00")
        order_items_to_create = []

        try:
            for item_req in items_payload:
                product_id = item_req.get("product_id")
                qty = item_req.get("quantity")

                if not product_id or not qty or int(qty) <= 0:
                    raise ValueError("Invalid item format or quantity.")
                
                qty = int(qty)
                product = Product.query.filter_by(id=product_id, is_active=True).first()
                if not product:
                    raise ValueError(f"Product ID {product_id} is unavailable.")

                # Deduct stock atomically
                InventoryService.deduct_stock_atomic(product.id, qty)

                unit_price = Decimal(str(product.price))
                line_total = unit_price * qty
                calculated_subtotal += line_total

                order_item = OrderItem(
                    product_id=product.id,
                    product_name_snapshot=product.name,
                    unit_price_snapshot=unit_price,
                    quantity=qty,
                    line_total=line_total
                )
                order_items_to_create.append(order_item)

            final_total = calculated_subtotal + flat_delivery_fee

            new_order = Order(
                order_reference=Order.generate_reference(),
                idempotency_key=idempotency_key,
                customer_id=customer_id,
                customer_name=customer_name.strip(),
                customer_phone=customer_phone.strip(),
                customer_email=customer_email.strip() if customer_email else None,
                delivery_address=delivery_address.strip(),
                order_notes=order_notes.strip() if order_notes else None,
                order_status="Pending",
                payment_status="Pending COD",
                payment_method="COD",
                subtotal=calculated_subtotal,
                delivery_fee=flat_delivery_fee,
                total_amount=final_total,
                items=order_items_to_create
            )

            # Record initial status history
            initial_history = OrderStatusHistory(
                previous_status=None,
                new_status="Pending",
                changed_by="Customer Checkout",
                notes="Order placed via Cash on Delivery"
            )
            new_order.history.append(initial_history)

            db.session.add(new_order)
            db.session.commit()

            ActivityService.log(
                action="ORDER_CREATED",
                entity_type="Order",
                entity_id=new_order.id,
                details=f"Ref: {new_order.order_reference}, Total: ₹{final_total}, Items: {len(order_items_to_create)}",
                username="Customer"
            )

            # Customer in-app notification & activity log
            if customer_id:
                from services.customer_service import CustomerService
                CustomerService.create_notification(
                    customer_id=customer_id,
                    type="order",
                    title="Order Placed Successfully",
                    message=f"Your COD order #{new_order.order_reference} for ₹{final_total:,.2f} has been received and is pending confirmation.",
                    link_url=f"/account/orders"
                )
                CustomerService.log_activity(
                    customer_id=customer_id,
                    event_type="ORDER_PLACED",
                    title=f"Placed Order #{new_order.order_reference}",
                    description=f"{len(order_items_to_create)} item(s) • Total ₹{final_total:,.2f} via Cash on Delivery",
                    entity_type="Order",
                    entity_id=str(new_order.id)
                )

            return new_order

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_order_status(order_id: int, new_status: str, changed_by: str = "Shop Owner", notes: str = None) -> Order:
        if new_status not in ALLOWED_ORDER_STATUSES:
            raise ValueError(f"Invalid order status '{new_status}'. Allowed: {ALLOWED_ORDER_STATUSES}")

        order = Order.query.get(order_id)
        if not order:
            raise ValueError("Order not found.")

        old_status = order.order_status
        if old_status == new_status:
            return order

        # Stock restoration logic on cancellation or return
        if new_status in ["Cancelled", "Returned"] and old_status not in ["Cancelled", "Returned"]:
            for item in order.items:
                if item.product_id:
                    InventoryService.restore_stock_atomic(item.product_id, item.quantity)
        
        # If un-cancelling or un-returning, deduct back
        if old_status in ["Cancelled", "Returned"] and new_status not in ["Cancelled", "Returned"]:
            for item in order.items:
                if item.product_id:
                    InventoryService.deduct_stock_atomic(item.product_id, item.quantity)

        order.order_status = new_status
        
        # Add to history
        history_entry = OrderStatusHistory(
            order_id=order.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes or f"Status transitioned from {old_status} to {new_status}"
        )
        db.session.add(history_entry)
        db.session.commit()

        ActivityService.log(
            action="ORDER_STATUS_CHANGED",
            entity_type="Order",
            entity_id=order.id,
            details=f"Order {order.order_reference}: {old_status} -> {new_status}",
            username=changed_by
        )

        # Notify Customer in real-time
        if order.customer_id:
            from services.customer_service import CustomerService
            CustomerService.create_notification(
                customer_id=order.customer_id,
                type="order",
                title=f"Order Update: {new_status}",
                message=f"Order #{order.order_reference} status has been updated to '{new_status}'.",
                link_url="/account/orders"
            )
            CustomerService.log_activity(
                customer_id=order.customer_id,
                event_type="ORDER_UPDATED",
                title=f"Order #{order.order_reference} -> {new_status}",
                description=f"Status changed from {old_status} to {new_status}",
                entity_type="Order",
                entity_id=str(order.id)
            )

        return order

    @staticmethod
    def record_cod_payment(order_id: int, amount: Decimal = None, recorded_by: str = "Shop Owner", notes: str = None) -> PaymentRecord:
        order = Order.query.get(order_id)
        if not order:
            raise ValueError("Order not found.")

        if amount is None:
            amount = order.total_amount

        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Collection amount must be positive.")

        payment_rec = PaymentRecord(
            order_id=order.id,
            amount=amount,
            payment_method="Cash on Delivery",
            recorded_by=recorded_by,
            notes=notes or "Payment collected on physical delivery"
        )

        order.payment_status = "Collected"
        if order.order_status in ["Pending", "Confirmed", "Packed", "Shipped"]:
            order.order_status = "Delivered"

        history_entry = OrderStatusHistory(
            order_id=order.id,
            previous_status=order.order_status,
            new_status="Delivered",
            changed_by=recorded_by,
            notes="Payment recorded as Collected; order marked Delivered"
        )
        db.session.add(history_entry)
        db.session.add(payment_rec)
        db.session.commit()

        ActivityService.log(
            action="COD_PAYMENT_COLLECTED",
            entity_type="Payment",
            entity_id=order.id,
            details=f"Collected ₹{amount} for order {order.order_reference}",
            username=recorded_by
        )

        return payment_rec

    @staticmethod
    def get_analytics_summary(days: int = 7) -> dict:
        start_date = datetime.utcnow() - timedelta(days=days)

        period_orders = Order.query.filter(Order.created_at >= start_date).all()
        active_orders = [o for o in period_orders if o.order_status not in ["Cancelled", "Returned"]]
        total_orders_count = len(period_orders)

        # 1. Total order value (sum of total_amount for non-cancelled/non-returned)
        total_order_value = sum((o.total_amount for o in active_orders), Decimal("0.00"))

        # 2. Delivered COD orders value
        delivered_orders = [o for o in period_orders if o.order_status == "Delivered"]
        delivered_cod_value = sum((o.total_amount for o in delivered_orders), Decimal("0.00"))

        # 3. Actually collected revenue (PaymentRecords in period)
        collected_payments = PaymentRecord.query.filter(PaymentRecord.collected_at >= start_date).all()
        collected_sales = sum((p.amount for p in collected_payments), Decimal("0.00"))

        # 4. COD amount awaiting collection (Active orders with 'Pending COD')
        awaiting_orders = Order.query.filter(
            Order.payment_status == "Pending COD",
            ~Order.order_status.in_(["Cancelled", "Returned"])
        ).all()
        cod_awaiting = sum((o.total_amount for o in awaiting_orders), Decimal("0.00"))

        # 5. Orders pending processing (Pending, Confirmed, Packed)
        orders_pending_count = Order.query.filter(
            Order.order_status.in_(["Pending", "Confirmed", "Packed"])
        ).count()

        delivered_count = len(delivered_orders)

        # 6. Average order value for active orders
        aov = (total_order_value / len(active_orders)) if active_orders else Decimal("0.00")

        # 7. Low stock items
        all_inventory = Inventory.query.join(Product).filter(Product.is_active == True).all()
        low_stock_products = [
            inv.product.to_dict()
            for inv in all_inventory
            if inv.quantity <= inv.low_stock_threshold
        ]

        # 8. Order status counts
        status_counts = {s: 0 for s in ALLOWED_ORDER_STATUSES}
        for o in period_orders:
            status_counts[o.order_status] = status_counts.get(o.order_status, 0) + 1

        # 9. Daily collected sales & order value trend (last N days)
        daily_trends = []
        for d in range(days - 1, -1, -1):
            day_dt = (datetime.utcnow() - timedelta(days=d)).date()
            day_str = day_dt.strftime("%d %b")

            day_payments = [p for p in collected_payments if p.collected_at.date() == day_dt]
            day_collected = sum((p.amount for p in day_payments), Decimal("0.00"))

            day_placed_orders = [o for o in active_orders if o.created_at.date() == day_dt]
            day_order_val = sum((o.total_amount for o in day_placed_orders), Decimal("0.00"))

            daily_trends.append({
                "date": day_str,
                "collected": float(day_collected),
                "order_value": float(day_order_val)
            })

        # 10. Top selling products
        product_sales = {}
        for o in active_orders:
            for item in o.items:
                p_name = item.product_name_snapshot
                product_sales[p_name] = product_sales.get(p_name, 0) + item.quantity

        top_products = sorted(
            [{"name": k, "units_sold": v} for k, v in product_sales.items()],
            key=lambda x: x["units_sold"],
            reverse=True
        )[:5]

        return {
            "range": f"{days}d",
            "totalOrders": total_orders_count,
            "activeOrders": len(active_orders),
            "pendingOrders": orders_pending_count,
            "deliveredOrders": delivered_count,
            "orderValue": float(total_order_value),
            "orderValueFormatted": f"₹{total_order_value:,.2f}",
            "deliveredCodValue": float(delivered_cod_value),
            "deliveredCodValueFormatted": f"₹{delivered_cod_value:,.2f}",
            "collectedSales": float(collected_sales),
            "collectedSalesFormatted": f"₹{collected_sales:,.2f}",
            "codAwaitingCollection": float(cod_awaiting),
            "codAwaitingCollectionFormatted": f"₹{cod_awaiting:,.2f}",
            "averageOrderValue": float(aov),
            "averageOrderValueFormatted": f"₹{aov:,.2f}",
            "lowStockCount": len(low_stock_products),
            "lowStockProducts": low_stock_products,
            "ordersByStatus": status_counts,
            "dailyTrends": daily_trends,
            "topProducts": top_products,
            "isSampleData": False
        }
