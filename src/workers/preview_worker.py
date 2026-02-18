"""
preview_worker.py - Background worker for fetching video previews.
"""

import sys
import os
import subprocess
import requests
import re
from io import BytesIO

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
from PIL import Image

# Regex for YouTube URLs
YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)

class PreviewWorker(QThread):
    """
    Background thread to fetch preview image and metadata.
    """
    previewReady = pyqtSignal(QImage, str)  # Image, Title/Filename
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, source: str, is_local_file: bool = False):
        super().__init__()
        self.source = source
        self.is_local_file = is_local_file

    def run(self):
        try:
            if self.is_local_file:
                self._process_local_file()
            else:
                self._process_youtube_url()
        except FileNotFoundError as e:
            # Captures missing ffmpeg/yt-dlp executable
            self.errorOccurred.emit(f"Missing dependency: {str(e).split('] ')[-1]}")
        except Exception as e:
            self.errorOccurred.emit(str(e))

    def _process_local_file(self):
        """Extract frame from local video file using OpenCV."""
        if not os.path.exists(self.source):
            raise Exception("File not found")

        filename = os.path.basename(self.source)
        
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Try to seek to 1 second, fallback to start
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        
        ret, frame = cap.read()
        if not ret or frame is None:
            # Fallback to first frame
            cap.set(cv2.CAP_PROP_POS_MSEC, 0)
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                raise Exception("Could not extract frame from video")
        
        cap.release()
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        image = Image.fromarray(frame_rgb)
        self._emit_image(image, filename)

    def _process_youtube_url(self):
        """Fetch metadata and thumbnail using yt-dlp."""
        # FIX: Use --print to force strict output order: Title first, then Thumbnail
        cmd = [
            'yt-dlp',
            '--print', 'title',
            '--print', 'thumbnail',
            '--no-warnings',
            self.source
        ]
        
        startupinfo = self._get_startup_info()
            
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                startupinfo=startupinfo
            )
            out, err = process.communicate()
        except FileNotFoundError:
             raise FileNotFoundError("yt-dlp executable not found in PATH")
        
        if process.returncode != 0:
            raise Exception("Invalid YouTube URL")
            
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        
        # FIX: Robust parsing based on known output order
        if len(lines) >= 2:
            title = lines[0]
            thumb_url = lines[1]
        elif len(lines) == 1:
            title = "Unknown Title"
            thumb_url = lines[0]
        else:
            raise Exception("No metadata found")

        # Validation
        if not thumb_url.startswith('http'):
            # Sometimes yt-dlp errors print to stdout, catch that here
            raise Exception("Failed to retrieve thumbnail URL")

        # Download image
        try:
            response = requests.get(thumb_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            raise Exception("Network error fetching thumbnail")
        
        try:
            image = Image.open(BytesIO(response.content))
            self._emit_image(image, title)
        except Exception:
            raise Exception("Invalid image data received")

    def _emit_image(self, pil_image: Image.Image, title: str):
        """Convert PIL Image to QImage safely."""
        # Convert to RGB (standardize format)
        if pil_image.mode != "RGB" and pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGB")
            
        buffer = BytesIO()
        # Use JPEG for speed and small size in memory
        fmt = "PNG" if pil_image.mode == "RGBA" else "JPEG"
        pil_image.save(buffer, format=fmt)
        
        qimage = QImage()
        qimage.loadFromData(buffer.getvalue())
        
        self.previewReady.emit(qimage, title)

    def _get_startup_info(self):
        """Hide console window on Windows."""
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return startupinfo
        return None