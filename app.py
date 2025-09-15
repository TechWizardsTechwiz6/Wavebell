import cv2, threading, time, os, base64, wave, io
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from sensors import Sensors
from face_recognizer import FaceRecognizer
from firebase_client import init_firebase, log_event, send_fcm, verify_firebase_token, upload_audio_to_storage
from twilio.rest import Client
import pyttsx3
import pyaudio
import numpy as np

TWILIO_SID = id
TWILIO_TOKEN = token
TWILIO_FROM = from
twilio_client = None
owner_phone_number = None

def load_phone_number():
    global owner_phone_number
    try:
        if os.path.exists('phone_config.txt'):
            with open('phone_config.txt', 'r') as f:
                owner_phone_number = f.read().strip()
                if owner_phone_number:
                    print(f"Loaded saved phone number: {owner_phone_number}")
    except Exception as e:
        print(f"Error loading phone number: {e}")

def save_phone_number(phone):
    try:
        with open('phone_config.txt', 'w') as f:
            f.write(phone)
        print(f"Phone number saved to file: {phone}")
    except Exception as e:
        print(f"Error saving phone number: {e}")

load_phone_number()

if TWILIO_SID and TWILIO_TOKEN:
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
        print("Twilio client initialized")
    except Exception as e:
        print(f"Twilio initialization failed: {e}")
else:
    print("Twilio credentials not found")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

try:
    init_firebase()
    print("Firebase initialized")
except Exception as e:
    print(f"Firebase initialization failed: {e}")

face_rec = FaceRecognizer()
face_rec.load_known_faces()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Warning: camera not detected")
    cap = None

tts = None
try:
    tts = pyttsx3.init()
    tts.setProperty('rate', 150)
    tts.setProperty('volume', 0.9)
    print("Text-to-speech initialized")
except Exception as e:
    print(f"TTS initialization failed: {e}")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5

audio = None
try:
    audio = pyaudio.PyAudio()
    print("Audio system initialized")
except Exception as e:
    print(f"Audio initialization failed: {e}")

def send_sms(phone_number, message):
    try:
        if twilio_client and TWILIO_FROM:
            msg = twilio_client.messages.create(
                body=message,
                from_=TWILIO_FROM,
                to=phone_number
            )
            print(f"SMS sent to {phone_number}: {msg.sid}")
            log_event("sms_sent", f"SMS sent to {phone_number}", {"sid": msg.sid, "to": phone_number})
            return True
        else:
            print("Twilio not configured")
            return False
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def alert_callback(distance):
    print(f"Alert triggered! Distance: {distance:.1f}cm")
    
    if not cap:
        print("Camera not available!")
        return
        
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame!")
        return

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    name, confidence_dist = face_rec.recognize(rgb)
    
    if name:
        print(f"Face recognized: {name}")
        log_event("face_recognized", {"name": name, "distance": distance, "confidence": confidence_dist})
        
        sensors.lcd_write(f"Welcome, {name}", "Door Unlocking...")
        sensors.beep(200)
        threading.Thread(target=sensors.unlock, args=(4,), daemon=True).start()
        
        socketio.emit('event', {
            'type': 'recognized', 
            'name': name, 
            'distance': distance,
            'confidence': confidence_dist,
            'is_dark': sensors.is_dark,
            'light_on': sensors.light_state
        })
        
    else:
        print(f"Face not recognized - alerting owner")
        log_event("alert", {"reason": "unknown_face", "distance": distance, "confidence": confidence_dist})
        
        sensors.lcd_write("Access Denied", "Alerting Owner")
        
        for _ in range(2):
            sensors.beep(200)
            time.sleep(0.12)
        
        socketio.emit('event', {
            'type': 'unknown', 
            'distance': distance,
            'confidence': confidence_dist,
            'two_way_comm_ready': True,
            'is_dark': sensors.is_dark,
            'light_on': sensors.light_state
        })

        try:
            from firebase_admin import db
            t_ref = db.reference('/doorcam/device_tokens')
            tokens = t_ref.get() or []
            if isinstance(tokens, dict):
                tokens = list(tokens.values())
            if tokens:
                send_fcm(tokens, "Unknown Visitor Alert",
                         f"Unknown person detected! Distance: {int(distance)}cm",
                         {"type": "unknown", "distance": distance, "action": "two_way_comm"})
                log_event("notification_sent", {"method": "fcm", "count": len(tokens)})
        except Exception as e:
            print("Error sending FCM:", e)

        try:
            if owner_phone_number and twilio_client and TWILIO_FROM:
                message_text = f"DOORCAM ALERT: Unknown visitor detected! Distance: {int(distance)}cm. Check live feed immediately."
                msg = twilio_client.messages.create(
                    body=message_text,
                    from_=TWILIO_FROM,
                    to=owner_phone_number
                )
                print(f"SMS Alert sent successfully to {owner_phone_number}: {msg.sid}")
                log_event("twilio_sms_sent", {"sid": msg.sid, "to": owner_phone_number, "message": message_text})
            else:
                missing = []
                if not owner_phone_number: missing.append("phone_number")
                if not twilio_client: missing.append("twilio_client")
                if not TWILIO_FROM: missing.append("TWILIO_FROM")
                print(f"SMS not sent - missing: {missing}")
        except Exception as e:
            print(f"Twilio SMS error: {e}")
            log_event("twilio_sms_error", {"error": str(e), "phone": owner_phone_number})

