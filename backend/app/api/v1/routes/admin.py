from flask import Blueprint, render_template, request, redirect, url_for, session
from backend.app.core.database import SessionLocal
from backend.app.models.event import Event
from backend.app.models.user import User
from backend.app.services.qr_service import QRService
from backend.app.services.sync_service import FolderWatcher
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import joinedload
from backend.app.services.upload_service import CloudflareR2Uploader
import os



admin_bp = Blueprint('admin', __name__)

def is_authenticated():
    return "user_id" in session

def get_current_user():
    if not is_authenticated():
        return None
    db = SessionLocal()
    user = db.query(User).filter(User.id == session["user_id"]).first()
    db.close()
    return user

@admin_bp.route("/admin/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = SessionLocal()
        user = db.query(User).filter(User.username == username).first()
        
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            db.close()
            return redirect(url_for('admin.event_list'))
        
        db.close()
        return render_template("admin_login.html", error="Invalid username or password")
    
    return render_template("admin_login.html")

@admin_bp.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for('admin.login'))

@admin_bp.route("/admin/events")
def event_list():
    if not is_authenticated():
        return redirect(url_for('admin.login'))
    
    db = SessionLocal()
    if session["role"] == "admin":
        events = db.query(Event).options(joinedload(Event.owner)).all()
    else:
        events = db.query(Event).filter(Event.owner_id == session["user_id"]).options(joinedload(Event.owner)).all()

    
    db.close()
    return render_template("admin_events.html", events=events, user_role=session["role"])

@admin_bp.route("/admin/events/create", methods=['GET', 'POST'])
def create_event():
    if not is_authenticated():
        return redirect(url_for('admin.login'))
    
    # Only admins can create events for now (or maybe clients too, but let's stick to admin)
    if session["role"] != "admin":
        return "Unauthorized", 403
    
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        event_name = request.form.get('event_name')
        transfer_method = request.form.get('transfer_method', 'wired')
        folder_path = request.form.get('folder_path')
        wifi_password = request.form.get('wifi_password')
        
        # New: Client Credentials
        client_username = request.form.get('client_username')
        client_password = request.form.get('client_password')
        
        # New: Logo Upload
        logo_url = None
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename != '':
            logo_url = CloudflareR2Uploader().upload_fileobj(logo_file, logo_file.filename)

        db = SessionLocal()

        
        # 1. Create Client User if provided
        owner_id = None
        if client_username and client_password:
            # Check if user exists
            existing_user = db.query(User).filter(User.username == client_username).first()
            if not existing_user:
                new_user = User(
                    username=client_username,
                    password=generate_password_hash(client_password),
                    role="client"
                )
                db.add(new_user)
                db.flush() # Get ID
                owner_id = new_user.id
            else:
                owner_id = existing_user.id

        # 2. Create Event
        face_scan_enabled = request.form.get('face_scan_enabled') == 'on'
        
        new_event = Event(
            client_name=client_name,
            event_name=event_name,
            transfer_method=transfer_method,
            folder_path=folder_path if transfer_method == "wired" else None,
            wifi_password=wifi_password if transfer_method == "wifi" else None,
            owner_id=owner_id,
            logo_url=logo_url,
            face_scan_enabled=face_scan_enabled
        )

        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        # Generate QR
        QRService.generate_qr(new_event.id)

        # Local logic
        if os.getenv("RUN_WATCHER", "true") == "true":
            if transfer_method == "wired" and folder_path:
                FolderWatcher().add_watch(new_event.folder_path)
        
        db.close()
        return redirect(url_for('admin.event_list'))

    return render_template("admin_create_event.html")

@admin_bp.route("/admin/events/delete/<int:event_id>", methods=['POST'])
def delete_event(event_id):
    if not is_authenticated():
        return redirect(url_for('admin.login'))
    
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        
        # Security check: Only admin or owner can delete
        if not event or (session["role"] != "admin" and event.owner_id != session["user_id"]):
            return "Unauthorized", 403

        if event:
            qr_path = f"backend/app/static/qr/event_{event_id}.png"
            if os.path.exists(qr_path):
                os.remove(qr_path)
            
            from backend.app.models.photo import Photo
            db.query(Photo).filter(Photo.event_id == event_id).delete()
            
            db.delete(event)
            db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()
    
    return redirect(url_for('admin.event_list'))

@admin_bp.route("/admin/events/edit/<int:event_id>", methods=['GET', 'POST'])
def edit_event(event_id):
    if not is_authenticated():
        return redirect(url_for('admin.login'))
    
    if session["role"] != "admin":
        return "Unauthorized", 403
    
    db = SessionLocal()
    event = db.query(Event).options(joinedload(Event.owner)).filter(Event.id == event_id).first()

    
    if not event:
        db.close()
        return "Event not found", 404

    if request.method == 'POST':
        event.client_name = request.form.get('client_name')
        event.event_name = request.form.get('event_name')
        event.folder_path = request.form.get('folder_path')
        event.face_scan_enabled = 'face_scan_enabled' in request.form
        
        # Update Logo
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename != '':
            event.logo_url = CloudflareR2Uploader().upload_fileobj(logo_file, logo_file.filename)

        # Update User Credentials if they exist

        if event.owner:
            client_username = request.form.get('client_username')
            client_password = request.form.get('client_password')
            
            if client_username:
                event.owner.username = client_username
            if client_password:
                event.owner.password = generate_password_hash(client_password)
        
        db.commit()
        db.close()
        return redirect(url_for('admin.event_list'))

    db.close()
    return render_template("admin_edit_event.html", event=event)


@admin_bp.route("/admin/api/browse")
def browse_directories():
    if not is_authenticated():
        return {"error": "Unauthorized"}, 401
    
    path = request.args.get('path', 'DRIVES')
    
    if path == "DRIVES" or not path:
        import string
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:/"
            if os.path.exists(drive):
                drives.append({
                    "name": f"Local Disk ({letter}:)",
                    "path": drive,
                    "is_dir": True,
                    "is_drive": True
                })
        return {
            "current_path": "DRIVES",
            "parent_path": None,
            "folders": drives
        }

    try:
        path = os.path.abspath(path).replace("\\", "/")
        if not path.endswith("/"):
            path += "/"
        
        parent = os.path.dirname(path.rstrip("/"))
        if parent == path.rstrip("/") or len(path) <= 3:
            parent = "DRIVES"

        items = []
        for entry in os.scandir(path):
            try:
                if entry.is_dir():
                    items.append({
                        "name": entry.name,
                        "path": entry.path.replace("\\", "/"),
                        "is_dir": True
                    })
            except (PermissionError, OSError):
                continue
        
        items.sort(key=lambda x: x['name'].lower())
        
        return {
            "current_path": path,
            "parent_path": parent,
            "folders": items
        }
    except Exception as e:
        return {"error": str(e)}, 500
