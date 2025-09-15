<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Poppins&weight=600&size=28&duration=3500&pause=500&color=151CF7&center=true&vCenter=true&width=435&lines=DoorCam+Security;Smart+Door+System;TechWiz+2025;" alt="Typing SVG" />
</div>

# 🔐 DoorCam - Smart Security System

Advanced Raspberry Pi-based facial recognition door security system with real-time monitoring, two-way communication, and mobile notifications.

## 🚀 Features

- **Face Recognition**: Automated door unlock for registered users
- **Live Video Streaming**: Real-time camera feed via web interface
- **Audio Communication**: Record messages and live audio
- **Smart Lighting**: Automatic light control based on ambient conditions
- **Mobile Alerts**: SMS and push notifications for security events
- **Web Dashboard**: Modern responsive interface for remote monitoring
- **Firebase Integration**: Cloud storage and real-time database

## 📋 Installation

1. **Clone the repository**
```bash
git clone https://github.com/TechWizardsTechwiz6/Wavebell.git
cd Wavebell
```

2. **Install dependencies**
```bash
pip install opencv-python face-recognition flask flask-socketio
pip install firebase-admin twilio pyttsx3 pyaudio
pip install RPi.GPIO RPLCD smbus2
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Setup Firebase**
- Add your `firebase-key.json` credentials file
- Update Firebase configuration in `.env`

5. **Run the application**
```bash
python app.py
```

## 🔧 Hardware Setup

### Required Components
- Raspberry Pi 4
- Camera Module
- PIR Motion Sensor (GPIO 23)
- Ultrasonic Sensor (GPIO 24, 25)
- LCD Display (I2C)
- Relay Module (GPIO 19)
- LDR Sensor (GPIO 22)
- LED Light (GPIO 17)
- Buzzer (GPIO 26)

### Wiring Diagram
```
PIR Sensor    -> GPIO 23
Ultrasonic    -> GPIO 24 (Echo), GPIO 25 (Trigger)
Relay Module  -> GPIO 19
LDR Sensor    -> GPIO 22
LED Light     -> GPIO 17
Buzzer        -> GPIO 26
LCD Display   -> I2C (SDA, SCL)
```

## 🌐 Web Interface

Access the system at `http://your-pi-ip:5000`

### Available Routes
- `/` - Main dashboard (requires authentication)
- `/login` - Firebase authentication
- `/video_feed` - Live camera stream
- `/register_face` - Add new users
- `/record_audio` - Audio recording endpoint

## 📱 Mobile Features

- Real-time push notifications
- SMS alerts for unknown visitors
- Remote door unlock
- Live audio communication
- Emergency alert system

## ⚙️ Configuration

### Firebase Setup
1. Create Firebase project
2. Enable Authentication, Realtime Database, and Storage
3. Download service account key as `firebase-key.json`
4. Update database URL in `.env`

### Twilio SMS
1. Create Twilio account
2. Get Account SID, Auth Token, and phone number
3. Update credentials in `.env`

## 🔗 Technologies Used

<p align="left">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/OpenCV-27338e?style=for-the-badge&logo=OpenCV&logoColor=white">
  <img src="https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black">
  <img src="https://img.shields.io/badge/Raspberry%20Pi-C51A4A?style=for-the-badge&logo=Raspberry-Pi">
  <img src="https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white">
</p>

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │◄──►│  Flask Server    │◄──►│   Hardware      │
│                 │    │                  │    │                 │
│ • Live Video    │    │ • Face Recognition│    │ • Camera        │
│ • Audio Control │    │ • Audio Recording│    │ • Sensors       │
│ • Remote Access │    │ • Firebase Sync  │    │ • Door Lock     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Cloud Services │
                       │                  │
                       │ • Firebase DB    │
                       │ • Push Notifications│
                       │ • SMS Alerts     │
                       └──────────────────┘
```

## 🛡️ Security Features

- Face recognition with confidence threshold
- Firebase authentication
- Encrypted data transmission
- Automatic door re-lock
- Motion detection with cooldown
- Emergency alert system

## 📝 Usage

1. **Initial Setup**: Register authorized faces through web interface
2. **Normal Operation**: System automatically detects and unlocks for registered users
3. **Unknown Visitors**: Sends alerts and enables two-way communication
4. **Remote Access**: Monitor and control system from anywhere via web dashboard
5. **Emergency**: Use emergency alert for immediate notifications

## 🔗 Important Links

- [GitHub Repository](https://github.com/TechWizardsTechwiz6/Wavebell)
- [Hardware Guide](https://github.com/MohammadShayan1/doorcam_pi/wiki/hardware)

## 👥 Development Team

| Student ID | Name | Role |
|------------|------|------|
| Student1423331 | Habeel | Hardware Integration |
| Student1413931 | Mohammad Shayan | Lead Developer |
| Student1413950 | Shahmeer Fareed | System Architecture |

---

<div align="center">
  Made with ❤️ by Team TechWizards
  <br>
  <img src="https://img.shields.io/badge/License-MIT-blue.svg">
  <img src="https://img.shields.io/badge/Version-2.0-green.svg">
</div>
