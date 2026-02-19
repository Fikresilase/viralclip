"""
widgets.py - Reusable custom PyQt6 widgets for ViralClips.
"""

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect, QCheckBox, QSizePolicy, QDialog, QMessageBox,
    QLineEdit
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QMimeData, QSettings,
    QRectF, pyqtProperty
)
from PyQt6.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QDragEnterEvent, QDropEvent, 
    QPixmap, QPainterPath
)

from src.ui.theme import (
    PRIMARY, PRIMARY_HOVER, BG_DARK, SURFACE_DARK, SURFACE_INPUT,
    BORDER_DARK, TEXT_MUTED, TEXT_WHITE, BLUE_ACCENT, BLUE_ACCENT_BG
)

# ── Icon Badge ─────────────────────────────────────────────────────────────────
class IconBadge(QLabel):
    """Small rounded square icon sticker matching web design."""
    def __init__(self, icon: str, bg_color: str, fg_color: str, size: int = 32):
        super().__init__(icon)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI Emoji", 14))
        self.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 8px;
        """)

# ── Glow Button ────────────────────────────────────────────────────────────────
class GlowButton(QPushButton):
    """Primary action button with pink glow matching web design."""
    def __init__(self, text: str):
        super().__init__(f"{text}   ✨")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(40)
        self.shadow.setColor(QColor(244, 37, 140, 80))
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)
        
        self._apply_style(PRIMARY)

    def _apply_style(self, bg):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border-radius: 12px;
                font-weight: 700;
                font-size: 18px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #3f3f46;
                color: #71717a;
            }}
        """)

    def enterEvent(self, event):
        self.shadow.setBlurRadius(50)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.shadow.setBlurRadius(40)
        super().leaveEvent(event)

# ── Upgrade Button ─────────────────────────────────────────────────────────────
class UpgradeButton(QPushButton):
    """Pink gradient 'Upgrade to pro' button matching web design."""
    def __init__(self):
        super().__init__("⚡ Upgrade to pro")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(150)
        
        # Add glow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(244, 37, 140, 100))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 12px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)

