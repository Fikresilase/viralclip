# 📜 ViralClips Development Rules

> **MANDATORY** - Read before contributing

## 🔒 Python Version

✅ **REQUIRED**: Python 3.11

This project is built and tested exclusively with **Python 3.11**. Using any other Python version may cause unexpected behavior.

```bash
# Verify your Python version
python --version
# Expected output: Python 3.11.x
```

---

## ⚠️ PyQt5 + PyQt6 Mixing is FORBIDDEN

### ❌ Mixing PyQt5 and PyQt6

> **DO NOT install or use PyQt5 alongside PyQt6**

 Mixing PyQt5 and PyQt6 in the same environment will break imports and cause runtime errors.

### Symptoms of Mixing

```
ImportError: DLL load failed while importing QtCore
AttributeError: module 'PyQt6.QtCore' has no attribute 'pyqtSignal'
```

### ✅ Correct Usage

```bash
# ✅ CORRECT - Only PyQt6
pip install PyQt6

# ❌ WRONG - Do NOT do this
pip install PyQt5  # FORBIDDEN
pip install PyQt6 PyQt5  # FORBIDDEN
```

### Uninstalling PyQt5 (if accidentally installed)

```bash
pip uninstall PyQt5
pip uninstall PyQt6
pip install PyQt6
```

---

## 📦 Dependency Management

### Installing Dependencies

```bash
# Always use the lock file
pip install -r requirements.txt
```

### Adding New Dependencies

```bash
# Add to requirements.txt with version pin
# Example: PyQt6==6.7.0
```

### Verified Working Dependencies

| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.11.x | Required |
| PyQt6 | ^6.7.0 | UI Framework |
| google-generativeai | ^0.5.0 | Gemini API |
| opencv-python | ^4.9.0 | Face tracking |
| moviepy | ^1.0.3 | Video processing |

---

## 🏗️ Code Standards

### Imports

```python
# ✅ CORRECT
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer

# ❌ WRONG - PyQt5 imports will fail
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
```

### Signal/Slot Connections

```python
# ✅ CORRECT - PyQt6 style
button.clicked.connect(self.handle_click)

# ❌ WRONG - PyQt5 legacy style
button.clicked.connect(self.handle_click)
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

---

## 🚀 Running the Application

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Run
python main.py
```

---

## 📝 Commit Conventions

Format: `<type>: <description>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `chore`: Maintenance

Example:
```
feat: Add face tracking for frame selection
fix: Resolve video export error
docs: Update README with FFmpeg instructions
```

---

## ⚡ Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | Uninstall PyQt5, reinstall PyQt6 |
| FFmpeg not found | Add FFmpeg to system PATH |
| API errors | Check GEMINI_API_KEY in .env |

---

## 📞 Questions?

Open an issue on GitHub if you encounter problems not covered here.
