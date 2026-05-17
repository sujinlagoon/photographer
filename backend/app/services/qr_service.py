import os
import qrcode
import socket
from backend.app.core.config import settings

class QRService:

    @staticmethod
    def get_local_ip():
        try:
            # This creates a dummy socket to find the primary interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def generate_qr(event_id: int):
        # Use the public URL (PythonAnywhere) for the QR code
        base_url = settings.BASE_PUBLIC_URL.rstrip("/")
        gallery_url = f"{base_url}/search/{event_id}"


        print(f"[INFO] Generating QR for mobile access: {gallery_url}")


        qr = qrcode.make(gallery_url)

        save_path = f"backend/app/static/qr/event_{event_id}.png"
        qr.save(save_path)

        return f"/static/qr/event_{event_id}.png"