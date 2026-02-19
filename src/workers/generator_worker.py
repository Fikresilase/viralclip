
import os
import json
import re
import time
import subprocess
import shutil
from datetime import timedelta
import concurrent.futures

import cv2
from google import genai
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp

from src.prompts import VIRAL_MOMENTS_PROMPT, VISUAL_MOMENTS_PROMPT
from src.core.face_tracker import FaceTracker
from src.utils.storage import StorageManager

class GeneratorWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, source: str, is_local: bool, api_key: str):
        super().__init__()
        self.source = source
        self.is_local = is_local
        self.api_key = api_key
        
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

    def run(self):
        try:
            self.log(f"Initialization started.")
            self.log(f"Source: {self.source}")
            self.log(f"Is Local: {self.is_local}")
            self.log(f"Output Directory: {self.output_dir}")
            self.log(f"FFmpeg Path detected: {self.ffmpeg_path or 'System PATH'}")

            if not self.api_key:
                raise Exception("Gemini API Key is missing.")

            self.log("Configuring Gemini AI...")
            self.client = genai.Client(api_key=self.api_key)
            self.log("Gemini AI configured successfully.")

            # 1. Get Context (Text or Audio)
            self.log("Step 1: Extracting Context (Subtitles or Audio)...")
            context_type, context_path = self._get_context()
            self.log(f"Context acquired: Type={context_type}, Path={context_path}")

            # 2. Analyze
            self.log("Step 2: Analyzing content for viral moments...")
            viral_segments = self._analyze_content(context_type, context_path)
            
            if not viral_segments:
                raise Exception("No viral moments found during analysis.")
            self.log(f"Found {len(viral_segments)} potential viral segments.")

            # 3. Download & Process Clips
            self.log(f"Step 3: Processing clips (Downloading/Cutting)...")
            results = self._process_clips(viral_segments)
            
            self.log(f"Generation finished. Emitting {len(results)} results.")
            self.finished.emit(results)

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
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
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
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
            self.log(f"Analyzing chunk {i+1}/{len(chunks)} with Gemini...")
            
            response_text = ""
            try:
                if context_type == 'text':
                    prompt = VIRAL_MOMENTS_PROMPT + "\n\nTRANSCRIPT:\n" + chunk_data['content']
                    response = self.client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=prompt
                    )
                    response_text = response.text
                else:
                    self.log(f"Uploading audio chunk {i+1} ({os.path.getsize(chunk_data['path'])/1024/1024:.2f} MB)...")
                    uploaded_file = self.client.files.upload(file_path=chunk_data['path'])
                    
                    self.log("Waiting for file processing...")
                    while uploaded_file.state == 'PROCESSING':
                        time.sleep(2)
                        uploaded_file = self.client.files.get(name=uploaded_file.name)
                    
                    self.log("Sending to Gemini...")
                    response = self.client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=[VIRAL_MOMENTS_PROMPT, uploaded_file]
                    )
                    response_text = response.text
                    
                    # Cleanup
                    if os.path.exists(chunk_data['path']):
                        os.remove(chunk_data['path'])

                self.log(f"Gemini Response received for chunk {i+1}.")
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

        self.log(f"Extracted {len(frames)} frames. Uploading to Gemini...")
        
        prompt_parts = [VISUAL_MOMENTS_PROMPT]
        uploaded_files = []
        
        try:
            for i, frame in enumerate(frames):
                self.log(f"Uploading frame {i+1}...")
                uploaded_file = self.client.files.upload(file_path=frame['path'])
                
                # Wait for processing
                while uploaded_file.state == 'PROCESSING':
                    time.sleep(1)
                    uploaded_file = self.client.files.get(name=uploaded_file.name)
                
                uploaded_files.append(uploaded_file)
                prompt_parts.append(f"Frame {i+1} (taken at {timedelta(seconds=frame['time'])})")
                prompt_parts.append(uploaded_file)
            
            self.log("Sending prompt to Gemini...")
            response = self.client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt_parts
            )
            response_text = response.text
            self.log("Gemini response received.")
            
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
            
            # Cleanup remote files
            for uploaded_file in uploaded_files:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except:
                    pass

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
        
        # Reduce parallelism to avoid OpenCV thread conflicts
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks
            future_to_seg = {
                executor.submit(self._process_single_clip, i, seg): seg 
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
                # Download Range
                if start >= end:
                    return None
                
                ydl_opts_dl = {
                    'download_ranges': lambda _, __: [{'start_time': start, 'end_time': end}],
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
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
                return None

            # 2. Face Tracking & Cropping
            self.log(f"  Clip {i+1}: Running Face Tracking...")
            
            cap = cv2.VideoCapture(temp_raw_path)
            if not cap.isOpened():
                raise Exception("Failed to open raw clip for processing.")
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Validate dimensions
            if width <= 0 or height <= 0 or fps <= 0:
                cap.release()
                raise Exception(f"Invalid video properties: {width}x{height} @ {fps}fps")
            
            # Target dimensions (9:16)
            target_h = height
            target_w = int(target_h * 9 / 16)
            
            # Ensure dimensions are even (required by H.264 encoder)
            target_w = target_w - (target_w % 2)
            target_h = target_h - (target_h % 2)
            
            # Ensure target dimensions are valid
            if target_w <= 0 or target_h <= 0:
                cap.release()
                raise Exception(f"Invalid target dimensions: {target_w}x{target_h}")
            
            self.log(f"  Clip {i+1}: Processing frames to {target_w}x{target_h} @ {fps}fps")
            
            # Create frames directory
            frames_dir = os.path.join(self.output_dir, f"frames_{i}")
            os.makedirs(frames_dir, exist_ok=True)
            
            tracker = FaceTracker()
            frame_count = 0
            
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
                if frame_count % 30 == 0:
                    self.log(f"  Clip {i+1}: Processed {frame_count} frames...")
            
            cap.release()
            tracker.release()
            
            self.log(f"  Clip {i+1}: Processed {frame_count} frames total")
            
            if frame_count == 0:
                raise Exception("No frames were processed")
            
            # 3. Use FFmpeg to create video from frames
            self.log(f"  Clip {i+1}: Creating video from frames with FFmpeg...")
            temp_cropped_video = temp_cropped_path.replace('.mp4', '_video.mp4')
            
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd_frames = [
                cmd_exe, '-y',
                '-framerate', str(fps),
                '-i', os.path.join(frames_dir, 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '23',
                '-preset', 'medium',
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

            # 4. Merge Audio and Finalize
            self.log(f"  Clip {i+1}: Merging audio and finalizing...")
            cmd_merge = [
                cmd_exe, '-y',
                '-i', temp_cropped_video,
                '-i', temp_raw_path,
                '-c:v', 'copy',  # Copy video stream (already encoded)
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest',
                out_path
            ]
            subprocess.run(cmd_merge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Cleanup Temps
            if os.path.exists(temp_raw_path):
                os.remove(temp_raw_path)
            if os.path.exists(temp_cropped_video):
                os.remove(temp_cropped_video)
            if os.path.exists(temp_cropped_path):
                os.remove(temp_cropped_path)

            if os.path.exists(out_path):
                self.log(f"  Clip {i+1}: Generating thumbnail...")
                cmd_thumb = [
                    cmd_exe, '-y',
                    '-i', out_path,
                    '-ss', str(duration/2),
                    '-vframes', '1',
                    '-q:v', '2',
                    thumb_path
                ]
                subprocess.run(cmd_thumb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                return {
                    'path': out_path,
                    'thumb': thumb_path,
                    'score': seg.get('virality_score', 0),
                    'title': seg.get('title', 'Viral Clip'),
                    'reason': seg.get('reason', '')
                }
            else:
                 self.log(f"  Clip {i+1}: Output file missing.")
                 return None

        except Exception as e:
            self.log(f"  Clip {i+1} Failed: {e}")
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
