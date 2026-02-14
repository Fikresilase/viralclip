"""
theme.py - Color palette and stylesheet constants for ViralClips.

All colors are derived from the original HTML/Tailwind design:
    primary:          #f4258c  (hot pink)
    primary-hover:    #d61c78
    background-dark:  #221019
    surface-dark:     #2e1a24
    surface-input:    #3b2330
    border-dark:      #543b47
    text-muted:       #ba9cab
"""

# ── Color Palette ──────────────────────────────────────────────────────────────
PRIMARY = "#f4258c"
PRIMARY_HOVER = "#d61c78"
BG_DARK = "#221019"
SURFACE_DARK = "#2e1a24"
SURFACE_INPUT = "#3b2330"
BORDER_DARK = "#543b47"
TEXT_MUTED = "#ba9cab"
TEXT_WHITE = "#ffffff"
BLUE_ACCENT = "#60a5fa"       # blue-400 equivalent
BLUE_ACCENT_BG = "#1e3a5f"   # blue-500/10 equivalent

# ── Global Stylesheet ──────────────────────────────────────────────────────────
GLOBAL_STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────────── */
QWidget {{
    font-family: "Segoe UI", "Space Grotesk", "Helvetica Neue", sans-serif;
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
    background: {SURFACE_DARK};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DARK};
    border-radius: 4px;
    min-height: 30px;
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
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_DARK};
    border: 1px solid {BORDER_DARK};
    selection-background-color: {SURFACE_INPUT};
    color: {TEXT_WHITE};
    outline: none;
    padding: 4px;
}}
QComboBox::item {{
    padding: 8px;
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
    padding: 8px 16px;
}}

/* ── Tooltips ─────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {SURFACE_DARK};
    color: {TEXT_WHITE};
    border: 1px solid {BORDER_DARK};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""
