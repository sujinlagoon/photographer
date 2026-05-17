from dotenv import load_dotenv
import os
import socket

load_dotenv()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class Settings:
    APP_NAME = os.getenv("APP_NAME", "Photo Cloud")
    
    # Check if running on PythonAnywhere
    IS_PYTHONANYWHERE = "PYTHONANYWHERE_DOMAIN" in os.environ

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///storage/photo.db"
    )

    WATCH_FOLDER = os.getenv(
        "WATCH_FOLDER",
        "D:/PhotoSync"
    )

    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
    R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
    R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")
    
    # Automatic URL switching
    if IS_PYTHONANYWHERE:
        BASE_PUBLIC_URL = "https://SUJINKUMAR.pythonanywhere.com"
        CLOUD_API_URL = None
    else:
        # Use Local IP so phones on the same Wi-Fi can connect
        local_ip = get_local_ip()
        # Changed to HTTPS to allow camera access on mobile
        BASE_PUBLIC_URL = f"https://{local_ip}:8000"
        CLOUD_API_URL = "https://SUJINKUMAR.pythonanywhere.com"


settings = Settings()