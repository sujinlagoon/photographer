import sys
import os
import threading

# Add the current directory to the path so it can find 'backend'
sys.path.append(os.getcwd())

from flask import Flask, render_template, jsonify, request
from backend.app.core.config import settings
from backend.app.core.init_db import init_db

# Create the Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = "supersecretkey" # In production, use os.getenv("SECRET_KEY")


# Initialize DB on startup
with app.app_context():
    init_db()

# Import and register Blueprints
from backend.app.api.v1.routes.admin import admin_bp
from backend.app.api.v1.routes.gallery import gallery_bp
from backend.app.api.v1.routes.qr import qr_bp
from backend.app.api.v1.routes.sync import sync_bp

app.register_blueprint(admin_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(qr_bp)
app.register_blueprint(sync_bp)

@app.route("/")
def home():
    return jsonify({"message": f"{settings.APP_NAME} Running"})

if __name__ == "__main__":
    app.debug = True
    # In Flask Debug mode, the reloader starts the app twice. 
    # We only want to start background services once.
    if not settings.IS_PYTHONANYWHERE:
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:

            
            # 1. Start Wi-Fi FTP Service
            from backend.app.services.wifi_service import launch_wifi_service
            launch_wifi_service()

            # 2. Start Folder Watcher
            from backend.app.workers.folder_watcher import start_folder_watcher
            watcher_thread = threading.Thread(
                target=start_folder_watcher,
                daemon=True
            )
            watcher_thread.start()
            # 3. Regenerate QR codes to ensure they use the new HTTPS URL
            try:
                from backend.app.core.database import SessionLocal
                from backend.app.models.event import Event
                from backend.app.services.qr_service import QRService
                db = SessionLocal()
                events = db.query(Event).all()
                for event in events:
                    QRService.generate_qr(event.id)
                db.close()
                print("[SUCCESS] All event QR codes updated to HTTPS.")
            except Exception as qr_err:
                print(f"[ERROR] QR Regeneration failed: {qr_err}")

            print("[SUCCESS] Background services (FTP & Watcher) started successfully.")
            print(f"[INFO] SCAN READY! Use this URL on your phone: {settings.BASE_PUBLIC_URL}/admin/events")

    
    # Run the Flask app
    # use_reloader=True is fine now that we handle the WERKZEUG_RUN_MAIN check
    # ssl_context='adhoc' enables HTTPS locally (requires pip install pyOpenSSL)
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True, ssl_context='adhoc')
