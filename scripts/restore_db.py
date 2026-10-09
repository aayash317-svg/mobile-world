import os
import sys
import subprocess
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def run_restore(backup_file=None, target_db="mobile_world_test_restore_db", user=None, password=None):
    db_user = user or os.environ.get("DB_USER", "mobile_user")
    db_pass = password or os.environ.get("DB_PASSWORD", "MobileWorld@2026")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")
    live_db = os.environ.get("DB_NAME", "mobile_world_db")

    if target_db == live_db and "--force-production" not in sys.argv:
        print("[!] SAFETY SHIELD: Refusing to overwrite production database without --force-production.")
        return False

    mysql_candidates = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "mysql"
    ]
    mysql_bin = None
    for cand in mysql_candidates:
        if os.path.exists(cand) or cand == "mysql":
            mysql_bin = cand
            break

    if not mysql_bin:
        print("[!] mysql utility not found.")
        return False

    # Find backup file
    if not backup_file:
        backups = sorted(
            [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")],
            key=os.path.getmtime
        )
        if not backups:
            print("[!] No backup SQL files found in backups/")
            return False
        backup_file = backups[-1]

    print(f"[*] Restoring from: {backup_file}")
    print(f"[*] Target database: {target_db}")

    try:
        # 1. Create target database if it doesn't exist
        create_db_cmd = [
            mysql_bin,
            f"-u{db_user}",
            f"-p{db_pass}",
            f"-h{db_host}",
            f"-P{db_port}",
            "-e",
            f"CREATE DATABASE IF NOT EXISTS `{target_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        ]
        res1 = subprocess.run(create_db_cmd, capture_output=True, text=True)
        if res1.returncode != 0:
            print(f"[!] Could not create target database: {res1.stderr}")
            return False

        # 2. Restore the SQL backup into target database
        with open(backup_file, "r", encoding="utf-8") as sql_in:
            restore_cmd = [
                mysql_bin,
                f"-u{db_user}",
                f"-p{db_pass}",
                f"-h{db_host}",
                f"-P{db_port}",
                target_db
            ]
            res2 = subprocess.run(restore_cmd, stdin=sql_in, capture_output=True, text=True)
            if res2.returncode != 0:
                print(f"[!] Restore failed: {res2.stderr}")
                return False

        # 3. Verify restored tables and count
        verify_cmd = [
            mysql_bin,
            f"-u{db_user}",
            f"-p{db_pass}",
            f"-h{db_host}",
            f"-P{db_port}",
            "-e",
            f"SELECT 'products' as tbl, count(*) as cnt FROM `{target_db}`.products UNION ALL SELECT 'users', count(*) FROM `{target_db}`.users UNION ALL SELECT 'inventory', count(*) FROM `{target_db}`.inventory;"
        ]
        res3 = subprocess.run(verify_cmd, capture_output=True, text=True)
        print("[+] Restore verified successfully! Table contents in test database:")
        print(res3.stdout)
        return True

    except Exception as e:
        print(f"[!] Restore encountered exception: {e}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "mobile_world_test_restore_db"
    ok = run_restore(target_db=target)
    sys.exit(0 if ok else 1)
