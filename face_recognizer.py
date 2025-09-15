import os
import face_recognition
import numpy as np

KNOWN_DIR = os.path.join(os.path.dirname(__file__), "known_faces")

class FaceRecognizer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces()

    def load_known_faces(self):
        print("Loading known faces...")
        self.known_encodings = []
        self.known_names = []
        
        if not os.path.exists(KNOWN_DIR):
            os.makedirs(KNOWN_DIR)
            print("No known faces yet. Add images under known_faces/<Name>/")
            return
            
        for person_name in os.listdir(KNOWN_DIR):
            person_dir = os.path.join(KNOWN_DIR, person_name)
            if not os.path.isdir(person_dir):
                continue
            for fn in os.listdir(person_dir):
                if not fn.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                path = os.path.join(person_dir, fn)
                try:
                    img = face_recognition.load_image_file(path)
                    encs = face_recognition.face_encodings(img)
                    if len(encs) > 0:
                        self.known_encodings.append(encs[0])
                        self.known_names.append(person_name)
                        print("Loaded", person_name, fn)
                except Exception as e:
                    print("Error loading", path, e)

    def recognize(self, frame_rgb):
        face_locations = face_recognition.face_locations(frame_rgb, model="hog")
        
        if len(face_locations) == 0:
            return None, None
            
        if len(self.known_encodings) == 0:
            return None, None
        
        encodings = face_recognition.face_encodings(frame_rgb, face_locations)
        
        for face_encoding in encodings:
            distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            best_idx = np.argmin(distances)
            best_distance = float(distances[best_idx])
            
            if best_distance < 0.5:
                return self.known_names[best_idx], best_distance
            else:
                return None, best_distance
        
        return None, None
