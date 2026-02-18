
import cv2
import numpy as np
import os

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
except ImportError:
    YOLO_AVAILABLE = False
    print("[FaceTracker] YOLO (Ultralytics) not available.")

class FaceTracker:
    def __init__(self, target_aspect_ratio=9/16, smoothing_factor=0.1, deadzone_px=50, scene_change_threshold=300):
        self.target_aspect_ratio = target_aspect_ratio
        self.smoothing_factor = smoothing_factor # Low value = slow, cinematic glide
        self.deadzone_px = deadzone_px
        self.scene_change_threshold = scene_change_threshold
        
        # --- 1. DETECTORS SETUP ---
        self.mp_face = None
        self.mp_pose = None
        self.yolo_model = None

        if MP_AVAILABLE:
            try:
                self.mp_face = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.6)
                self.mp_pose = mp.solutions.pose.Pose(static_image_mode=False, min_detection_confidence=0.5)
                print("[FaceTracker] MediaPipe (Face & Pose) initialized.")
            except Exception as e:
                print(f"[FaceTracker] MediaPipe initialization error: {e}")

        if YOLO_AVAILABLE:
            try:
                # Load Nano model (fastest)
                self.yolo_model = YOLO("yolov8n.pt")
                print("[FaceTracker] YOLOv8 initialized.")
            except Exception as e:
                print(f"[FaceTracker] YOLO initialization error: {e}")

        # --- 2. STATE VARIABLES ---
        self.current_crop_x = None # The actual camera X position
        self.locked_target_x = None # The person we are following
        self.frames_without_lock = 0
        self.lock_patience = 30 # How many frames to wait before switching targets (1 sec @ 30fps)

    def get_target_center(self, frame_rgb, width, height):
        """
        Determines the best X-coordinate to center on, using the fallback hierarchy.
        Returns: (best_x, method_name) or (None, "None")
        """
        
        # Priority 1: Face Detection (Head)
        if self.mp_face:
            results = self.mp_face.process(frame_rgb)
            if results.detections:
                # Find the face closest to our last locked position (Locking Logic)
                if self.locked_target_x is not None:
                     # Get all centers
                     candidates = []
                     for detection in results.detections:
                         bbox = detection.location_data.relative_bounding_box
                         center_x = (bbox.xmin + bbox.width / 2) * width
                         candidates.append(center_x)
                     
                     # Find candidate with min distance to lock
                     best_x = min(candidates, key=lambda x: abs(x - self.locked_target_x))
                     
                     # If it's reasonable distance, keep it. If massive jump, might be new person?
                     # For now, just track closest.
                     return best_x, "Face"
                else:
                    # No lock? Pick the most confident/largest face
                    # MediaPipe returns score[0]
                    best = max(results.detections, key=lambda d: d.score[0])
                    bbox = best.location_data.relative_bounding_box
                    return (bbox.xmin + bbox.width / 2) * width, "Face"

        # Priority 2: Pose Detection (Shoulders/Body)
        if self.mp_pose:
            results = self.mp_pose.process(frame_rgb)
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                # Midpoint between shoulders (Indices 11 & 12)
                left_shoulder = landmarks[11]
                right_shoulder = landmarks[12]
                
                # Check visibility
                if left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5:
                    mid_x = (left_shoulder.x + right_shoulder.x) / 2 * width
                    return mid_x, "Pose"

        # Priority 3: YOLO Object Detection (Person > Dog/Cat > Car)
        if self.yolo_model:
            # Run inference
            results = self.yolo_model(frame_rgb, verbose=False)
            boxes = results[0].boxes
            if boxes:
                # Filter for classes: 0=person, 15=cat, 16=dog, etc.
                # Prioritize 'person' (class 0) with highest confidence
                persons = [b for b in boxes if int(b.cls) == 0]
                if persons:
                    best_person = max(persons, key=lambda p: p.conf)
                    xywh = best_person.xywh[0].cpu().numpy() # x_center, y_center, w, h
                    return xywh[0], "YOLO-Person"
                
                # Fallback to any high-confidence object
                best_obj = max(boxes, key=lambda b: b.conf)
                xywh = best_obj.xywh[0].cpu().numpy()
                return xywh[0], f"YOLO-{int(best_obj.cls)}"

        # Priority 4: Center (Default)
        return width / 2, "Center"

    def get_crop_params(self, frame_width, frame_height, frame_rgb):
        """
        Calculates the crop parameters (x, y, w, h) for a given frame.
        """
        crop_h = frame_height
        crop_w = int(crop_h * self.target_aspect_ratio)
        
        # 1. Get Ideal Target
        target_x, method = self.get_target_center(frame_rgb, frame_width, frame_height)
        
        # 2. Locking & Patience Logic
        if self.locked_target_x is None:
            self.locked_target_x = target_x
        else:
            # Check distance to previous lock
            dist = abs(target_x - self.locked_target_x)
            
            # Scene Change Check
            if dist > self.scene_change_threshold:
                # Massive jump? Assume cut. Reset lock instantly.
                self.locked_target_x = target_x
                self.frames_without_lock = 0
                # Also reset current camera to snap immediately
                self.current_crop_x = None 
            else:
                # Normal movement
                self.locked_target_x = target_x
        
        # 3. Calculate Crop X (Top-Left)
        # Center the crop around the target_x
        desired_crop_x = self.locked_target_x - (crop_w / 2)
        
        # Clamp to bounds
        desired_crop_x = max(0, min(desired_crop_x, frame_width - crop_w))

        # 4. Camera Smoothing Logic
        if self.current_crop_x is None:
            self.current_crop_x = desired_crop_x
        else:
            # Deadzone Check
            # If camera needs to move less than X pixels, don't move it.
            # This creates a steady "tripod" feel for small movements.
            diff = desired_crop_x - self.current_crop_x
            if abs(diff) < self.deadzone_px:
                # Inside deadzone: Keep current position (don't update self.current_crop_x)
                pass 
            else:
                # Outside deadzone: Glide towards target
                # Apply EMA (Exponential Moving Average)
                self.current_crop_x = (self.current_crop_x * (1 - self.smoothing_factor)) + (desired_crop_x * self.smoothing_factor)

        return int(self.current_crop_x), 0, crop_w, crop_h

    def process_frame(self, frame):
        """
        Processes a single BGR frame.
        """
        h, w, _ = frame.shape
        # Convert to RGB for Detectors
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        x, y, cw, ch = self.get_crop_params(w, h, frame_rgb)
        
        # Apply Crop
        cropped = frame[y:y+ch, x:x+cw]
        return cropped

    def release(self):
        if self.mp_face: self.mp_face.close()
        if self.mp_pose: self.mp_pose.close()
        # YOLO model doesn't need explicit close
