"""
theme.py - Color palette and stylesheet constants for ViralClips.
"""

# ── Color Palette (Matching Web Design) ───────────────────────────────────────
PRIMARY = "#f4258c"
PRIMARY_HOVER = "#d61c78"
BG_DARK = "#221019"          # background-dark from web
SURFACE_DARK = "#2e1a24"     # surface-dark from web
SURFACE_INPUT = "#3b2330"    # surface-input from web
BORDER_DARK = "#543b47"      # border-dark from web
TEXT_MUTED = "#ba9cab"       # text-muted from web
TEXT_WHITE = "#ffffff"
BLUE_ACCENT = "#60a5fa"
BLUE_ACCENT_BG = "rgba(96, 165, 250, 0.1)"

# ── Global Stylesheet (Matching Web Design) ───────────────────────────────────
GLOBAL_STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────────── */
QWidget {{
    font-family: "Space Grotesk", "Segoe UI", sans-serif;
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
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DARK};
    border-radius: 4px;
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
    font-size: 16px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus {{
    border: 1px solid {PRIMARY};
    outline: none;
}}
QLineEdit::placeholder {{
    color: rgba(186, 156, 171, 0.5);
}}

/* ── ComboBox ─────────────────────────────────────────────────────── */
QComboBox {{
    background-color: transparent;
    border: none;
    color: {TEXT_WHITE};
    font-size: 14px;
    font-weight: 500;
    padding: 0;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
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
    font-weight: 700;
}}
"""

