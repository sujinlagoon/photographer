from sqlalchemy.orm import (
    Session
)

from backend.app.models.event import (
    Event
)


class EventService:

    @staticmethod
    def get_event_by_folder(
        db: Session,
        folder_path: str
    ):

        return db.query(Event).filter(
            Event.folder_path
            == folder_path
        ).first()