from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from datetime import datetime

from backend.app.core.database import Base


class Photo(Base):

    __tablename__ = "photos"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id")
    )

    file_name = Column(
        String,
        nullable=False
    )

    image_url = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )