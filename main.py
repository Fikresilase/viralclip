"""
main.py - Entry point for the ViralClips desktop application.

Usage:
    python main.py

Requirements:
    - Python 3.11
    - PyQt6 (do NOT mix with PyQt5 — see RULES.md)
"""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from src.ui.main_window import MainWindow


def main():
    """Initialize the QApplication and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("Content Factory")
    app.setOrganizationName("ViralClips")

    # Apply global font
    from PyQt6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
