from flask import request
from models import db
from models.activity_log import ActivityLog

class ActivityService:

    @staticmethod
    def log(action: str, entity_type: str = None, entity_id: str = None, details: str = None, user_id: int = None, username: str = None):
        try:
            ip = None
            if request:
                ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            
            log_entry = ActivityLog(
                user_id=user_id,
                username=username or "System",
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                details=details,
                ip_address=ip
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            # Avoid breaking business transactions if logging fails
            db.session.rollback()
            print(f"[ActivityLog Error] {e}")
            return None

    @staticmethod
    def get_recent_logs(limit: int = 50):
        return ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
