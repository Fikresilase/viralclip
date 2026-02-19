"""
main_window.py - Main application window for ViralClips.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QFrame, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QLinearGradient, QPen, QPixmap, QImage

# Assumed imports based on your provided context
from src.ui.theme import (
    PRIMARY, BG_DARK, SURFACE_DARK, SURFACE_INPUT, BORDER_DARK, TEXT_MUTED, 
    TEXT_WHITE, BLUE_ACCENT, BLUE_ACCENT_BG, GLOBAL_STYLESHEET
)
from src.ui.widgets import (
    GlowButton, UpgradeButton, ToggleSwitch, IconBadge, DropZone, ApiKeyButton,
    PreviewWidget
)
from src.ui.results_view import ResultsView
from src.workers.preview_worker import PreviewWorker
from src.workers.generator_worker import GeneratorWorker
from src.utils.storage import StorageManager


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        # Clean up old cache on startup
        self.storage.cleanup()
        
        self.current_source = None
        self.current_is_local = False
        
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
        body_layout.setContentsMargins(24, 32, 24, 32)
        body_layout.setSpacing(40)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Hero heading
        self.hero_widget = self._build_hero()
        body_layout.addWidget(self.hero_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Main Interface Card
        body_layout.addWidget(self._build_main_card(), alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Results View (Full Width Container)
        self.results_container = QWidget()
        self.results_container.setMaximumWidth(1400)  # max-w-7xl equivalent
        results_container_layout = QVBoxLayout(self.results_container)
        results_container_layout.setContentsMargins(0, 0, 0, 0)
        results_container_layout.setSpacing(0)
        
        # Move results view here
        self.results_view_main = ResultsView()
        self.results_view_main.hide()
        self.results_view_main.back_btn.clicked.connect(self._reset_input_mode)
        results_container_layout.addWidget(self.results_view_main)
        
        body_layout.addWidget(self.results_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Bottom stretch to push content up if window is huge
        body_layout.addStretch()

        root_layout.addWidget(body)

    # ══════════════════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════════════════
    def _build_header(self) -> QWidget:
        """Sticky top bar with logo and buttons matching web design."""
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DARK};
                border: none;
                border-bottom: 1px solid {BORDER_DARK};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(48, 0, 48, 0)
        layout.setSpacing(24)

        # Logo Section
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(12)

        robot_icon = QLabel("🤖")
        robot_icon.setFont(QFont("Segoe UI Emoji", 24))
        robot_icon.setFixedSize(32, 32)
        robot_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        robot_icon.setStyleSheet(f"color: {PRIMARY};")
        logo_layout.addWidget(robot_icon)

        title = QLabel("Content Factory")
        title.setFont(QFont("Space Grotesk", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: white;")
        logo_layout.addWidget(title)

        layout.addLayout(logo_layout)
        layout.addStretch()

        # Action Buttons
        layout.addWidget(ApiKeyButton())
        layout.addWidget(UpgradeButton())

        return header

    # ══════════════════════════════════════════════════════════════════════
    #  HERO HEADING
    # ══════════════════════════════════════════════════════════════════════
    def _build_hero(self) -> QWidget:
        """Centered heading + subtitle matching web design."""
        hero = QWidget()
        hero.setMaximumWidth(900)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main heading
        heading = QLabel()
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setFont(QFont("Space Grotesk", 42, QFont.Weight.Bold))
        heading.setText(
            f'<div style="text-align: center; color: white; line-height: 1.15;">'
            f'Turn long videos into<br>'
            f'<span style="color: {PRIMARY};">viral Shorts</span> instantly.'
            f'</div>'
        )
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)

        # Subtitle
        subtitle = QLabel("Paste a link, customize your vibe, and let AI do the editing, captioning, and b-roll.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Space Grotesk", 16))
        subtitle.setStyleSheet(f"color: {TEXT_MUTED};")
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(700)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)

        return hero

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN CARD
    # ══════════════════════════════════════════════════════════════════════
    def _build_main_card(self) -> QWidget:
        """The large rounded card containing inputs matching web design."""
        self.main_card = QFrame()
        self.main_card.setFixedWidth(1100)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 24px;
            }}
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self.main_card)
        shadow.setBlurRadius(80)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.main_card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # ── Top Row Container (Swappable) ────────────────────────────────
        self.top_container = QWidget()
        self.top_layout = QVBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Input View
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
        
        # 2. Preview View
        self.preview_widget = PreviewWidget()
        self.preview_widget.hide()
        self.preview_widget.removeClicked.connect(self._reset_input_mode)
        self.top_layout.addWidget(self.preview_widget)



        layout.addWidget(self.top_container)

        # ── Options Section (Hidden initially) ──
        self.options_container = QWidget()
        self.options_container.hide()
        options_layout = QVBoxLayout(self.options_container)
        options_layout.setContentsMargins(0, 24, 0, 0)
        options_layout.setSpacing(20)

        # Settings
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)
        settings_row.addWidget(self._build_smart_transform_card(), stretch=1)
        settings_row.addWidget(self._build_language_card(), stretch=1)
        options_layout.addLayout(settings_row)
        
        # Button
        self.generate_btn = GlowButton("Generate Shorts")
        self.generate_btn.clicked.connect(self._on_generate)
        options_layout.addWidget(self.generate_btn)

        layout.addWidget(self.options_container)

        return self.main_card

    # ── URL Input Section ──────────────────────────────────────────────────
    def _build_url_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(IconBadge("🔗", f"rgba(244, 37, 140, 0.1)", PRIMARY, size=32))
        
        lbl = QLabel("Paste URL")
        lbl.setFont(QFont("Space Grotesk", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color: white;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.setFixedHeight(64)
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {SURFACE_INPUT};
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
                padding-left: 48px;
                padding-right: 16px;
                color: {TEXT_WHITE};
                font-size: 16px;
                font-family: "Space Grotesk";
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
        helper.setFont(QFont("Space Grotesk", 10))
        helper.setStyleSheet(f"color: {TEXT_MUTED}; padding-left: 4px;")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        # Add stretch to match the height of the Upload section if Upload is taller
        layout.addStretch()

        return layout

    # ── Upload Section ─────────────────────────────────────────────────────
    def _build_upload_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(IconBadge("📄", "rgba(96, 165, 250, 0.1)", BLUE_ACCENT, size=32))
        
        lbl = QLabel("Upload File")
        lbl.setFont(QFont("Space Grotesk", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color: white;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_zone)

        return layout

    def _build_or_divider(self) -> QWidget:
        return _OrDivider()

    # ── Smart Transform Card ───────────────────────────────────────────────
    def _build_smart_transform_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(59, 35, 48, 0.3);
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: rgba(244, 37, 140, 0.3); }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        icon = QLabel("✨")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px; font-size: 18px;")
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("Smart Transform")
        title.setFont(QFont("Space Grotesk", 13, QFont.Weight.Medium))
        title.setStyleSheet("color: white;")
        text_layout.addWidget(title)

        desc = QLabel("Reduce similarity & copyright strikes")
        desc.setFont(QFont("Space Grotesk", 10))
        desc.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(desc)
        
        layout.addLayout(text_layout)
        layout.addStretch()

        self.smart_toggle = ToggleSwitch()
        layout.addWidget(self.smart_toggle)

        return card

    # ── Language Card ──────────────────────────────────────────────────────
    def _build_language_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(59, 35, 48, 0.3);
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: rgba(244, 37, 140, 0.3); }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        icon = QLabel("🌐")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px; font-size: 18px;")
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("Output Language")
        lbl.setFont(QFont("Space Grotesk", 10))
        lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        text_layout.addWidget(lbl)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English (US)", "Spanish", "French", "German", "Japanese"])
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_combo.setFont(QFont("Space Grotesk", 13, QFont.Weight.Medium))
        self.language_combo.setStyleSheet("color: white;")
        text_layout.addWidget(self.language_combo)

        layout.addLayout(text_layout)
        layout.addStretch()

        return card

    # ══════════════════════════════════════════════════════════════════════
    #  SLOTS
    # ══════════════════════════════════════════════════════════════════════
    def _on_generate(self):
        """Handle Generate Shorts button click."""
        if not self.current_source:
             QMessageBox.warning(self, "Error", "No video selected.")
             return

        # Get API Key
        settings = QSettings("ViralClips", "Content Factory")
        api_key = settings.value("gemini_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Error", "Please set your Gemini API Key first (top right button).")
            return

        # Disable UI
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Processing... ⏳")
        self.input_view.hide()
        self.preview_widget.hide()
        self.options_container.hide()
        
        # Reuse preview widget loading state for progress
        self.preview_widget.show()
        self.preview_widget.set_loading(True)
        # Access internal label directly or add a method. For now, hack it:
        self.preview_widget._loading_label.setText("Analyzing Content with Gemini AI...\nDepending on video length, this can take a few minutes.")

        # Start Worker
        self.gen_worker = GeneratorWorker(self.current_source, self.current_is_local, api_key)
        self.gen_worker.finished.connect(self._on_generation_finished)
        self.gen_worker.error.connect(self._on_generation_error)
        self.gen_worker.progress.connect(self._on_generation_progress)
        self.gen_worker.start()

    def _on_generation_progress(self, msg):
        if self.preview_widget.isVisible():
             self.preview_widget._loading_label.setText(msg)

    def _on_generation_finished(self, results):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Shorts   ✨")
        
        # Hide all input UI
        self.preview_widget.hide()
        self.options_container.hide()
        self.main_card.hide()
        self.hero_widget.hide()
        
        # Show results in full-width container
        self.results_view_main.populate(results)
        self.results_container.show()
        self.results_view_main.show()

    def _on_generation_error(self, err):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Shorts   ✨")
        
        # Restore preview state
        self.preview_widget.hide()
        self.results_view_main.hide()
        self.results_container.hide()
        
        self.main_card.show()
        self.hero_widget.show()
        self.preview_widget.show()
        self.preview_widget.set_loading(False)
        self.options_container.show()
        
        QMessageBox.critical(self, "Generation Failed", f"Error: {err}")

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
        self.current_source = source
        self.current_is_local = is_local
        
        # Update UI state
        self.input_view.hide()
        self.results_view_main.hide()
        self.results_container.hide()
        self.preview_widget.show()
        self.options_container.show()
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

    def closeEvent(self, event):
        """Cleanup resources on close."""
        if hasattr(self, 'storage'):
            self.storage.cleanup()
        super().closeEvent(event)

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
        self.results_view_main.hide()
        self.results_container.hide()
        self.options_container.hide()
        
        # Show input UI
        self.main_card.show()
        self.hero_widget.show()
        self.input_view.show()
        self.url_input.clear()
        
        self.current_source = None
        self.current_is_local = False
        
        if hasattr(self, 'worker') and self.worker:
            self.worker.terminate()
            self.worker.wait()


class _OrDivider(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(60)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx = w // 2
        
        # Lines
        p.setPen(QPen(QColor(BORDER_DARK), 1))
        p.drawLine(cx, 10, cx, h // 2 - 20)
        p.drawLine(cx, h // 2 + 20, cx, h - 10)
        
        # Badge
        p.setBrush(QBrush(QColor(SURFACE_DARK)))
        p.drawEllipse(cx - 15, h // 2 - 15, 30, 30)
        
        p.setPen(QColor(TEXT_MUTED))
        p.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "OR")