"""
Moderation module for admin functions
"""
import os

# ID админа из переменных окружения или hardcoded для теста
ADMIN_IDS = os.getenv("ADMIN_TELEGRAM_ID", "")

def is_admin(telegram_id: int) -> bool:
    """Проверить, является ли пользователь админом"""
    if not ADMIN_IDS:
        return False
    admin_list = [int(x.strip()) for x in str(ADMIN_IDS).split(",") if x.strip()]
    return telegram_id in admin_list

def approve_event(event_id: int, db):
    """Одобрить событие (модерация)"""
    from models import Event
    event = db.query(Event).filter(Event.id == event_id).first()
    if event:
        event.is_moderated = True
        event.is_active = True
        db.commit()
        return True
    return False

def reject_event(event_id: int, db):
    """Отклонить событие"""
    from models import Event
    event = db.query(Event).filter(Event.id == event_id).first()
    if event:
        event.is_active = False
        db.commit()
        return True
    return False
