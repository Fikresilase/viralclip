import os
import cv2
import time
import subprocess
import shutil
import concurrent.futures
from datetime import timedelta
import yt_dlp

from src.core.face_tracker import FaceTracker

class VideoProcessor:
    def __init__(self, ffmpeg_path: str, storage, log_callback, clip_progress_callback, clip_complete_callback):
        self.ffmpeg_path = ffmpeg_path
        self.storage = storage
        self.output_dir = storage.temp_dir
        self.log = log_callback
        self.clip_progress = clip_progress_callback
        self.clip_complete = clip_complete_callback

    def process_clips(self, segments, source, is_local, enable_captions, caption_semaphore, caption_engine, is_supported_whisper_lang, context_type, context_path):
        processed = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as video_executor:
            future_to_seg = {
                video_executor.submit(
                    self.process_single_clip, 
                    i, seg, source, is_local, enable_captions, caption_semaphore, 
                    caption_engine, is_supported_whisper_lang, context_type, context_path
                ): seg 
                for i, seg in enumerate(segments)
            }
            
            for future in concurrent.futures.as_completed(future_to_seg):
                try:
                    result = future.result()
                    if result:
                        processed.append(result)
                except Exception as e:
                    self.log(f"Error processing clip: {e}")
        
        processed.sort(key=lambda x: x.get('score', 0), reverse=True)
        return processed

    def process_single_clip(self, i, seg, source, is_local, enable_captions, caption_semaphore, caption_engine, is_supported_whisper_lang, context_type, context_path):
        start = seg['abs_start']
        end = seg['abs_end']
        duration = end - start
        
        self.log(f"Processing Clip {i+1}: {seg.get('title', 'Unknown')}")
        self.log(f"  Range: {timedelta(seconds=start)} - {timedelta(seconds=end)} (Duration: {duration}s)")
        
        self.clip_progress(i, 0, "Starting...")
        
        filename = f"short_{int(time.time())}_{i}.mp4"
        out_path = self.storage.get_new_path(filename)
        thumb_path = self.storage.get_new_path(f"thumb_{i}.jpg")
        temp_raw_path = self.storage.get_new_path(f"temp_raw_{i}.mp4")
        temp_cropped_path = self.storage.get_new_path(f"temp_cropped_{i}.mp4")
        
        cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'

        try:
            if is_local:
                self.log(f"  Clip {i+1}: Extracting raw from local...")
                self.clip_progress(i, 10, "Extracting clip...")
                cmd = [
                    cmd_exe, '-y',
                    '-ss', str(start),
                    '-t', str(duration),
                    '-i', source,
                    '-c:v', 'libx264', '-c:a', 'aac',
                    temp_raw_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.log(f"  Clip {i+1}: Downloading raw from YouTube...")
                self.clip_progress(i, 10, "Downloading clip...")
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
                    ydl.download([source])
            
            if not os.path.exists(temp_raw_path):
                self.log(f"  Clip {i+1}: Failed to acquire raw clip.")
                self.clip_progress(i, 0, "Failed")
                return None
            
            self.clip_progress(i, 25, "Clip downloaded")
            
            caption_future = None
            if enable_captions:
                with caption_semaphore:
                    self.log(f"  Clip {i+1}: Starting caption generation in background...")
                    caption_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    
                    if is_supported_whisper_lang:
                        self.log(f"  Clip {i+1}: Supported Whisper language detected. Using Whisper AI for word-level karaoke captions.")
                        caption_future = caption_executor.submit(
                            caption_engine.generate_captions_from_clip,
                            i,
                            temp_raw_path,
                            start,
                            end
                        )
                    else:
                        self.log(f"  Clip {i+1}: Other language detected. Using VTT extraction for standard captions.")
                        caption_future = caption_executor.submit(
                            caption_engine.generate_captions_for_clip,
                            i,
                            start,
                            end,
                            context_type,
                            context_path
                        )

            self.log(f"  Clip {i+1}: Running Face Tracking...")
            self.clip_progress(i, 30, "Processing frames...")
            
            cap = cv2.VideoCapture(temp_raw_path)
            if not cap.isOpened():
                raise Exception("Failed to open raw clip for processing.")
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if width <= 0 or height <= 0 or fps <= 0:
                cap.release()
                raise Exception(f"Invalid video properties: {width}x{height} @ {fps}fps")
            
            target_w = 1080
            target_h = 1920
            self.log(f"  Clip {i+1}: Target output resolution: {target_w}x{target_h}")
            
            frames_dir = os.path.join(self.output_dir, f"frames_{i}")
            os.makedirs(frames_dir, exist_ok=True)
            
            tracker = FaceTracker()
            frame_count = 0
            self.log(f"  Clip {i+1}: Processing all frames at original FPS: {fps}")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                try:
                    cropped = tracker.process_frame(frame)
                except Exception as e:
                    self.log(f"  Clip {i+1}: Frame {frame_count} tracking error: {e}")
                    frame_count += 1
                    continue
                
                if cropped is None or cropped.size == 0:
                    self.log(f"  Clip {i+1}: Warning - empty frame at {frame_count}, skipping")
                    frame_count += 1
                    continue
                
                if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
                    cropped = cv2.resize(cropped, (target_w, target_h))
                
                frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                cv2.imwrite(frame_path, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                frame_count += 1
                
                if frame_count % 30 == 0:
                    if total_frames > 0:
                        progress = 30 + int((frame_count / total_frames) * 40)
                        self.clip_progress(i, progress, f"Frame {frame_count}/{total_frames}")
            
            cap.release()
            tracker.release()
            
            self.clip_progress(i, 70, "Frames processed")
            
            if frame_count == 0:
                raise Exception("No frames were processed")
            
            self.log(f"  Clip {i+1}: Creating video from frames with FFmpeg at {fps}fps (original frame rate)...")
            self.clip_progress(i, 75, "Encoding video...")
            temp_cropped_video = temp_cropped_path.replace('.mp4', '_video.mp4')
            
            cmd_frames = [
                cmd_exe, '-y',
                '-framerate', str(fps),
                '-i', os.path.join(frames_dir, 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '20',
                '-preset', 'slow',
                temp_cropped_video
            ]
            
            result = subprocess.run(cmd_frames, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise Exception("FFmpeg failed to create video from frames")
            
            shutil.rmtree(frames_dir, ignore_errors=True)
            
            if not os.path.exists(temp_cropped_video):
                raise Exception("Failed to create cropped video.")
            
            self.clip_progress(i, 85, "Video encoded")

            self.log(f"  Clip {i+1}: Merging audio and finalizing...")
            self.clip_progress(i, 90, "Merging audio...")
            
            temp_final_no_subs = self.storage.get_new_path(f"temp_final_no_subs_{i}.mp4")
            
            cmd_merge = [
                cmd_exe, '-y',
                '-i', temp_cropped_video,
                '-i', temp_raw_path,
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '192k',
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest',
                '-movflags', '+faststart',
                temp_final_no_subs
            ]
            subprocess.run(cmd_merge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(temp_final_no_subs):
                raise Exception("Failed to merge audio and video.")
            
            if enable_captions and caption_future:
                self.log(f"  Clip {i+1}: Waiting for captions to be ready...")
                self.clip_progress(i, 92, "Waiting for captions...")
                
                try:
                    subtitle_path = caption_future.result(timeout=60)
                    caption_executor.shutdown(wait=False)
                    
                    if subtitle_path and os.path.exists(subtitle_path):
                        self.log(f"  Clip {i+1}: Burning captions...")
                        self.clip_progress(i, 94, "Burning captions...")
                        
                        if caption_engine.burn_subtitles(temp_final_no_subs, subtitle_path, out_path):
                            if os.path.exists(temp_final_no_subs):
                                os.remove(temp_final_no_subs)
                        else:
                            self.log(f"  Clip {i+1}: Failed to burn captions, using video without captions")
                            caption_engine.apply_watermark(temp_final_no_subs, out_path)
                    else:
                        self.log(f"  Clip {i+1}: No captions generated, using video without captions")
                        caption_engine.apply_watermark(temp_final_no_subs, out_path)
                except concurrent.futures.TimeoutError:
                    self.log(f"  Clip {i+1}: Caption generation timed out, using video without captions")
                    caption_engine.apply_watermark(temp_final_no_subs, out_path)
                except Exception as e:
                    self.log(f"  Clip {i+1}: Caption error: {e}, using video without captions")
                    caption_engine.apply_watermark(temp_final_no_subs, out_path)
            else:
                if not enable_captions:
                    self.log(f"  Clip {i+1}: Captions disabled")
                caption_engine.apply_watermark(temp_final_no_subs, out_path)
            
            if os.path.exists(temp_raw_path): os.remove(temp_raw_path)
            if os.path.exists(temp_cropped_video): os.remove(temp_cropped_video)
            if os.path.exists(temp_cropped_path): os.remove(temp_cropped_path)

            if os.path.exists(out_path):
                self.log(f"  Clip {i+1}: Generating thumbnail...")
                self.clip_progress(i, 95, "Creating thumbnail...")
                cmd_thumb = [
                    cmd_exe, '-y',
                    '-i', out_path,
                    '-ss', str(duration/2),
                    '-vframes', '1',
                    '-q:v', '2',
                    thumb_path
                ]
                subprocess.run(cmd_thumb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.clip_progress(i, 100, "Complete!")
                
                result = {
                    'path': out_path,
                    'thumb': thumb_path,
                    'score': seg.get('virality_score', 0),
                    'title': seg.get('title', 'Viral Clip'),
                    'reason': seg.get('reason', '')
                }
                
                self.clip_complete(i, result)
                return result
            else:
                 self.log(f"  Clip {i+1}: Output file missing.")
                 self.clip_progress(i, 0, "Failed")
                 return None

        except Exception as e:
            self.log(f"  Clip {i+1} Failed: {e}")
            self.clip_progress(i, 0, "Failed")
            import traceback
            self.log(traceback.format_exc())
            return None
