import firebase_admin
from firebase_admin import credentials, auth, db, messaging, storage
import os
import time
import base64

_firebase_app = None

def init_firebase():
    global _firebase_app
    if _firebase_app: return _firebase_app

    cred_path = "firebase-key.json"
    if not os.path.exists(cred_path):
        raise RuntimeError("Firebase credentials JSON missing")

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred, {
        "databaseURL": "https://wavebell-cd074-default-rtdb.asia-southeast1.firebasedatabase.app"
    })
    return _firebase_app

def verify_firebase_token(token):
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception as e:
        print("Invalid Firebase token:", e)
        return None

def log_event(event, data=None):
    try:
        ref = db.reference("/doorcam/logs")
        ref.push({"event": event, "data": data, "timestamp": time.time()})
    except Exception as e:
        print("Firebase log error:", e)

def send_fcm(tokens, title, body, data=None):
    try:
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
            data={k:str(v) for k,v in (data or {}).items()}
        )
        resp = messaging.send_multicast(msg)
        print("FCM sent:", resp.success_count)
    except Exception as e:
        print("Error sending FCM:", e)

def upload_audio_to_storage(audio_data, filename):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"audio_recordings/{filename}")
        blob.upload_from_string(audio_data, content_type='audio/wav')
        blob.make_public()
        
        audio_ref = db.reference('/doorcam/audio_recordings')
        audio_ref.push({
            'filename': filename,
            'url': blob.public_url,
            'timestamp': time.time(),
            'size': len(audio_data)
        })
        
        print(f"Audio uploaded: {filename}")
        return blob.public_url
    except Exception as e:
        print("Error uploading audio:", e)
        return None
