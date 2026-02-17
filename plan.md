# 🚀 Project: Content Factory (Desktop AI Clipper)
**Target Platform:** Windows Desktop (PyQt6)
**Core Engine:** Python + FFmpeg + gemini-3-flash-preview

---

## 1. System Architecture

### The Workflow Pipeline
The application follows a linear pipeline with parallel processing where possible.

1.  **Ingestion:** Accept YouTube URL or Local File.
2.  **Preprocessing:** Extract Audio/Captions & Chunking.
3.  **Intelligence (Gemini):** Analyze chunks for viral moments.
4.  **Refinement (Gemini):** Generate precise karaoke timestamps for selected clips.
5.  **Vision (MediaPipe):** Face tracking and 9:16 cropping.
6.  **Rendering (FFmpeg):** Burn captions, apply "Stealth Mode," and export.

---

## 2. Technical Stack (Libraries)

| Component | Library / Tool | Purpose |
| :--- | :--- | :--- |
| **GUI** | `PyQt6` + `qdarktheme` | Modern dark-mode interface. |
| **Video Core** | `ffmpeg-python` (or `subprocess`) | Cutting, cropping, rendering, filters. |
| **Downloader** | `yt-dlp` | Handling YouTube links and metadata. |
| **AI Brain** | `google-generativeai` | gemini-3-flash-preview API (Analysis & Transcription). |
| **Face Tracking** | `mediapipe` | Detecting faces for dynamic cropping. |
| **Concurrency** | `concurrent.futures` / `QThread` | Handling the 5-request limit and UI non-blocking. |
| **Math/Logic** | `numpy` | Calculating smooth camera movements. |

---

## 3. Detailed Logic & Implementation Steps

### Phase 1: Ingestion & Extraction
**Goal:** Convert input into a standardized format for the AI.

#### A. Input Source: YouTube Link
1.  **Check Captions:** Use `yt-dlp --list-subs` to check for **manual** (non-auto-generated) captions.
    *   *If Exists:* Download `.vtt` format. (Faster/Cheaper).
    *   *If Missing:* Download Audio (`m4a`/`mp3`).
2.  **Chunking Strategy:**
    *   **Logic:** Divide source into **30-minute chunks**.
    *   **Overlap:** **10-minute overlap** to ensure context isn't cut off (e.g., 0-30m, 20-50m, 40-70m).
    *   *Note:* If using Audio, compress to low-bitrate MP3 (32k) to save bandwidth before sending to Gemini.

#### B. Input Source: Local File
1.  **Extraction:** Use FFmpeg to extract audio track immediately.
2.  **Chunking:** Apply the same 30m/10m overlap logic as above.

---

### Phase 2: The "Viral" Analysis (Gemini Brain)
**Goal:** Identify start/end timestamps of viral moments.

1.  **The Prompt:** Send chunks to gemini-3-flash-preview.
    *   *Constraint:* "Analyze this content. Return a JSON list of the top 3 most viral segments. Criteria: High energy, controversy, or strong hook."
2.  **Concurrency Control:**
    *   Implement a `Semaphore` or `ThreadPoolExecutor` to limit active API calls to **5 simultaneous requests** (to prevent rate limiting).
3.  **Result Aggregation:**
    *   Collect all JSON responses.
    *   **Deduplication:** Check if overlapping chunks returned the same clip. If Clip A ends at 25:00 and Clip B starts at 25:01, merge them if the context matches.

---

### Phase 3: Clip Refinement & Transcription
**Goal:** Get the actual audio for the clip and prepare karaoke text.

1.  **Audio Slicing:** Use FFmpeg to cut the *exact* audio of the viral moments identified in Phase 2.
2.  **Precise Transcription (Gemini):**
    *   Send the short audio clip (e.g., 60 seconds) back to Gemini.
    *   **Prompt:** "Transcribe this audio. Return a JSON object with `word`, `start_time_ms`, and `end_time_ms` for every single word."
    *   *Fallback:* If Gemini struggles with ms-level precision, use `faster-whisper` locally as a backup.

---

### Phase 4: Visual Processing (The "Eyes")
**Goal:** Convert 16:9 to 9:16 Vertical format.

