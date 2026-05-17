from backend.app.core.database import (
    engine,
    Base
)

from backend.app.models.event import Event
from backend.app.models.photo import Photo
from backend.app.models.user import User
from backend.app.models.face import FaceEmbedding

from werkzeug.security import generate_password_hash
from backend.app.core.database import SessionLocal



def init_db():
    Base.metadata.create_all(
        bind=engine
    )

    # Create default admin if not exists
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "sujin").first()
    if not admin:
        admin = User(
            username="sujin",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
    db.close()