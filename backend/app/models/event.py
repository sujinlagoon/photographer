from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean
)

from sqlalchemy.orm import relationship


from datetime import datetime

from backend.app.core.database import (
    Base
)


class Event(Base):

    __tablename__ = "events"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    client_name = Column(
        String,
        nullable=False
    )

    event_name = Column(
        String,
        nullable=False
    )

    folder_path = Column(
        String,
        unique=True,
        nullable=True
    )

    transfer_method = Column(
        String,
        default="wired"  # "wired" or "wifi"
    )

    wifi_password = Column(
        String,
        nullable=True
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    owner = relationship("User")

    logo_url = Column(
        String,
        nullable=True
    )

    face_scan_enabled = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )