from flask import Blueprint, render_template, jsonify, abort, request, session, redirect, url_for
from backend.app.services.ai_service import FaceAIService
import os
import tempfile
import time

from backend.app.core.database import SessionLocal
from backend.app.models.photo import Photo
from backend.app.models.event import Event

gallery_bp = Blueprint('gallery', __name__)

@gallery_bp.route("/gallery-view/<int:event_id>")
def gallery_view(event_id):
    db = SessionLocal()
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        db.close()
        abort(404, description="Event not found")
        
    # Check for secure session access
    is_secure_view = request.args.get('view') == 'secure'
    auth_key = f"auth_photos_{event_id}"
    expiry_key = f"auth_expiry_{event_id}"
    
    if is_secure_view:
        # Check if session exists and is not expired (30 minute limit)
        auth_ids = session.get(auth_key)
        expiry = session.get(expiry_key, 0)
        
        if auth_ids and time.time() < expiry:
            photos = db.query(Photo).filter(Photo.id.in_(auth_ids)).all()
            db.close()
            return render_template("gallery.html", photos=photos, event=event, is_search=True)
        else:
            # Session expired or missing - redirect to scan
            db.close()
            return render_template("search.html", event=event, error="Session expired. Please scan your face again.")

    # Normal view (show all photos)
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    db.close()
    return render_template("gallery.html", photos=photos, event=event)

@gallery_bp.route("/search/<int:event_id>", methods=['GET', 'POST'])
def search_view(event_id):
    db = SessionLocal()
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        db.close()
        abort(404, description="Event not found")

    # NEW: Logic for Scan Enable = OFF
    if not event.face_scan_enabled:
        db.close()
        return redirect(url_for('gallery.gallery_view', event_id=event_id))

    if request.method == 'POST':
        selfie = request.files.get('selfie')
        if selfie and selfie.filename != '':
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                selfie.save(tmp.name)
                tmp_path = tmp.name
            
            try:
                matched_ids = FaceAIService().search_face(event_id, tmp_path)
                if matched_ids:
                    # Secure the results in session
                    session[f"auth_photos_{event_id}"] = matched_ids
                    session[f"auth_expiry_{event_id}"] = time.time() + (30 * 60) # 30 mins
                    
                    unsorted_photos = db.query(Photo).filter(Photo.id.in_(matched_ids)).all()
                    photo_map = {p.id: p for p in unsorted_photos}
                    photos = [photo_map[pid] for pid in matched_ids if pid in photo_map]
                    db.close()
                    return render_template("gallery.html", photos=photos, event=event, is_search=True)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
    
    db.close()
    return render_template("search.html", event=event)

@gallery_bp.route("/api/v1/search-live/<int:event_id>", methods=['POST'])
def search_live(event_id):
    """Real-time search endpoint that secures results in session"""
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"error": "No image data"}), 400
    
    import base64
    try:
        header, encoded = data['image'].split(",", 1)
        image_data = base64.b64decode(encoded)
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name
        
        try:
            matched_ids = FaceAIService().search_face(event_id, tmp_path)
            if matched_ids:
                # Store in session so they can't be shared via URL
                session[f"auth_photos_{event_id}"] = matched_ids
                session[f"auth_expiry_{event_id}"] = time.time() + (30 * 60) # 30 mins
                
                return jsonify({
                    "success": True, 
                    "match_count": len(matched_ids),
                    "redirect_url": f"/gallery-view/{event_id}?view=secure"
                })
            return jsonify({"success": False, "message": "No match found"})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500