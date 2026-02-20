import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QStackedWidget, QFileDialog, 
    QDialog, QCheckBox, QComboBox, QGridLayout, QProgressBar,
    QFrame, QMessageBox, QApplication, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont, QIcon, QPainter, QBrush, QPen

from src.workers.preview_worker import PreviewWorker
from src.workers.generator_worker import GeneratorWorker
from src.ui.flow_layout import FlowLayout

from PyQt6.QtWidgets import QGraphicsDropShadowEffect

def add_shadow(widget, radius=20, y_offset=8, alpha=40):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)

STYLE_SHEET = """
QWidget {
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    color: #E0E0E0;
    background-color: #121212;
}

QMainWindow, QDialog {
    background-color: #121212;
}

QFrame#headerPanel {
    background-color: #1E1E1E;
    border-bottom: 1px solid #333333;
}

QFrame#inputCard, QFrame#resultsSection, QFrame#settingsPanel {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 8px;
}

QFrame#innerGroup, QFrame#resultItem {
    background-color: #181818;
    border: 1px solid #333333;
    border-radius: 8px;
}

QLineEdit, QComboBox {
    background-color: #2D2D2D;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 8px 12px;
    color: #E0E0E0;
    font-size: 13px;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
    background-color: #252525;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9CA3AF;
    margin-right: 12px;
}

QComboBox QAbstractItemView {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 4px;
    selection-background-color: #2D2D2D;
    outline: none;
}

QPushButton {
    background-color: #2D2D2D;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 12px;
    color: #E0E0E0;
    font-weight: 500;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3A3A3A;
}
QPushButton:pressed {
    background-color: #2D2D2D;
}

QPushButton#primaryBtn {
    background-color: #2563EB;
    color: white;
    border: none;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 4px;
}
QPushButton#primaryBtn:hover {
    background-color: #1D4ED8;
}
QPushButton#primaryBtn:pressed {
    background-color: #1E40AF;
}

QPushButton#linkBtn {
    background-color: #2D2D2D;
    border: 1px solid #333333;
    color: #9CA3AF;
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
}
QPushButton#linkBtn:hover {
    color: #E0E0E0;
    background-color: #3A3A3A;
}

QPushButton#browseBtn {
    background-color: #2D2D2D;
    border: 1px solid #333333;
    color: #E0E0E0;
    height: 60px;
    font-weight: 500;
    font-size: 13px;
    border-radius: 4px;
}
QPushButton#browseBtn:hover {
    background-color: #3A3A3A;
    border: 1px solid #4A4A4A;
    color: #FFFFFF;
}

QCheckBox {
    spacing: 12px;
    padding: 8px 12px;
    background-color: #2D2D2D;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #E0E0E0;
    font-size: 13px;
    font-weight: 600;
}
QCheckBox:hover {
    background-color: #3A3A3A;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    background-color: #121212;
    border: 1px solid #333333;
    border-radius: 2px;
}
QCheckBox::indicator:hover {
    border: 1px solid #2563EB;
}
QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
}

QProgressBar {
    background-color: #2D2D2D;
    border: 1px solid #333333;
    border-radius: 2px;
    height: 16px;
    text-align: right;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 2px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #121212;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4a4a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QLabel#pageHeadingTitle {
    font-size: 30px;
    font-weight: 700;
    color: white;
    background-color: transparent;
}
QLabel#pageHeadingSub {
    color: #9CA3AF;
    font-size: 14px;
    background-color: transparent;
    margin-top: 4px;
}
QLabel#cardTitle {
    font-size: 15px;
    font-weight: 700;
    color: white;
    background-color: transparent;
}
QLabel#labelText {
    font-size: 13px;
    font-weight: 600;
    color: white;
    background-color: transparent;
    margin-bottom: 2px;
}
QLabel#mutedText {
    font-size: 12px;
    color: #9CA3AF;
    background-color: transparent;
}
QLabel#resultTitle {
    font-size: 14px;
    font-weight: 700;
    color: white;
    background-color: transparent;
}

QFrame#thumbnailFrame {
    background-color: #000000;
    border: 1px solid #333333;
    border-radius: 4px;
}
"""

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setFixedSize(350, 220)
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
        
        lbl = QLabel("API Key Configuration")
        lbl.setObjectName("labelText")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter Gemini API key...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        saved_key = self.settings.value("api_key", "")
        if saved_key:
            self.api_input.setText(saved_key)
            
        c_layout.addWidget(lbl)
        c_layout.addWidget(self.api_input)
        c_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("primaryBtn")
        
        clear_btn.clicked.connect(self.clear_key)
        apply_btn.clicked.connect(self.save_key)
        
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(apply_btn)
        
        c_layout.addLayout(btn_layout)
        
        layout.addWidget(header)
        layout.addWidget(content)

    def clear_key(self):
        self.api_input.clear()
        self.settings.remove("api_key")

    def save_key(self):
        val = self.api_input.text().strip()
        if val:
            self.settings.setValue("api_key", val)
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
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setObjectName("resultItem")
        add_shadow(self, radius=12, y_offset=4, alpha=30)
        self.data = data
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Thumbnail Base
        thumb_frame = QFrame()
        thumb_frame.setObjectName("thumbnailFrame")
        thumb_frame.setFixedSize(160, 284)
        
        thumb_layout = QVBoxLayout(thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load image
        if os.path.exists(data.get('thumb', '')):
            pixmap = QPixmap(data['thumb']).scaled(160, 284, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pixmap)
            
        thumb_layout.addWidget(img_label)
        
        # Overlay title
        title_lbl = QLabel(data.get('title', 'Generated Clip'))
        title_lbl.setObjectName("resultTitle")
        title_lbl.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0), stop:1 rgba(0,0,0,200)); padding: 8px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;")
        title_lbl.setFixedHeight(40)
        
        # Absolute positioning for overlay
        title_lbl.setParent(thumb_frame)
        title_lbl.setGeometry(0, 244, 160, 40)
        
        # Buttons
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
        self.setWindowTitle("Content Factory")
        self.resize(1024, 768)
        
        # Set central widget to use app background
        self.setStyleSheet(STYLE_SHEET)
        
        self.settings = QSettings()
        
        self.source = ""
        self.is_local = False
        
        self._init_ui()

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
        app_title = QLabel("Content Factory")
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
        
        h1 = QLabel("Automated Video Shorts")
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
        
        # Inner Stack for Input vs Preview Settings
        self.inner_stack = QStackedWidget()
        
        # Inner Page 0: The Inputs
        inputs_widget = QWidget()
        in_grid = QGridLayout(inputs_widget)
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
        
        u_lbl = QLabel("<span style='color: #2563EB;'>🔗</span> URL Source")
        u_lbl.setTextFormat(Qt.TextFormat.RichText)
        u_lbl.setObjectName("labelText")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.textChanged.connect(self.on_url_changed)
        
        u_sub = QLabel("Paste a link to any public video.")
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
        
        f_lbl = QLabel("<span style='color: #2563EB;'>📁</span> Local File")
        f_lbl.setTextFormat(Qt.TextFormat.RichText)
        f_lbl.setObjectName("labelText")
        
        browse_btn = QPushButton("📄 Browse Files...")
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self.browse_files)
        
        f_layout.addWidget(f_lbl)
        f_layout.addWidget(browse_btn)
        f_layout.addStretch()
        
        in_grid.addWidget(url_box, 0, 0)
        in_grid.addWidget(file_box, 0, 1)
        
        self.inner_stack.addWidget(inputs_widget)
        
        # Inner Page 1: Preview & Settings
        preview_opts_widget = QWidget()
        po_layout = QHBoxLayout(preview_opts_widget)
        po_layout.setContentsMargins(0, 0, 0, 0)
        po_layout.setSpacing(24)
        
        # Left: Thumb
        thumb_v = QVBoxLayout()
        thumb_lbl = QLabel("Video Preview")
        thumb_lbl.setObjectName("labelText")
        
        self.preview_image = QLabel()
        self.preview_image.setObjectName("thumbnailFrame")
        self.preview_image.setMinimumSize(320, 180)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Absolute positioning overlay inside preview_image isn't clean with layouts unless we use a wrapper.
        # Let's wrap it.
        preview_wrap = QFrame()
        preview_wrap.setMinimumSize(320, 180)
        p_layout = QVBoxLayout(preview_wrap)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.addWidget(self.preview_image)
        
        self.preview_title = QLabel("Title")
        self.preview_title.setObjectName("resultTitle")
        self.preview_title.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0), stop:1 rgba(0,0,0,220)); padding: 12px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;")
        
        self.preview_title.setParent(preview_wrap)
        # We will adjust geometry dynamically or use layout. Better to use layout alignment.
        # Let's put it back to normal layout but overlapping.
        self.preview_title.setVisible(False) # we can set visibility or handle in resizeEvent. We'll stick to a simpler approach: Just add it as a child of preview_image later or use a layout inside it.
        
        # Wait, the easiest way is to let preview_title just sit inside the image using a QVBoxLayout on preview_image.
        img_layout = QVBoxLayout(self.preview_image)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.addWidget(self.preview_title, alignment=Qt.AlignmentFlag.AlignBottom)
        
        # Simulate video thumb layout
        thumb_v.addWidget(thumb_lbl)
        thumb_v.addWidget(self.preview_image)
        
        play_prev = QPushButton("▶ Preview Media")
        thumb_v.addWidget(play_prev)
        
        po_layout.addLayout(thumb_v, 1)
        
        # Right: Settings
        settings_box = QFrame()
        # Remove innerGroup styling and shadow to match Image 2 which shows it flat inside the card
        # Or wait, Image 2 shows settings are just directly on the card!
        s_layout = QVBoxLayout(settings_box)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(12)
        
        s_title = QLabel("2. Generation Settings")
        s_title.setObjectName("cardTitle")
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #333333;")
        
        # Smart crop box
        sc_box = QFrame()
        sc_box.setStyleSheet("background-color: #2D2D2D; border: 1px solid #333333; border-radius: 4px;")
        sc_layout = QVBoxLayout(sc_box)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sc_layout.setSpacing(4)
        
        self.smart_crop_chk = QCheckBox("Enable Smart Crop")
        self.smart_crop_chk.setChecked(True)
        self.smart_crop_chk.setStyleSheet("border: none; background-color: transparent;")
        
        sc_sub = QLabel("Keep speakers centered")
        sc_sub.setObjectName("mutedText")
        sc_sub.setStyleSheet("border: none; background-color: transparent; padding-left: 28px;") # align with text
        
        sc_layout.addWidget(self.smart_crop_chk)
        sc_layout.addWidget(sc_sub)
        
        c_lbl = QLabel("Caption Style")
        c_lbl.setObjectName("labelText")
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Hormozi Style (Bold, Emojis)", 
            "Minimalist (Clean, Standard)", 
            "Gaming (High Contrast)"
        ])
        
        generate_btn = QPushButton("🎬 Generate Shorts")
        generate_btn.setObjectName("primaryBtn")
        generate_btn.setFixedHeight(44)
        generate_btn.clicked.connect(self.on_generate)
        
        s_layout.addWidget(s_title)
        s_layout.addWidget(sep2)
        s_layout.addWidget(sc_box)
        s_layout.addSpacing(6)
        s_layout.addWidget(c_lbl)
        s_layout.addWidget(self.style_combo)
        s_layout.addStretch()
        s_layout.addWidget(generate_btn)
        
        po_layout.addWidget(settings_box, 1)
        
        self.inner_stack.addWidget(preview_opts_widget)
        
        ic_layout.addWidget(self.inner_stack)
        
        self.main_stack.addWidget(self.input_card)
        
        # --- Page 1: Results Section ---
        self.results_section = QFrame()
        self.results_section.setObjectName("resultsSection")
        add_shadow(self.results_section)
        res_layout = QVBoxLayout(self.results_section)
        res_layout.setContentsMargins(24, 24, 24, 24)
        res_layout.setSpacing(16)
        
        res_header = QHBoxLayout()
        res_title = QLabel("<span style='color: #2563EB;'>▶</span> Output Gallery")
        res_title.setTextFormat(Qt.TextFormat.RichText)
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
            # Short delay to allow user to paste fully
            QTimer.singleShot(300, lambda: self.start_preview(self.url_input.text().strip(), False))

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
        self.inner_stack.setCurrentIndex(1)
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
        self.inner_stack.setCurrentIndex(0)
        self.cancel_btn.setVisible(False)
        self.url_input.clear()
        self.source = ""
        self.is_local = False
        self.preview_image.clear()
        self.preview_title.clear()

    def on_generate(self):
        api_key = self.settings.value("api_key", "").strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please configure your Gemini API Key in Settings first.")
            self.open_settings()
            return
            
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        
        self.g_worker = GeneratorWorker(self.source, self.is_local, api_key)
        self.g_worker.progress.connect(self.loading_dialog.update_text)
        self.g_worker.finished.connect(self.on_generate_finished)
        self.g_worker.error.connect(self.on_generate_error)
        self.g_worker.start()

    def on_generate_finished(self, results):
        if self.loading_dialog:
            self.loading_dialog.accept()
            
        self.populate_results(results)
        self.heading_widget.setVisible(False)
        self.main_stack.setCurrentIndex(1)

    def on_generate_error(self, err):
        if self.loading_dialog:
            self.loading_dialog.accept()
        QMessageBox.critical(self, "Generation Error", str(err))

    def populate_results(self, results):
        # Clear existing
        for i in reversed(range(self.results_grid.count())): 
            item = self.results_grid.itemAt(i)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
                
        if not results:
            lbl = QLabel("No viral moments found.")
            self.results_grid.addWidget(lbl)
            return

        for i, res in enumerate(results):
            item_widget = ResultItem(res, self)
            self.results_grid.addWidget(item_widget)

    def reset_all(self):
        self.reset_input()
        self.heading_widget.setVisible(True)
        self.main_stack.setCurrentIndex(0)
