from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey
from backend.app.core.database import Base

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"))
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    embedding = Column(LargeBinary, nullable=False) # Stores 512-dim float32 vector as bytes
