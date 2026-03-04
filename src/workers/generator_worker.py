import os
import json
import re
import time
import subprocess
import shutil
from datetime import timedelta
import concurrent.futures
import threading
import base64

import cv2
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
from openai import OpenAI

from src.prompts import VIRAL_MOMENTS_PROMPT, VISUAL_MOMENTS_PROMPT
from src.core.face_tracker import FaceTracker
from src.utils.storage import StorageManager

class GeneratorWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    clipsFound = pyqtSignal(list)  # Emits list of segment info when analysis completes
    clipProgress = pyqtSignal(int, int, str)  # (clip_index, percentage, status_text)
    clipComplete = pyqtSignal(int, dict)  # (clip_index, result_data) when single clip finishes

    def __init__(self, source: str, is_local: bool, api_key: str, enable_captions: bool = True):
        super().__init__()
        self.source = source
        self.is_local = is_local
        self.api_key = api_key
        self.enable_captions = enable_captions
        
        # OpenAI client (initialized in run())
        self.openai_client = None
        
        # Semaphore for limiting concurrent API calls
        self.caption_semaphore = threading.Semaphore(5)
        
        # Dictionary to store caption results {clip_index: subtitle_path}
        self.caption_results = {}
        
        # Use StorageManager for output directory
        self.storage = StorageManager()
        self.output_dir = self.storage.temp_dir 
        
        # Locate system ffmpeg
        self.ffmpeg_path = shutil.which('ffmpeg')
        if not self.ffmpeg_path:
             # Fallback to None (let yt-dlp find it in PATH, use 'ffmpeg' command for subprocess)
             self.ffmpeg_path = None
        
        # Determine ffprobe path (usually next to ffmpeg)
        self.ffprobe_path = shutil.which('ffprobe')
        if not self.ffprobe_path and self.ffmpeg_path:
             # Try to guess based on ffmpeg path
             base = os.path.dirname(self.ffmpeg_path)
             probe_guess = os.path.join(base, 'ffprobe.exe' if os.name=='nt' else 'ffprobe')
             if os.path.exists(probe_guess):
                 self.ffprobe_path = probe_guess
             else:
                 self.ffprobe_path = 'ffprobe'

    def log(self, message: str):
        self.progress.emit(message)
        print(f"[GeneratorWorker] {message}")
    
    def _call_ai_text(self, prompt: str) -> str:
        """Call AI with text prompt, returns text response"""
        response = self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    def _call_ai_with_audio(self, prompt: str, audio_path: str) -> str:
        """Call AI with audio file: transcribe with whisper-1, then analyze with gpt-5-mini"""
        # First transcribe with whisper-1
        with open(audio_path, 'rb') as f:
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        
        # Then analyze the transcript with gpt-5-mini
        full_prompt = f"{prompt}\n\nTRANSCRIPT:\n{transcript}"
        response = self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response.choices[0].message.content
    
    def _call_ai_with_images(self, prompt: str, image_paths: list) -> str:
        """Call AI with multiple images, returns text response"""
        # Build messages with base64 encoded images
        content = [{"type": "text", "text": prompt}]
        
        for img_path in image_paths:
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": "high"
                }
            })
        
        response = self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": content}]
        )
        return response.choices[0].message.content

    def run(self):
        try:
            self.log(f"Initialization started.")
            self.log(f"Source: {self.source}")
            self.log(f"Is Local: {self.is_local}")
            self.log(f"AI Provider: OpenAI")
            self.log(f"Output Directory: {self.output_dir}")
            self.log(f"FFmpeg Path detected: {self.ffmpeg_path or 'System PATH'}")

            if not self.api_key:
                raise Exception("OpenAI API Key is missing.")

            # Initialize OpenAI client
            self.log(f"Configuring OpenAI...")
            self.openai_client = OpenAI(api_key=self.api_key)
            self.log("OpenAI configured successfully.")

            # 1. Get Context (Text or Audio)
            self.log("Step 1: Extracting Context (Subtitles or Audio)...")
            context_type, context_path = self._get_context()
            self.log(f"Context acquired: Type={context_type}, Path={context_path}")
            
            # Store context info for caption generation
            self.context_type = context_type
            self.context_path = context_path

            # 2. Analyze
            self.log("Step 2: Analyzing content for viral moments...")
            viral_segments = self._analyze_content(context_type, context_path)
            
            if not viral_segments:
                raise Exception("No viral moments found during analysis.")
            self.log(f"Found {len(viral_segments)} potential viral segments.")
            
            # Emit segments info so UI can create placeholders
            self.clipsFound.emit(viral_segments)

            # 3. Process Clips (video processing + parallel caption generation)
            self.log(f"Step 3: Processing clips with parallel caption generation...")
            results = self._process_clips(viral_segments)
            
            self.log(f"Generation finished. Emitting {len(results)} results.")
            self.finished.emit(results)
            
            # Cleanup temp files after successful generation
            self.log("Cleaning up temporary files...")
            self._cleanup_temp_files()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            # Cleanup on error too
            self._cleanup_temp_files()
            self.error.emit(str(e))

    def _get_context(self):
        """
        Determines and retrieves the best context source (Subs > Audio).
        Returns (type, path).
        """
        if self.is_local:
            return self._get_local_context()
        else:
            return self._get_youtube_context()

    def _get_youtube_context(self):
        self.log("Checking YouTube for existing captions...")
        
        ydl_opts = {
            'skip_download': True,
            'list_subs': True,
            'quiet': True,
        }
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        has_subs = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.source, download=False)
                if 'subtitles' in info and info['subtitles']:
                    self.log(f"Manual subtitles found: {list(info['subtitles'].keys())}")
                    has_subs = True
                elif 'automatic_captions' in info and info['automatic_captions']:
                    self.log("Automatic captions found.")
                    has_subs = True
        except Exception as e:
            self.log(f"Error checking subs: {e}")

        if has_subs:
            self.log("Attempting to download subtitles (VTT)...")
            vtt_path_template = os.path.join(self.output_dir, 'subs_%(id)s')
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitlesformat': 'vtt',
                'subtitleslangs': ['en'],
                'outtmpl': vtt_path_template,
                'quiet': True,
            }
            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.source, download=True)
                    video_id = info['id']
                    # yt-dlp saves as subs_VIDEOID.en.vtt or similar
                    # We need to find the exact file
                    expected_prefix = f"subs_{video_id}"
                    for f in os.listdir(self.output_dir):
                        if f.startswith(expected_prefix) and f.endswith('.vtt'):
                            full_path = os.path.join(self.output_dir, f)
                            self.log(f"Subtitles downloaded to: {full_path}")
                            return 'text', full_path
            except Exception as e:
                self.log(f"Failed to download subs: {e}")

            self.log("Could not verify downloaded VTT file. Switching to audio fallback.")

        # Fallback: Audio
        self.log("Downloading audio track for analysis (Audio-only)...")
        audio_path_template = os.path.join(self.output_dir, 'audio_%(id)s.%(ext)s')
        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'outtmpl': audio_path_template,
            'quiet': True,
        }
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.source, download=True)
                path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(path) and os.path.getsize(path) > 1024: # Check if > 1KB
                    self.log(f"Audio downloaded to: {path}")
                    return 'audio', path
                self.log("Audio file seems invalid or missing.")
        except Exception as e:
            self.log(f"Audio download failed: {e}")

        # Fallback to visual
        self.log("Switching to visual analysis (downloading video)...")
        video_path_template = os.path.join(self.output_dir, 'video_%(id)s.%(ext)s')
        ydl_opts_video = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'outtmpl': video_path_template,
            'quiet': True,
        }
        if self.ffmpeg_path:
             ydl_opts_video['ffmpeg_location'] = self.ffmpeg_path
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                 info = ydl.extract_info(self.source, download=True)
                 path = ydl.prepare_filename(info)
                 self.log(f"Video downloaded for visual analysis: {path}")
                 self.is_local = True
                 self.source = path
                 return 'visuals', path
        except Exception as e:
            raise Exception(f"Failed to download video for visual analysis: {e}")

    def _get_local_context(self):
        self.log(f"Inspecting local file: {self.source}")
        base, _ = os.path.splitext(self.source)
        
        # Check sidecar files
        if os.path.exists(base + '.srt'):
            self.log(f"Found sidecar SRT: {base}.srt")
            return 'text', base + '.srt'
        if os.path.exists(base + '.vtt'):
            self.log(f"Found sidecar VTT: {base}.vtt")
            return 'text', base + '.vtt'
            
        self.log("No sidecar subtitles. Extracting audio from video...")
        audio_path = os.path.join(self.output_dir, "local_audio.mp3")
        
        cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
        cmd = [
            cmd_exe, '-y', '-i', self.source,
            '-vn', '-acodec', 'libmp3lame', '-q:a', '2', 
            audio_path
        ]
        self.log(f"Executing FFmpeg: {' '.join(cmd)}")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(audio_path):
             self.log(f"Audio extracted to: {audio_path}")
             return 'audio', audio_path
        else:
             self.log("Failed to extract audio. Falling back to visual analysis.")
             return 'visuals', self.source

    def _analyze_content(self, context_type, context_path):
        if context_type == 'visuals':
            return self._analyze_visuals(context_path)

        chunks = []
        if context_type == 'text':
            self.log("Chunking subtitle text...")
            chunks = self._chunk_text_vtt(context_path)
        else:
            self.log("Chunking audio file...")
            chunks = self._chunk_audio(context_path)
        
        self.log(f"Prepared {len(chunks)} chunks for analysis.")

        all_moments = []
        for i, chunk_data in enumerate(chunks):
            self.log(f"Analyzing chunk {i+1}/{len(chunks)} with OpenAI...")
            
            response_text = ""
            try:
                if context_type == 'text':
                    prompt = VIRAL_MOMENTS_PROMPT + "\n\nTRANSCRIPT:\n" + chunk_data['content']
                    response_text = self._call_ai_text(prompt)
                else:
                    # Audio analysis
                    self.log(f"Reading audio chunk {i+1} ({os.path.getsize(chunk_data['path'])/1024/1024:.2f} MB)...")
                    response_text = self._call_ai_with_audio(VIRAL_MOMENTS_PROMPT, chunk_data['path'])
                    
                    # Cleanup
                    if os.path.exists(chunk_data['path']):
                        os.remove(chunk_data['path'])

                self.log(f"OpenAI Response received for chunk {i+1}.")
                # Parse JSON
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                     response_text = response_text.split("```")[1].split("```")[0]
                
                data = json.loads(response_text.strip())
                self.log(f"Parsed {len(data)} moments from chunk {i+1}.")
                
                # Offset timestamps
                chunk_start_sec = chunk_data['start_sec']
                for item in data:
                    try:
                        s_min, s_sec = map(int, item['start_time'].split(':'))
                        e_min, e_sec = map(int, item['end_time'].split(':'))
                    except ValueError:
                         self.log(f"Invalid timestamp format in response: {item}")
                         continue
                    
                    rel_start = s_min * 60 + s_sec
                    rel_end = e_min * 60 + e_sec
                    
                    if context_type == 'audio':
                        item['abs_start'] = chunk_start_sec + rel_start
                        item['abs_end'] = chunk_start_sec + rel_end
                    else:
                        # VTT timestamps usually absolute
                        item['abs_start'] = rel_start
                        item['abs_end'] = rel_end
                        
                    all_moments.append(item)

            except Exception as e:
                self.log(f"Error analyzing chunk {i}: {e}")

        self.log(f"Total raw moments identified: {len(all_moments)}")
        return self._deduplicate(all_moments)

    def _analyze_visuals(self, video_path):
        self.log("Starting visual analysis...")
        duration = self._get_duration(video_path)
        self.log(f"Video duration: {timedelta(seconds=duration)}")
        
        num_parts = 10
        interval = duration / num_parts
        frames = []
        
        self.log(f"Extracting {num_parts} frames for visual analysis...")
        cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
        
        for i in range(num_parts):
            t = (i * interval) + (interval / 2)
            frame_path = os.path.join(self.output_dir, f"frame_{i}.jpg")
            
            cmd = [
                cmd_exe, '-y',
                '-ss', str(t),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                frame_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(frame_path):
                frames.append({'path': frame_path, 'time': t})
            else:
                self.log(f"Failed to extract frame at {t}s")

        self.log(f"Extracted {len(frames)} frames. Preparing for OpenAI...")
        
        # Collect frame paths for AI call
        frame_paths = [f['path'] for f in frames]
        
        try:
            self.log(f"Sending prompt to OpenAI...")
            response_text = self._call_ai_with_images(VISUAL_MOMENTS_PROMPT, frame_paths)
            self.log(f"OpenAI response received.")
            
            # Cleanup local frames
            for f in frames:
                if os.path.exists(f['path']):
                    os.remove(f['path'])

            # Parse JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                 response_text = response_text.split("```")[1].split("```")[0]
            
            try:
                data = json.loads(response_text.strip())
            except json.JSONDecodeError:
                self.log("JSON Decode Error in visual analysis response.")
                return []

            self.log(f"Parsed {len(data)} moments from visual analysis.")
            
            final_moments = []
            for item in data:
                try:
                    s_min, s_sec = map(int, item['start_time'].split(':'))
                    e_min, e_sec = map(int, item['end_time'].split(':'))
                    
                    abs_start = s_min * 60 + s_sec
                    abs_end = e_min * 60 + e_sec
                    
                    if abs_start >= abs_end:
                         continue

                    item['abs_start'] = abs_start
                    item['abs_end'] = abs_end
                    final_moments.append(item)
                except Exception as e:
                    self.log(f"Error parsing timestamp {item}: {e}")

            return self._deduplicate(final_moments)
            
        except Exception as e:
            self.log(f"Error in visual analysis: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _chunk_audio(self, audio_path):
        duration = self._get_duration(audio_path)
        self.log(f"Audio duration: {timedelta(seconds=duration)}")
        
        chunk_size = 30 * 60
        overlap = 10 * 60
        step = chunk_size - overlap
        
        chunks = []
        start = 0
        while start < duration:
            end = min(start + chunk_size, duration)
            
            chunk_file = f"{audio_path}_chunk_{start}.mp3"
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd = [
                cmd_exe, '-y', '-i', audio_path,
                '-ss', str(start), '-to', str(end),
                '-c', 'copy', chunk_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            chunks.append({
                'path': chunk_file,
                'start_sec': start,
                'end_sec': end
            })
            
            if end == duration:
                break
            start += step
            
        return chunks

    def _chunk_text_vtt(self, vtt_path):
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [{'content': "".join(lines), 'start_sec': 0, 'end_sec': 99999}]

    def _process_clips(self, segments):
        processed = []
        
        # Process videos with integrated caption generation (max 2 workers to avoid OpenCV conflicts)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as video_executor:
            # Submit all video processing tasks
            future_to_seg = {
                video_executor.submit(self._process_single_clip, i, seg): seg 
                for i, seg in enumerate(segments)
            }
            
            for future in concurrent.futures.as_completed(future_to_seg):
                try:
                    result = future.result()
                    if result:
                        processed.append(result)
                except Exception as e:
                    self.log(f"Error processing clip: {e}")
        
        # Sort by virality score
        processed.sort(key=lambda x: x.get('score', 0), reverse=True)
        return processed

    def _process_single_clip(self, i, seg):
        start = seg['abs_start']
        end = seg['abs_end']
        duration = end - start
        
        self.log(f"Processing Clip {i+1}: {seg.get('title', 'Unknown')}")
        self.log(f"  Range: {timedelta(seconds=start)} - {timedelta(seconds=end)} (Duration: {duration}s)")
        
        # Emit initial progress
        self.clipProgress.emit(i, 0, "Starting...")
        
        # Use StorageManager for file paths
        filename = f"short_{int(time.time())}_{i}.mp4"
        out_path = self.storage.get_new_path(filename)
        thumb_path = self.storage.get_new_path(f"thumb_{i}.jpg")
        temp_raw_path = self.storage.get_new_path(f"temp_raw_{i}.mp4")
        temp_cropped_path = self.storage.get_new_path(f"temp_cropped_{i}.mp4")
        
        cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'

        # 1. Get Raw Clip
        try:
            if self.is_local:
                self.log(f"  Clip {i+1}: Extracting raw from local...")
                self.clipProgress.emit(i, 10, "Extracting clip...")
                cmd = [
                    cmd_exe, '-y',
                    '-ss', str(start),
                    '-t', str(duration),
                    '-i', self.source,
                    '-c:v', 'libx264', '-c:a', 'aac', # Re-encode to ensure keyframes at cut
                    temp_raw_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.log(f"  Clip {i+1}: Downloading raw from YouTube...")
                self.clipProgress.emit(i, 10, "Downloading clip...")
                # Download Range
                if start >= end:
                    return None
                
                ydl_opts_dl = {
                    'download_ranges': lambda _, __: [{'start_time': start, 'end_time': end}],
                    'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
                    'outtmpl': temp_raw_path,
                    'quiet': True,
                    'force_keyframes_at_cuts': True,
                }
                if self.ffmpeg_path:
                    ydl_opts_dl['ffmpeg_location'] = self.ffmpeg_path
                
                with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                    ydl.download([self.source])
            
            if not os.path.exists(temp_raw_path):
                self.log(f"  Clip {i+1}: Failed to acquire raw clip.")
                self.clipProgress.emit(i, 0, "Failed")
                return None
            
            self.clipProgress.emit(i, 25, "Clip downloaded")
            
            # Start caption generation in parallel (using downloaded clip)
            caption_future = None
            if self.enable_captions:
                with self.caption_semaphore:
                    self.log(f"  Clip {i+1}: Starting caption generation in background...")
                    caption_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    caption_future = caption_executor.submit(
                        self._generate_captions_from_clip,
                        i,
                        temp_raw_path,
                        start,
                        end
                    )

            # 2. Face Tracking & Cropping
            self.log(f"  Clip {i+1}: Running Face Tracking...")
            self.clipProgress.emit(i, 30, "Processing frames...")
            
            cap = cv2.VideoCapture(temp_raw_path)
            if not cap.isOpened():
                raise Exception("Failed to open raw clip for processing.")
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Validate dimensions
            if width <= 0 or height <= 0 or fps <= 0:
                cap.release()
                raise Exception(f"Invalid video properties: {width}x{height} @ {fps}fps")
            
            # Target dimensions (9:16) - Cap at 1080p
            target_w = 1080
            target_h = 1920
            
            # If source is smaller, we'll upscale. If larger, we'll downscale.
            self.log(f"  Clip {i+1}: Target output resolution: {target_w}x{target_h}")
            
            # Ensure target dimensions are valid
            if target_w <= 0 or target_h <= 0:
                cap.release()
                raise Exception(f"Invalid target dimensions: {target_w}x{target_h}")
            
            self.log(f"  Clip {i+1}: Processing frames to {target_w}x{target_h} @ {fps}fps (preserving original frame rate)")
            
            # Create frames directory
            frames_dir = os.path.join(self.output_dir, f"frames_{i}")
            os.makedirs(frames_dir, exist_ok=True)
            
            tracker = FaceTracker()
            frame_count = 0
            
            self.log(f"  Clip {i+1}: Processing all frames at original FPS: {fps}")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Apply face tracking and cropping
                try:
                    cropped = tracker.process_frame(frame)
                except Exception as e:
                    self.log(f"  Clip {i+1}: Frame {frame_count} tracking error: {e}")
                    frame_count += 1
                    continue
                
                # Validate cropped frame
                if cropped is None or cropped.size == 0:
                    self.log(f"  Clip {i+1}: Warning - empty frame at {frame_count}, skipping")
                    frame_count += 1
                    continue
                
                # Resize if necessary
                if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
                    cropped = cv2.resize(cropped, (target_w, target_h))
                
                # Save frame as image
                frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                cv2.imwrite(frame_path, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                frame_count += 1
                
                # Update progress every 30 frames (30-70% range for frame processing)
                if frame_count % 30 == 0:
                    self.log(f"  Clip {i+1}: Processed {frame_count} frames...")
                    if total_frames > 0:
                        progress = 30 + int((frame_count / total_frames) * 40)
                        self.clipProgress.emit(i, progress, f"Frame {frame_count}/{total_frames}")
            
            cap.release()
            tracker.release()
            
            self.log(f"  Clip {i+1}: Processed {frame_count} frames total at original frame rate")
            self.clipProgress.emit(i, 70, "Frames processed")
            
            if frame_count == 0:
                raise Exception("No frames were processed")
            
            # 3. Use FFmpeg to create video from frames at original fps
            self.log(f"  Clip {i+1}: Creating video from frames with FFmpeg at {fps}fps (original frame rate)...")
            self.clipProgress.emit(i, 75, "Encoding video...")
            temp_cropped_video = temp_cropped_path.replace('.mp4', '_video.mp4')
            
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd_frames = [
                cmd_exe, '-y',
                '-framerate', str(fps),  # Use original fps
                '-i', os.path.join(frames_dir, 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '20',  # High quality (was 23)
                '-preset', 'slow',  # Better compression (was medium)
                temp_cropped_video
            ]
            
            result = subprocess.run(cmd_frames, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.log(f"  Clip {i+1}: FFmpeg error: {result.stderr}")
                raise Exception("FFmpeg failed to create video from frames")
            
            # Cleanup frames directory
            import shutil
            shutil.rmtree(frames_dir, ignore_errors=True)
            
            if not os.path.exists(temp_cropped_video):
                raise Exception("Failed to create cropped video.")
            
            self.clipProgress.emit(i, 85, "Video encoded")

            # 4. Merge Audio and Finalize
            self.log(f"  Clip {i+1}: Merging audio and finalizing...")
            self.clipProgress.emit(i, 90, "Merging audio...")
            
            temp_final_no_subs = self.storage.get_new_path(f"temp_final_no_subs_{i}.mp4")
            
            cmd_merge = [
                cmd_exe, '-y',
                '-i', temp_cropped_video,
                '-i', temp_raw_path,
                '-c:v', 'copy',  # Copy video stream (already encoded)
                '-c:a', 'aac', '-b:a', '192k',  # High quality audio
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest',  # Use shortest stream
                '-movflags', '+faststart',  # Optimize for web streaming
                temp_final_no_subs
            ]
            subprocess.run(cmd_merge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(temp_final_no_subs):
                raise Exception("Failed to merge audio and video.")
            
            # 5. Wait for and burn captions (if enabled)
            if self.enable_captions and caption_future:
                self.log(f"  Clip {i+1}: Waiting for captions to be ready...")
                self.clipProgress.emit(i, 92, "Waiting for captions...")
                
                try:
                    # Wait for caption generation to complete (with timeout)
                    subtitle_path = caption_future.result(timeout=60)
                    caption_executor.shutdown(wait=False)
                    
                    if subtitle_path and os.path.exists(subtitle_path):
                        self.log(f"  Clip {i+1}: Burning captions...")
                        self.clipProgress.emit(i, 94, "Burning captions...")
                        
                        if self._burn_subtitles(temp_final_no_subs, subtitle_path, out_path):
                            self.log(f"  Clip {i+1}: Captions burned successfully")
                            # Cleanup temp file
                            if os.path.exists(temp_final_no_subs):
                                os.remove(temp_final_no_subs)
                        else:
                            self.log(f"  Clip {i+1}: Failed to burn captions, using video without captions")
                            self._apply_watermark(temp_final_no_subs, out_path)
                    else:
                        self.log(f"  Clip {i+1}: No captions generated, using video without captions")
                        self._apply_watermark(temp_final_no_subs, out_path)
                except concurrent.futures.TimeoutError:
                    self.log(f"  Clip {i+1}: Caption generation timed out, using video without captions")
                    self._apply_watermark(temp_final_no_subs, out_path)
                except Exception as e:
                    self.log(f"  Clip {i+1}: Caption error: {e}, using video without captions")
                    self._apply_watermark(temp_final_no_subs, out_path)
            else:
                # Captions disabled or no future, apply watermark only
                if not self.enable_captions:
                    self.log(f"  Clip {i+1}: Captions disabled")
                self._apply_watermark(temp_final_no_subs, out_path)
            
            # Cleanup Temps
            if os.path.exists(temp_raw_path):
                os.remove(temp_raw_path)
            if os.path.exists(temp_cropped_video):
                os.remove(temp_cropped_video)
            if os.path.exists(temp_cropped_path):
                os.remove(temp_cropped_path)

            if os.path.exists(out_path):
                self.log(f"  Clip {i+1}: Generating thumbnail...")
                self.clipProgress.emit(i, 95, "Creating thumbnail...")
                cmd_thumb = [
                    cmd_exe, '-y',
                    '-i', out_path,
                    '-ss', str(duration/2),
                    '-vframes', '1',
                    '-q:v', '2',
                    thumb_path
                ]
                subprocess.run(cmd_thumb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.clipProgress.emit(i, 100, "Complete!")
                
                result = {
                    'path': out_path,
                    'thumb': thumb_path,
                    'score': seg.get('virality_score', 0),
                    'title': seg.get('title', 'Viral Clip'),
                    'reason': seg.get('reason', '')
                }
                
                # Emit individual clip completion immediately
                self.clipComplete.emit(i, result)
                
                return result
            else:
                 self.log(f"  Clip {i+1}: Output file missing.")
                 self.clipProgress.emit(i, 0, "Failed")
                 return None

        except Exception as e:
            self.log(f"  Clip {i+1} Failed: {e}")
            self.clipProgress.emit(i, 0, "Failed")
            import traceback
            self.log(traceback.format_exc())
            return None

    def _get_duration(self, video_path):
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd = [cmd_exe, '-i', video_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                h, m, s = map(float, match.groups())
                return h * 3600 + m * 60 + s
            return 0.0
        except Exception as e:
            self.log(f"Error getting duration: {e}")
            return 0.0

    def _deduplicate(self, moments):
        self.log(f"Deduplicating {len(moments)} moments...")
        moments.sort(key=lambda x: x.get('virality_score', 0), reverse=True)
        final_moments = []
        for m in moments:
            is_overlap = False
            for existing in final_moments:
                start1, end1 = m['abs_start'], m['abs_end']
                start2, end2 = existing['abs_start'], existing['abs_end']
                if max(start1, start2) < min(end1, end2):
                    is_overlap = True
                    break
            if not is_overlap:
                final_moments.append(m)
                if len(final_moments) >= 10: 
                    break
        self.log(f"Retained {len(final_moments)} unique moments.")
        return final_moments
    
    def _cleanup_temp_files(self):
        """
        Clean up all temporary files except final outputs.
        Keeps only the generated videos and thumbnails.
        """
        try:
            self.log("Starting temp file cleanup...")
            
            # Get list of all files in temp directory
            if not os.path.exists(self.output_dir):
                return
            
            files_to_keep = set()
            
            # Collect final output files to keep (videos and thumbnails)
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                # Keep files that start with 'short_' or 'thumb_' (final outputs)
                if filename.startswith('short_') or filename.startswith('thumb_'):
                    files_to_keep.add(filepath)
            
            # Delete everything else
            deleted_count = 0
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                
                if filepath not in files_to_keep:
                    try:
                        if os.path.isfile(filepath):
                            os.remove(filepath)
                            deleted_count += 1
                        elif os.path.isdir(filepath):
                            shutil.rmtree(filepath)
                            deleted_count += 1
                    except Exception as e:
                        self.log(f"Failed to delete {filename}: {e}")
            
            self.log(f"Cleanup complete: Removed {deleted_count} temporary files/folders")
            
        except Exception as e:
            self.log(f"Cleanup error: {e}")
    
    def _generate_captions_from_clip(self, clip_index, clip_video_path, start_time, end_time):
        """
        Generate Hormozi-style karaoke captions from the downloaded clip.
        Uses Whisper-1 for word-level timestamps, then generates .ass with karaoke \k tags.
        Returns path to .ass file or None if failed.
        """
        try:
            self.log(f"  [Caption] Clip {clip_index+1}: Extracting audio from downloaded clip...")
            
            # Extract audio from the downloaded clip
            audio_path = self.storage.get_new_path(f"clip_audio_{clip_index}.mp3")
            
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd = [
                cmd_exe, '-y',
                '-i', clip_video_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',
                '-q:a', '2',
                audio_path
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1024:
                self.log(f"  [Caption] Clip {clip_index+1}: Failed to extract audio")
                return None
            
            self.log(f"  [Caption] Clip {clip_index+1}: Sending audio to Whisper-1 for word-level transcription...")
            
            # Call Whisper-1 with word-level timestamps
            with open(audio_path, 'rb') as f:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            # Cleanup temp audio
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Extract words with timestamps
            words = transcription.words if hasattr(transcription, 'words') and transcription.words else []
            
            if not words:
                self.log(f"  [Caption] Clip {clip_index+1}: No words returned from Whisper")
                return None
            
            self.log(f"  [Caption] Clip {clip_index+1}: Whisper returned {len(words)} words with timestamps")
            
            # Generate Hormozi-style karaoke ASS file
            ass_path = self.storage.get_new_path(f"captions_{clip_index}.ass")
            ass_content = self._generate_karaoke_ass(words)
            
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            self.log(f"  [Caption] Clip {clip_index+1}: Karaoke ASS captions saved to {ass_path}")
            return ass_path
            
        except Exception as e:
            self.log(f"  [Caption] Clip {clip_index+1}: Caption generation failed: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None
    
    def _generate_karaoke_ass(self, words):
        """
        Generate ASS file with Hormozi-style karaoke word-by-word highlighting.
        Uses \\k tags for word-by-word color fill effect.
        Words appear white, then fill to yellow as they are spoken.
        """
        ass_lines = [
            "[Script Info]",
            "Title: Hormozi Style Karaoke Captions",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # PrimaryColour = white (before spoken), SecondaryColour = yellow (fill color for \\k)
            # OutlineColour = black, thick outline (4px), no shadow, bold, centered bottom
            "Style: Main,Arial Black,68,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1.5,2,50,50,120,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]
        
        # Group words into phrases (4-7 words or ~30 chars, break on long pauses)
        phrases = []
        current_phrase = []
        
        for i, w in enumerate(words):
            word_text = w.word.strip() if hasattr(w, 'word') else w.get('word', '').strip()
            word_start = w.start if hasattr(w, 'start') else w.get('start', 0)
            word_end = w.end if hasattr(w, 'end') else w.get('end', 0)
            
            if not word_text:
                continue
            
            current_phrase.append({
                'word': word_text,
                'start': word_start,
                'end': word_end
            })
            
            # Check if we should break the phrase
            total_chars = sum(len(p['word']) for p in current_phrase)
            next_word_start = None
            if i + 1 < len(words):
                next_w = words[i + 1]
                next_word_start = next_w.start if hasattr(next_w, 'start') else next_w.get('start', 0)
            
            should_break = (
                len(current_phrase) >= 6 or
                total_chars > 30 or
                (next_word_start is not None and next_word_start - word_end > 0.5) or  # Long pause
                i == len(words) - 1  # Last word
            )
            
            if should_break and current_phrase:
                phrases.append(current_phrase)
                current_phrase = []
        
        # Generate dialogue lines with karaoke tags
        for phrase in phrases:
            if not phrase:
                continue
            
            phrase_start = phrase[0]['start']
            phrase_end = phrase[-1]['end'] + 0.3  # Small grace period
            
            start_str = self._seconds_to_ass_time(phrase_start)
            end_str = self._seconds_to_ass_time(phrase_end)
            
            # Build karaoke text with \k tags (centiseconds)
            karaoke_parts = []
            for pw in phrase:
                # Duration in centiseconds for the \k tag
                duration_cs = max(1, round((pw['end'] - pw['start']) * 100))
                # \kf = smooth fill from left to right (most Hormozi-like)
                karaoke_parts.append(f"{{\\kf{duration_cs}}}{pw['word']} ")
            
            text_line = "".join(karaoke_parts).rstrip()
            
            ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Main,,0,0,0,,{text_line}")
        
        return "\n".join(ass_lines)
    
    def _seconds_to_ass_time(self, s):
        """Convert seconds to ASS timestamp format (H:MM:SS.cc)."""
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = s % 60
        cs = int((sec % 1) * 100)
        sec = int(sec)
        return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

    def _generate_captions_for_clip(self, clip_index, start_time, end_time, context_type, context_path):
        """
        Generate SRT captions for a specific clip segment.
        Returns path to .srt file or None if failed.
        """
        try:
            self.log(f"  Clip {clip_index+1}: Generating captions...")
            
            if context_type == 'text':
                # Extract VTT segment for this time range
                caption_content = self._extract_vtt_segment(context_path, start_time, end_time)
                if not caption_content:
                    self.log(f"  Clip {clip_index+1}: No VTT content found for time range")
                    return None
                
                # Send to AI for SRT conversion
                prompt = CAPTION_GENERATION_PROMPT + f"\n\nVTT CONTENT:\n{caption_content}"
                srt_content = self._call_ai_text(prompt)
                self.log(f"  Clip {clip_index+1}: {self.ai_provider} returned captions (length: {len(srt_content)} chars)")
                self.log(f"  Clip {clip_index+1}: Caption preview:\n{srt_content[:500]}...")
                
            elif context_type == 'audio':
                # Extract audio segment for this time range
                audio_segment_path = self._extract_audio_segment(context_path, start_time, end_time, clip_index)
                if not audio_segment_path or not os.path.exists(audio_segment_path):
                    self.log(f"  Clip {clip_index+1}: Failed to extract audio segment")
                    return None
                
                # Send audio to AI for transcription
                srt_content = self._call_ai_with_audio(CAPTION_GENERATION_PROMPT, audio_segment_path)
                self.log(f"  Clip {clip_index+1}: {self.ai_provider} returned captions (length: {len(srt_content)} chars)")
                self.log(f"  Clip {clip_index+1}: Caption preview:\n{srt_content[:500]}...")
                
                # Cleanup temp audio
                if os.path.exists(audio_segment_path):
                    os.remove(audio_segment_path)
            
            elif context_type == 'visuals':
                # No captions for visual-only analysis
                self.log(f"  Clip {clip_index+1}: Skipping captions (visual-only source)")
                return None
            else:
                return None
            
            # Clean up response (remove markdown if present)
            if "```srt" in srt_content:
                srt_content = srt_content.split("```srt")[1].split("```")[0].strip()
            elif "```" in srt_content:
                srt_content = srt_content.split("```")[1].split("```")[0].strip()
            
            # Validate SRT format
            if not self._validate_srt(srt_content):
                self.log(f"  Clip {clip_index+1}: Invalid SRT format received from {self.ai_provider}")
                return None
            
            # CRITICAL: Offset timestamps to be relative to 00:00:00
            self.log(f"  Clip {clip_index+1}: Offsetting timestamps by -{start_time}s")
            srt_content = self._offset_srt_timestamps(srt_content, start_time)
            
            # Save SRT file
            srt_path = self.storage.get_new_path(f"captions_{clip_index}.srt")
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            self.log(f"  Clip {clip_index+1}: Captions saved to {srt_path}")
            return srt_path
            
        except Exception as e:
            self.log(f"  Clip {clip_index+1}: Caption generation failed: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None
    
    def _extract_vtt_segment(self, vtt_path, start_time, end_time):
        """Extract VTT content for a specific time range."""
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple extraction - get all content between start and end times
            # VTT format: HH:MM:SS.mmm --> HH:MM:SS.mmm
            lines = content.split('\n')
            segment_lines = []
            in_range = False
            
            for line in lines:
                # Check if line contains timestamp
                if '-->' in line:
                    # Parse timestamp
                    try:
                        time_parts = line.split('-->')[0].strip()
                        # Convert to seconds for comparison
                        time_sec = self._vtt_time_to_seconds(time_parts)
                        
                        if start_time <= time_sec <= end_time:
                            in_range = True
                            segment_lines.append(line)
                        elif time_sec > end_time:
                            in_range = False
                            break
                    except:
                        continue
                elif in_range and line.strip():
                    segment_lines.append(line)
            
            return '\n'.join(segment_lines)
            
        except Exception as e:
            self.log(f"Error extracting VTT segment: {e}")
            return ""
    
    def _vtt_time_to_seconds(self, time_str):
        """Convert VTT timestamp to seconds."""
        # Format: HH:MM:SS.mmm or MM:SS.mmm
        parts = time_str.strip().replace(',', '.').split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return 0
    
    def _extract_audio_segment(self, audio_path, start_time, end_time, clip_index):
        """Extract audio segment for a specific time range."""
        try:
            duration = end_time - start_time
            segment_path = self.storage.get_new_path(f"audio_segment_{clip_index}.mp3")
            
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd = [
                cmd_exe, '-y',
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',
                segment_path
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(segment_path) and os.path.getsize(segment_path) > 1024:
                return segment_path
            return None
            
        except Exception as e:
            self.log(f"Error extracting audio segment: {e}")
            return None
    
    def _validate_srt(self, srt_content):
        """Basic validation of SRT format."""
        if not srt_content or len(srt_content) < 10:
            return False
        
        # Check for basic SRT structure
        lines = srt_content.strip().split('\n')
        
        # Should have at least: number, timestamp, text, blank line
        if len(lines) < 4:
            return False
        
        # Check if first line is a number
        try:
            int(lines[0].strip())
        except:
            return False
        
        # Check if second line has timestamp arrow
        if '-->' not in lines[1]:
            return False
        
        return True
    
    def _offset_srt_timestamps(self, srt_content, offset_seconds):
        """
        Offset all SRT timestamps by subtracting offset_seconds.
        This makes timestamps relative to 00:00:00 for extracted clips.
        """
        import re
        
        def srt_time_to_seconds(time_str):
            """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
            time_str = time_str.strip()
            h, m, rest = time_str.split(':')
            s, ms = rest.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
        
        def seconds_to_srt_time(seconds):
            """Convert seconds to SRT timestamp (HH:MM:SS,mmm)."""
            if seconds < 0:
                seconds = 0
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
        lines = srt_content.split('\n')
        result_lines = []
        
        for line in lines:
            if '-->' in line:
                # Parse timestamp line
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
                if match:
                    start_str, end_str = match.groups()
                    
                    # Convert to seconds, subtract offset, convert back
                    start_sec = srt_time_to_seconds(start_str) - offset_seconds
                    end_sec = srt_time_to_seconds(end_str) - offset_seconds
                    
                    # Skip captions that would be before 00:00:00
                    if end_sec <= 0:
                        continue
                    
                    new_line = f"{seconds_to_srt_time(start_sec)} --> {seconds_to_srt_time(end_sec)}"
                    result_lines.append(new_line)
                else:
                    result_lines.append(line)
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _convert_srt_to_ass(self, srt_path):
        """
        Convert SRT to ASS format with Hormozi-style thick outlines and bold font.
        Returns path to .ass file or None if failed.
        """
        try:
            ass_path = srt_path.replace('.srt', '.ass')
            
            # Read SRT content
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # Parse SRT
            srt_blocks = self._parse_srt(srt_content)
            if not srt_blocks:
                self.log("Failed to parse SRT content")
                return None
            
            # Generate ASS content
            ass_content = self._generate_ass_content(srt_blocks)
            
            # Write ASS file
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            self.log(f"Converted SRT to ASS: {ass_path}")
            return ass_path
            
        except Exception as e:
            self.log(f"Error converting SRT to ASS: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None
    
    def _parse_srt(self, srt_content):
        """Parse SRT content into structured blocks."""
        import re
        
        blocks = []
        lines = srt_content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Read sequence number
            try:
                seq_num = int(lines[i].strip())
            except ValueError:
                i += 1
                continue
            
            i += 1
            if i >= len(lines):
                break
            
            # Read timestamp
            timestamp_line = lines[i].strip()
            if '-->' not in timestamp_line:
                i += 1
                continue
            
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
            if not match:
                i += 1
                continue
            
            start_time, end_time = match.groups()
            i += 1
            
            # Read text (can be multiple lines)
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            
            text = ' '.join(text_lines)
            
            blocks.append({
                'seq': seq_num,
                'start': start_time,
                'end': end_time,
                'text': text
            })
        
        return blocks
    
    def _generate_ass_content(self, srt_blocks):
        """Generate ASS file content with Hormozi-style formatting."""
        
        # ASS Header with Hormozi-style settings
        ass_header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,70,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,50,50,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Convert SRT blocks to ASS dialogue lines
        dialogue_lines = []
        for block in srt_blocks:
            start_ass = self._srt_time_to_ass_time(block['start'])
            end_ass = self._srt_time_to_ass_time(block['end'])
            text = block['text'].replace('\n', '\\N')
            
            dialogue_line = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}"
            dialogue_lines.append(dialogue_line)
        
        return ass_header + '\n'.join(dialogue_lines)
    
    def _srt_time_to_ass_time(self, srt_time):
        """Convert SRT timestamp (HH:MM:SS,mmm) to ASS timestamp (H:MM:SS.cc)."""
        # SRT: 00:00:01,500
        # ASS: 0:00:01.50
        parts = srt_time.replace(',', '.').split(':')
        h = int(parts[0])
        m = parts[1]
        s_ms = parts[2].split('.')
        s = s_ms[0]
        ms = s_ms[1] if len(s_ms) > 1 else '000'
        cs = ms[:2]  # centiseconds (first 2 digits of milliseconds)
        
        return f"{h}:{m}:{s}.{cs}"
    
    def _get_watermark_filter(self):
        """Return ffmpeg drawtext filter for a moving transparent watermark."""
        # Fast diagonal bounce: text drifts across the screen and bounces off edges
        # Speed: 150px/s horizontal, 90px/s vertical (5x speed)
        # Opacity: 60% white — clearly visible bold watermark
        # Using a literal newline character for multiline support
        watermark = (
            "drawtext=text='made with\n"
            "Mirage.company'"
            ":fontsize=80"
            ":fontcolor=white@0.60"
            ":font='Arial Black'"
            ":line_spacing=15"
            ":x='abs(mod(t*150\\,2*(w-tw))-(w-tw))'"
            ":y='abs(mod(t*90\\,2*(h-th))-(h-th))'"
        )
        return watermark
    
    def _apply_watermark(self, input_path, output_path):
        """Apply only the moving watermark to a video (no subtitles)."""
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            watermark_filter = self._get_watermark_filter()
            
            cmd = [
                cmd_exe, '-y',
                '-i', input_path,
                '-vf', watermark_filter,
                '-c:a', 'copy',
                output_path
            ]
            
            self.log(f"  Applying watermark...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                self.log(f"  Watermark failed: {result.stderr}")
                # Fallback: just move the file without watermark
                if os.path.exists(input_path):
                    shutil.move(input_path, output_path)
            else:
                # Cleanup input file
                if os.path.exists(input_path) and os.path.exists(output_path):
                    os.remove(input_path)
                    
        except Exception as e:
            self.log(f"  Watermark error: {e}, using video without watermark")
            if os.path.exists(input_path) and not os.path.exists(output_path):
                shutil.move(input_path, output_path)

    def _burn_subtitles(self, video_path, subtitle_path, output_path):
        """Burn subtitles + watermark into video. Handles both .ass and .srt files."""
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            watermark_filter = self._get_watermark_filter()
            
            # Determine subtitle type based on extension
            is_ass = subtitle_path.lower().endswith('.ass')
            
            if is_ass:
                # Burn ASS directly (karaoke style from Whisper pipeline)
                self.log(f"  Burning karaoke ASS subtitles + watermark with FFmpeg...")
                ass_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
                subtitle_filter = f"ass='{ass_path_escaped}'"
            else:
                # Convert SRT to ASS first (legacy path)
                self.log(f"  Converting SRT to ASS format...")
                ass_path = self._convert_srt_to_ass(subtitle_path)
                
                if ass_path and os.path.exists(ass_path):
                    self.log(f"  Burning ASS subtitles + watermark with FFmpeg...")
                    ass_path_escaped = ass_path.replace('\\', '/').replace(':', '\\:')
                    subtitle_filter = f"ass='{ass_path_escaped}'"
                else:
                    # Fallback: burn SRT directly with basic styling
                    self.log(f"  Failed to convert to ASS, burning SRT directly...")
                    srt_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
                    subtitle_filter = (
                        f"subtitles='{srt_path_escaped}':force_style='"
                        "FontName=Arial Black,FontSize=24,PrimaryColour=&H00FFFFFF,"
                        "OutlineColour=&H00000000,Outline=3,Bold=1,"
                        "Alignment=2,MarginV=80'"
                    )
            
            # Chain subtitle filter with watermark filter
            combined_filter = f"{subtitle_filter},{watermark_filter}"
            
            cmd = [
                cmd_exe, '-y',
                '-i', video_path,
                '-vf', combined_filter,
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                self.log(f"  FFmpeg subtitle error: {result.stderr}")
                
                # If ASS failed, try basic SRT fallback
                if is_ass or (not is_ass and 'ass=' in subtitle_filter):
                    self.log(f"  ASS burning failed, trying basic subtitle fallback...")
                    return self._burn_srt_fallback(video_path, subtitle_path, output_path)
                return False
            
            # Cleanup temporary ASS file if we converted from SRT
            if not is_ass and 'ass_path' in locals() and ass_path and os.path.exists(ass_path):
                os.remove(ass_path)
            
            return os.path.exists(output_path)
            
        except Exception as e:
            self.log(f"Error burning subtitles: {e}")
            return self._burn_srt_fallback(video_path, subtitle_path, output_path)
    
    def _burn_srt_fallback(self, video_path, subtitle_path, output_path):
        """Fallback to basic subtitle burning + watermark if ASS fails."""
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            watermark_filter = self._get_watermark_filter()
            
            # Escape path for FFmpeg filter
            path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
            
            if subtitle_path.lower().endswith('.ass'):
                subtitle_filter = f"ass='{path_escaped}'"
            else:
                subtitle_filter = (
                    f"subtitles='{path_escaped}':force_style='"
                    "FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,Outline=2,Bold=1,"
                    "Alignment=2,MarginV=40'"
                )
            
            # Chain subtitle filter with watermark
            combined_filter = f"{subtitle_filter},{watermark_filter}"
            
            cmd = [
                cmd_exe, '-y',
                '-i', video_path,
                '-vf', combined_filter,
                '-c:a', 'copy',
                output_path
            ]
            
            self.log(f"  Burning subtitles with FFmpeg (fallback)...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                self.log(f"  FFmpeg subtitle fallback error: {result.stderr}")
                return False
            
            return os.path.exists(output_path)
            
        except Exception as e:
            self.log(f"Error burning subtitles (fallback): {e}")
            return False
