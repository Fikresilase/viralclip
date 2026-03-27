import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QStackedWidget, QFileDialog, 
    QDialog, QCheckBox, QComboBox, QGridLayout, QProgressBar,
    QFrame, QMessageBox, QApplication, QScrollArea, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont, QIcon, QPainter, QBrush, QPen

from src.workers.preview_worker import PreviewWorker, YOUTUBE_REGEX
from src.workers.generator_worker import GeneratorWorker
from src.ui.flow_layout import FlowLayout

from PyQt6.QtWidgets import QGraphicsDropShadowEffect

def add_shadow(widget, radius=20, y_offset=8, alpha=60):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)

class ToggleButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self._checked = False
        self._animation_position = 0.0
        
    def setChecked(self, checked):
        self._checked = checked
        self._animation_position = 1.0 if checked else 0.0
        self.update()
        
    def isChecked(self):
        return self._checked
        
    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._animation_position = 1.0 if self._checked else 0.0
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background track with gradient
        if self._checked:
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, 44, 24)
            gradient.setColorAt(0, QColor("#3B82F6"))
            gradient.setColorAt(1, QColor("#2563EB"))
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(QColor("#3A3A3A")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 44, 24, 12, 12)
        
        # Knob
        knob_x = int(2 + (18 * self._animation_position))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(knob_x, 2, 20, 20)

