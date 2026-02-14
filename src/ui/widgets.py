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
    QGraphicsDropShadowEffect, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QMimeData
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QDragEnterEvent, QDropEvent

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

    def paintEvent(self, event):
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
    @property
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

        # Cloud icon circle
        self._icon_label = QLabel("☁")
        self._icon_label.setFixedSize(32, 32)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFont(QFont("Segoe UI", 13))
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
