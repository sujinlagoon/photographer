import insightface
import numpy as np
import cv2
import os
from backend.app.core.database import SessionLocal
from backend.app.models.face import FaceEmbedding

class FaceAIService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceAIService, cls).__new__(cls)
            # buffalo_l is highly accurate for multiple faces/weddings
            cls._instance.app = insightface.app.FaceAnalysis(
                name='buffalo_l', 
                providers=['CPUExecutionProvider']
            )
            cls._instance.app.prepare(ctx_id=0, det_size=(640, 640))
        return cls._instance

    def process_photo(self, photo_id, event_id, image_path):
        """Detect faces and save embeddings to DB"""
        try:
            # Use imdecode to handle non-ASCII paths and avoid file locks
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"[AI ERROR] Could not decode image: {image_path}")
                return
                
            # Increased det_size for better accuracy on high-res photos
            faces = self.app.get(img)
            
            db = SessionLocal()
            try:
                count = 0
                for face in faces:
                    # ArcFace 512-dim embedding
                    embedding_bytes = face.normed_embedding.tobytes()
                    
                    new_face = FaceEmbedding(
                        photo_id=photo_id,
                        event_id=event_id,
                        embedding=embedding_bytes
                    )
                    db.add(new_face)
                    count += 1
                db.commit()
                if count > 0:
                    print(f"[AI] Successfully extracted {count} face(s) from photo {photo_id}")
            except Exception as e:
                print(f"[AI ERROR] DB Error during face save: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as outer_err:
            print(f"[AI ERROR] processing failed: {outer_err}")

    def search_face(self, event_id, selfie_path, threshold=0.42):
        """Find matching photos in an event using a selfie"""
        try:
            with open(selfie_path, 'rb') as f:
                img_bytes = f.read()
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
                
            faces = self.app.get(img)
            if not faces:
                print("[AI] No faces detected in the provided selfie.")
                return []
                
            # Use the most prominent face (largest bounding box area)
            best_face = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))
            selfie_vec = best_face.normed_embedding
            
            db = SessionLocal()
            try:
                # Get all embeddings for this event
                stored_faces = db.query(FaceEmbedding).filter(FaceEmbedding.event_id == event_id).all()
                if not stored_faces:
                    return []
                
                # Convert stored bytes back to float32 vectors
                event_vecs = []
                photo_ids = []
                for f in stored_faces:
                    vec = np.frombuffer(f.embedding, dtype=np.float32)
                    if vec.shape[0] == 512:
                        event_vecs.append(vec)
                        photo_ids.append(f.photo_id)
                
                if not event_vecs:
                    return []
                    
                event_vecs = np.array(event_vecs)
                
                # Cosine similarity (dot product since normed)
                similarities = np.dot(event_vecs, selfie_vec)
                
                # Filter matches and sort by similarity score (highest first)
                matches = np.where(similarities > threshold)[0]
                matched_data = sorted([(photo_ids[i], similarities[i]) for i in matches], key=lambda x: x[1], reverse=True)
                
                # Get unique photo IDs that matched, preserving highest similarity order
                matched_photo_ids = []
                seen = set()
                for pid, score in matched_data:
                    if pid not in seen:
                        matched_photo_ids.append(pid)
                        seen.add(pid)
                        
                print(f"[AI] Search complete. Found {len(matched_photo_ids)} matching photos.")
                return matched_photo_ids
                
            finally:
                db.close()
        except Exception as e:
            print(f"[AI ERROR] Search failed: {e}")
            return []
