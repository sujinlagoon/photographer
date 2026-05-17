import os
import time

from watchdog.observers import (
    Observer
)

from watchdog.events import (
    FileSystemEventHandler
)

from backend.app.services.upload_service import (
    CloudflareR2Uploader
)

from backend.app.core.database import (
    SessionLocal
)

from backend.app.services.photo_service import (
    PhotoService
)

from backend.app.models.event import (
    Event
)
import requests
from backend.app.core.config import settings


class PhotoHandler(FileSystemEventHandler):
    def __init__(self):
        self.uploader = CloudflareR2Uploader()
        self.processed_files = set()

    def on_moved(self, event):
        if not event.is_directory:
            self.process_photo(event.dest_path)

    def on_created(self, event):
        if not event.is_directory:
            self.process_photo(event.src_path)

    def process_photo(self, file_path):
        file_path = os.path.normpath(file_path)
        
        # Filter by extensions
        allowed = (".jpg", ".jpeg", ".png", ".webp")
        if not file_path.lower().endswith(allowed):
            return

        # Prevent duplicate triggers
        if file_path in self.processed_files:
            return
        
        # Wait a bit longer for Utility files (they take time to write)
        time.sleep(1.5)
        
        if not os.path.exists(file_path):
            return

        print(f"[WATCH] Processing: {file_path}")

        
        db = SessionLocal()
        try:
            folder_path = os.path.dirname(file_path)
            events = db.query(Event).all()
            matched_event = None
            for e in events:
                if e.folder_path and os.path.normpath(e.folder_path) == folder_path:
                    matched_event = e
                    break
            
            if not matched_event:
                # If no exact match, check if it's in a subfolder of an event
                for e in events:
                    if e.folder_path and folder_path.startswith(os.path.normpath(e.folder_path)):
                        matched_event = e
                        break

            if matched_event:
                print(f"[MATCH] Event: {matched_event.client_name}")

                uploaded_url = self.uploader.upload_file(file_path)
                photo = PhotoService.save_photo(db=db, event_id=matched_event.id, file_path=file_path, image_url=uploaded_url)
                self.processed_files.add(file_path)
                print(f"[SUCCESS] Sync Complete: {uploaded_url}")

                # --- NEW: Trigger AI Face Processing Locally ---
                try:
                    from backend.app.services.ai_service import FaceAIService
                    print(f"[AI] Extracting face embeddings for photo {photo.id}...")
                    FaceAIService().process_photo(photo.id, matched_event.id, file_path)
                except Exception as ai_err:
                    print(f"[AI ERROR] Local AI Processing Failed: {ai_err}")

                # --- CLOUD NOTIFICATION ---
                if settings.CLOUD_API_URL and "YOUR_USERNAME" not in settings.CLOUD_API_URL:
                    try:
                        print(f"[CLOUD] Notifying cloud server: {settings.CLOUD_API_URL}")

                        payload = {
                            "event_id": matched_event.id,
                            "file_name": os.path.basename(file_path),
                            "image_url": uploaded_url
                        }
                        # Using a short timeout to prevent blocking the watcher
                        requests.post(f"{settings.CLOUD_API_URL}/api/v1/sync/photo", json=payload, timeout=5)
                    except Exception as cloud_err:
                        print(f"[ERROR] Cloud Notification Failed: {cloud_err}")

                # --------------------------

            else:
                print(f"[ERROR] No event for: {folder_path}")


        except Exception as e:
            print(f"[ERROR] Sync Failed: {e}")

        finally:
            db.close()


class FolderWatcher:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FolderWatcher, cls).__new__(cls)
            cls._instance.observer = Observer()
            cls._instance.handler = PhotoHandler()
            cls._instance.watched_paths = set()
        return cls._instance

    def __init__(self, root_path=None):
        pass

    def start(self):
        db = SessionLocal()
        events = db.query(Event).all()
        
        if not events:
            print("[INFO] No events found in DB to watch.")

        
        for event in events:
            if event.folder_path:
                self.add_watch(event.folder_path)
        db.close()

        if not self.observer.is_alive():
            self.observer.start()
            print("[START] Photo Watcher is now active and listening...")


    def add_watch(self, path):
        normalized_path = os.path.normpath(path)
        if normalized_path and os.path.exists(normalized_path) and normalized_path not in self.watched_paths:
            try:
                self.observer.schedule(self.handler, normalized_path, recursive=True)
                self.watched_paths.add(normalized_path)
                print(f"[INFO] Now watching folder (recursive): {normalized_path}")

            except Exception as e:

                print(f"[ERROR] Failed to watch {normalized_path}: {e}")


    def stop(self):
        self.observer.stop()
        self.observer.join()