
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, 
    QFrame, QGridLayout, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QDesktopServices

from src.ui.theme import BG_DARK, SURFACE_DARK, PRIMARY, TEXT_WHITE, TEXT_MUTED, BORDER_DARK

class ResultCard(QFrame):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setFixedSize(200, 380)
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
        layout.setSpacing(10)
        
        # Thumbnail (Vertical 9:16)
        self.thumb = QLabel()
        self.thumb.setFixedHeight(280)
        self.thumb.setStyleSheet("background-color: #000; border-top-left-radius: 16px; border-top-right-radius: 16px;")
        
        pix = QPixmap(data['thumb'])
        if not pix.isNull():
            self.thumb.setPixmap(pix.scaled(200, 280, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.thumb)
        
        # Info
        info_l = QVBoxLayout()
        info_l.setContentsMargins(12, 0, 12, 0)
        info_l.setSpacing(4)

        title = QLabel(data['title'])
        title.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        title.setWordWrap(True)
        title.setFixedHeight(34)
        info_l.addWidget(title)
        
        score_l = QHBoxLayout()
        score_l.setSpacing(4)
        flash = QLabel("⚡")
        flash.setStyleSheet(f"color: {PRIMARY}; font-size: 10px;")
        score_l.addWidget(flash)
        
        score = QLabel(f"{data.get('score', '95%')} Viral Score")
        score.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        score.setStyleSheet(f"color: {PRIMARY};")
        score_l.addWidget(score)
        score_l.addStretch()
        info_l.addLayout(score_l)

        layout.addLayout(info_l)
        
        # Hover Overlay Actions (Simplified for this version)
        btns = QHBoxLayout()
        btns.setContentsMargins(12, 0, 12, 0)
        
        p_btn = QPushButton("▶ Play")
        p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        p_btn.setFixedHeight(28)
        p_btn.setStyleSheet(f"background: white; color: black; border-radius: 4px; font-size: 10px; font-weight: bold;")
        p_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(data['path'])))
        
        s_btn = QPushButton("⬇")
        s_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        s_btn.setFixedSize(28, 28)
        s_btn.setStyleSheet(f"background: #3f3f46; color: white; border-radius: 4px;")
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
        self.layout.setSpacing(24)
        
        # Header
        header = QHBoxLayout()
        h_lbl = QLabel("🗓️ Generated Clips")
        h_lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.addWidget(h_lbl)
        header.addStretch()
        
        self.back_btn = QPushButton("↺ Start New Project")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        header.addWidget(self.back_btn)
        self.layout.addLayout(header)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(24)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.container)
        self.layout.addWidget(scroll)

    def populate(self, results):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()
        for i, res in enumerate(results):
            self.grid.addWidget(ResultCard(res), i // 4, i % 4)