sensors = Sensors(alert_callback=alert_callback)
sensors.start()
@app.route('/')
def index():
    token = request.cookies.get('firebase_token')
    if not token or not verify_firebase_token(token):
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        id_token = request.form.get('idToken')
        if verify_firebase_token(id_token):
            resp = redirect(url_for('index'))
            resp.set_cookie('firebase_token', id_token)
            return resp
        return "Invalid login", 401
    return render_template('login.html')

@app.route('/register_face', methods=['POST'])
def register_face():
    name = request.form.get('name')
    if not name:
        return jsonify({'error':'name missing'}), 400

    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    else:
        snapshot = request.form.get('snapshot')
        if snapshot:
            if snapshot.startswith('data:'):
                image_bytes = base64.b64decode(snapshot.split(',',1)[1])
            else:
                image_bytes = base64.b64decode(snapshot)
        else:
            return jsonify({'error':'no image provided'}), 400

    person_dir = os.path.join(os.path.dirname(__file__), 'known_faces', name)
    os.makedirs(person_dir, exist_ok=True)
    fname = os.path.join(person_dir, f"{int(time.time())}.jpg")
    with open(fname, 'wb') as f:
        f.write(image_bytes)

    face_rec.load_known_faces()
    log_event("face_registered", {"name": name, "file": fname})
    return jsonify({'ok': True, 'file': fname})

