
import cv2
import numpy as np
import os
from collections import deque

# Robust imports
try:
    import mediapipe as mp
    # Fix for some mediapipe versions missing 'solutions'
    if not hasattr(mp, 'solutions'):
        import mediapipe.python.solutions as solutions
        mp.solutions = solutions
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False
    print("[FaceTracker] MediaPipe not available.")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except (ImportError, OSError) as e:
    YOLO_AVAILABLE = False
    print(f"[FaceTracker] YOLO (Ultralytics) not available: {e}")

class FaceTracker:
    def __init__(self, target_aspect_ratio=9/16):
        self.target_aspect_ratio = target_aspect_ratio
        
        # Smoothing parameters (optimized for no jitter)
        self.smoothing_factor = 0.03  # Very slow, cinematic movement
        self.deadzone_ratio = 0.12  # 12% of frame width
        self.max_velocity_per_frame = 20  # Max pixels camera can move per frame
        
        # Lock and patience parameters
        self.lock_patience = 60  # Frames to wait before switching targets (2 sec @ 30fps)
        self.method_switch_patience = 15  # Frames before switching detection method
        self.min_confidence = 0.75  # Minimum detection confidence
        
        # Scene change detection
        self.scene_change_threshold = 0.3  # Histogram difference threshold (0-1)
        self.prev_frame_gray = None
        
        # --- DETECTORS SETUP ---
        self.mp_face = None
        self.mp_pose = None
        self.yolo_model = None

        if MP_AVAILABLE:
            try:
                self.mp_face = mp.solutions.face_detection.FaceDetection(
                    model_selection=1, 
                    min_detection_confidence=self.min_confidence
                )
                self.mp_pose = mp.solutions.pose.Pose(
                    static_image_mode=False, 
                    min_detection_confidence=0.6
                )
                print("[FaceTracker] MediaPipe (Face & Pose) initialized.")
            except Exception as e:
                print(f"[FaceTracker] MediaPipe initialization error: {e}")

        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO("yolov8n.pt")
                print("[FaceTracker] YOLOv8 initialized.")
            except Exception as e:
                print(f"[FaceTracker] YOLO initialization error: {e}")

        # --- STATE VARIABLES ---
        self.current_crop_x = None  # Actual camera X position
        self.locked_target_x = None  # The person we are following
        self.target_position_buffer = deque(maxlen=10)  # Moving average buffer
        self.frames_since_target_switch = 0
        self.current_method = None
        self.frames_without_current_method = 0
        self.previous_target_x = None  # For velocity prediction

    def detect_scene_change(self, frame_gray):
        """Detect scene cuts using histogram comparison"""
        if self.prev_frame_gray is None:
            self.prev_frame_gray = frame_gray
            return False
        
        # Calculate histograms
        hist1 = cv2.calcHist([self.prev_frame_gray], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([frame_gray], [0], None, [256], [0, 256])
        
        # Normalize
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # Compare using correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        self.prev_frame_gray = frame_gray
        
        # Low correlation = scene change
        return correlation < (1 - self.scene_change_threshold)

    def get_target_center(self, frame_rgb, width, height):
        """
        Determines the best X-coordinate to center on with confidence filtering.
        Returns: (best_x, confidence, method_name) or (None, 0, "None")
        """
        
        # Priority 1: Face Detection (Head)
        if self.mp_face:
            results = self.mp_face.process(frame_rgb)
            if results.detections:
                # Filter by confidence
                valid_detections = [d for d in results.detections if d.score[0] >= self.min_confidence]
                
                if valid_detections:
                    # If we have a locked target, find closest face
                    if self.locked_target_x is not None:
                        candidates = []
                        for detection in valid_detections:
                            bbox = detection.location_data.relative_bounding_box
                            center_x = (bbox.xmin + bbox.width / 2) * width
                            distance = abs(center_x - self.locked_target_x)
                            candidates.append((center_x, distance, detection.score[0]))
                        
                        # Get closest with reasonable distance (within 30% of frame width)
                        reasonable_candidates = [c for c in candidates if c[1] < width * 0.3]
                        if reasonable_candidates:
                            best = min(reasonable_candidates, key=lambda x: x[1])
                            return best[0], best[2], "Face"
                    
                    # No lock or no close match - pick most confident
                    best = max(valid_detections, key=lambda d: d.score[0])
                    bbox = best.location_data.relative_bounding_box
                    center_x = (bbox.xmin + bbox.width / 2) * width
                    return center_x, best.score[0], "Face"

        # Priority 2: Pose Detection (Shoulders/Body)
        if self.mp_pose:
            results = self.mp_pose.process(frame_rgb)
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                left_shoulder = landmarks[11]
                right_shoulder = landmarks[12]
                
                # Check visibility
                if left_shoulder.visibility > 0.6 and right_shoulder.visibility > 0.6:
                    mid_x = (left_shoulder.x + right_shoulder.x) / 2 * width
                    confidence = (left_shoulder.visibility + right_shoulder.visibility) / 2
                    return mid_x, confidence, "Pose"

        # Priority 3: YOLO Object Detection (Person)
        if self.yolo_model:
            results = self.yolo_model(frame_rgb, verbose=False)
            boxes = results[0].boxes
            if boxes:
                # Filter for persons with high confidence
                persons = [b for b in boxes if int(b.cls) == 0 and b.conf > self.min_confidence]
                if persons:
                    # If locked, find closest person
                    if self.locked_target_x is not None:
                        candidates = []
                        for person in persons:
                            xywh = person.xywh[0].cpu().numpy()
                            center_x = xywh[0]
                            distance = abs(center_x - self.locked_target_x)
                            candidates.append((center_x, distance, float(person.conf)))
                        
                        reasonable = [c for c in candidates if c[1] < width * 0.3]
                        if reasonable:
                            best = min(reasonable, key=lambda x: x[1])
                            return best[0], best[2], "YOLO-Person"
                    
                    # Pick most confident
                    best_person = max(persons, key=lambda p: p.conf)
                    xywh = best_person.xywh[0].cpu().numpy()
                    return xywh[0], float(best_person.conf), "YOLO-Person"

        # Priority 4: Center (Default)
        return width / 2, 0.5, "Center"

    def smooth_target_position(self, raw_target_x):
        """Apply moving average to target position"""
        self.target_position_buffer.append(raw_target_x)
        
        if len(self.target_position_buffer) < 3:
            return raw_target_x
        
        # Weighted moving average (more weight on recent frames)
        weights = np.linspace(0.5, 1.0, len(self.target_position_buffer))
        weights = weights / weights.sum()
        
        smoothed = np.average(list(self.target_position_buffer), weights=weights)
        return smoothed

    def predict_target_position(self, current_x):
        """Predict next position based on velocity"""
        if self.previous_target_x is None:
            self.previous_target_x = current_x
            return current_x
        
        # Calculate velocity
        velocity = current_x - self.previous_target_x
        
        # Limit velocity to reasonable values (prevent jumps)
        velocity = np.clip(velocity, -30, 30)
        
        # Predict next position
        predicted = current_x + velocity * 0.5  # 50% prediction
        
        self.previous_target_x = current_x
        return predicted

    def get_crop_params(self, frame_width, frame_height, frame_rgb, frame_gray):
        """
        Calculates the crop parameters (x, y, w, h) for a given frame.
        """
        crop_h = frame_height
        crop_w = int(crop_h * self.target_aspect_ratio)
        
        # Calculate deadzone in pixels
        deadzone_px = int(frame_width * self.deadzone_ratio)
        
        # Detect scene changes
        scene_changed = self.detect_scene_change(frame_gray)
        
        if scene_changed:
            # Reset everything on scene cut
            self.locked_target_x = None
            self.current_crop_x = None
            self.target_position_buffer.clear()
            self.frames_since_target_switch = 0
            self.current_method = None
            self.frames_without_current_method = 0
            self.previous_target_x = None
        
        # Get raw target
        raw_target_x, confidence, method = self.get_target_center(frame_rgb, frame_width, frame_height)
        
        # Method switching with hysteresis
        if method != self.current_method:
            if self.current_method is None:
                self.current_method = method
                self.frames_without_current_method = 0
            else:
                self.frames_without_current_method += 1
                if self.frames_without_current_method >= self.method_switch_patience:
                    self.current_method = method
                    self.frames_without_current_method = 0
                else:
                    # Keep using previous method's last known position
                    if self.locked_target_x is not None:
                        raw_target_x = self.locked_target_x
        else:
            self.frames_without_current_method = 0
        
        # Apply moving average smoothing
        smoothed_target_x = self.smooth_target_position(raw_target_x)
        
        # Apply velocity prediction
        predicted_target_x = self.predict_target_position(smoothed_target_x)
        
        # Lock patience logic
        if self.locked_target_x is None:
            self.locked_target_x = predicted_target_x
            self.frames_since_target_switch = 0
        else:
            distance = abs(predicted_target_x - self.locked_target_x)
            
            # Only switch if significantly different AND patience expired
            if distance > frame_width * 0.15:  # 15% of frame width
                self.frames_since_target_switch += 1
                if self.frames_since_target_switch >= self.lock_patience:
                    self.locked_target_x = predicted_target_x
                    self.frames_since_target_switch = 0
            else:
                # Close enough - update lock smoothly
                self.locked_target_x = predicted_target_x
                self.frames_since_target_switch = 0
        
        # Calculate desired crop position
        desired_crop_x = self.locked_target_x - (crop_w / 2)
        desired_crop_x = max(0, min(desired_crop_x, frame_width - crop_w))
        
        # Initialize camera position
        if self.current_crop_x is None:
            self.current_crop_x = desired_crop_x
            return int(self.current_crop_x), 0, crop_w, crop_h
        
        # Deadzone check
        diff = desired_crop_x - self.current_crop_x
        
        if abs(diff) < deadzone_px:
            # Inside deadzone - don't move
            pass
        else:
            # Outside deadzone - move with velocity limiting
            # Calculate movement with smoothing
            movement = diff * self.smoothing_factor
            
            # Limit velocity
            movement = np.clip(movement, -self.max_velocity_per_frame, self.max_velocity_per_frame)
            
            # Apply movement
            self.current_crop_x += movement
        
        # Final clamp
        self.current_crop_x = max(0, min(self.current_crop_x, frame_width - crop_w))
        
        return int(self.current_crop_x), 0, crop_w, crop_h

    def process_frame(self, frame):
        """
        Processes a single BGR frame.
        """
        h, w, _ = frame.shape
        
        # Convert to RGB for detectors
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to grayscale for scene detection
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        x, y, cw, ch = self.get_crop_params(w, h, frame_rgb, frame_gray)
        
        # Apply crop
        cropped = frame[y:y+ch, x:x+cw]
        return cropped

    def release(self):
        if self.mp_face: 
            self.mp_face.close()
        if self.mp_pose: 
            self.mp_pose.close()
        # YOLO model doesn't need explicit close
