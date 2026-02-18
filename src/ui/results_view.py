
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
        self.setFixedSize(220, 340)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Thumbnail
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(196, 110) # 16:9 approx
        thumb_lbl.setStyleSheet(f"background-color: #000; border-radius: 8px;")
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(data['thumb'])
        if not pixmap.isNull():
             thumb_lbl.setPixmap(pixmap.scaled(
                 thumb_lbl.size(), 
                 Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                 Qt.TransformationMode.SmoothTransformation
             ))
        layout.addWidget(thumb_lbl)
        
        # Title
        title = QLabel(data['title'])
        title.setWordWrap(True)
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_WHITE}; border: none;")
        title.setFixedHeight(40)
        title.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(title)
        
        # Score Badge
        score_container = QHBoxLayout()
        score_badge = QLabel(f"🔥 {data['score']}")
        score_badge.setStyleSheet(f"""
            background-color: rgba(244, 37, 140, 0.2);
            color: {PRIMARY};
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        """)
        score_container.addWidget(score_badge)
        score_container.addStretch()
        layout.addLayout(score_container)
        
        # Reason (Tooltip or small text)
        reason = QLabel(data['reason'])
        reason.setWordWrap(True)
        reason.setFont(QFont("Segoe UI", 8))
        reason.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        reason.setFixedHeight(30)
        layout.addWidget(reason)
        
        layout.addStretch()
        
        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        play_btn = QPushButton("▶ Play")
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                color: {TEXT_WHITE};
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {BORDER_DARK};
            }}
        """)
        play_btn.clicked.connect(self._play_video)
        
        dl_btn = QPushButton("💾 Save")
        dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                border: none;
                color: {TEXT_WHITE};
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #d61c78;
            }}
        """)
        dl_btn.clicked.connect(self._save_video)
        
        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(dl_btn)
        layout.addLayout(btn_layout)
        
    def _play_video(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.data['path']))
        
    def _save_video(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Video", 
            self.data['title'] + ".mp4", 
            "MP4 Files (*.mp4)"
        )
        if dest:
            import shutil
            try:
                shutil.copy2(self.data['path'], dest)
            except Exception as e:
                print(f"Error saving: {e}")

class ResultsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        header = QLabel("Viral Shorts Generated ✨")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {TEXT_WHITE}; margin-bottom: 16px;")
        layout.addWidget(header)
        
        # Grid Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {SURFACE_DARK}; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {BORDER_DARK}; border-radius: 4px; }}
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
        
        # Back Button
        self.back_btn = QPushButton("← Create More")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedSize(120, 36)
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {BORDER_DARK};
                color: {TEXT_MUTED};
                border-radius: 18px;
            }}
            QPushButton:hover {{
                color: {TEXT_WHITE};
                border-color: {TEXT_WHITE};
            }}
        """)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def populate(self, results):
        # Clear existing
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add cards
        row, col = 0, 0
        cols = 3 # 3 columns grid
        
        for item in results:
            card = ResultCard(item)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
