import os
import re
import shutil
import subprocess
import yt_dlp
from datetime import timedelta

class MediaExtractor:
    def __init__(self, ffmpeg_path: str, output_dir: str, log_callback):
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = output_dir
        self.log = log_callback

    def get_duration(self, video_path):
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

    def get_context(self, source: str, is_local: bool):
        """
        Determines and retrieves the best context source (Subs > Audio > Visuals).
        Returns (context_type, context_path, is_supported_whisper_lang).
        """
        if is_local:
            return self._get_local_context(source)
        else:
            return self._get_youtube_context(source)

    def _get_youtube_context(self, source: str):
        self.log("Checking YouTube for existing captions...")
        
        ydl_opts = {
            'skip_download': True,
            'list_subs': True,
            'quiet': True,
        }
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        has_subs = False
        lang_to_download = 'en'
        is_supported_whisper_lang = True
        
        WHISPER_SUPPORTED_CODES = {
            'en', 'es', 'hi', 'pt', 'ru', 'ja', 'ko', 'fr', 'ar', 'de', 
            'vi', 'tr', 'th', 'zh', 'zh-hans', 'zh-hant', 'zh-cn', 'zh-tw', 'zh-hk',
            'bn', 'it', 'ur', 'pl', 'ta'
        }
        
        video_duration = 0
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source, download=False)
                video_duration = info.get('duration', 0)
                
                vid_lang = info.get('language') or 'en'
                base_lang = vid_lang.split('-')[0]
                
                if 'subtitles' in info and info['subtitles']:
                    subs = info['subtitles']
                    if vid_lang in subs:
                        lang_to_download = vid_lang
                    elif base_lang in subs:
                        lang_to_download = base_lang
                    elif 'en' in subs or 'en-US' in subs or 'en-GB' in subs:
                        lang_to_download = 'en'
                    else:
                        lang_to_download = list(subs.keys())[0]
                        
                    is_supported_whisper_lang = lang_to_download.lower() in WHISPER_SUPPORTED_CODES or base_lang.lower() in WHISPER_SUPPORTED_CODES
                    self.log(f"Manual subtitles found. Selected language: {lang_to_download} (Video original: {vid_lang})")
                    has_subs = True
                    
                elif 'automatic_captions' in info and info['automatic_captions']:
                    subs = info['automatic_captions']
                    if vid_lang in subs:
                        lang_to_download = vid_lang
                    elif base_lang in subs:
                        lang_to_download = base_lang
                    elif 'en' in subs or 'en-US' in subs or 'en-GB' in subs:
                        lang_to_download = 'en'
                    else:
                        lang_to_download = list(subs.keys())[0]
                        
                    is_supported_whisper_lang = lang_to_download.lower() in WHISPER_SUPPORTED_CODES or base_lang.lower() in WHISPER_SUPPORTED_CODES
                    self.log(f"Automatic captions found. Selected language: {lang_to_download} (Video original: {vid_lang})")
                    has_subs = True
        except Exception as e:
            self.log(f"Error checking subs: {e}")

        if has_subs:
            self.log(f"Attempting to download subtitles (VTT) for language: {lang_to_download}...")
            vtt_path_template = os.path.join(self.output_dir, 'subs_%(id)s')
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitlesformat': 'vtt',
                'subtitleslangs': [lang_to_download],
                'outtmpl': vtt_path_template,
                'quiet': True,
            }
            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source, download=True)
                    video_id = info['id']
                    expected_prefix = f"subs_{video_id}"
                    for f in os.listdir(self.output_dir):
                        if f.startswith(expected_prefix) and f.endswith('.vtt'):
                            full_path = os.path.join(self.output_dir, f)
                            self.log(f"Subtitles downloaded to: {full_path}")
                            return 'text', full_path, is_supported_whisper_lang
            except Exception as e:
                self.log(f"Failed to download subs: {e}")

            self.log("Could not verify downloaded VTT file. Switching to audio fallback.")

        if video_duration > 1800:
            self.log("Video is over 30 minutes long. Skipping audio analysis. Falling back to visual analysis.")
            return 'youtube_visuals', source, is_supported_whisper_lang

        self.log("Downloading audio track for analysis (Audio-only)...")
        audio_path_template = os.path.join(self.output_dir, 'audio_%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_path_template,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source, download=True)
                path = ydl.prepare_filename(info)
                base_path = os.path.splitext(path)[0]
                mp3_path = base_path + '.mp3'
                
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1024:
                    self.log(f"Audio downloaded to: {mp3_path}")
                    return 'audio', mp3_path, is_supported_whisper_lang
                self.log("Audio file seems invalid or missing.")
        except Exception as e:
            self.log(f"Audio download failed: {e}")
            
        self.log("Switching to visual analysis (will download small chunks instead of full video)...")
        return 'youtube_visuals', source, is_supported_whisper_lang

    def _get_local_context(self, source: str):
        self.log(f"Inspecting local file: {source}")
        base, _ = os.path.splitext(source)
        
        is_supported_whisper_lang = True
        
        if os.path.exists(base + '.srt'):
            self.log(f"Found sidecar SRT: {base}.srt")
            return 'text', base + '.srt', is_supported_whisper_lang
        if os.path.exists(base + '.vtt'):
            self.log(f"Found sidecar VTT: {base}.vtt")
            return 'text', base + '.vtt', is_supported_whisper_lang
            
        video_duration = self.get_duration(source)
        if video_duration > 1800:
            self.log("Local video is over 30 minutes long. Skipping audio analysis. Falling back to visual analysis.")
            return 'visuals', source, is_supported_whisper_lang
            
        self.log("No sidecar subtitles. Extracting audio from video...")
        audio_path = os.path.join(self.output_dir, "local_audio.mp3")
        
        cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
        cmd = [
            cmd_exe, '-y', '-i', source,
            '-vn', '-acodec', 'libmp3lame', '-q:a', '2', 
            audio_path
        ]
        self.log(f"Executing FFmpeg: {' '.join(cmd)}")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(audio_path):
             self.log(f"Audio extracted to: {audio_path}")
             return 'audio', audio_path, is_supported_whisper_lang
        else:
             self.log("Failed to extract audio. Falling back to visual analysis.")
             return 'visuals', source, is_supported_whisper_lang

    def chunk_audio(self, audio_path: str):
        duration = self.get_duration(audio_path)
        self.log(f"Audio duration: {timedelta(seconds=duration)}")
        
        overlap = 2 * 60
        chunks = []
        start = 0
        
        while start < duration:
            current_chunk_size = 20 * 60
            end = min(start + current_chunk_size, duration)
            
            chunk_file = f"{audio_path}_chunk_{start}.mp3"
            
            while True:
                cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
                cmd = [
                    cmd_exe, '-y', '-i', audio_path,
                    '-ss', str(start), '-to', str(end),
                    '-c', 'copy', chunk_file
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                size_mb = os.path.getsize(chunk_file) / (1024 * 1024)
                if size_mb <= 23.0 or (end - start) <= 4 * 60:
                    break
                else:
                    self.log(f"Chunk from {start}s to {end}s is {size_mb:.2f}MB (>23MB). Stripping 4 mins...")
                    os.remove(chunk_file)
                    end -= 4 * 60
                    if end <= start + overlap:
                        end = start + overlap + 60
                        
            chunks.append({
                'path': chunk_file,
                'start_sec': start,
                'end_sec': end
            })
            
            if end >= duration:
                break
                
            start = end - overlap
            
        return chunks

    def chunk_text_vtt(self, vtt_path: str):
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        chunk_size = 2000
        overlap = 200
        step = chunk_size - overlap
        
        chunks = []
        start = 0
        total_lines = len(lines)
        
        while start < total_lines:
            end = min(start + chunk_size, total_lines)
            chunk_content = "".join(lines[start:end])
            
            chunks.append({
                'content': chunk_content,
                'start_sec': 0, 
                'end_sec': 99999
            })
            
            if end == total_lines:
                break
            start += step
            
        return chunks

    def extract_youtube_visual_frames(self, source_url: str):
        self.log("Starting YouTube visual analysis (chunked downloading)...")
        
        ydl_opts = {'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source_url, download=False)
                duration = info.get('duration', 0)
        except Exception as e:
            self.log(f"Failed to get video info for visuals: {e}")
            return []
            
        if duration <= 0:
            self.log("Invalid video duration for visual analysis.")
            return []
            
        self.log(f"Video duration: {timedelta(seconds=duration)}")
        
        num_parts = 10
        interval = duration / num_parts
        frames = []
        
        self.log(f"Extracting {num_parts} frames by downloading 2-second chunks...")
        
        for i in range(num_parts):
            t = (i * interval) + (interval / 2)
            start_t = max(0, t - 1)
            end_t = min(duration, t + 1)
            
            temp_chunk_path = os.path.join(self.output_dir, f"temp_vis_chunk_{i}.mp4")
            frame_path = os.path.join(self.output_dir, f"frame_{i}.jpg")
            
            ydl_opts_dl = {
                'download_ranges': lambda _, __: [{'start_time': start_t, 'end_time': end_t}],
                'format': 'bestvideo[height<=720][ext=mp4]/best[height<=720]',
                'outtmpl': temp_chunk_path,
                'quiet': True,
                'force_keyframes_at_cuts': True,
            }
            if self.ffmpeg_path:
                ydl_opts_dl['ffmpeg_location'] = self.ffmpeg_path
                
            try:
                with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                    ydl.download([source_url])
                    
                if os.path.exists(temp_chunk_path):
                    cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
                    cmd = [
                        cmd_exe, '-y',
                        '-i', temp_chunk_path,
                        '-vframes', '1',
                        '-q:v', '2',
                        frame_path
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if os.path.exists(frame_path):
                        frames.append({'path': frame_path, 'time': t})
                        
                    os.remove(temp_chunk_path)
            except Exception as e:
                self.log(f"Failed to process visual chunk {i}: {e}")
                
        if not frames:
            self.log("No frames could be extracted for visual analysis.")
        else:
            self.log(f"Extracted {len(frames)} frames. Preparing for OpenAI...")
        return frames

    def extract_local_visual_frames(self, video_path: str):
        self.log("Starting visual analysis...")
        duration = self.get_duration(video_path)
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
        return frames