def gen_frames():
    while True:
        if not cap:
            time.sleep(1)
            continue
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue
        cv2.putText(frame, "DoorCam Live", (10,20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    resp = redirect(url_for('login_page'))
    resp.delete_cookie('firebase_token')
    return resp

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    from webrtc_server import handle_offer
    sdp = data.get('sdp')
    sid = request.sid
    if not sdp:
        emit('webrtc_answer', {'error':'missing sdp'})
        return
    answer = handle_offer(sdp, sid)
    if answer:
        emit('webrtc_answer', {'sdp': answer})
    else:
        emit('webrtc_answer', {'error':'failed to create answer'})

@socketio.on('connect')
def on_connect():
    print('client connected')

@socketio.on('tts')
def on_tts(data):
    text = data.get('text')
    if text and tts:
        try:
            tts.say(text)
            tts.runAndWait()
            emit('tts_ack', {'ok': True})
        except Exception as e:
            print("TTS error:", e)
            emit('tts_ack', {'ok': False, 'error': str(e)})

@socketio.on('chat')
def on_chat(data):
    socketio.emit('chat', data)

@socketio.on('set_phone_number')
def handle_set_phone(data):
    global owner_phone_number
    phone = data.get('phone', '').strip()
    if phone:
        owner_phone_number = phone
        save_phone_number(phone)
        print(f"Owner phone number set and saved: {phone}")
        socketio.emit('phone_updated', {
            'success': True,
            'message': f'Phone number saved: {phone}'
        })
    else:
        socketio.emit('phone_updated', {
            'success': False,
            'message': 'Invalid phone number'
        })

@socketio.on('manual_unlock')
def handle_manual_unlock(data):
    duration = data.get('duration', 4)
    reason = data.get('reason', 'Manual unlock by owner')
    
    print(f"Manual unlock: {reason}")
    log_event("manual_unlock", {"reason": reason, "duration": duration})
    
    sensors.lcd_write("Owner Override", "Door Unlocking...")
    sensors.beep(100)
    sensors.manual_unlock(duration)
    
    socketio.emit('event', {
        'type': 'manual_unlock', 
        'reason': reason,
        'duration': duration
    })

@socketio.on('manual_light')
def handle_manual_light(data):
    try:
        state = data.get('state', False)
        reason = f"Manual control via web interface: {'ON' if state else 'OFF'}"
        
        if state:
            sensors.turn_on_light(reason)
        else:
            sensors.turn_off_light(reason)
        
        socketio.emit('light_update', {
            'success': True,
            'light_on': state,
            'message': f"Light turned {'ON' if state else 'OFF'}"
        })
        
    except Exception as e:
        print(f"Error in manual light control: {e}")
        socketio.emit('light_update', {
            'success': False,
            'message': f"Error: {str(e)}"
        })

@socketio.on('start_audio_recording')
def handle_start_audio_recording():
    try:
        socketio.emit('audio_recording_status', {
            'status': 'starting',
            'message': 'Starting audio recording...'
        })
        
        def record_and_upload():
            audio_data = record_audio(5)
            if audio_data:
                filename = f"visitor_audio_{int(time.time())}.wav"
                audio_url = upload_audio_to_storage(audio_data, filename)
                
                if audio_url:
                    socketio.emit('audio_recording_complete', {
                        'success': True,
                        'audio_url': audio_url,
                        'filename': filename,
                        'message': 'Audio recorded and uploaded successfully'
                    })
                else:
                    socketio.emit('audio_recording_complete', {
                        'success': False,
                        'message': 'Failed to upload audio'
                    })
            else:
                socketio.emit('audio_recording_complete', {
                    'success': False,
                    'message': 'Failed to record audio'
                })
        
        import threading
        thread = threading.Thread(target=record_and_upload)
        thread.start()
        
    except Exception as e:
        print(f"Error starting audio recording: {e}")
        socketio.emit('audio_recording_complete', {
            'success': False,
            'message': f'Error: {str(e)}'
        })

@socketio.on('audio_stream')
def handle_audio_stream(data):
    try:
        socketio.emit('audio_data', data, broadcast=True)
    except Exception as e:
        print(f"Error handling audio stream: {e}")



@socketio.on('emergency_alert')
def handle_emergency_alert():
    try:
        global owner_phone_number
        
        if owner_phone_number and twilio_client:
            message = "🚨 EMERGENCY ALERT from DoorCam System! Please check the live feed immediately."
            send_sms(owner_phone_number, message)
        
        send_fcm("Emergency Alert", "Emergency button pressed on DoorCam system", {"type": "emergency"})
        
        log_event('emergency_alert', {
            'type': 'emergency_alert',
            'timestamp': time.time(),
            'triggered_by': 'web_interface',
            'message': 'Emergency alert triggered from web interface'
        })
        
        socketio.emit('alert_sent', {
            'success': True,
            'message': 'Emergency alert sent to owner'
        })
        
    except Exception as e:
        print(f"Error sending emergency alert: {e}")
        socketio.emit('alert_sent', {
            'success': False,
            'message': f"Error: {str(e)}"
        })



@app.route('/light_status')
def light_status():
    return jsonify({
        'is_dark': sensors.is_dark,
        'light_on': sensors.light_state,
        'ldr_value': not sensors.is_dark
    })

@app.route('/phone_status')
def phone_status():
    global owner_phone_number
    return jsonify({
        'phone_number': owner_phone_number,
        'twilio_configured': bool(twilio_client and TWILIO_FROM),
        'twilio_from': TWILIO_FROM if TWILIO_FROM else None
    })

@app.route('/test_sms', methods=['POST'])
def test_sms():
    try:
        if not owner_phone_number:
            return jsonify({'success': False, 'error': 'No phone number set'})
        
        if not (twilio_client and TWILIO_FROM):
            return jsonify({'success': False, 'error': 'Twilio not configured'})
        
        test_message = "DoorCam Test: SMS system is working correctly!"
        success = send_sms(owner_phone_number, test_message)
        
        if success:
            return jsonify({'success': True, 'message': f'Test SMS sent to {owner_phone_number}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send SMS'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def record_audio(duration=5):
    try:
        frames = []
        stream = audio.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)
        
        print(f"Recording audio for {duration} seconds...")
        
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        audio_data = io.BytesIO()
        wf = wave.open(audio_data, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        audio_data.seek(0)
        return audio_data.getvalue()
        
    except Exception as e:
        print(f"Error recording audio: {e}")
        return None

@app.route('/record_audio', methods=['POST'])
def record_audio_endpoint():
    try:
        audio_data = record_audio(5)
        if audio_data:
            filename = f"audio_recording_{int(time.time())}.wav"
            audio_url = upload_audio_to_storage(audio_data, filename)
            
            if audio_url:
                socketio.emit('audio_recorded', {
                    'success': True,
                    'audio_url': audio_url,
                    'filename': filename,
                    'timestamp': time.time()
                })
                return jsonify({'success': True, 'audio_url': audio_url})
            else:
                return jsonify({'success': False, 'error': 'Failed to upload audio'})
        else:
            return jsonify({'success': False, 'error': 'Failed to record audio'})
    except Exception as e:
        print(f"Error in record_audio_endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    try:
        print("Starting DoorCam application...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Application stopped by user")
    except Exception as e:
        print(f"Application error: {e}")
    finally:
        if cap:
            cap.release()
        if 'sensors' in locals():
            sensors.cleanup()
        print("Application shutdown complete")
