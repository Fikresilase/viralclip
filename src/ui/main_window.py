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
        body_layout.setContentsMargins(24, 40, 24, 40)
        body_layout.setSpacing(32)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Hero heading
        body_layout.addWidget(self._build_hero(), alignment=Qt.AlignmentFlag.AlignHCenter)

        # Main Interface Card
        body_layout.addWidget(self._build_main_card(), alignment=Qt.AlignmentFlag.AlignHCenter)
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
        """Sticky top bar with logo and buttons."""
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"background-color: {BG_DARK}; border: none;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(12)

        # Logo Section
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)

        robot_icon = QLabel("🤖")
        robot_icon.setFont(QFont("Segoe UI Emoji", 20))
        logo_layout.addWidget(robot_icon)

        title = QLabel("Content Factory")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
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
        """Centered heading + subtitle."""
        hero = QWidget()
        hero.setMaximumWidth(820)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(0, 40, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main heading
        heading = QLabel()
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        heading.setText(
            f'<div style="text-align: center; color: white; line-height: 1.2;">'
            f'Turn long videos into<br>'
            f'<span style="color: {PRIMARY};">viral Shorts</span> instantly.'
            f'</div>'
        )
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)

        # Subtitle
        subtitle = QLabel("Paste a link, customize your vibe, and let AI do the editing, captioning, and b-roll.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Inter", 12))
        subtitle.setStyleSheet("color: #94a3b8;")
        subtitle.setWordWrap(True)
        subtitle.setFixedWidth(600)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)

        return hero

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN CARD
    # ══════════════════════════════════════════════════════════════════════
    def _build_main_card(self) -> QWidget:
        """The large rounded card containing inputs."""
        card = QFrame()
        card.setFixedWidth(900)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DARK};
                border-radius: 20px;
            }}
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 40, 32, 40)
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

        # 3. Results View
        self.results_view = ResultsView()
        self.results_view.hide()
        self.results_view.back_btn.clicked.connect(self._reset_input_mode)
        self.top_layout.addWidget(self.results_view)

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

        return card

    # ── URL Input Section ──────────────────────────────────────────────────
    def _build_url_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(IconBadge("🔗", "rgba(244, 37, 140, 0.1)", PRIMARY, size=32))
        
        lbl = QLabel("Paste URL")
        lbl.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.setFixedHeight(50)
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
        helper.setFont(QFont("Inter", 9))
        helper.setStyleSheet("color: #64748b;")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        # Add stretch to match the height of the Upload section if Upload is taller
        layout.addStretch()

        return layout

    # ── Upload Section ─────────────────────────────────────────────────────
    def _build_upload_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(IconBadge("📄", "rgba(96, 165, 250, 0.1)", BLUE_ACCENT, size=32))
        
        lbl = QLabel("Upload File")
        lbl.setFont(QFont("Inter", 13, QFont.Weight.Bold))
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
        card.setFixedHeight(70)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_INPUT};
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {PRIMARY}; }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        icon = QLabel("✨")
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px; font-size: 14px;")
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("Smart Transform")
        title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        text_layout.addWidget(title)

        desc = QLabel("Reduce copyright strikes")
        desc.setFont(QFont("Inter", 9))
        desc.setStyleSheet("color: #64748b;")
        text_layout.addWidget(desc)
        
        layout.addLayout(text_layout)
        layout.addStretch()

        self.smart_toggle = ToggleSwitch()
        layout.addWidget(self.smart_toggle)

        return card

    # ── Language Card ──────────────────────────────────────────────────────
    def _build_language_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(70)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_INPUT};
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {PRIMARY}; }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        icon = QLabel("文")
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px; font-size: 14px;")
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("Output Language")
        lbl.setFont(QFont("Inter", 9))
        lbl.setStyleSheet("color: #64748b;")
        text_layout.addWidget(lbl)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English (US)", "Spanish", "French", "German"])
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
        self.preview_widget.hide()
        self.options_container.hide()
        
        self.results_view.populate(results)
        self.results_view.show()

    def _on_generation_error(self, err):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Shorts   ✨")
        
        # Restore preview state
        self.preview_widget.hide()
        self.results_view.hide()
        
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
        self.results_view.hide()
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

    # ── Language Card ──────────────────────────────────────────────────────
    def _build_language_card(self) -> QFrame:
        card = QFrame()
        card.setFixedHeight(70)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_INPUT};
                border: 1px solid {BORDER_DARK};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {PRIMARY}; }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        icon = QLabel("文")
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {BG_DARK}; border-radius: 8px; font-size: 14px;")
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("Output Language")
        lbl.setFont(QFont("Inter", 9))
        lbl.setStyleSheet("color: #64748b;")
        text_layout.addWidget(lbl)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English (US)", "Spanish", "French", "German"])
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
        self.preview_widget.hide()
        self.options_container.hide()
        
        self.results_view.populate(results)
        self.results_view.show()

    def _on_generation_error(self, err):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Shorts   ✨")
        
        # Restore preview state
        self.preview_widget.hide()
        self.results_view.hide()
        
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
        self.results_view.hide()
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
        self.results_view.hide()
        self.options_container.hide()
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