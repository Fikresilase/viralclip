import re

def parse_time(ts):
    """Parse MM:SS, HH:MM:SS or SS.mmm to seconds"""
    ts = str(ts).split('.')[0].split(',')[0]
    parts = list(map(int, ts.split(':')))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:
        return parts[0]
    else:
        raise ValueError(f"Invalid timestamp format: {ts}")

def seconds_to_ass_time(s):
    """Convert seconds to ASS timestamp format (H:MM:SS.cc)."""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int((sec % 1) * 100)
    sec = int(sec)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

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

def srt_time_to_ass_time(srt_time):
    """Convert SRT timestamp (HH:MM:SS,mmm) to ASS timestamp (H:MM:SS.cc)."""
    parts = srt_time.replace(',', '.').split(':')
    h = int(parts[0])
    m = parts[1]
    s_ms = parts[2].split('.')
    s = s_ms[0]
    ms = s_ms[1] if len(s_ms) > 1 else '000'
    cs = ms[:2]  # centiseconds (first 2 digits of milliseconds)
    return f"{h}:{m}:{s}.{cs}"

def vtt_time_to_seconds(time_str):
    """Convert VTT timestamp to seconds."""
    parts = time_str.strip().replace(',', '.').split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0
