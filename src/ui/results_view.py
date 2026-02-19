
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, 
    QFrame, QGridLayout, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QDesktopServices, QPainter, QLinearGradient, QBrush

from src.ui.theme import BG_DARK, SURFACE_DARK, PRIMARY, PRIMARY_HOVER, TEXT_WHITE, TEXT_MUTED, BORDER_DARK, SURFACE_INPUT

class ResultCard(QFrame):
    def __init__(self, data):
        super().__init__()
        self.data = data
        
        # Proper sizing for 9:16 aspect ratio shorts
        card_width = 240
        thumb_height = int(card_width * 16 / 9)  # 9:16 aspect ratio
        
        self.setFixedSize(card_width, thumb_height)
        
        # Main container styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 16px;
            }}
            QFrame:hover {{ border-color: {PRIMARY}; }}
        """)
        
        # Background Image (Thumbnail)
        self.bg_label = QLabel(self)
        self.bg_label.setFixedSize(card_width, thumb_height)
        self.bg_label.setStyleSheet("border-radius: 16px; background-color: #000;")
        self.bg_label.setScaledContents(True)
        
        pix = QPixmap(data['thumb'])
        if not pix.isNull():
            # Crop to aspect ratio if needed, or just scale
            scaled = pix.scaled(
                card_width, thumb_height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center crop logic could go here, but simple scaling is okay for now
            self.bg_label.setPixmap(scaled)
            
        # Overlay Container (Gradient + Content)
        self.overlay = QWidget(self)
        self.overlay.setFixedSize(card_width, thumb_height)
        self.overlay.setStyleSheet("background: transparent; border-radius: 16px;")
        
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(16, 16, 16, 16)
        
        # Top: Viral Score Badge
        top_row = QHBoxLayout()
        top_row.addStretch()
        
        score_badge = QLabel(f"📈 {data.get('score', '95%')}")
        score_badge.setFixedHeight(24)
        score_badge.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.6);
            color: {PRIMARY};
            border: 1px solid {PRIMARY};
            border-radius: 12px;
            padding: 0 8px;
            font-family: "Space Grotesk";
            font-weight: bold;
            font-size: 11px;
        """)
        top_row.addWidget(score_badge)
        overlay_layout.addLayout(top_row)
        
        overlay_layout.addStretch()
        
        # Bottom: Title + Actions
        bottom_container = QWidget()
        bottom_container.setStyleSheet("background: transparent;")
        bottom_l = QVBoxLayout(bottom_container)
        bottom_l.setContentsMargins(0, 0, 0, 0)
        bottom_l.setSpacing(8)
        
        # Title
        title = QLabel(data['title'])
        title.setFont(QFont("Space Grotesk", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title.setWordWrap(True)
        title.setMaximumHeight(60)
        
        # Add shadow effect to title for better readability
        shadow = QGraphicsDropShadowEffect(title)
        shadow.setBlurRadius(4)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(1, 1)
        title.setGraphicsEffect(shadow)
        
        bottom_l.addWidget(title)
        
        # Buttons Row
        btns = QHBoxLayout()
        btns.setSpacing(8)
        
        p_btn = QPushButton("▶ Play")
        p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        p_btn.setFixedHeight(32)
        p_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY};
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                font-family: "Space Grotesk";
                border: none;
            }}
            QPushButton:hover {{
                background: {PRIMARY_HOVER};
            }}
        """)
        p_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(data['path'])))
        
        s_btn = QPushButton("⬇")
        s_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        s_btn.setFixedSize(32, 32)
        s_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.4);
            }}
        """)
        s_btn.clicked.connect(self._save)
        
        btns.addWidget(p_btn, stretch=1)
        btns.addWidget(s_btn)
        bottom_l.addLayout(btns)
        
        overlay_layout.addWidget(bottom_container)

    def paintEvent(self, event):
        # Draw the gradient overlay manually since stylesheet gradients on widgets can be tricky with transparency
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Gradient from bottom to middle
        grad = QLinearGradient(0, self.height(), 0, self.height() * 0.4)
        grad.setColorAt(0, QColor(0, 0, 0, 240))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 16, 16)

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

