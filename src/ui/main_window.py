"""
main_window.py - Main application window for ViralClips.

Recreates the HTML/Tailwind "Content Factory" design as a native PyQt6 window:
    ┌─────────────────────────────────────────────────┐
    │  Header  (logo + Upgrade to Pro)                │
    ├─────────────────────────────────────────────────┤
    │  Hero heading                                   │
    │  ┌───────────────────────────────────────────┐  │
    │  │  Paste URL  │  OR  │  Upload File         │  │
    │  ├───────────────────────────────────────────┤  │
    │  │  Smart Transform  │  Output Language      │  │
    │  ├───────────────────────────────────────────┤  │
    │  │         [ Generate Shorts ✨ ]             │  │
    │  └───────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────┘
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QFrame, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QLinearGradient, QPen

from src.ui.theme import (
    PRIMARY, PRIMARY_HOVER, BG_DARK, SURFACE_DARK, SURFACE_INPUT,
    BORDER_DARK, TEXT_MUTED, TEXT_WHITE, BLUE_ACCENT, BLUE_ACCENT_BG,
    GLOBAL_STYLESHEET
)
from src.ui.widgets import (
    GlowButton, UpgradeButton, ToggleSwitch, IconBadge, DropZone
)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Content Factory — AI Video Generator")
        self.setMinimumSize(600, 600)
        self.resize(1000, 750)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # Central scroll area so the UI is scrollable on small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Header ─────────────────────────────────────────────────────
        root_layout.addWidget(self._build_header())

        # ── 2. Body (centered content) ────────────────────────────────────
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 24, 16, 24)
        body_layout.setSpacing(0)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Hero heading
        body_layout.addWidget(self._build_hero(), alignment=Qt.AlignmentFlag.AlignHCenter)
        body_layout.addSpacing(24)

        # Main card
        body_layout.addWidget(self._build_main_card(), alignment=Qt.AlignmentFlag.AlignHCenter)
        body_layout.addStretch()

        root_layout.addWidget(body, stretch=1)

    # ══════════════════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════════════════
    def _build_header(self) -> QWidget:
        """Sticky top bar with logo and upgrade button."""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(34, 16, 25, 0.95);
                border-bottom: 1px solid {BORDER_DARK};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        # Logo
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)

        robot_icon = QLabel("🤖")
        robot_icon.setFont(QFont("Segoe UI Emoji", 20))
        robot_icon.setStyleSheet(f"color: {PRIMARY};")
        logo_layout.addWidget(robot_icon)

        title = QLabel("Content Factory")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_WHITE};")
        logo_layout.addWidget(title)

        layout.addLayout(logo_layout)
        layout.addStretch()

        # Upgrade button
        layout.addWidget(UpgradeButton())

        return header

    # ══════════════════════════════════════════════════════════════════════
    #  HERO HEADING
    # ══════════════════════════════════════════════════════════════════════
    def _build_hero(self) -> QWidget:
        """Centered heading + subtitle."""
        hero = QWidget()
        hero.setMaximumWidth(700)
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main heading (two lines)
        heading = QLabel("Turn long videos into\nviral Shorts instantly.")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        heading.setWordWrap(True)
        # Use rich text for the pink "viral Shorts" part
        heading.setText(
            '<p style="line-height:1.2; letter-spacing:-0.5px;">'
            '<span style="color: white;">Turn long videos into</span><br/>'
            f'<span style="color: {PRIMARY};">viral Shorts</span>'
            ' <span style="color: white;">instantly.</span>'
            '</p>'
        )
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)

        # Subtitle
        subtitle = QLabel("Paste a link, customize your vibe, and let AI do the editing, captioning, and b-roll.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet(f"color: {TEXT_MUTED};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return hero

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN CARD
    # ══════════════════════════════════════════════════════════════════════
    def _build_main_card(self) -> QWidget:
        """The large rounded card containing all inputs and the CTA."""
        card = QFrame()
        card.setMinimumWidth(320)
        card.setMaximumWidth(900)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 16px;
            }}
        """)
        card.setObjectName("mainCard")

        # Card shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        # ── Top row: URL input | OR | Upload ──────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(0)

        # Left: Paste URL section
        top_row.addLayout(self._build_url_section(), stretch=1)

        # Vertical divider with "OR"
        top_row.addWidget(self._build_or_divider())

        # Right: Upload section
        top_row.addLayout(self._build_upload_section(), stretch=1)

        layout.addLayout(top_row)
        layout.addSpacing(24)

        # ── Settings row ──────────────────────────────────────────────────
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)
        settings_row.addWidget(self._build_smart_transform_card(), stretch=1)
        settings_row.addWidget(self._build_language_card(), stretch=1)
        layout.addLayout(settings_row)

        layout.addSpacing(24)

        # ── Generate button ───────────────────────────────────────────────
        self.generate_btn = GlowButton("Generate Shorts   ✨")
        self.generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self.generate_btn)

        return card

    # ── URL Input Section ──────────────────────────────────────────────────
    def _build_url_section(self) -> QVBoxLayout:
        """Left column: paste URL input."""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Section header
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(IconBadge("🔗", f"rgba(244, 37, 140, 0.1)", PRIMARY, size=28))
        lbl = QLabel("Paste URL")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {TEXT_WHITE};")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.setFixedHeight(48)
        self.url_input.setMinimumWidth(180)
        layout.addWidget(self.url_input)

        # Helper text
        helper = QLabel("Supports YouTube, TikTok, and Instagram Reels")
        helper.setFont(QFont("Segoe UI", 9))
        helper.setStyleSheet(f"color: {TEXT_MUTED};")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        return layout

    # ── Upload Section ─────────────────────────────────────────────────────
    def _build_upload_section(self) -> QVBoxLayout:
        """Right column: file upload drop zone."""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Section header
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(IconBadge("📁", BLUE_ACCENT_BG, BLUE_ACCENT, size=28))
        lbl = QLabel("Upload File")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {TEXT_WHITE};")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_zone)

        # Spacer to align with URL helper text
        layout.addSpacing(14)

        return layout

    # ── OR Divider ─────────────────────────────────────────────────────────
    def _build_or_divider(self) -> QWidget:
        """Vertical line with centered 'OR' badge."""
        divider = QWidget()
        divider.setFixedWidth(48)
        divider_layout = QVBoxLayout(divider)
        divider_layout.setContentsMargins(0, 0, 0, 0)
        divider_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # We paint the line + badge in a custom widget
        class _OrDivider(QWidget):
            def __init__(self):
                super().__init__()
                self.setFixedWidth(48)
                self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

            def paintEvent(self, event):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                cx = self.width() // 2
                h = self.height()

                # Gradient line top
                grad_top = QLinearGradient(cx, 0, cx, h // 2 - 14)
                grad_top.setColorAt(0, QColor(0, 0, 0, 0))
                grad_top.setColorAt(1, QColor(BORDER_DARK))
                p.setPen(QPen(QBrush(grad_top), 1))
                p.drawLine(cx, 0, cx, h // 2 - 14)

                # Gradient line bottom
                grad_bot = QLinearGradient(cx, h // 2 + 14, cx, h)
                grad_bot.setColorAt(0, QColor(BORDER_DARK))
                grad_bot.setColorAt(1, QColor(0, 0, 0, 0))
                p.setPen(QPen(QBrush(grad_bot), 1))
                p.drawLine(cx, h // 2 + 14, cx, h)

                # OR badge
                badge_rect = self.rect()
                badge_rect.setTop(h // 2 - 10)
                badge_rect.setBottom(h // 2 + 10)
                badge_rect.setLeft(cx - 14)
                badge_rect.setRight(cx + 14)

                p.setBrush(QBrush(QColor(SURFACE_DARK)))
                p.setPen(QPen(QColor(BORDER_DARK), 1))
                p.drawRoundedRect(badge_rect, 10, 10)

                p.setPen(QColor(TEXT_MUTED))
                font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                p.setFont(font)
                p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "OR")
                p.end()

        divider_layout.addWidget(_OrDivider())
        return divider

    # ── Smart Transform Card ───────────────────────────────────────────────
    def _build_smart_transform_card(self) -> QFrame:
        """Settings card with toggle for Smart Transform."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame#smartCard {{
                background-color: rgba(59, 35, 48, 0.3);
                border: 1px solid {BORDER_DARK};
                border-radius: 10px;
            }}
            QFrame#smartCard:hover {{
                border: 1px solid rgba(244, 37, 140, 0.3);
            }}
        """)
        card.setObjectName("smartCard")
        card.setMinimumHeight(70)
        card.setMaximumHeight(80)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon
        icon_container = QLabel("✨")
        icon_container.setFixedSize(32, 32)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_container.setFont(QFont("Segoe UI Emoji", 13))
        icon_container.setStyleSheet(f"""
            background-color: {BG_DARK};
            border-radius: 6px;
            color: {TEXT_MUTED};
        """)
        layout.addWidget(icon_container)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("Smart Transform")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {TEXT_WHITE};")
        text_layout.addWidget(title)

        desc = QLabel("Reduce similarity & copyright strikes")
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet(f"color: {TEXT_MUTED};")
        desc.setWordWrap(True)
        text_layout.addWidget(desc)
        
        layout.addLayout(text_layout, stretch=1)

        # Toggle
        self.smart_toggle = ToggleSwitch()
        layout.addWidget(self.smart_toggle)

        return card

    # ── Language Card ──────────────────────────────────────────────────────
    def _build_language_card(self) -> QFrame:
        """Settings card with language dropdown."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame#langCard {{
                background-color: rgba(59, 35, 48, 0.3);
                border: 1px solid {BORDER_DARK};
                border-radius: 10px;
            }}
            QFrame#langCard:hover {{
                border: 1px solid rgba(244, 37, 140, 0.3);
            }}
        """)
        card.setObjectName("langCard")
        card.setMinimumHeight(70)
        card.setMaximumHeight(80)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon
        icon_container = QLabel("🌐")
        icon_container.setFixedSize(32, 32)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_container.setFont(QFont("Segoe UI Emoji", 13))
        icon_container.setStyleSheet(f"""
            background-color: {BG_DARK};
            border-radius: 6px;
            color: {TEXT_MUTED};
        """)
        layout.addWidget(icon_container)

        # Text + combo
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        label = QLabel("Output Language")
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        label.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(label)

        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "English (US)", "Spanish", "French", "German", "Japanese"
        ])
        self.language_combo.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        text_layout.addWidget(self.language_combo)

        layout.addLayout(text_layout, stretch=1)

        return card

    # ══════════════════════════════════════════════════════════════════════
    #  SLOTS / CALLBACKS
    # ══════════════════════════════════════════════════════════════════════
    def _on_generate(self):
        """Handle Generate Shorts button click (placeholder)."""
        url = self.url_input.text().strip()
        language = self.language_combo.currentText()
        smart = self.smart_toggle.isChecked()
        print(f"[Generate] URL={url!r}  Language={language}  SmartTransform={smart}")

    def _on_file_dropped(self, path: str):
        """Handle file drop/selection (placeholder)."""
        print(f"[File Selected] {path}")
