from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.event import Event
from backend.app.schemas.event_schema import EventCreate


from backend.app.services.qr_service import QRService

router = APIRouter()


@router.post("/events")
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db)
):
    new_event = Event(
        client_name=event.client_name,
        event_name=event.event_name,
        folder_path=event.folder_path
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Generate QR Code immediately
    qr_path = QRService.generate_qr(new_event.id)

    return {
        "message": "Event created",
        "event_id": new_event.id,
        "qr_image": qr_path
    }