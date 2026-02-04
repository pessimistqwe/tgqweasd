import os
from models import SessionLocal, Event, User
from sqlalchemy.orm import Session

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS

def get_pending_events(db: Session):
    return db.query(Event).filter(
        Event.is_moderated == False
    ).order_by(Event.created_at.desc()).all()

def approve_event(event_id: int, db: Session):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError("Событие не найдено")
    event.is_moderated = True
    db.commit()
    return event

def reject_event(event_id: int, db: Session):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError("Событие не найдено")
    db.delete(event)
    db.commit()
    return True