from flask import Blueprint, jsonify
from backend.app.services.qr_service import QRService

qr_bp = Blueprint('qr', __name__)

@qr_bp.route("/generate-qr/<int:event_id>")
def generate_qr(event_id):
    qr_path = QRService.generate_qr(event_id)
    return jsonify({
        "message": "QR generated",
        "qr_image": qr_path
    })