# ── API Key Button ─────────────────────────────────────────────────────────────
class ApiKeyButton(QPushButton):
    """Dark 'API Key' button matching web design."""
    def __init__(self):
        super().__init__("🔑 API Key")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(110)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {SURFACE_DARK};
                color: {TEXT_WHITE};
                border: 1px solid {BORDER_DARK};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {SURFACE_INPUT};
            }}
        """)
        self.clicked.connect(self._open_dialog)

    def _open_dialog(self):
        from src.ui.widgets import ApiKeyDialog
        dlg = ApiKeyDialog(self)
        dlg.exec()

# ── Toggle Switch ──────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    """Minimal animated toggle."""
    toggled = pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.setFixedSize(36, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._knob_x = 2.0
        self.anim = QPropertyAnimation(self, b"knob_x")
        self.anim.setDuration(150)

    @pyqtProperty(float)
    def knob_x(self): return self._knob_x
    @knob_x.setter
    def knob_x(self, v): self._knob_x = v; self.update()

    def setChecked(self, c):
        self._checked = c
        self.anim.setEndValue(20.0 if c else 2.0)
        self.anim.start()

    def mousePressEvent(self, e):
        self._checked = not self._checked
        self.setChecked(self._checked)
        self.toggled.emit(self._checked)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#f4258c" if self._checked else "#3f3f46")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 9, 9)
        p.setBrush(QBrush(Qt.GlobalColor.white))
        p.drawEllipse(int(self._knob_x), 2, 14, 14)

# ── Drop Zone ──────────────────────────────────────────────────────────────────
class DropZone(QWidget):
    """Dashed upload container matching web design."""
    fileDropped = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedHeight(88)
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        self.icon_lbl = QLabel("☁️")
        self.icon_lbl.setFixedSize(40, 40)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(f"""
            background-color: {SURFACE_INPUT};
            color: {BLUE_ACCENT};
            border: 1px solid {BORDER_DARK};
            border-radius: 20px;
            font-size: 18px;
        """)
        layout.addWidget(self.icon_lbl)
        
        # Labels
        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        txt_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.t_lbl = QLabel("Drop files or browse")
        self.t_lbl.setFont(QFont("Space Grotesk", 12, QFont.Weight.Medium))
        txt_layout.addWidget(self.t_lbl)
        
        self.s_lbl = QLabel("MP4, MOV up to 2GB")
        self.s_lbl.setFont(QFont("Space Grotesk", 10))
        self.s_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        txt_layout.addWidget(self.s_lbl)
        
        layout.addLayout(txt_layout)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): 
            e.acceptProposedAction()
            self._hover = True
            self.update()
            
    def dragLeaveEvent(self, e): 
        self._hover = False
        self.update()
        
    def dropEvent(self, e):
        self._hover = False
        self.update()
        urls = e.mimeData().urls()
        if urls: 
            self.fileDropped.emit(urls[0].toLocalFile())

    def mousePressEvent(self, e):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.mov)")
        if path: 
            self.fileDropped.emit(path)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        p.setBrush(QBrush(QColor(SURFACE_INPUT) if not self._hover else QColor("#3b2330")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        
        # Dashed border
        pen = QPen(QColor(BLUE_ACCENT if self._hover else BORDER_DARK))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)

# ── Preview Widget ─────────────────────────────────────────────────────────────
class PreviewWidget(QWidget):
    """Large video preview with info."""
    removeClicked = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setFixedHeight(450)
        self._pixmap = None
        self._overlay = QWidget(self)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        l = QVBoxLayout(self._overlay)
        l.setContentsMargins(24, 24, 24, 24)
        
        # Close btn
        row1 = QHBoxLayout()
        row1.addStretch()
        self.c_btn = QPushButton("✕", self._overlay)
        self.c_btn.setFixedSize(32, 32)
        self.c_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.c_btn.clicked.connect(self.removeClicked.emit)
        self.c_btn.setStyleSheet("background: rgba(0,0,0,0.5); color: white; border-radius: 16px; font-weight: bold;")
        row1.addWidget(self.c_btn)
        l.addLayout(row1)
        
        l.addStretch()
        
        # Center Play Icon
        pi = QLabel("▶")
        pi.setFixedSize(60, 60)
        pi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pi.setStyleSheet(f"background: rgba(244,37,140,0.2); color: {PRIMARY}; border: 2px solid {PRIMARY}; border-radius: 30px; font-size: 20px; padding-left: 4px;")
        l.addWidget(pi, alignment=Qt.AlignmentFlag.AlignCenter)
        
        l.addStretch()
        
        # Title/Meta
        self.t_lbl = QLabel(self._overlay)
        self.t_lbl.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        l.addWidget(self.t_lbl)
        
        self.m_lbl = QLabel("10:45 duration • 1080p", self._overlay)
        self.m_lbl.setStyleSheet("color: #94a3b8;")
        l.addWidget(self.m_lbl)
        
        self._loading_label = QLabel("Analyzing Content...", self)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet("color: #94a3b8;")
        self._loading_label.hide()

    def set_loading(self, l):
        self._loading_label.setVisible(l)
        self._overlay.setVisible(not l)
        if l: self._loading_label.setText("Analyzing Content with Gemini AI...\nThis can take a few minutes.")
        self.update()

    def set_preview(self, p, t):
        self._loading_label.hide()
        self._pixmap = p
        self.t_lbl.setText(t or "Untitled Video")
        self._overlay.show()
        self.update()

    def set_error(self, error_msg):
        self._loading_label.hide()
        self._pixmap = None
        self.t_lbl.setText("Error Loading Preview")
        self.m_lbl.setText(error_msg)
        self._overlay.show()
        self.update()

    def resizeEvent(self, e):
        self._overlay.setGeometry(self.rect())
        self._loading_label.setGeometry(self.rect())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        p.setClipPath(path)
        p.setBrush(QBrush(QColor(SURFACE_DARK)))
        p.drawRect(self.rect())
        if self._pixmap:
            s = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((self.width()-s.width())//2, (self.height()-s.height())//2, s)

# ── API Key Dialog ─────────────────────────────────────────────────────────────
class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Settings")
        self.setFixedSize(400, 220)
        self.setStyleSheet(f"background: {BG_DARK};")
        l = QVBoxLayout(self)
        l.setContentsMargins(32, 32, 32, 32)
        l.setSpacing(16)
        
        t = QLabel("Gemini API Key")
        t.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        l.addWidget(t)
        
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Paste your API key...")
        self.inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp.setFixedHeight(40)
        l.addWidget(self.inp)
        
        btns = QHBoxLayout()
        r_btn = QPushButton("Remove")
        r_btn.setFixedSize(100, 34)
        r_btn.setStyleSheet("color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; font-weight: 600;")
        r_btn.clicked.connect(self.remove)
        
        s_btn = QPushButton("Save")
        s_btn.setFixedSize(100, 34)
        s_btn.setStyleSheet(f"background: {PRIMARY}; color: white; border-radius: 6px; font-weight: 600;")
        s_btn.clicked.connect(self.save)
        
        btns.addWidget(r_btn)
        btns.addStretch()
        btns.addWidget(s_btn)
        l.addLayout(btns)
        
        self.sets = QSettings("ViralClips", "Content Factory")
        self.inp.setText(self.sets.value("gemini_api_key", ""))

    def save(self):
        self.sets.setValue("gemini_api_key", self.inp.text().strip())
        self.accept()
    def remove(self):
        self.sets.remove("gemini_api_key")
        self.inp.clear()
        self.accept()
