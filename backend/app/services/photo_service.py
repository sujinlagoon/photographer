import os

from sqlalchemy.orm import Session

from backend.app.models.photo import (
    Photo
)


class PhotoService:

    @staticmethod
    def save_photo(
        db: Session,
        event_id: int,
        file_path: str,
        image_url: str
    ):

        file_name = (
            os.path.basename(
                file_path
            )
        )

        photo = Photo(
            event_id=event_id,
            file_name=file_name,
            image_url=image_url
        )

        db.add(photo)
        db.commit()
        db.refresh(photo)

        return photo