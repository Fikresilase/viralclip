
import cv2
import numpy as np

# Try importing MediaPipe
try:
    import mediapipe as mp
    try:
        if not hasattr(mp, 'solutions'):
            import mediapipe.python.solutions as solutions
            mp.solutions = solutions
        MP_AVAILABLE = True
    except ImportError:
        MP_AVAILABLE = False
except ImportError:
    MP_AVAILABLE = False

class FaceTracker:
    def __init__(self, target_aspect_ratio=9/16, smoothing_factor=0.9, scene_change_threshold=300):
        self.target_aspect_ratio = target_aspect_ratio
        self.smoothing_factor = smoothing_factor
        self.scene_change_threshold = scene_change_threshold
        self.use_mediapipe = False
        
        if MP_AVAILABLE and hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
             try:
                 self.mp_face_detection = mp.solutions.face_detection
                 self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
                 self.use_mediapipe = True
                 print("[FaceTracker] Using MediaPipe Face Detection.")
             except Exception as e:
                 print(f"[FaceTracker] MediaPipe initialization failed: {e}")
        
        if not self.use_mediapipe:
             print("[FaceTracker] Falling back to OpenCV Haar Cascade.")
             # Load Haar Cascade
             self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        self.current_crop_x = None
        self.last_face_x = None

    def get_crop_params(self, frame_width, frame_height, detections):
        """
        Calculates the crop parameters (x, y, w, h) for a given frame based on face detections.
        """
        # Determine target crop width and height (vertical 9:16)
        crop_h = frame_height
        crop_w = int(crop_h * self.target_aspect_ratio)
        
        # Default: Center Crop
        target_center_x = frame_width / 2

        if self.use_mediapipe:
            if detections and detections.detections:
                # Find face with highest confidence
                best_detection = max(detections.detections, key=lambda d: d.score[0])
                
                # Get relative bounding box
                bbox = best_detection.location_data.relative_bounding_box
                face_center_x = (bbox.xmin + bbox.width / 2) * frame_width
                target_center_x = face_center_x
        else:
            # OpenCV Detections (list of rects [x, y, w, h])
            if len(detections) > 0:
                # Pick largest face
                best_face = max(detections, key=lambda r: r[2] * r[3])
                x, y, w, h = best_face
                face_center_x = x + w / 2
                target_center_x = face_center_x

        # Calculate target top-left X for the crop
        target_crop_x = target_center_x - (crop_w / 2)
        
        # Clamp to frame boundaries
        target_crop_x = max(0, min(target_crop_x, frame_width - crop_w))

        # Apply smoothing logic
        if self.current_crop_x is None:
            self.current_crop_x = target_crop_x
            self.last_face_x = target_center_x
        else:
            # Scene Change Detection
            if self.last_face_x is not None:
                dist = abs(target_center_x - self.last_face_x)
                if dist > self.scene_change_threshold:
                    # Scene change detected! Snap immediately.
                    self.current_crop_x = target_crop_x
                else:
                    # Apply smoothing
                    self.current_crop_x = (self.current_crop_x * self.smoothing_factor) + (target_crop_x * (1 - self.smoothing_factor))
            else:
                 self.current_crop_x = target_crop_x

            self.last_face_x = target_center_x

        return int(self.current_crop_x), 0, crop_w, crop_h

    def process_frame(self, frame):
        """
        Processes a single frame: detects faces, calculates crop, returns cropped frame.
        """
        h, w, _ = frame.shape
        detections = None
        
        if self.use_mediapipe:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detections = self.face_detection.process(rgb_frame)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        x, y, cw, ch = self.get_crop_params(w, h, detections)
        
        cropped_frame = frame[y:y+ch, x:x+cw]
        return cropped_frame

    def release(self):
        if self.use_mediapipe:
            self.face_detection.close()