1.  **Face Detection:**
    *   Run `MediaPipe Face Mesh` on the video clip.
    *   Identify the "Active Speaker" (Looking at camera + lips moving).
2.  **Dynamic Cropping:**
    *   Calculate the `x_center` of the face.
    *   Apply **Exponential Smoothing** (Math) to the camera movement so it "glides" rather than jitters.
    *   *Logic:* Create a 1080x1920 crop window centered on the smooth x-coordinate.

---

### Phase 5: The "Stealth Mode" (Heavily Transform)
**Goal:** Apply copyright evasion if the toggle is ON.

**FFmpeg Filter Chain:**
1.  **Mirroring:** `hflip` (Horizontal Flip).
2.  **Speed:** `atempo=1.05` (Audio), `setpts=1/1.05*PTS` (Video).
3.  **Pitch:** `asetrate=44100*0.98` (Shift pitch down slightly) or `rubberband` filter.
4.  **Metadata:** `-map_metadata -1` (Wipe all creation date/camera data).
5.  **Noise:** Overlay a 2% opacity noise grain layer.

---

### Phase 6: Rendering & UI Display
**Goal:** Output the final video.

1.  **Karaoke Overlay:**
    *   Draw text using the JSON data from Phase 3.
    *   Highlight current word in **Yellow/Green**, previous words in **White**.
    *   Burn subtitles into video using FFmpeg (`drawtext` filter or complex overlay).
2.  **UI Feedback:**
    *   Show the generated clips in the "Results List."
    *   Allow users to Preview (Play), Save, or Delete.

---

## 4. Development Roadmap (Step-by-Step)

### Step 1: The Skeleton
*   Set up Python environment.
*   Build the PyQt6 UI (The "Zero Friction" layout defined previously).
*   Create a `WorkerThread` class to handle background tasks without freezing the UI.

### Step 2: The Downloader & Chunker
*   Implement `yt-dlp` to fetch captions or audio.
*   Write the Python logic to slice audio/text into 30m chunks with overlap.

### Step 3: The Gemini Integration
*   Set up `google.generativeai` with API Key input.
*   Write the Prompt Engineering for "Viral detection."
*   Handle the JSON parsing.

### Step 4: The Clipper Engine
*   Implement MediaPipe for face coordinate extraction.
*   Write the FFmpeg script to crop 16:9 to 9:16 based on those coordinates.

### Step 5: The "Stealth" & Captioning
*   Implement the transcription request for karaoke timing.
*   Build the final FFmpeg render command that combines:
    *   Crop + Stealth Filters + Subtitles.

---

## 5. Risk Management & Edge Cases

*   **Gemini Rate Limits:** Use a `time.sleep(1)` between requests if hitting 429 errors, even with the 5-concurrency limit.
*   **No Face Detected:** If MediaPipe finds no face (e.g., gaming video), fallback to **Center Crop** or use YOLOv8 to find "Objects."
*   **FFmpeg Path:** Ensure `ffmpeg.exe` is bundled inside the app folder so the user doesn't have to install it manually.
*   **Large Files:** If a user drags a 10GB file, ensure the "Chunking" happens on the disk stream, not by loading 10GB into RAM.

---

## 6. Prompt Engineering Strategy (System Prompt for Gemini)

**For Viral Detection:**
> "You are an expert video editor for TikTok. You have been given a transcript/audio of a long video. Your job is to find the most viral, high-retention moments.
> Rules:
> 1. Clips must be between 30s and 60s.
> 2. Look for strong hooks, controversy, or high emotion.
> 3. Return output strictly as JSON: `[{'start': '00:10:00', 'end': '00:11:00', 'score': 95, 'reason': '...'}]`"

**For Karaoke Transcription:**
> "Transcribe the following audio segment. Output strictly JSON.
> Structure: `words: [{'word': 'Hello', 'start_ms': 100, 'end_ms': 500}, ...]`
> Ensure timestamps are extremely accurate."
**very importmant**
 1. Do not use TextClip from MoviePy on Windows if you can avoid it (it requires ImageMagick and often breaks).
 2. include all the packages in the @/requirements.txt and i will install them.
 3. do not change the ui