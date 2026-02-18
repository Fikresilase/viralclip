"""
theme.py - Color palette and stylesheet constants for ViralClips.
"""

# ── Color Palette ──────────────────────────────────────────────────────────────
PRIMARY = "#f4258c"
PRIMARY_HOVER = "#d61c78"
BG_DARK = "#120a0e"          # Darker background like the screenshot
SURFACE_DARK = "#1a0f14"     # Dark card background
SURFACE_INPUT = "#22141a"    # Input background
BORDER_DARK = "#35202a"      # Border color
TEXT_MUTED = "#94a3b8"       # More neutral muted text
TEXT_WHITE = "#ffffff"
BLUE_ACCENT = "#60a5fa"
BLUE_ACCENT_BG = "rgba(96, 165, 250, 0.1)"

# ── Global Stylesheet ──────────────────────────────────────────────────────────
GLOBAL_STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────────── */
QWidget {{
    font-family: "Inter", "Segoe UI", sans-serif;
    color: {TEXT_WHITE};
    background-color: {BG_DARK};
}}

/* ── Scroll Area ──────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DARK};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── Labels ───────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    border: none;
}}

/* ── Inputs ───────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {SURFACE_INPUT};
    border: 1px solid {BORDER_DARK};
    border-radius: 12px;
    padding: 0 16px;
    color: {TEXT_WHITE};
    font-size: 14px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit::placeholder {{
    color: #64748b;
}}

/* ── ComboBox ─────────────────────────────────────────────────────── */
QComboBox {{
    background-color: transparent;
    border: none;
    color: {TEXT_WHITE};
    font-size: 14px;
    font-weight: 600;
    padding: 0;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_DARK};
    border: 1px solid {BORDER_DARK};
    selection-background-color: {SURFACE_INPUT};
    color: {TEXT_WHITE};
    outline: none;
    padding: 8px;
    border-radius: 8px;
}}
QComboBox::item {{
    padding: 8px 12px;
    border-radius: 4px;
}}
QComboBox::item:selected {{
    background-color: {SURFACE_INPUT};
}}

/* ── Push Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    border: none;
    border-radius: 8px;
    font-weight: 600;
}}
"""