STYLE_SHEET = """
QWidget {
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    color: #E0E0E0;
    background-color: #0F0F0F;
}

QMainWindow, QDialog {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #0F0F0F, 
        stop:1 #1A1A1A);
}

QFrame#headerPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #1E1E1E, 
        stop:1 #181818);
    border-bottom: 1px solid #2A2A2A;
}

QFrame#inputCard, QFrame#resultsSection, QFrame#settingsPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #1E1E1E, 
        stop:1 #181818);
    border: 1px solid #2A2A2A;
    border-radius: 12px;
}

QFrame#innerGroup, QFrame#resultItem {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #222222, 
        stop:1 #1A1A1A);
    border: 1px solid #2A2A2A;
    border-radius: 10px;
}

QFrame#resultItem:hover {
    border: 1px solid #3B82F6;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #252525, 
        stop:1 #1D1D1D);
}

QLineEdit, QComboBox {
    background-color: #1A1A1A;
    border: 1.5px solid #2A2A2A;
    border-radius: 8px;
    padding: 10px 14px;
    color: #F0F0F0;
    font-size: 13px;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QComboBox:focus {
    border: 1.5px solid #3B82F6;
    background-color: #1F1F1F;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 35px;
    border-left: 1px solid #3A3A3A;
    background-color: #252525;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox::drop-down:hover {
    background-color: #2D2D2D;
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #E0E0E0;
}

QComboBox QAbstractItemView {
    background-color: #1E1E1E;
    border: 1px solid #2A2A2A;
    border-radius: 8px;
    selection-background-color: #2D2D2D;
    outline: none;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2D2D2D, 
        stop:1 #252525);
    border: 1px solid #3A3A3A;
    border-radius: 8px;
    padding: 8px 16px;
    color: #F0F0F0;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3A3A3A, 
        stop:1 #2D2D2D);
    border: 1px solid #4A4A4A;
}
QPushButton:pressed {
    background: #252525;
    border: 1px solid #2A2A2A;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3B82F6, 
        stop:1 #2563EB);
    color: white;
    border: none;
    font-weight: 700;
    padding: 10px 20px;
    border-radius: 8px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #60A5FA, 
        stop:1 #3B82F6);
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2563EB, 
        stop:1 #1D4ED8);
}

QPushButton#linkBtn {
    background-color: transparent;
    border: 1px solid #3A3A3A;
    color: #9CA3AF;
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton#linkBtn:hover {
    color: #F0F0F0;
    background-color: #2A2A2A;
    border: 1px solid #4A4A4A;
}

QPushButton#browseBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2D2D2D, 
        stop:1 #252525);
    border: 2px dashed #3A3A3A;
    color: #E0E0E0;
    height: 60px;
    font-weight: 600;
    font-size: 13px;
    border-radius: 10px;
}
QPushButton#browseBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3A3A3A, 
        stop:1 #2D2D2D);
    border: 2px dashed #4A4A4A;
    color: #FFFFFF;
}

QCheckBox {
    spacing: 12px;
    padding: 10px 14px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2D2D2D, 
        stop:1 #252525);
    border: 1px solid #3A3A3A;
    border-radius: 8px;
    color: #F0F0F0;
    font-size: 13px;
    font-weight: 600;
}
QCheckBox:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3A3A3A, 
        stop:1 #2D2D2D);
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #1A1A1A;
    border: 2px solid #3A3A3A;
    border-radius: 4px;
}
QCheckBox::indicator:hover {
    border: 2px solid #3B82F6;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3B82F6, 
        stop:1 #2563EB);
    border-color: #2563EB;
}

QProgressBar {
    background-color: #1A1A1A;
    border: 1px solid #2A2A2A;
    border-radius: 8px;
    height: 20px;
    text-align: right;
    color: #F0F0F0;
    font-weight: 600;
    font-size: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3B82F6, 
        stop:1 #8B5CF6);
    border-radius: 8px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2A2A2A;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #3A3A3A;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    height: 0px;
}

QLabel#pageHeadingTitle {
    font-size: 36px;
    font-weight: 800;
    color: white;
    background-color: transparent;
    letter-spacing: -1px;
}
QLabel#pageHeadingSub {
    color: #9CA3AF;
    font-size: 15px;
    background-color: transparent;
    margin-top: 6px;
}
QLabel#cardTitle {
    font-size: 16px;
    font-weight: 700;
    color: white;
    background-color: transparent;
    letter-spacing: -0.3px;
}
QLabel#labelText {
    font-size: 14px;
    font-weight: 600;
    color: #F0F0F0;
    background-color: transparent;
    margin-bottom: 4px;
}
QLabel#mutedText {
    font-size: 12px;
    color: #9CA3AF;
    background-color: transparent;
    line-height: 1.4;
}
QLabel#resultTitle {
    font-size: 14px;
    font-weight: 700;
    color: white;
    background-color: transparent;
}

QFrame#thumbnailFrame {
    background-color: #000000;
    border: 1px solid #2A2A2A;
    border-radius: 8px;
}
"""

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        
        # Set window icon
        icon_path = self._get_resource_path(os.path.join("src", "assets", "logo.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        elif os.path.exists(self._get_resource_path(os.path.join("src", "assets", "favicon.ico"))):
            self.setWindowIcon(QIcon(self._get_resource_path(os.path.join("src", "assets", "favicon.ico"))))

        self.setFixedSize(400, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.settings = QSettings()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QFrame()
        header.setObjectName("innerGroup")
        header.setStyleSheet("border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        h_layout = QHBoxLayout(header)
        title = QLabel("Application Settings")
        title.setObjectName("cardTitle")
        
        close_btn = QPushButton("✖")
        close_btn.setObjectName("linkBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(close_btn)
        
        content = QWidget()
        c_layout = QVBoxLayout(content)
        
        # AI Provider info
        provider_label = QLabel("AI Provider")
        provider_label.setObjectName("labelText")
        provider_info = QLabel("OpenAI")
        provider_info.setObjectName("mutedText")
        
        c_layout.addWidget(provider_label)
        c_layout.addWidget(provider_info)
        c_layout.addSpacing(10)
        
        # OpenAI API Key
        self.openai_label = QLabel("OpenAI API Key")
        self.openai_label.setObjectName("labelText")
        self.openai_input = QLineEdit()
        self.openai_input.setPlaceholderText("Enter OpenAI API key...")
        self.openai_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        saved_openai_key = self.settings.value("openai_api_key", "")
        if saved_openai_key:
            self.openai_input.setText(saved_openai_key)
        
        c_layout.addWidget(self.openai_label)
        c_layout.addWidget(self.openai_input)
        
        c_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("primaryBtn")
        
        clear_btn.clicked.connect(self.clear_keys)
        apply_btn.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(apply_btn)
        
        c_layout.addLayout(btn_layout)
        
        layout.addWidget(header)
        layout.addWidget(content)

    def _get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # Running as script: return current project directory
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def clear_keys(self):
        self.openai_input.clear()
        self.settings.remove("openai_api_key")

    def save_settings(self):
        openai_key = self.openai_input.text().strip()
        if openai_key:
            self.settings.setValue("openai_api_key", openai_key)
        
        self.accept()

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(340, 160)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setObjectName("settingsPanel")
        self.setStyleSheet("QDialog { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        self.title = QLabel("Processing Job")
        self.title.setObjectName("cardTitle")
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        
        self.status = QLabel("Initializing...")
        self.status.setObjectName("mutedText")
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(self.title)
        layout.addSpacing(10)
        layout.addWidget(self.progress)
        layout.addSpacing(4)
        layout.addWidget(self.status)

    def update_text(self, text):
        self.status.setText(text)

class ResultItem(QFrame):
    def __init__(self, data, parent=None, is_placeholder=False):
        super().__init__(parent)
        self.setObjectName("resultItem")
        add_shadow(self, radius=12, y_offset=4, alpha=30)
        self.data = data
        self.is_placeholder = is_placeholder
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Thumbnail Base
        thumb_frame = QFrame()
        thumb_frame.setObjectName("thumbnailFrame")
        thumb_frame.setFixedSize(160, 284)
        
        thumb_layout = QVBoxLayout(thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        if is_placeholder:
            # Show progress bar instead of image
            progress_container = QWidget()
            progress_container.setStyleSheet("background-color: transparent;")
            progress_layout = QVBoxLayout(progress_container)
            progress_layout.setContentsMargins(20, 100, 20, 100)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p%")
            
            self.status_label = QLabel("Processing")
            self.status_label.setObjectName("mutedText")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_label.setStyleSheet("background-color: transparent; color: #9CA3AF;")
            
            progress_layout.addWidget(self.progress_bar)
            progress_layout.addSpacing(10)
            progress_layout.addWidget(self.status_label)
            progress_layout.addStretch()
            
            thumb_layout.addWidget(progress_container)
        else:
            # Show actual image
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Load image
            if os.path.exists(data.get('thumb', '')):
                pixmap = QPixmap(data['thumb']).scaled(160, 284, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                img_label.setPixmap(pixmap)
                
            thumb_layout.addWidget(img_label)
        
        # Title and score overlay (always visible)
        title_text = data.get('title', 'Generated Clip')
        score = data.get('score', 0)
        
        overlay_widget = QWidget()
        overlay_widget.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 rgba(0,0,0,0), 
                stop:0.2 rgba(0,0,0,120),
                stop:1 rgba(0,0,0,240));
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(4)
        
        title_lbl = QLabel(title_text)
        title_lbl.setObjectName("resultTitle")
        title_lbl.setStyleSheet("background-color: transparent; color: white; font-size: 13px;")
        title_lbl.setWordWrap(True)
        title_lbl.setMaximumWidth(140)  # Constrain to card width minus padding
        title_lbl.setMaximumHeight(50)  # Fixed height for title
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        score_lbl = QLabel(f"⭐ {score}/10")
        score_lbl.setStyleSheet("background-color: transparent; color: #60A5FA; font-size: 12px; font-weight: 700;")
        score_lbl.setFixedHeight(20)
        
        overlay_layout.addWidget(title_lbl)
        overlay_layout.addWidget(score_lbl)
        
        # Absolute positioning for overlay - positioned lower with fixed height
        overlay_widget.setParent(thumb_frame)
        overlay_widget.setGeometry(0, 200, 160, 84)
        
        # Buttons
        if not is_placeholder:
            play_btn = QPushButton("Play Video")
            save_btn = QPushButton("Save Output")
            save_btn.setObjectName("primaryBtn")
            
            play_btn.clicked.connect(self.play_video)
            save_btn.clicked.connect(self.save_video)
            
            layout.addWidget(thumb_frame)
            layout.addSpacing(10)
            layout.addWidget(play_btn)
            layout.addWidget(save_btn)
        else:
            layout.addWidget(thumb_frame)
    
    def update_progress(self, percentage, status_text):
        """Update the progress bar for placeholder cards - only show 'Processing'"""
        if self.is_placeholder and hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(percentage)
            # Always show "Processing" regardless of status_text
            self.status_label.setText("Processing")
    
    def convert_to_final(self, data):
        """Convert placeholder to final result with thumbnail and buttons"""
        self.data = data
        self.is_placeholder = False
        
        # Clear existing layout
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Rebuild with final content
        thumb_frame = QFrame()
        thumb_frame.setObjectName("thumbnailFrame")
        thumb_frame.setFixedSize(160, 284)
        
        thumb_layout = QVBoxLayout(thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(data.get('thumb', '')):
            pixmap = QPixmap(data['thumb']).scaled(160, 284, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pixmap)
            
        thumb_layout.addWidget(img_label)
        
        # Title and score overlay
        title_text = data.get('title', 'Generated Clip')
        score = data.get('score', 0)
        
        overlay_widget = QWidget()
        overlay_widget.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 rgba(0,0,0,0), 
                stop:0.2 rgba(0,0,0,120),
                stop:1 rgba(0,0,0,240));
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(4)
        
        title_lbl = QLabel(title_text)
        title_lbl.setObjectName("resultTitle")
        title_lbl.setStyleSheet("background-color: transparent; color: white; font-size: 13px;")
        title_lbl.setWordWrap(True)
        title_lbl.setMaximumWidth(140)  # Constrain to card width minus padding
        title_lbl.setMaximumHeight(50)  # Fixed height for title
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        score_lbl = QLabel(f"⭐ {score}/10")
        score_lbl.setStyleSheet("background-color: transparent; color: #60A5FA; font-size: 12px; font-weight: 700;")
        score_lbl.setFixedHeight(20)
        
        overlay_layout.addWidget(title_lbl)
        overlay_layout.addWidget(score_lbl)
        
        overlay_widget.setParent(thumb_frame)
        overlay_widget.setGeometry(0, 200, 160, 84)
        
        play_btn = QPushButton("Play Video")
        save_btn = QPushButton("Save Output")
        save_btn.setObjectName("primaryBtn")
        
        play_btn.clicked.connect(self.play_video)
        save_btn.clicked.connect(self.save_video)
        
        layout.addWidget(thumb_frame)
        layout.addSpacing(10)
        layout.addWidget(play_btn)
        layout.addWidget(save_btn)

    def play_video(self):
        path = self.data.get('path', '')
        if os.path.exists(path):
            os.startfile(path) if os.name == 'nt' else os.system(f"xdg-open '{path}'")
        else:
            QMessageBox.warning(self, "Error", "Video file not found.")

    def save_video(self):
        path = self.data.get('path', '')
        if not os.path.exists(path):
            QMessageBox.warning(self, "Error", "Video file not found.")
            return
            
        dest, _ = QFileDialog.getSaveFileName(self, "Save Video", os.path.basename(path), "Video (*.mp4)")
        if dest:
            import shutil
            shutil.copy2(path, dest)
            QMessageBox.information(self, "Success", "Video saved successfully.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ViralClip")
        
        # Set window icon
        icon_path = self._get_resource_path(os.path.join("src", "assets", "logo.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        elif os.path.exists(self._get_resource_path(os.path.join("src", "assets", "favicon.ico"))):
            self.setWindowIcon(QIcon(self._get_resource_path(os.path.join("src", "assets", "favicon.ico"))))
            
        self.resize(1024, 768)
        
        # Set central widget to use app background
        self.setStyleSheet(STYLE_SHEET)
        
        self.settings = QSettings()
        
        self.source = ""
        self.is_local = False
        
        # Track placeholder cards for progress updates
        self.placeholder_cards = []
        
        self._init_ui()
    
    def closeEvent(self, event):
        """Clean up temp files when app closes"""
        from src.utils.storage import StorageManager
        StorageManager().cleanup()
        event.accept()

    def _get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # Running as script: return current project directory
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header (ToolBar equivalent)
        header = QFrame()
        header.setObjectName("headerPanel")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        
        title_box = QHBoxLayout()
        icon_lbl = QLabel("🤖")
        icon_lbl.setStyleSheet("font-size: 24px; background-color: transparent;")
        app_title = QLabel("ViralClip")
        app_title.setStyleSheet("font-weight: 800; font-size: 16px; color: #FAFAFA; background-color: transparent; letter-spacing: -0.5px;")
        title_box.addWidget(icon_lbl)
        title_box.addWidget(app_title)
        title_box.addStretch()
        
        action_box = QHBoxLayout()
        action_box.setSpacing(12)
        api_btn = QPushButton("🔑 API Key")
        upgrade_btn = QPushButton("⚡ Upgrade to pro")
        upgrade_btn.setObjectName("primaryBtn")
        
        api_btn.clicked.connect(self.open_settings)
        
        action_box.addWidget(api_btn)
        action_box.addWidget(upgrade_btn)
        
        h_layout.addLayout(title_box)
        h_layout.addLayout(action_box)
        
        main_layout.addWidget(header)
        
        # Content Area - scrollable stack
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(40, 24, 40, 24)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        content_container = QWidget()
        content_container.setMaximumWidth(850)
        cc_layout = QVBoxLayout(content_container)
        cc_layout.setContentsMargins(0,0,0,0)
        cc_layout.setSpacing(24)
        
        # Top Heading (Visible only on Page 0)
        self.heading_widget = QWidget()
        hw_layout = QVBoxLayout(self.heading_widget)
        hw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hw_layout.setContentsMargins(0,0,0,0)
        hw_layout.setSpacing(8)
        
        h1 = QLabel("Get Viral Shorts Instantly")
        h1.setObjectName("pageHeadingTitle")
        h1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h2 = QLabel("Provide a video source to begin extraction and generation.")
        h2.setObjectName("pageHeadingSub")
        h2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        hw_layout.addWidget(h1)
        hw_layout.addWidget(h2)
        cc_layout.addWidget(self.heading_widget)
        
        # Main Stacks
        self.main_stack = QStackedWidget()
        cc_layout.addWidget(self.main_stack)
        
        scroll_layout.addWidget(content_container)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # --- Page 0: Input Card ---
        self.input_card = QFrame()
        self.input_card.setObjectName("inputCard")
        add_shadow(self.input_card)
        ic_layout = QVBoxLayout(self.input_card)
        ic_layout.setContentsMargins(24, 24, 24, 24)
        ic_layout.setSpacing(16)
        
        # Card Header
        card_header = QHBoxLayout()
        lbl_1 = QLabel("1. Select Media Source")
        lbl_1.setObjectName("cardTitle")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.reset_input)
        
        card_header.addWidget(lbl_1)
        card_header.addStretch()
        card_header.addWidget(self.cancel_btn)
        ic_layout.addLayout(card_header)
        
        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #333333;")
        ic_layout.addWidget(sep)
        
        # Inner Page 0: The Inputs
        self.inputs_widget = QWidget()
        in_grid = QGridLayout(self.inputs_widget)
        in_grid.setContentsMargins(0, 0, 0, 0)
        in_grid.setSpacing(24)
        in_grid.setColumnStretch(0, 1)
        in_grid.setColumnStretch(1, 1)
        
        # URL Block
        url_box = QFrame()
        url_box.setObjectName("innerGroup")
        add_shadow(url_box, radius=10, y_offset=4, alpha=20)
        u_layout = QVBoxLayout(url_box)
        u_layout.setContentsMargins(20, 20, 20, 20)
        u_layout.setSpacing(12)
        
        u_lbl = QLabel("🔗 URL Source")
        u_lbl.setObjectName("labelText")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.textChanged.connect(self.on_url_changed)
        
        u_sub = QLabel("Paste a link to a youtube video.")
        u_sub.setObjectName("mutedText")
        
        u_layout.addWidget(u_lbl)
        u_layout.addWidget(self.url_input)
        u_layout.addWidget(u_sub)
        u_layout.addStretch()
        
        # File Block
        file_box = QFrame()
        file_box.setObjectName("innerGroup")
        add_shadow(file_box, radius=10, y_offset=4, alpha=20)
        f_layout = QVBoxLayout(file_box)
        f_layout.setContentsMargins(20, 20, 20, 20)
        f_layout.setSpacing(12)
        
        f_lbl = QLabel("📁 Local File")
        f_lbl.setObjectName("labelText")
        
        browse_btn = QPushButton("⬆ Browse Files...")
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self.browse_files)
        
        f_layout.addWidget(f_lbl)
        f_layout.addWidget(browse_btn)
        f_layout.addStretch()
        
        in_grid.addWidget(url_box, 0, 0)
        in_grid.addWidget(file_box, 0, 1)
        in_grid.setRowStretch(1, 1)
        
        ic_layout.addWidget(self.inputs_widget)
        
        # Inner Page 1: Preview & Settings
        self.preview_opts_widget = QWidget()
        po_layout = QHBoxLayout(self.preview_opts_widget)
        po_layout.setContentsMargins(0, 0, 0, 0)
        po_layout.setSpacing(24)
        
        # Left: Thumb (centered container)
        thumb_container = QWidget()
        thumb_container_layout = QVBoxLayout(thumb_container)
        thumb_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        thumb_v = QVBoxLayout()
        thumb_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        thumb_lbl = QLabel("Video Preview")
        thumb_lbl.setObjectName("labelText")
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_image = QLabel()
        self.preview_image.setObjectName("thumbnailFrame")
        self.preview_image.setFixedSize(320, 180)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title with fixed width and height
        title_container = QWidget()
        title_container.setFixedSize(320, 65)
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(0, 0, 0, 0)
        title_container_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.preview_title = QLabel("Title")
        self.preview_title.setObjectName("resultTitle")
        self.preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_title.setWordWrap(True)
        self.preview_title.setMaximumWidth(320)
        self.preview_title.setMaximumHeight(65)
        self.preview_title.setStyleSheet("background-color: transparent; padding: 8px 0px;")
        
        title_container_layout.addWidget(self.preview_title)
        
        thumb_v.addWidget(thumb_lbl)
        thumb_v.addWidget(self.preview_image)
        thumb_v.addWidget(title_container)
        
        thumb_container_layout.addLayout(thumb_v)
        
        po_layout.addWidget(thumb_container, 1)
        
        # Right: Settings
        settings_box = QWidget()
        s_layout = QVBoxLayout(settings_box)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(12)
        s_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        s_title = QLabel("2. Generation Settings")
        s_title.setObjectName("cardTitle")
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #333333;")
        
        # Smart crop box
        sc_box = QFrame()
        sc_box.setStyleSheet("background-color: #2D2D2D; border: 1px solid #333333; border-radius: 4px;")
        sc_layout = QHBoxLayout(sc_box)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sc_layout.setSpacing(12)
        
        sc_text_layout = QVBoxLayout()
        # Clip Count Box
        cc_box = QFrame()
        cc_box.setStyleSheet("background-color: #2D2D2D; border: 1px solid #333333; border-radius: 4px;")
        cc_layout = QHBoxLayout(cc_box)
        cc_layout.setContentsMargins(12, 12, 12, 12)
        cc_layout.setSpacing(12)
        
        cc_text_layout = QVBoxLayout()
        cc_text_layout.setSpacing(2)
        
        cc_label = QLabel("Clip Count")
        cc_label.setObjectName("labelText")
        cc_label.setStyleSheet("border: none; background-color: transparent;")
        
        cc_sub = QLabel("Number of clips to generate")
        cc_sub.setObjectName("mutedText")
        cc_sub.setStyleSheet("border: none; background-color: transparent;")
        
        cc_text_layout.addWidget(cc_label)
        cc_text_layout.addWidget(cc_sub)
        
        self.clip_count_spinbox = QSpinBox()
        self.clip_count_spinbox.setMinimum(1)
        self.clip_count_spinbox.setMaximum(15)
        self.clip_count_spinbox.setValue(5)
        self.clip_count_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #1A1A1A;
                border: 1px solid #404040;
                border-radius: 4px;
                color: white;
                padding: 4px;
                width: 40px;
                height: 24px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                background-color: transparent;
            }
        """)
        
        cc_layout.addLayout(cc_text_layout)
        cc_layout.addStretch()
        cc_layout.addWidget(self.clip_count_spinbox)

        # Auto caption box
        ac_box = QFrame()
        ac_box.setStyleSheet("background-color: #2D2D2D; border: 1px solid #333333; border-radius: 4px;")
        ac_layout = QHBoxLayout(ac_box)
        ac_layout.setContentsMargins(12, 12, 12, 12)
        ac_layout.setSpacing(12)
        
        ac_text_layout = QVBoxLayout()
        ac_text_layout.setSpacing(2)
        
        ac_label = QLabel("Auto Caption")
        ac_label.setObjectName("labelText")
        ac_label.setStyleSheet("border: none; background-color: transparent;")
        
        ac_sub = QLabel("Generate captions automatically")
        ac_sub.setObjectName("mutedText")
        ac_sub.setStyleSheet("border: none; background-color: transparent;")
        
        ac_text_layout.addWidget(ac_label)
        ac_text_layout.addWidget(ac_sub)
        
        self.auto_caption_toggle = ToggleButton()
        self.auto_caption_toggle.setChecked(False)
        
        ac_layout.addLayout(ac_text_layout)
        ac_layout.addStretch()
        ac_layout.addWidget(self.auto_caption_toggle)
        
        generate_btn = QPushButton("🎬 Generate Shorts")
        generate_btn.setObjectName("primaryBtn")
        generate_btn.setFixedHeight(44)
        generate_btn.setFixedWidth(320)
        generate_btn.clicked.connect(self.on_generate)
        
        s_layout.addWidget(s_title)
        s_layout.addWidget(sep2)
        s_layout.addWidget(cc_box)
        s_layout.addWidget(ac_box)
        s_layout.addSpacing(20)
        s_layout.addWidget(generate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        po_layout.addWidget(settings_box, 1)
        
        ic_layout.addWidget(self.preview_opts_widget)
        self.preview_opts_widget.setVisible(False)
        
        self.main_stack.addWidget(self.input_card)
        
        # --- Page 1: Results Section ---
        self.results_section = QFrame()
        self.results_section.setObjectName("resultsSection")
        add_shadow(self.results_section)
        res_layout = QVBoxLayout(self.results_section)
        res_layout.setContentsMargins(24, 24, 24, 24)
        res_layout.setSpacing(16)
        
        res_header = QHBoxLayout()
        res_title = QLabel("▶ Output Gallery")
        res_title.setObjectName("cardTitle")
        
        restart_btn = QPushButton("↻ Start Over")
        restart_btn.setObjectName("linkBtn")
        restart_btn.clicked.connect(self.reset_all)
        
        res_header.addWidget(res_title)
        res_header.addStretch()
        res_header.addWidget(restart_btn)
        res_layout.addLayout(res_header)
        
        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet("background-color: #333333;")
        res_layout.addWidget(sep3)
        
        # Empty state message
        self.empty_state = QLabel("No clips generated yet")
        self.empty_state.setObjectName("mutedText")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("font-size: 14px; padding: 40px; color: #6B7280;")
        res_layout.addWidget(self.empty_state)
        
        # Grid for Outputs
        self.results_grid_widget = QWidget()
        self.results_grid = FlowLayout(self.results_grid_widget, hSpacing=16, vSpacing=16)
        
        res_layout.addWidget(self.results_grid_widget)
        
        self.main_stack.addWidget(self.results_section)
        
        # Keep references to dialogs
        self.loading_dialog = None

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def on_url_changed(self, text):
        if "http" in text:
            # Validate YouTube URL before preview
            if not YOUTUBE_REGEX.match(text.strip()):
                return
            # Short delay to allow user to paste fully - check widget still exists
            QTimer.singleShot(300, lambda: self._safe_start_preview(text.strip(), False))
    
    def _safe_start_preview(self, source, is_local):
        """Safe wrapper to prevent crashes if widget destroyed"""
        try:
            if self.isVisible() and source:
                self.start_preview(source, is_local)
        except RuntimeError:
            # Widget was destroyed, ignore
            pass

    def browse_files(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '', "Video files (*.mp4 *.mkv *.avi *.mov)")
        if fname:
            self.start_preview(fname, True)

    def start_preview(self, source, is_local):
        if not source:
            return
            
        self.source = source
        self.is_local = is_local
        
        # Prevent double triggers
        self.url_input.blockSignals(True)
        
        # Show loading state locally
        self.preview_image.setText("Loading Preview...")
        self.inputs_widget.setVisible(False)
        self.preview_opts_widget.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        self.p_worker = PreviewWorker(source, is_local)
        self.p_worker.previewReady.connect(self.on_preview_ready)
        self.p_worker.errorOccurred.connect(self.on_preview_error)
        self.p_worker.start()



    def on_preview_ready(self, qimage, title):
        pixmap = QPixmap.fromImage(qimage)
        self.preview_image.setPixmap(pixmap.scaled(self.preview_image.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        self.preview_title.setText(title)
        self.url_input.blockSignals(False)

    def on_preview_error(self, msg):
        QMessageBox.warning(self, "Preview Error", f"Failed to fetch preview:\n{msg}")
        self.reset_input()
        self.url_input.blockSignals(False)

    def reset_input(self):
        self.preview_opts_widget.setVisible(False)
        self.inputs_widget.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.url_input.clear()
        self.source = ""
        self.is_local = False
        self.preview_image.clear()
        self.preview_title.clear()

    def on_generate(self):
        # Get OpenAI API key
        api_key = self.settings.value("openai_api_key", "").strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please configure your OpenAI API Key in Settings first.")
            self.open_settings()
            return
        
        # Get caption setting
        enable_captions = self.auto_caption_toggle.isChecked()
        
        # Get clip count
        num_clips = self.clip_count_spinbox.value()
        
        # Show loading dialog until clips are found
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.update_text(f"Analyzing content for {num_clips} viral moments...")
        self.loading_dialog.show()
            
        self.g_worker = GeneratorWorker(self.source, self.is_local, api_key, enable_captions, num_clips)
        self.g_worker.progress.connect(lambda msg: print(f"[Worker] {msg}"))
        self.g_worker.clipsFound.connect(self.on_clips_found)
        self.g_worker.clipProgress.connect(self.on_clip_progress)
        self.g_worker.clipComplete.connect(self.on_clip_complete)
        self.g_worker.finished.connect(self.on_generate_finished)
        self.g_worker.error.connect(self.on_generate_error)
        self.g_worker.start()
    
    def on_clips_found(self, segments):
        """Create placeholder cards when clips are identified"""
        # Close loading dialog and switch to results view
        if self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        
        self.heading_widget.setVisible(False)
        self.main_stack.setCurrentIndex(1)
        
        self.clear_results_grid()
        self.placeholder_cards = []
        
        # Hide empty state when adding clips
        self.empty_state.setVisible(False)
        
        for i, seg in enumerate(segments):
            placeholder_data = {
                'title': seg.get('title', f'Clip {i+1}'),
                'thumb': '',
                'path': '',
                'score': seg.get('virality_score', 0),
                'reason': seg.get('reason', '')
            }
            card = ResultItem(placeholder_data, self, is_placeholder=True)
            self.results_grid.addWidget(card)
            self.placeholder_cards.append(card)
    
    def on_clip_progress(self, clip_index, percentage, status_text):
        """Update progress for a specific clip"""
        if 0 <= clip_index < len(self.placeholder_cards):
            self.placeholder_cards[clip_index].update_progress(percentage, status_text)
    
    def on_clip_complete(self, clip_index, result_data):
        """Convert placeholder to final card when clip completes"""
        if 0 <= clip_index < len(self.placeholder_cards):
            self.placeholder_cards[clip_index].convert_to_final(result_data)
    
    def clear_results_grid(self):
        """Clear all items from results grid and delete associated files"""
        # Collect file paths before clearing widgets
        files_to_delete = []
        for i in range(self.results_grid.count()):
            item = self.results_grid.itemAt(i)
            if item:
                w = item.widget()
                if w and hasattr(w, 'data'):
                    # Collect video and thumbnail paths
                    if 'path' in w.data and w.data['path']:
                        files_to_delete.append(w.data['path'])
                    if 'thumb' in w.data and w.data['thumb']:
                        files_to_delete.append(w.data['thumb'])
        
        # Clear UI widgets
        for i in reversed(range(self.results_grid.count())): 
            item = self.results_grid.itemAt(i)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
        self.placeholder_cards = []
        
        # Delete files from disk
        import os
        for filepath in files_to_delete:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"[UI] Deleted: {filepath}")
            except Exception as e:
                print(f"[UI] Failed to delete {filepath}: {e}")
        
        # Show empty state when grid is cleared
        self.empty_state.setVisible(self.results_grid.count() == 0)

    def on_generate_finished(self, results):
        # All clips are done - nothing special to do since cards already converted individually
        pass

    def on_generate_error(self, err):
        if self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        QMessageBox.critical(self, "Generation Error", str(err))
        self.reset_all()

    def reset_all(self):
        self.reset_input()
        self.clear_results_grid()
        self.heading_widget.setVisible(True)
        self.main_stack.setCurrentIndex(0)
