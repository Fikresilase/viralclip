"""
widgets.py - Reusable custom PyQt6 widgets for ViralClips.

Contains:
    - GlowButton:       Primary CTA button with pink glow effect
    - ToggleSwitch:      Custom animated toggle switch
    - IconBadge:         Small rounded icon container
    - UpgradeButton:     Header "Upgrade to Pro" button
    - DropZone:          Drag-and-drop file upload area
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
class IconBadge(QWidget):
    """
    A small rounded square with a background tint and a centered unicode/text icon.
    Used next to section headers (e.g. the link icon, upload icon).
    """

    def __init__(
        self,
        icon_text: str,
        bg_color: str = f"rgba(244, 37, 140, 0.1)",
        icon_color: str = PRIMARY,
        size: int = 32,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._icon_text = icon_text
        self._bg_color = bg_color
        self._icon_color = icon_color

    def paintEvent(self, a0):
        """Draw rounded rect background and centered icon text."""
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.setBrush(QBrush(QColor(self._bg_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

        # Icon text
        painter.setPen(QPen(QColor(self._icon_color)))
        font = QFont("Segoe UI", 13)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._icon_text)
        painter.end()


# ── Glow Button (Generate Shorts) ─────────────────────────────────────────────
class GlowButton(QPushButton):
    """
    Full-width primary action button with a pink drop-shadow glow.
    Matches the "Generate Shorts" CTA from the HTML design.
    """

    def __init__(self, text: str = "Generate Shorts", parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setMaximumHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        # Pink glow shadow
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(25)
        self._glow.setColor(QColor(244, 37, 140, 70))
        self._glow.setOffset(0, 0)
        self.setGraphicsEffect(self._glow)

        self._apply_style(PRIMARY)

    # ── Hover feedback ─────────────────────────────────────────────────────
    def enterEvent(self, event):
        self._apply_style(PRIMARY_HOVER)
        self._glow.setBlurRadius(35)
        self._glow.setColor(QColor(244, 37, 140, 110))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(PRIMARY)
        self._glow.setBlurRadius(25)
        self._glow.setColor(QColor(244, 37, 140, 70))
        super().leaveEvent(event)

    def _apply_style(self, bg: str):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 8px 16px;
            }}
        """)


