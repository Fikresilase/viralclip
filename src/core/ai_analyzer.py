import json
import base64
import os
import concurrent.futures
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional

from src.prompts import VIRAL_MOMENTS_PROMPT, VISUAL_MOMENTS_PROMPT
from src.utils.time_utils import parse_time


class ViralMoment(BaseModel):
    start_time: str = Field(description="The exact start timestamp (MM:SS)")
    end_time: str = Field(description="The exact end timestamp (MM:SS)")
    duration_type: Optional[str] = Field(None, description="Dopamine/Story/Value")
    virality_score: int = Field(description="A score from 0-100 indicating viral potential")
    psychological_hook: Optional[str] = Field(None, description="Pattern Interrupt / Open Loop / Social Currency / Sudden Motion / Facial Distortion / Satisfying Visual")
    title: str = Field(description="A catchy, click-baity title for the clip")
    reason: str = Field(description="Explain the emotional trigger and why the ending forces a rewatch")

class ViralMomentsResponse(BaseModel):
    clips: list[ViralMoment]


class AIAnalyzer:
    def __init__(self, api_key: str, num_clips: int, log_callback):
        self.client = OpenAI(api_key=api_key)
        self.num_clips = num_clips
        self.log = log_callback

    def _call_ai_text(self, prompt: str, model: str = "gpt-5-mini") -> str:
        """Call AI with text prompt, returns JSON text response via parsed model"""
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=ViralMomentsResponse,
            timeout=120.0
        )
        return response.choices[0].message.parsed.model_dump_json()

    def _call_ai_with_audio(self, prompt: str, audio_path: str, model: str = "gpt-5-mini") -> str:
        """Call AI with audio file: transcribe with whisper-1, then analyze"""
        with open(audio_path, 'rb') as f:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
                timeout=120.0
            )
        
        full_prompt = f"{prompt}\n\nTRANSCRIPT:\n{transcript}"
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            response_format=ViralMomentsResponse,
            timeout=120.0
        )
        return response.choices[0].message.parsed.model_dump_json()

    def _call_ai_with_images(self, prompt: str, image_paths: list, model: str = "gpt-5-mini") -> str:
        """Call AI with multiple images, returns JSON text response via parsed model"""
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
        
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format=ViralMomentsResponse,
            timeout=120.0
        )
        return response.choices[0].message.parsed.model_dump_json()

    def deduplicate(self, moments):
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
                if len(final_moments) >= self.num_clips: 
                    break
        self.log(f"Retained {len(final_moments)} unique moments.")
        return final_moments

    def process_chunk(self, i, chunk_data, context_type, total_chunks):
        self.log(f"Analyzing chunk {i+1}/{total_chunks} with OpenAI...")
        moments = []
        
        clips_per_chunk = self.num_clips if total_chunks == 1 else max(3, int((self.num_clips * 1.5) / total_chunks) + 1)
        
        response_text = ""
        success = False
        
        def attempt_analysis(model_name):
            if context_type == 'text':
                prompt = VIRAL_MOMENTS_PROMPT.format(num_clips=clips_per_chunk) + "\n\nTRANSCRIPT:\n" + chunk_data['content']
                return self._call_ai_text(prompt, model=model_name)
            else:
                self.log(f"Reading audio chunk {i+1} ({os.path.getsize(chunk_data['path'])/1024/1024:.2f} MB)...")
                prompt = VIRAL_MOMENTS_PROMPT.format(num_clips=clips_per_chunk)
                return self._call_ai_with_audio(prompt, chunk_data['path'], model=model_name)

        try:
            self.log(f"Chunk {i+1}: Attempting analysis with gpt-5-mini (120s timeout)...")
            response_text = attempt_analysis("gpt-5-mini")
            success = True
        except Exception as e:
            self.log(f"Chunk {i+1}: Primary attempt failed ({e}). Retrying with gpt-4o-mini...")
            try:
                response_text = attempt_analysis("gpt-4o-mini")
                success = True
            except Exception as e2:
                self.log(f"Chunk {i+1}: Retry failed ({e2}). Moving on without this chunk.")

        # Cleanup audio chunk
        if context_type != 'text' and 'path' in chunk_data and os.path.exists(chunk_data['path']):
            try:
                os.remove(chunk_data['path'])
            except Exception as e:
                pass

        if not success:
            return []

        self.log(f"OpenAI Response received for chunk {i+1}.")
        
        try:
            parsed_response = json.loads(response_text)
            data = parsed_response.get("clips", [])
        except json.JSONDecodeError as je:
            self.log(f"JSON Parse Error. Error: {je}")
            data = []
        
        self.log(f"Parsed {len(data)} moments from chunk {i+1}.")
        
        chunk_start_sec = chunk_data['start_sec']
        for item in data:
            try:
                rel_start = parse_time(item['start_time'])
                rel_end = parse_time(item['end_time'])
            except Exception as e:
                 self.log(f"Invalid timestamp format in response: {item} - Error: {e}")
                 continue
            
            if context_type == 'audio':
                item['abs_start'] = chunk_start_sec + rel_start
                item['abs_end'] = chunk_start_sec + rel_end
            else:
                item['abs_start'] = rel_start
                item['abs_end'] = rel_end
                
            moments.append(item)

        return moments

    def analyze_chunks(self, chunks, context_type):
        """Analyzes textual or audio chunks in parallel."""
        all_moments = []
        total_chunks = len(chunks)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_chunk = {
                executor.submit(self.process_chunk, i, chunk_data, context_type, total_chunks): i
                for i, chunk_data in enumerate(chunks)
            }
            
            completed_chunks = 0
            for future in concurrent.futures.as_completed(future_to_chunk):
                completed_chunks += 1
                chunk_index = future_to_chunk[future]
                self.log(f"Completed processing for chunk {chunk_index+1} ({completed_chunks}/{total_chunks} total completed).")
                try:
                    moments = future.result()
                    all_moments.extend(moments)
                except Exception as e:
                    self.log(f"Chunk processing failed unexpectedly: {e}")

        self.log(f"Total raw moments identified: {len(all_moments)}")
        return self.deduplicate(all_moments)

    def analyze_visual_frames(self, frames):
        """Analyzes extracted frames for visual viral moments."""
        frame_paths = [f['path'] for f in frames]
        response_text = ""
        success = False
        
        try:
            self.log(f"Sending prompt to OpenAI (gpt-5-mini, 120s timeout)...")
            prompt = VISUAL_MOMENTS_PROMPT.format(num_clips=self.num_clips)
            response_text = self._call_ai_with_images(prompt, frame_paths, model="gpt-5-mini")
            success = True
        except Exception as e:
            self.log(f"Primary visual attempt failed ({e}). Retrying with gpt-4o-mini...")
            try:
                response_text = self._call_ai_with_images(prompt, frame_paths, model="gpt-4o-mini")
                success = True
            except Exception as e2:
                self.log(f"Visual retry failed ({e2}). Moving on.")
                
        # Cleanup local frames
        for f in frames:
            if os.path.exists(f['path']):
                try:
                    os.remove(f['path'])
                except:
                    pass

        if not success:
            return []
            
        self.log(f"OpenAI response received.")
        
        try:
            parsed_response = json.loads(response_text)
            data = parsed_response.get("clips", [])
        except json.JSONDecodeError as je:
            self.log(f"JSON Parse Error. Error: {je}")
            data = []

        self.log(f"Parsed {len(data)} moments from visual analysis.")
            
        final_moments = []
        for item in data:
            try:
                abs_start = parse_time(item['start_time'])
                abs_end = parse_time(item['end_time'])
                
                if abs_start >= abs_end:
                     continue

                item['abs_start'] = abs_start
                item['abs_end'] = abs_end
                final_moments.append(item)
            except Exception as e:
                self.log(f"Error parsing timestamp {item}: {e}")

        return self.deduplicate(final_moments)
