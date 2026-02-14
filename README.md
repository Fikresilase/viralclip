# 🎬 ViralClips

Transform long videos into viral-ready shorts with AI-powered insights.

## 📌 Overview

ViralClips is a desktop application built with PyQt6 that automatically converts long-form videos into engaging viral shorts. It leverages Gemini AI for intelligent viral moment detection through transcript analysis and includes face tracking for optimal frame selection.

## ✨ Features

- **AI-Powered Viral Selection**: Send video transcripts to Gemini API to identify the most viral-worthy moments
- **Face Tracking**: Intelligent frame selection using face detection to keep subjects centered
- **Modern UI**: Beautiful, contemporary interface built with PyQt6
- **Video Processing**: Efficient video trimming and export capabilities

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| GUI Framework | PyQt6 |
| AI/ML | Google Gemini API, OpenCV |
| Video Processing | FFmpeg, MoviePy |

## 📋 Prerequisites

- Python 3.11 (required - see [RULES](RULES.md))
- FFmpeg installed and in PATH
- Google Gemini API key

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/viralclips.git
cd viralclips
```

### 2. Create Virtual Environment (Required)

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

### 5. Run the Application

```bash
python main.py
```

## 📁 Project Structure

```
viralclips/
├── src/
│   ├── ui/              # PyQt6 UI components
│   ├── core/            # Core processing logic
│   ├── ai/              # Gemini API integration
│   └── utils/           # Utility functions
├── assets/              # Icons, images, styles
├── config/              # Configuration files
├── tests/               # Unit tests
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── main.py              # Application entry point
└── README.md            # This file
```

## 🔧 Configuration

### FFmpeg Installation

**Windows (via Chocolatey):**
```bash
choco install ffmpeg
```

**Windows (Manual):**
1. Download from https://ffmpeg.org/download.html
2. Add `ffmpeg/bin` to your PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure only PyQt6 is installed (see [RULES](RULES.md))
2. **FFmpeg Not Found**: Add FFmpeg to your system PATH
3. **API Key Error**: Verify your Gemini API key in the `.env` file

## 📝 Development Guidelines

Please read [RULES.md](RULES.md) before contributing.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Google Gemini API
- PyQt6 Community
- OpenCV Contributors
