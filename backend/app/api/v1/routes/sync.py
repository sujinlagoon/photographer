from flask import Blueprint, request, jsonify
from backend.app.core.database import SessionLocal
from backend.app.models.photo import Photo
from backend.app.services.ai_service import FaceAIService
import threading
import requests
import os
import tempfile


sync_bp = Blueprint('sync', __name__)

@sync_bp.route("/api/v1/sync/photo", methods=['POST'])
def sync_photo():
    """
    Endpoint for the local worker to report a new photo upload.
    This runs on PythonAnywhere (Flask).
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db = SessionLocal()
    try:
        new_photo = Photo(
            event_id=data.get('event_id'),
            file_name=data.get('file_name'),
            image_url=data.get('image_url')
        )
        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)
        
        # --- NEW: Trigger AI Face Processing in Background ---
        def run_ai_processing(photo_id, event_id, image_url):
            try:
                # Download image to temp file for InsightFace
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        tmp.write(response.content)
                        tmp_path = tmp.name
                        tmp.close()
                        
                        FaceAIService().process_photo(photo_id, event_id, tmp_path)
                        
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
            except Exception as ai_err:
                print(f"⚠️ AI Processing Background Error: {ai_err}")

        thread = threading.Thread(
            target=run_ai_processing,
            args=(new_photo.id, new_photo.event_id, new_photo.image_url),
            daemon=True
        )
        thread.start()
        # ----------------------------------------------------

        result = {"status": "success", "photo_id": new_photo.id}

        db.close()
        return jsonify(result)
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 500
