from decimal import Decimal
from models import db
from models.order import Inventory
from models.product import Product

class InventoryService:

    @staticmethod
    def get_stock(product_id: int) -> int:
        inv = Inventory.query.filter_by(product_id=product_id).first()
        return inv.quantity if inv else 0

    @staticmethod
    def adjust_stock(product_id: int, new_quantity: int, low_threshold: int = None):
        if new_quantity < 0:
            raise ValueError("Stock quantity cannot be negative")

        inv = Inventory.query.filter_by(product_id=product_id).with_for_update().first()
        if not inv:
            inv = Inventory(
                product_id=product_id,
                quantity=new_quantity,
                low_stock_threshold=low_threshold if low_threshold is not None else 5
            )
            db.session.add(inv)
        else:
            inv.quantity = new_quantity
            if low_threshold is not None:
                inv.low_stock_threshold = low_threshold

        db.session.commit()
        return inv

    @staticmethod
    def deduct_stock_atomic(product_id: int, quantity_to_deduct: int):
        """
        Deducts stock using row-level locking (with_for_update) inside an active transaction.
        Raises ValueError if stock is insufficient.
        """
        if quantity_to_deduct <= 0:
            raise ValueError("Deduction quantity must be positive")

        inv = Inventory.query.filter_by(product_id=product_id).with_for_update().first()
        if not inv:
            raise ValueError(f"Inventory record for product {product_id} not found")

        if inv.quantity < quantity_to_deduct:
            product = Product.query.get(product_id)
            p_name = product.name if product else f"ID {product_id}"
            raise ValueError(f"Insufficient stock for '{p_name}'. Available: {inv.quantity}, Requested: {quantity_to_deduct}")

        inv.quantity -= quantity_to_deduct
        return inv

    @staticmethod
    def restore_stock_atomic(product_id: int, quantity_to_restore: int):
        """
        Restores stock when an order is cancelled.
        """
        if quantity_to_restore <= 0:
            return

        inv = Inventory.query.filter_by(product_id=product_id).with_for_update().first()
        if inv:
            inv.quantity += quantity_to_restore
            return inv
