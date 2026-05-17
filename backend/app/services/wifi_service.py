import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import threading
from backend.app.core.config import settings
from backend.app.services.upload_service import CloudflareR2Uploader
from backend.app.services.photo_service import PhotoService
from backend.app.services.event_service import EventService
from backend.app.core.database import SessionLocal

class CameraFTPHandler(FTPHandler):
    def on_file_received(self, file_path):
        """Called when a photo is uploaded via Wi-Fi from the camera"""
        print(f"[WIFI] Photo Received: {file_path}")

        
        uploader = CloudflareR2Uploader()
        try:
            # 1. Upload to R2
            uploaded_url = uploader.upload_file(file_path)
            
            # 2. Identify the event based on the FTP user or subfolder
            # For simplicity, we'll assume the camera uploads to a folder named after the event ID
            db = SessionLocal()
            
            # Extract event ID from filename or path if possible, 
            # for now, let's look for an active Wi-Fi event
            # In a production app, we would use unique FTP accounts per event
            event = db.query(Event).filter(Event.transfer_method == "wifi").first()
            
            if event:
                PhotoService.save_photo(
                    db=db,
                    event_id=event.id,
                    file_path=file_path,
                    image_url=uploaded_url
                )
                print(f"[SUCCESS] Wi-Fi Photo saved to Event {event.id}")

            
            db.close()
            
        except Exception as e:
            print(f"[ERROR] Wi-Fi Upload Error: {e}")


def start_ftp_server():
    """Starts the FTP server on port 2121 for camera Wi-Fi transfers"""
    authorizer = DummyAuthorizer()
    
    # Create a storage directory for Wi-Fi uploads
    upload_dir = "storage/wifi_uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    # Add a generic user for cameras
    # Username: camera, Password: (from config or event)
    authorizer.add_user("camera", "photo123", upload_dir, perm="elradfmw")
    
    handler = CameraFTPHandler
    handler.authorizer = authorizer
    
    try:
        server = FTPServer(("0.0.0.0", 2121), handler)
        print("[START] Wi-Fi FTP Server running on port 2121...")
        server.serve_forever()
    except OSError as e:
        if e.errno == 10048:
            print("[INFO] Wi-Fi FTP Server already running (port 2121).")
        else:
            print(f"[ERROR] FTP Server failed: {e}")


def launch_wifi_service():
    thread = threading.Thread(target=start_ftp_server, daemon=True)
    thread.start()
