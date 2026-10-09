import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

MAX_BACKUP_RETENTION = 7  # Keep latest 7 backups

def run_backup():
    db_user = os.environ.get("DB_USER", "mobile_user")
    db_pass = os.environ.get("DB_PASSWORD", "MobileWorld@2026")
    db_name = os.environ.get("DB_NAME", "mobile_world_db")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")

    mysqldump_candidates = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        "mysqldump"
    ]
    
    mysqldump_bin = None
    for cand in mysqldump_candidates:
        if os.path.exists(cand) or cand == "mysqldump":
            mysqldump_bin = cand
            break

    if not mysqldump_bin:
        print("[Error] mysqldump utility not found on system.")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"mobile_world_backup_{timestamp}.sql")

    cmd = [
        mysqldump_bin,
        f"-u{db_user}",
        f"-p{db_pass}",
        f"-h{db_host}",
        f"-P{db_port}",
        "--single-transaction",
        "--quick",
        "--routines",
        "--triggers",
        db_name
    ]

    print(f"[*] Starting backup of '{db_name}' to: {backup_file}")
    try:
        with open(backup_file, "w", encoding="utf-8") as out:
            res = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                print(f"[!] mysqldump failed with error: {res.stderr}")
                return False

        file_size_kb = os.path.getsize(backup_file) / 1024
        print(f"[+] Backup completed successfully! Size: {file_size_kb:.2f} KB")

        # Rotate old backups
        apply_retention_policy()
        return backup_file

    except Exception as e:
        print(f"[!] Backup failed with exception: {e}")
        return False

def apply_retention_policy():
    backups = sorted(
        [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")],
        key=os.path.getmtime
    )
    if len(backups) > MAX_BACKUP_RETENTION:
        to_delete = backups[:-MAX_BACKUP_RETENTION]
        for f in to_delete:
            try:
                os.remove(f)
                print(f"[*] Rotated old backup: {os.path.basename(f)}")
            except OSError as err:
                print(f"[!] Could not remove {f}: {err}")

if __name__ == "__main__":
    result = run_backup()
    sys.exit(0 if result else 1)
