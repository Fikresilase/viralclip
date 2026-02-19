
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, 
    QFrame, QGridLayout, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QDesktopServices

from src.ui.theme import BG_DARK, SURFACE_DARK, PRIMARY, TEXT_WHITE, TEXT_MUTED, BORDER_DARK, SURFACE_INPUT

class ResultCard(QFrame):
    def __init__(self, data):
        super().__init__()
        self.data = data
        
        # Proper sizing for 9:16 aspect ratio shorts
        card_width = 220
        thumb_height = int(card_width * 16 / 9)  # 9:16 aspect ratio = ~391px
        
        self.setFixedWidth(card_width)
        self.setMinimumHeight(thumb_height + 120)  # thumb + info section
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 16px;
            }}
            QFrame:hover {{ border-color: {PRIMARY}; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(12)
        
        # Thumbnail (Vertical 9:16)
        self.thumb = QLabel()
        self.thumb.setFixedSize(card_width, thumb_height)
        self.thumb.setStyleSheet("background-color: #000; border-top-left-radius: 16px; border-top-right-radius: 16px;")
        self.thumb.setScaledContents(False)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pix = QPixmap(data['thumb'])
        if not pix.isNull():
            self.thumb.setPixmap(pix.scaled(card_width, thumb_height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.thumb)
        
        # Info section with proper spacing
        info_container = QWidget()
        info_l = QVBoxLayout(info_container)
        info_l.setContentsMargins(12, 4, 12, 0)
        info_l.setSpacing(6)

        title = QLabel(data['title'])
        title.setFont(QFont("Space Grotesk", 11, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {TEXT_WHITE};")
        title.setWordWrap(True)
        title.setMaximumHeight(40)
        info_l.addWidget(title)
        
        score_l = QHBoxLayout()
        score_l.setSpacing(6)
        score_l.setContentsMargins(0, 0, 0, 0)
        
        flash = QLabel("📈")
        flash.setStyleSheet(f"font-size: 12px;")
        score_l.addWidget(flash)
        
        score = QLabel(f"{data.get('score', '95%')} Viral Score")
        score.setFont(QFont("Space Grotesk", 10, QFont.Weight.Bold))
        score.setStyleSheet(f"color: {PRIMARY};")
        score_l.addWidget(score)
        score_l.addStretch()
        info_l.addLayout(score_l)

        layout.addWidget(info_container)
        
        # Action buttons with proper styling
        btns = QHBoxLayout()
        btns.setContentsMargins(12, 8, 12, 0)
        btns.setSpacing(8)
        
        p_btn = QPushButton("▶ Play")
        p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        p_btn.setFixedHeight(32)
        p_btn.setStyleSheet(f"""
            QPushButton {{
                background: white; 
                color: black; 
                border-radius: 6px; 
                font-size: 11px; 
                font-weight: bold;
                font-family: "Space Grotesk";
            }}
            QPushButton:hover {{
                background: {PRIMARY};
                color: white;
            }}
        """)
        p_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(data['path'])))
        
        s_btn = QPushButton("⬇")
        s_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        s_btn.setFixedSize(32, 32)
        s_btn.setStyleSheet(f"""
            QPushButton {{
                background: {SURFACE_INPUT}; 
                color: white; 
                border: 1px solid {BORDER_DARK};
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: white;
                color: black;
            }}
        """)
        s_btn.clicked.connect(self._save)
        
        btns.addWidget(p_btn, stretch=1)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Save Video", self.data['title']+".mp4", "Video (*.mp4)")
        if dest:
            import shutil
            shutil.copy2(self.data['path'], dest)

class ResultsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(32)
        
        # Header with proper styling
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        h_container = QHBoxLayout()
        h_container.setSpacing(12)
        
        icon = QLabel("🎬")
        icon.setFont(QFont("Segoe UI Emoji", 20))
        icon.setStyleSheet(f"color: {PRIMARY};")
        h_container.addWidget(icon)
        
        h_lbl = QLabel("Generated Clips")
        h_lbl.setFont(QFont("Space Grotesk", 20, QFont.Weight.Bold))
        h_lbl.setStyleSheet(f"color: {TEXT_WHITE};")
        h_container.addWidget(h_lbl)
        
        header.addLayout(h_container)
        header.addStretch()
        
        self.back_btn = QPushButton("↺ Start New Project")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFont(QFont("Space Grotesk", 11, QFont.Weight.Medium))
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED}; 
                background: transparent;
                border: none;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                color: {TEXT_WHITE};
            }}
        """)
        header.addWidget(self.back_btn)
        self.layout.addLayout(header)
        
        # Grid with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: transparent; border: none; }}")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(24)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.container)
        self.layout.addWidget(scroll)

    def populate(self, results):
        # Clear existing cards
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()
        
        # Calculate columns based on container width (responsive)
        # Default to 5 columns for large screens, adjust based on width
        cols = 5  # xl:grid-cols-5 from HTML
        
        for i, res in enumerate(results):
            card = ResultCard(res)
            self.grid.addWidget(card, i // cols, i % cols)

