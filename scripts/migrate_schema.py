import os
import sys
from dotenv import load_dotenv
import pymysql

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def migrate():
    db_user = os.environ.get("DB_USER", "mobile_user")
    db_pass = os.environ.get("DB_PASSWORD", "MobileWorld@2026")
    db_name = os.environ.get("DB_NAME", "mobile_world_db")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = int(os.environ.get("DB_PORT", "3306"))

    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name,
        charset="utf8mb4"
    )

    with conn.cursor() as cursor:
        print("[*] Checking existing columns in products table...")
        cursor.execute("SHOW COLUMNS FROM products")
        existing_cols = [row[0] for row in cursor.fetchall()]

        new_product_cols = [
            ("mrp", "DECIMAL(10, 2) NULL AFTER price"),
            ("ram", "VARCHAR(50) NULL AFTER mrp"),
            ("storage", "VARCHAR(50) NULL AFTER ram"),
            ("color", "VARCHAR(50) NULL AFTER storage"),
            ("warranty_months", "INT NOT NULL DEFAULT 12 AFTER color")
        ]

        for col_name, col_def in new_product_cols:
            if col_name not in existing_cols:
                sql = f"ALTER TABLE products ADD COLUMN {col_name} {col_def};"
                cursor.execute(sql)
                print(f"    [+] Added products.{col_name}")

        print("[*] Checking existing columns in orders table...")
        cursor.execute("SHOW COLUMNS FROM orders")
        order_cols = [row[0] for row in cursor.fetchall()]

        if "customer_id" not in order_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN customer_id INT NULL AFTER id;")
            print("    [+] Added orders.customer_id")

    conn.commit()
    conn.close()
    print("[+] Migration completed successfully!")

if __name__ == "__main__":
    migrate()