# ── Upgrade Button ─────────────────────────────────────────────────────────────
class UpgradeButton(QPushButton):
    """Small header button: ⚡ Upgrade to Pro."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("⚡  Upgrade to Pro", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(QColor(244, 37, 140, 100))
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)


# ── Toggle Switch ──────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    """
    Custom animated toggle switch that mimics the HTML design.
    Emits `toggled(bool)` when state changes.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._knob_x = 2.0  # left position

        # Knob animation
        self._animation = QPropertyAnimation(self, b"knob_x")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── Qt property for animation ──────────────────────────────────────────
    @pyqtProperty(float)
    def knob_x(self) -> float:
        return self._knob_x

    @knob_x.setter
    def knob_x(self, value: float):
        self._knob_x = value
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        self._checked = checked
        end = 22.0 if checked else 2.0
        self._animation.setStartValue(self._knob_x)
        self._animation.setEndValue(end)
        self._animation.start()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.setChecked(self._checked)
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_color = QColor(PRIMARY) if self._checked else QColor(BG_DARK)
        border_color = QColor(PRIMARY) if self._checked else QColor(BORDER_DARK)
        
        painter.setBrush(QBrush(track_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(0, 0, 44, 24, 12, 12)

        # Knob
        if self._checked:
            knob_color = QColor(TEXT_WHITE)
            knob_border = QColor(TEXT_WHITE)
        else:
            knob_color = QColor(TEXT_MUTED)
            knob_border = QColor("#d1d5db") # gray-300

        painter.setBrush(QBrush(knob_color))
        painter.setPen(QPen(knob_border, 1))
        painter.drawEllipse(int(self._knob_x), 2, 20, 20)
        painter.end()


# ── Drop Zone (File Upload Area) ──────────────────────────────────────────────
class DropZone(QWidget):
    """
    Drag-and-drop file upload area with dashed border.
    Emits `fileDropped(str)` with the file path.
    """

    fileDropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(70)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovering = False

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Upload icon circle
        self._icon_label = QLabel("📤")
        self._icon_label.setFixedSize(32, 32)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFont(QFont("Segoe UI Emoji", 13))
        self._update_icon_style(False)
        layout.addWidget(self._icon_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("Drop files or browse")
        self._title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self._title.setStyleSheet(f"color: {TEXT_WHITE};")
        text_layout.addWidget(self._title)

        self._subtitle = QLabel("MP4, MOV up to 2GB")
        self._subtitle.setFont(QFont("Segoe UI", 9))
        self._subtitle.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(self._subtitle)

        layout.addLayout(text_layout)
        layout.addStretch()

    # ── Drag & Drop ────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._hovering = True
            self._update_icon_style(True)
            self.update()

    def dragLeaveEvent(self, event):
        self._hovering = False
        self._update_icon_style(False)
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._hovering = False
        self._update_icon_style(False)
        self.update()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.fileDropped.emit(path)

    def mousePressEvent(self, event):
        """Open file dialog on click."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)"
        )
        if path:
            self.fileDropped.emit(path)

    # ── Paint dashed border ────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = QColor(SURFACE_INPUT)
        if not self._hovering:
            bg_color.setAlpha(50)  # ~20% opacity
        else:
            bg_color = QColor(BLUE_ACCENT_BG)
            bg_color.setAlpha(100)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

        # Dashed border
        pen = QPen(QColor(BLUE_ACCENT if self._hovering else BORDER_DARK))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            self.rect().adjusted(1, 1, -1, -1), 12, 12
        )
        painter.end()

    def _update_icon_style(self, hover: bool):
        bg = BLUE_ACCENT_BG if hover else SURFACE_INPUT
        fg = BLUE_ACCENT if hover else TEXT_MUTED
        self._icon_label.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {BORDER_DARK};
            border-radius: 16px;
        """)


# ── Preview Widget ─────────────────────────────────────────────────────────────
class PreviewWidget(QWidget):
    """
    Displays a video thumbnail/preview image with a remove button.
    Used to replace the input area when a valid video is selected.
    """
    
    removeClicked = pyqtSignal()
    
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Internal state
        self._pixmap = None
        self._title = ""
        self._loading = False
        self._aspect_ratio = 16 / 9  # Default to 16:9
        
        # Layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Loading State
        self._loading_label = QLabel("Loading Preview...", self)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setFont(QFont("Segoe UI", 12))
        self._loading_label.setStyleSheet(f"color: {TEXT_MUTED};")
        self._loading_label.hide()
        
        # 2. Image Display (Custom Paint)
        # We handle painting in paintEvent to get rounded corners easily
        
        # 3. Overlay Controls (Close Button, Title)
        # We'll use a child widget for the overlay to position it absolutely?
        # Or just standard layout.
        
        # Let's use a container for the controls that sits on top
        self._overlay = QWidget(self)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._overlay.raise_()
        self._overlay.setGeometry(0, 0, 100, 100) # Will update in resizeEvent
        
        ov_layout = QVBoxLayout(self._overlay)
        ov_layout.setContentsMargins(12, 12, 12, 12)
        
        # Top Row: Close Button
        top_row = QHBoxLayout()
        top_row.addStretch()
        
        self.close_btn = QPushButton("✕", self._overlay)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.removeClicked.emit)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 0, 0, 0.85);
                color: {TEXT_WHITE};
                border-radius: 16px;
                border: 2px solid rgba(255, 255, 255, 0.5);
                font-weight: 900;
                font-size: 16px;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY};
                border-color: {PRIMARY};
            }}
        """)
        top_row.addWidget(self.close_btn)
        ov_layout.addLayout(top_row)
        
        ov_layout.addStretch()
        
        # Bottom Row: Title
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"""
            color: {TEXT_WHITE};
            background-color: rgba(0, 0, 0, 0.7);
            padding: 4px 8px;
            border-radius: 4px;
        """)
        self.title_label.setWordWrap(True)
        self.title_label.hide() # Show only when text is set
        ov_layout.addWidget(self.title_label)

        # 4. Final adjustments to layout
        # We need to make sure the overlay is above everything
        self._overlay.raise_()
        
    def set_loading(self, loading: bool):
        self._loading = loading
        self._loading_label.setVisible(loading)
        if loading:
            self._loading_label.setGeometry(self.rect())
        self._pixmap = None
        self.title_label.hide()
        self.close_btn.setVisible(not loading)
        self.update()
        
    def set_error(self, message: str):
        self._loading = False
        self._loading_label.setText(f"Error: {message}")
        self._loading_label.show()
        self._pixmap = None
        self.close_btn.show()
        self.update()
        
    def set_preview(self, pixmap: QPixmap, title: str):
        self._loading = False
        self._loading_label.hide()
        self._pixmap = pixmap
        self._title = title
        
        # Force 16:9 aspect ratio regardless of image dimensions
        self._aspect_ratio = 16 / 9
        
        if title:
            self.title_label.setText(title)
            self.title_label.show()
        else:
            self.title_label.hide()
            
        self.close_btn.show()
        self._overlay.raise_()
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, a0: int) -> int:
        return int(a0 / self._aspect_ratio)

    def resizeEvent(self, a0):
        self._overlay.setGeometry(self.rect())
        if self._loading_label.isVisible():
            self._loading_label.setGeometry(self.rect())
        super().resizeEvent(a0)
        
    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clip path for rounded corners
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        painter.setClipPath(path)
        
        # Background
        painter.setBrush(QBrush(QColor(SURFACE_INPUT)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
        
        # Draw Image if available (fit without cropping)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the image
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.drawPixmap(x, y, scaled)
        
        painter.end()



# ── API Key Button ─────────────────────────────────────────────────────────────
class ApiKeyButton(QPushButton):
    """Small header button: 🔑 API Key."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🔑  API Key", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {SURFACE_INPUT};
                color: {TEXT_WHITE};
                border: 1px solid {BORDER_DARK};
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border: 1px solid {PRIMARY};
                background-color: {SURFACE_DARK};
            }}
        """)
        self.clicked.connect(self._open_dialog)

    def _open_dialog(self):
        dlg = ApiKeyDialog(self)
        dlg.exec()


# ── API Key Dialog ─────────────────────────────────────────────────────────────
class ApiKeyDialog(QDialog):
    """Modal to Enter/Save/Remove API Key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Settings")
        self.setFixedSize(400, 220)
        
        # Apply theme to dialog
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_DARK};
            }}
            QLabel {{
                color: {TEXT_WHITE};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Title
        title = QLabel("Gemini API Key")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your API key here...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setFixedHeight(40)
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {SURFACE_INPUT};
                border: 1px solid {BORDER_DARK};
                border-radius: 8px;
                padding: 0 12px;
                color: {TEXT_WHITE};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {PRIMARY};
            }}
        """)
        layout.addWidget(self.key_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setFixedHeight(36)
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ff4444;
                border: 1px solid #ff4444;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 68, 68, 0.1);
            }}
        """)
        self.remove_btn.clicked.connect(self.remove_key)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(36)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
        self.save_btn.clicked.connect(self.save_key)
        
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        
        # Load existing
        self.settings = QSettings("ViralClips", "Content Factory")
        current_key = self.settings.value("gemini_api_key", "")
        if current_key:
            self.key_input.setText(current_key)
            
    def save_key(self):
        key = self.key_input.text().strip()
        if key:
            self.settings.setValue("gemini_api_key", key)
            QMessageBox.information(self, "Success", "API Key saved successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Please enter a valid API key.")
            
    def remove_key(self):
        self.settings.remove("gemini_api_key")
        self.key_input.clear()
        QMessageBox.information(self, "Removed", "API Key removed.")
        self.accept()
