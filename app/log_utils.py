from app.models import db, SystemLog

def log_action(user, action, details=''):
    try:
        log = SystemLog(user_id=user.id, action=action, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass