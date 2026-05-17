from pydantic import BaseModel


class EventCreate(BaseModel):
    client_name: str
    event_name: str
    folder_path: str