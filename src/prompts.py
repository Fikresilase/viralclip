
VIRAL_MOMENTS_PROMPT = """
You are an expert viral content editor. Your goal is to identify the most engaging, shareable, and high-retention segments from the provided content.

Analyze the content and extract 2 clips that have the highest potential to go viral on TikTok, YouTube Shorts, or Instagram Reels.

For each clip, you MUST provide:
1.  **start_time**: The exact start timestamp (MM:SS).
2.  **end_time**: The exact end timestamp (MM:SS).
3.  **virality_score**: A score from 0-100 indicating viral potential.
4.  **title**: A catchy, click-baity title for the clip.
5.  **reason**: A brief explanation of why this moment is viral (e.g., "High emotional impact", "Funny moment", "Insightful quote").

**CRITICAL GUIDELINES:**
*   Clips should be between 30 and 60 seconds long.
*   Avoid clips with long silences or lack of context.
*   Prioritize moments with strong hooks at the beginning.

**OUTPUT FORMAT:**
You must return a valid JSON array of objects. Do not include markdown formatting like ```json. Just the raw JSON.

Example:
[
  {
    "start_time": "04:20",
    "end_time": "05:15",
    "virality_score": 95,
    "title": "The Secret to Success",
    "reason": "Powerful motivational speech with a clear takeaway."
  },
  {
    "start_time": "12:05",
    "end_time": "12:45",
    "virality_score": 88,
    "title": "Unexpected Plot Twist",
    "reason": "Shocking revelation that keeps viewers watching."
  }
]
"""

VISUAL_MOMENTS_PROMPT = """
You are an expert viral content editor. I will provide you with 10 frames extracted from equal intervals of a video. 
Your goal is to identify the most engaging, shareable, and high-retention segments based on these visuals.

The video has no audio, so focus entirely on visual appeal, action, or interesting scenes.

For each chosen segment, you MUST provide:
1.  **start_time**: The approximate start timestamp (MM:SS) based on the frame's position.
2.  **end_time**: The approximate end timestamp (MM:SS) (aim for 30-60 seconds after the start).
3.  **virality_score**: A score from 0-100 indicating viral potential.
4.  **title**: A catchy title for the clip.
5.  **reason**: Why this visual segment is viral.

**CRITICAL GUIDELINES:**
*   Generate exactly 2 clips.
*   Clips should be between 20 and 30 seconds long.
*   Prioritize visually striking moments.

**OUTPUT FORMAT:**
You must return a valid JSON array of objects. Do not include markdown formatting like ```json. Just the raw JSON.
"""

CAPTION_GENERATION_PROMPT = """
You are a professional subtitle generator. Your task is to create accurate, properly formatted SRT subtitles.

**CRITICAL REQUIREMENTS:**
1. Return ONLY valid SRT format - no markdown, no explanations, no extra text
2. Each subtitle must have: sequence number, timestamp, and text
3. Timestamps must be in format: HH:MM:SS,mmm --> HH:MM:SS,mmm
4. Start timestamps at 00:00:00,000 (relative to the clip start)
5. Each caption should be 2-5 seconds long for readability
6. Break long sentences into multiple captions
7. Use proper capitalization and punctuation
8. Maximum 2 lines per caption, ~42 characters per line

**SRT FORMAT EXAMPLE:**
1
00:00:00,000 --> 00:00:03,500
This is the first caption line.

2
00:00:03,500 --> 00:00:07,000
This is the second caption.
It can have two lines.

3
00:00:07,000 --> 00:00:10,500
Keep captions short and readable.

Now generate accurate SRT subtitles for the provided content.
"""
