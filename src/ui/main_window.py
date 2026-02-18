"""
main_window.py - Main application window for ViralClips.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QFrame, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QLinearGradient, QPen, QPixmap, QImage

# Assumed imports based on your provided context
from src.ui.theme import (
    PRIMARY, BG_DARK, SURFACE_DARK, BORDER_DARK, TEXT_MUTED, 
    TEXT_WHITE, BLUE_ACCENT, BLUE_ACCENT_BG, GLOBAL_STYLESHEET
)
from src.ui.widgets import (
    GlowButton, UpgradeButton, ToggleSwitch, IconBadge, DropZone, ApiKeyButton,
    PreviewWidget
)
from src.workers.preview_worker import PreviewWorker


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Content Factory — AI Video Generator")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 850)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # ── Central Scroll Area ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {BG_DARK}; border: none; }}")
        self.setCentralWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background-color: {BG_DARK};")
        scroll.setWidget(container)

        # Root layout for the whole page
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Header ─────────────────────────────────────────────────────
        root_layout.addWidget(self._build_header())

        # ── 2. Body (Centered Content) ────────────────────────────────────
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 40, 24, 40)
        body_layout.setSpacing(32)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Hero heading
        body_layout.addWidget(self._build_hero(), alignment=Qt.AlignmentFlag.AlignHCenter)

        # Main Interface Card
        body_layout.addWidget(self._build_main_card(), alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Bottom stretch to push content up if window is huge
        body_layout.addStretch()

        root_layout.addWidget(body)

    # ══════════════════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════════════════
    def _build_header(self) -> QWidget:
        """Sticky top bar with logo and upgrade button."""
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DARK};
                border-bottom: 1px solid {BORDER_DARK};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(16)

        # Logo Section
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(12)

        robot_icon = QLabel("🤖")
        robot_icon.setFont(QFont("Segoe UI Emoji", 24))
        logo_layout.addWidget(robot_icon)

        title = QLabel("Content Factory")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_WHITE};")
        logo_layout.addWidget(title)

        layout.addLayout(logo_layout)
        layout.addStretch()

        # Right side actions
        layout.addWidget(ApiKeyButton())
        layout.addWidget(UpgradeButton())

        return header

    # ══════════════════════════════════════════════════════════════════════
    #  HERO HEADING
    # ══════════════════════════════════════════════════════════════════════
    def _build_hero(self) -> QWidget:
        """Centered heading + subtitle."""
        hero = QWidget()
        hero.setMaximumWidth(820)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main heading
        heading = QLabel()
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        # Rich text for mixed coloring
        heading.setText(
            f'<p style="line-height:1.2; margin-bottom:0;">'
            f'<span style="color: {TEXT_WHITE};">Turn long videos into </span>'
            f'<span style="color: {PRIMARY};">viral Shorts</span>'
            f'<span style="color: {TEXT_WHITE};"> instantly.</span>'
            f'</p>'
        )
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)

        # Subtitle
        subtitle = QLabel("Paste a link, customize your vibe, and let AI do the editing, captioning, and b-roll.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet(f"color: {TEXT_MUTED};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return hero

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN CARD
    # ══════════════════════════════════════════════════════════════════════
    def _build_main_card(self) -> QWidget:
        """The large rounded card containing inputs."""
        card = QFrame()
        card.setFixedWidth(900)  # Fixed width for consistent layout like screenshot
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 20px;
            }}
        """)
        card.setObjectName("mainCard")

        # Shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # ── Top Row Container (Swappable) ────────────────────────────────
        self.top_container = QWidget()
        self.top_layout = QVBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Input View (URL + Upload)
        self.input_view = QWidget()
        input_layout = QHBoxLayout(self.input_view)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)
        
        # Left: URL
        input_layout.addLayout(self._build_url_section(), stretch=4)
        
        # Center: Divider
        div_layout = QVBoxLayout()
        div_layout.setContentsMargins(0, 0, 0, 0)
        div_layout.addWidget(self._build_or_divider())
        input_layout.addLayout(div_layout, stretch=1)

        # Right: Upload
        input_layout.addLayout(self._build_upload_section(), stretch=4)
        
        self.top_layout.addWidget(self.input_view)
        
        # 2. Preview View (Hidden by default)
        self.preview_widget = PreviewWidget()
        self.preview_widget.hide()
        self.preview_widget.removeClicked.connect(self._reset_input_mode)
        self.top_layout.addWidget(self.preview_widget)

        layout.addWidget(self.top_container)

        # ── Settings Row ──────────────────────────────────────────────────
        settings_row = QHBoxLayout()
        settings_row.setSpacing(20)
        
        # Smart Transform
        settings_row.addWidget(self._build_smart_transform_card(), stretch=1)
        
        # Output Language
        settings_row.addWidget(self._build_language_card(), stretch=1)
        
        layout.addLayout(settings_row)
        layout.addSpacing(12)

        # ── Generate Button ───────────────────────────────────────────────
        self.generate_btn = GlowButton("Generate Shorts   ✨")
        self.generate_btn.clicked.connect(self._on_generate)
        self.generate_btn.setFixedHeight(56)
        layout.addWidget(self.generate_btn)

        return card

    # ── URL Input Section ──────────────────────────────────────────────────
    def _build_url_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Crucial: Keeps content at top

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(IconBadge("🔗", "rgba(244, 37, 140, 0.1)", PRIMARY, size=32))
        
        lbl = QLabel("Paste URL")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {TEXT_WHITE};")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.setFixedHeight(52)
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
                padding-left: 16px;
                color: {TEXT_WHITE};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {PRIMARY};
            }}
        """)
        self.url_input.textChanged.connect(self._on_url_text_changed)
        layout.addWidget(self.url_input)

        # Debounce timer for URL input
        self.url_timer = QTimer()
        self.url_timer.setSingleShot(True)
        self.url_timer.setInterval(800) # 800ms debounce
        self.url_timer.timeout.connect(self._process_url_input)

        # Helper
        helper = QLabel("Supports YouTube, TikTok, and Instagram Reels")
        helper.setFont(QFont("Segoe UI", 10))
        helper.setStyleSheet(f"color: {TEXT_MUTED};")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        # Add stretch to match the height of the Upload section if Upload is taller
        layout.addStretch()

        return layout

    # ── Upload Section ─────────────────────────────────────────────────────
    def _build_upload_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(IconBadge("📁", BLUE_ACCENT_BG, BLUE_ACCENT, size=32))
        
        lbl = QLabel("Upload File")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {TEXT_WHITE};")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        self.drop_zone.setMinimumHeight(100) # Ensure it has presence
        layout.addWidget(self.drop_zone)

        return layout

    # ── OR Divider ─────────────────────────────────────────────────────────
    def _build_or_divider(self) -> QWidget:
        """Custom painted widget that draws a line with 'OR' in the middle."""
        
        class _OrDivider(QWidget):
            def __init__(self):
                super().__init__()
                self.setFixedWidth(60)
                # This ensures the divider expands vertically to fill the QHBoxLayout
                self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

            def paintEvent(self, event):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                w = self.width()
                h = self.height()
                cx = w // 2

                # 1. Draw Lines (Gradient fade out at top/bottom)
                # Top line
                grad_top = QLinearGradient(cx, 0, cx, h // 2 - 18)
                grad_top.setColorAt(0, QColor(0,0,0,0))
                grad_top.setColorAt(0.2, QColor(BORDER_DARK))
                grad_top.setColorAt(1, QColor(BORDER_DARK))
                p.setPen(QPen(QBrush(grad_top), 1))
                p.drawLine(cx, 10, cx, h // 2 - 18)

                # Bottom line
                grad_bot = QLinearGradient(cx, h // 2 + 18, cx, h)
                grad_bot.setColorAt(0, QColor(BORDER_DARK))
                grad_bot.setColorAt(0.8, QColor(BORDER_DARK))
                grad_bot.setColorAt(1, QColor(0,0,0,0))
                p.setPen(QPen(QBrush(grad_bot), 1))
                p.drawLine(cx, h // 2 + 18, cx, h - 10)

                # 2. Draw 'OR' Badge
                badge_size = 28
                badge_rect = self.rect()
                badge_rect.setLeft(cx - badge_size // 2)
                badge_rect.setRight(cx + badge_size // 2)
                badge_rect.setTop(h // 2 - badge_size // 2)
                badge_rect.setBottom(h // 2 + badge_size // 2)

                p.setBrush(QBrush(QColor(SURFACE_DARK)))
                p.setPen(QPen(QColor(BORDER_DARK), 1))
                p.drawRoundedRect(badge_rect, 14, 14)

                p.setPen(QColor(TEXT_MUTED))
                font = QFont("Segoe UI", 8, QFont.Weight.Bold)
                p.setFont(font)
                p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "OR")
                
                p.end()

        return _OrDivider()

    # ── Smart Transform Card ───────────────────────────────────────────────
    def _build_smart_transform_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(59, 35, 48, 0.4);
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {PRIMARY};
                background-color: rgba(59, 35, 48, 0.6);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Icon
        icon = QLabel("✨")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFont(QFont("Segoe UI Emoji", 14))
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px;")
        layout.addWidget(icon)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("Smart Transform")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_WHITE};")
        text_layout.addWidget(title)

        desc = QLabel("Reduce copyright strikes")
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(desc)
        
        # Add stretch to push toggle to the right
        layout.addLayout(text_layout, stretch=1)

        # Toggle
        self.smart_toggle = ToggleSwitch()
        layout.addWidget(self.smart_toggle)

        return card

    # ── Language Card ──────────────────────────────────────────────────────
    def _build_language_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(59, 35, 48, 0.4);
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {PRIMARY};
                background-color: rgba(59, 35, 48, 0.6);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Icon
        icon = QLabel("文")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFont(QFont("Segoe UI Emoji", 14))
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px;")
        layout.addWidget(icon)

        # Text Area
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("Output Language")
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(lbl)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English (US)", "Spanish", "French", "German"])
        self.language_combo.setStyleSheet(f"""
            QComboBox {{
                border: none;
                background: transparent;
                color: {TEXT_WHITE};
                font-size: 11pt;
                font-weight: bold;
                padding: 0px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        text_layout.addWidget(self.language_combo)

        # Push everything to the left, but standard combobox arrow handles right
        layout.addLayout(text_layout, stretch=1)

        return card

    # ══════════════════════════════════════════════════════════════════════
    #  SLOTS
    # ══════════════════════════════════════════════════════════════════════
    def _on_generate(self):
        """Handle Generate Shorts button click."""
        url = self.url_input.text().strip()
        lang = self.language_combo.currentText()
        smart = self.smart_toggle.isChecked()
        print(f"Generating with: URL={url}, Lang={lang}, Smart={smart}")

    def _on_file_dropped(self, path: str):
        """Handle file drop."""
        print(f"File dropped: {path}")
        self._start_preview(path, is_local=True)

    def _on_url_text_changed(self):
        """Restart debounce timer on text change."""
        self.url_timer.start()
        
    def _process_url_input(self):
        """Check if URL is valid and start preview."""
        text = self.url_input.text().strip()
        if not text:
            return
            
        # Basic check if it looks like a URL
        if "youtube.com" in text or "youtu.be" in text:
            self._start_preview(text, is_local=False)

    def _start_preview(self, source: str, is_local: bool):
        """Switch to preview mode and start worker."""
        # Update UI state
        self.input_view.hide()
        self.preview_widget.show()
        self.preview_widget.set_loading(True)
        
        # Cleanup old worker
        if hasattr(self, 'worker') and self.worker:
            self.worker.quit()
            self.worker.wait()
            
        # Start new worker
        self.worker = PreviewWorker(source, is_local)
        self.worker.previewReady.connect(self._on_preview_ready)
        self.worker.errorOccurred.connect(self._on_preview_error)
        self.worker.start()

    def _on_preview_ready(self, image: QImage, title: str):
        """Handle successful preview."""
        pixmap = QPixmap.fromImage(image)
        self.preview_widget.set_preview(pixmap, title)
        
    def _on_preview_error(self, error: str):
        """Handle preview error."""
        self.preview_widget.set_error(error)
        print(f"Preview Error: {error}")
        
    def _reset_input_mode(self):
        """Go back to input mode."""
        self.preview_widget.hide()
        self.input_view.show()
        self.url_input.clear()
        
        # Stop worker if running
        if hasattr(self, 'worker') and self.worker:
            self.worker.quit()
