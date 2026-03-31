import os
import sys
import shutil
import threading
from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.storage import StorageManager
from src.core.ai_analyzer import AIAnalyzer
from src.core.media_extractor import MediaExtractor
from src.core.caption_engine import CaptionEngine
from src.core.video_processor import VideoProcessor

class GeneratorWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    clipsFound = pyqtSignal(list)
    clipProgress = pyqtSignal(int, int, str)
    clipComplete = pyqtSignal(int, dict)

    def __init__(self, source: str, is_local: bool, api_key: str, enable_captions: bool = True, num_clips: int = 5):
        super().__init__()
        self.source = source
        self.is_local = is_local
        self.api_key = api_key
        self.enable_captions = enable_captions
        self.num_clips = num_clips
        
        self.caption_semaphore = threading.Semaphore(5)
        self.storage = StorageManager()
        self.output_dir = self.storage.temp_dir 
        
        self.base_dir = self._get_resource_path()
        
        bin_dir = os.path.join(self.base_dir, "bin")
        ffmpeg_bundled = os.path.join(bin_dir, "ffmpeg.exe") if os.name == 'nt' else os.path.join(bin_dir, "ffmpeg")
        ffprobe_bundled = os.path.join(bin_dir, "ffprobe.exe") if os.name == 'nt' else os.path.join(bin_dir, "ffprobe")
        
        if os.path.exists(ffmpeg_bundled):
             self.ffmpeg_path = ffmpeg_bundled
        else:
             self.ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
             
        if os.path.exists(ffprobe_bundled):
             self.ffprobe_path = ffprobe_bundled
        else:
             self.ffprobe_path = shutil.which('ffprobe') or 'ffprobe'

    def _get_resource_path(self):
        try:
            return sys._MEIPASS
        except Exception:
            return os.path.abspath(".")

    def log(self, message: str):
        self.progress.emit(message)
        print(f"[GeneratorWorker] {message}")

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

            self.log("Configuring Core Engines...")
            ai_analyzer = AIAnalyzer(self.api_key, self.num_clips, self.log)
            media_extractor = MediaExtractor(self.ffmpeg_path, self.output_dir, self.log)
            caption_engine = CaptionEngine(self.api_key, self.ffmpeg_path, self.storage, self.log, self.clipProgress.emit)
            video_processor = VideoProcessor(self.ffmpeg_path, self.storage, self.log, self.clipProgress.emit, self.clipComplete.emit)

            self.log("Step 1: Extracting Context (Subtitles or Audio)...")
            context_type, context_path, is_supported_whisper_lang = media_extractor.get_context(self.source, self.is_local)
            self.log(f"Context acquired: Type={context_type}, Path={context_path}")

            self.log("Step 2: Analyzing content for viral moments...")
            
            if context_type == 'visuals':
                frames = media_extractor.extract_local_visual_frames(context_path)
                viral_segments = ai_analyzer.analyze_visual_frames(frames)
            elif context_type == 'youtube_visuals':
                frames = media_extractor.extract_youtube_visual_frames(context_path)
                viral_segments = ai_analyzer.analyze_visual_frames(frames)
            else:
                chunks = []
                if context_type == 'text':
                    self.log("Chunking subtitle text...")
                    chunks = media_extractor.chunk_text_vtt(context_path)
                else:
                    self.log("Chunking audio file...")
                    chunks = media_extractor.chunk_audio(context_path)
                
                self.log(f"Prepared {len(chunks)} chunks for analysis.")
                viral_segments = ai_analyzer.analyze_chunks(chunks, context_type)

            if not viral_segments:
                raise Exception("No viral moments found during analysis.")
            self.log(f"Found {len(viral_segments)} potential viral segments.")
            
            self.clipsFound.emit(viral_segments)

            self.log("Step 3: Processing clips with parallel caption generation...")
            results = video_processor.process_clips(
                viral_segments, 
                self.source, 
                self.is_local, 
                self.enable_captions, 
                self.caption_semaphore, 
                caption_engine, 
                is_supported_whisper_lang, 
                context_type, 
                context_path
            )
            
            self.log(f"Generation finished. Emitting {len(results)} results.")
            self.finished.emit(results)
            
            self.log("Cleaning up temporary files...")
            self._cleanup_temp_files()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self._cleanup_temp_files()
            self.error.emit(str(e))

    def _cleanup_temp_files(self):
        try:
            self.log("Starting temp file cleanup...")
            if not os.path.exists(self.output_dir):
                return
            
            files_to_keep = set()
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                if filename.startswith('short_') or filename.startswith('thumb_'):
                    files_to_keep.add(filepath)
            
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
