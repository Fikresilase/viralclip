import os
import re
import subprocess
import shutil
from openai import OpenAI
from src.prompts import CAPTION_GENERATION_PROMPT
from src.utils.time_utils import (
    seconds_to_ass_time, 
    vtt_time_to_seconds, 
    srt_time_to_seconds, 
    seconds_to_srt_time,
    srt_time_to_ass_time
)

class CaptionEngine:
    def __init__(self, api_key: str, ffmpeg_path: str, storage, log_callback, progress_callback):
        self.openai_client = OpenAI(api_key=api_key)
        self.ffmpeg_path = ffmpeg_path
        self.storage = storage
        self.log = log_callback
        self.progress = progress_callback

    def generate_captions_from_clip(self, clip_index, clip_video_path, start_time, end_time):
        """
        Generate Hormozi-style karaoke captions from the downloaded clip.
        Uses Whisper-1 for word-level timestamps, then generates .ass with karaoke \\k tags.
        """
        try:
            self.log(f"  [Caption] Clip {clip_index+1}: Extracting audio from downloaded clip...")
            audio_path = self.storage.get_new_path(f"clip_audio_{clip_index}.mp3")
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            cmd = [
                cmd_exe, '-y',
                '-i', clip_video_path,
                '-vn',  
                '-acodec', 'libmp3lame',
                '-q:a', '2',
                audio_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1024:
                self.log(f"  [Caption] Clip {clip_index+1}: Failed to extract audio")
                return None
            
            self.log(f"  [Caption] Clip {clip_index+1}: Sending audio to Whisper-1 for word-level transcription...")
            with open(audio_path, 'rb') as f:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            words = transcription.words if hasattr(transcription, 'words') and transcription.words else []
            if not words:
                self.log(f"  [Caption] Clip {clip_index+1}: No words returned from Whisper")
                return None
            
            self.log(f"  [Caption] Clip {clip_index+1}: Whisper returned {len(words)} words with timestamps")
            ass_path = self.storage.get_new_path(f"captions_{clip_index}.ass")
            ass_content = self._generate_karaoke_ass(words)
            
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            self.log(f"  [Caption] Clip {clip_index+1}: Karaoke ASS captions saved to {ass_path}")
            return ass_path
            
        except Exception as e:
            self.log(f"  [Caption] Clip {clip_index+1}: Caption generation failed: {e}")
            return None
    
    def generate_captions_for_clip(self, clip_index, start_time, end_time, context_type, context_path):
        """
        Generate SRT captions for a specific clip segment using OpenAI completion or VTT extraction.
        """
        try:
            self.log(f"  Clip {clip_index+1}: Generating captions...")
            
            if context_type == 'text':
                caption_content = self._extract_vtt_segment(context_path, start_time, end_time)
                if not caption_content:
                    self.log(f"  Clip {clip_index+1}: No VTT content found for time range")
                    return None
                
                prompt = CAPTION_GENERATION_PROMPT + f"\n\nVTT CONTENT:\n{caption_content}"
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                srt_content = response.choices[0].message.content
                
            elif context_type == 'audio':
                audio_segment_path = self._extract_audio_segment(context_path, start_time, end_time, clip_index)
                if not audio_segment_path or not os.path.exists(audio_segment_path):
                    self.log(f"  Clip {clip_index+1}: Failed to extract audio segment")
                    return None
                
                with open(audio_segment_path, 'rb') as f:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text"
                    )
                    
                prompt = CAPTION_GENERATION_PROMPT + f"\n\nTRANSCRIPT:\n{transcript}"
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                srt_content = response.choices[0].message.content
                
                if os.path.exists(audio_segment_path):
                    os.remove(audio_segment_path)
            
            elif context_type == 'visuals' or context_type == 'youtube_visuals':
                self.log(f"  Clip {clip_index+1}: Skipping captions (visual-only source)")
                return None
            else:
                return None
            
            if "```srt" in srt_content:
                srt_content = srt_content.split("```srt")[1].split("```")[0].strip()
            elif "```" in srt_content:
                srt_content = srt_content.split("```")[1].split("```")[0].strip()
            
            if not self._validate_srt(srt_content):
                self.log(f"  Clip {clip_index+1}: Invalid SRT format received")
                return None
            
            self.log(f"  Clip {clip_index+1}: Offsetting timestamps by -{start_time}s")
            srt_content = self._offset_srt_timestamps(srt_content, start_time)
            
            srt_path = self.storage.get_new_path(f"captions_{clip_index}.srt")
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            self.log(f"  Clip {clip_index+1}: Captions saved to {srt_path}")
            return srt_path
            
        except Exception as e:
            self.log(f"  Clip {clip_index+1}: Caption generation failed: {e}")
            return None

    def _generate_karaoke_ass(self, words):
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
            "Style: Main,Arial Black,102,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1.5,2,50,50,250,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]
        
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
            
            total_chars = sum(len(p['word']) for p in current_phrase)
            next_word_start = None
            if i + 1 < len(words):
                next_w = words[i + 1]
                next_word_start = next_w.start if hasattr(next_w, 'start') else next_w.get('start', 0)
            
            should_break = (
                len(current_phrase) >= 6 or
                total_chars > 30 or
                (next_word_start is not None and next_word_start - word_end > 0.5) or
                i == len(words) - 1
            )
            
            if should_break and current_phrase:
                phrases.append(current_phrase)
                current_phrase = []
        
        for phrase in phrases:
            if not phrase:
                continue
            
            phrase_start = phrase[0]['start']
            phrase_end = phrase[-1]['end'] + 0.3 
            
            start_str = seconds_to_ass_time(phrase_start)
            end_str = seconds_to_ass_time(phrase_end)
            
            karaoke_parts = []
            for pw in phrase:
                duration_cs = max(1, round((pw['end'] - pw['start']) * 100))
                karaoke_parts.append(f"{{\\kf{duration_cs}}}{pw['word']} ")
            
            text_line = "".join(karaoke_parts).rstrip()
            ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Main,,0,0,0,,{text_line}")
        
        return "\n".join(ass_lines)

    def _extract_vtt_segment(self, vtt_path, start_time, end_time):
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            segment_lines = []
            in_range = False
            
            for line in lines:
                if '-->' in line:
                    try:
                        time_parts = line.split('-->')[0].strip()
                        time_sec = vtt_time_to_seconds(time_parts)
                        
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

    def _extract_audio_segment(self, audio_path, start_time, end_time, clip_index):
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
        if not srt_content or len(srt_content) < 10:
            return False
        lines = srt_content.strip().split('\n')
        if len(lines) < 4:
            return False
        try:
            int(lines[0].strip())
        except:
            return False
        if '-->' not in lines[1]:
            return False
        return True

    def _offset_srt_timestamps(self, srt_content, offset_seconds):
        lines = srt_content.split('\n')
        result_lines = []
        for line in lines:
            if '-->' in line:
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
                if match:
                    start_str, end_str = match.groups()
                    start_sec = srt_time_to_seconds(start_str) - offset_seconds
                    end_sec = srt_time_to_seconds(end_str) - offset_seconds
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
        try:
            ass_path = srt_path.replace('.srt', '.ass')
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            srt_blocks = self._parse_srt(srt_content)
            if not srt_blocks:
                return None
            
            ass_content = self._generate_ass_content(srt_blocks)
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            return ass_path
        except Exception as e:
            self.log(f"Error converting SRT to ASS: {e}")
            return None

    def _parse_srt(self, srt_content):
        blocks = []
        lines = srt_content.strip().split('\n')
        i = 0
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                continue
            try:
                seq_num = int(lines[i].strip())
            except ValueError:
                i += 1
                continue
            i += 1
            if i >= len(lines):
                break
            
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
            
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            
            blocks.append({
                'seq': seq_num,
                'start': start_time,
                'end': end_time,
                'text': ' '.join(text_lines)
            })
        return blocks

    def _generate_ass_content(self, srt_blocks):
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
        dialogue_lines = []
        for block in srt_blocks:
            start_ass = srt_time_to_ass_time(block['start'])
            end_ass = srt_time_to_ass_time(block['end'])
            text = block['text'].replace('\n', '\\N')
            dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}")
        return ass_header + '\n'.join(dialogue_lines)

    def _get_watermark_filter(self):
        return (
            "drawtext=text='clipped with\n"
            "viralclip.company'"
            ":fontsize=64"
            ":fontcolor=white@0.65"
            ":font='Arial Black'"
            ":line_spacing=12"
            ":x='abs(mod(t*150\\,2*(w-tw))-(w-tw))'"
            ":y='abs(mod(t*90\\,2*(h-th))-(h-th))'"
        )

    def apply_watermark(self, input_path, output_path):
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
                if os.path.exists(input_path):
                    shutil.move(input_path, output_path)
            else:
                if os.path.exists(input_path) and os.path.exists(output_path):
                    os.remove(input_path)
        except Exception as e:
            self.log(f"  Watermark error: {e}, using video without watermark")
            if os.path.exists(input_path) and not os.path.exists(output_path):
                shutil.move(input_path, output_path)

    def burn_subtitles(self, video_path, subtitle_path, output_path):
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            watermark_filter = self._get_watermark_filter()
            is_ass = subtitle_path.lower().endswith('.ass')
            
            if is_ass:
                self.log(f"  Burning karaoke ASS subtitles + watermark with FFmpeg...")
                ass_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
                subtitle_filter = f"ass='{ass_path_escaped}'"
            else:
                self.log(f"  Converting SRT to ASS format...")
                ass_path = self._convert_srt_to_ass(subtitle_path)
                if ass_path and os.path.exists(ass_path):
                    self.log(f"  Burning ASS subtitles + watermark with FFmpeg...")
                    ass_path_escaped = ass_path.replace('\\', '/').replace(':', '\\:')
                    subtitle_filter = f"ass='{ass_path_escaped}'"
                else:
                    self.log(f"  Failed to convert to ASS, burning SRT directly...")
                    srt_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:')
                    subtitle_filter = (
                        f"subtitles='{srt_path_escaped}':force_style='"
                        "FontName=Arial Black,FontSize=36,PrimaryColour=&H00FFFFFF,"
                        "OutlineColour=&H00000000,Outline=3,Bold=1,"
                        "Alignment=2,MarginV=180'"
                    )
            
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
                if is_ass or (not is_ass and 'ass=' in subtitle_filter):
                    self.log(f"  ASS burning failed, trying basic subtitle fallback...")
                    return self._burn_srt_fallback(video_path, subtitle_path, output_path)
                return False
            
            if not is_ass and 'ass_path' in locals() and ass_path and os.path.exists(ass_path):
                os.remove(ass_path)
            return os.path.exists(output_path)
            
        except Exception as e:
            self.log(f"Error burning subtitles: {e}")
            return self._burn_srt_fallback(video_path, subtitle_path, output_path)

    def _burn_srt_fallback(self, video_path, subtitle_path, output_path):
        try:
            cmd_exe = self.ffmpeg_path if self.ffmpeg_path else 'ffmpeg'
            watermark_filter = self._get_watermark_filter()
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
