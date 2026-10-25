"""Native Midnight Crew design system; presentation never dispatches model work."""

from functools import lru_cache

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QWidget { background: #10141d; color: #e4e9f2; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: #10141d; }
QWidget#sidebar { background: #0c1018; border-right: 1px solid #252d3d; }
QWidget#sidebar QLabel { background: transparent; }
QLabel#brand { font-size: 20px; font-weight: 700; color: #eff3ff; letter-spacing: 2px; }
QLabel#eyebrow { color: #9ba9c2; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
QLabel#pageTitle { font-size: 25px; font-weight: 600; color: #f1f4fc; }
QLabel#sectionTitle { font-size: 17px; font-weight: 600; color: #f1f4fc; }
QLabel#muted, QLabel#setupBanner { color: #a9b5ca; font-size: 12px; }
QLabel#agentTitle { font-size: 22px; font-weight: 600; color: #d5caff; }
QLabel#runFacts { background: #172232; border: 1px solid #2c4057; border-radius: 8px; padding: 10px; color: #bed3f0; }
QLabel#metricValue { font-size: 25px; font-weight: 600; color: #d8d1ff; }
QWidget#metricCard, QWidget#composer { background: #171d2a; border: 1px solid #30394e; border-radius: 12px; }
QWidget#metricCard QLabel, QWidget#composer QLabel { background: transparent; border: none; }
QWidget#composer QPlainTextEdit { background: #171d2a; border: none; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 14px; padding: 8px; }
QPlainTextEdit, QLineEdit, QListWidget, QComboBox, QSpinBox, QTreeWidget, QTableWidget {
 background: #111824; border: 1px solid #2b3548; border-radius: 7px; padding: 7px;
 selection-background-color: #354573; selection-color: #ffffff;
}
QPlainTextEdit { font-family: Consolas, 'DejaVu Sans Mono', monospace; }
QPlainTextEdit#conversation { background: #10141d; border: none; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 14px; padding: 18px; }
QPlainTextEdit#conversation[technical="true"] { font-family: Consolas, monospace; font-size: 12px; }
QLineEdit, QComboBox, QSpinBox { min-height: 24px; padding: 5px 8px; }
QComboBox { padding-right: 22px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #1b2434; border: 1px solid #455576; selection-background-color: #354573; }
QMenu { background: #1b2434; border: 1px solid #455576; padding: 5px; }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #354573; }
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QListWidget:focus, QTreeWidget:focus { border-color: #96afff; }
QListWidget::item, QTreeWidget::item { padding: 9px 7px; border-radius: 6px; }
QListWidget::item:hover, QTreeWidget::item:hover { background: #202a3c; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #2b3651; color: #f2f4ff; }
QListWidget#agentLibrary::item { padding: 13px 8px; margin: 3px 0; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: #aab7cd; padding: 11px 17px; margin-right: 4px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #e3dcff; border-bottom: 2px solid #a18afa; }
QTabBar::tab:hover { background: #1c2535; }
QPushButton, QToolButton { background: #222d40; border: 1px solid #37465f; border-radius: 7px; padding: 8px 12px; min-height: 20px; }
QPushButton:hover, QToolButton:hover { background: #2e3b54; border-color: #607499; }
QPushButton:pressed, QToolButton:pressed { background: #384b70; }
QPushButton:focus, QToolButton:focus { border: 2px solid #aec1ff; padding: 7px 11px; }
QPushButton:disabled, QToolButton:disabled { color: #8290a8; background: #192130; border-color: #2a3447; }
QPushButton#primary { color: white; background: #6553cf; border-color: #8b77ee; font-weight: 600; }
QPushButton#primary:hover { background: #7864e2; border-color: #b7a5ff; }
QPushButton#primary:disabled { background: #343252; color: #aaa3c4; border-color: #474260; }
QPushButton#nav { text-align: left; background: transparent; border: 1px solid transparent; padding: 11px 12px; color: #aebbd0; }
QPushButton#nav:hover { background: #182132; color: #edf2ff; }
QPushButton#nav:checked { background: #252c49; border-color: #41476c; color: #e2d9ff; }
QPushButton#nav:focus { border-color: #aec1ff; }
QPushButton#quiet, QToolButton#disclosure { background: transparent; border-color: transparent; color: #b6c4db; }
QPushButton#quiet:hover, QToolButton#disclosure:hover { background: #202b3f; }
QPushButton#panelToggle:checked { background: #303857; border-color: #8676cf; }
QPushButton#danger { color: #ffc0cd; border-color: #855365; }
QCheckBox { spacing: 8px; padding: 4px 0; }
QCheckBox::indicator { width: 16px; height: 16px; }
QToolTip { color: #f1f5ff; background: #263249; border: 1px solid #8d9dc5; padding: 8px; }
QProgressBar { border: none; background: #252d42; border-radius: 5px; min-height: 9px; text-align: center; }
QProgressBar::chunk { background: #9c88f4; border-radius: 5px; }
QHeaderView::section { background: #1d2637; color: #b9c6db; padding: 9px; border: none; border-bottom: 1px solid #354158; }
QTableWidget { gridline-color: #273349; alternate-background-color: #172030; }
QTableWidget::item { padding: 6px; }
QSplitter::handle { background: #242e40; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #111824; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #3a4964; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #111824; height: 10px; }
QScrollBar::handle:horizontal { background: #3a4964; min-width: 28px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QStatusBar { background: #0c1018; border-top: 1px solid #252d3d; color: #99a8c1; font-size: 11px; }
QStatusBar::item { border: none; }
"""

# Original geometric symbols, independent of the unavailable character artwork.
PATHS = {
    "projects": '<path d="M3 7h7l2 3h9v11H3z"/><path d="M3 7V4h7l2 3h8v3"/>',
    "workbench": '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="m7 9 3 3-3 3m6 0h4M8 21h8m-4-3v3"/>',
    "agents": '<path d="m12 3 3 6 6 3-6 3-3 6-3-6-6-3 6-3z"/><circle cx="12" cy="12" r="3"/>',
    "tests": '<path d="M9 3h6m-5 0v7l-6 9c-1 2 1 2 2 2h12c1 0 3 0 2-2l-6-9V3M8 15h8"/>',
    "diagnose": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "connections": '<path d="M9 3v6m6-6v6M6 9h12v3a6 6 0 0 1-12 0zM12 18v4"/>',
    "data": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    "settings": '<path d="m9 3-1 3-3 1v4l-2 1 2 2v4l3 1 1 3h6l1-3 3-1v-4l2-2-2-1V7l-3-1-1-3z"/><circle cx="12" cy="12" r="3"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "george": '<path d="m3 7 4 4 5-8 5 8 4-4-2 12H5zM5 22h14"/><path d="m12 8 2 4-2 4-2-4z"/>',
    "scout": '<circle cx="10" cy="10" r="7"/><circle cx="10" cy="10" r="3"/><path d="m15 15 7 7"/>',
    "ada": '<path d="m9 3-1 3-3 1v4l-2 1 2 2v4l3 1 1 3h6l1-3 3-1v-4l2-2-2-1V7l-3-1-1-3z"/><path d="m12 8 1.5 2.5L16 12l-2.5 1.5L12 16l-1.5-2.5L8 12l2.5-1.5z"/>',
    "vera": '<path d="m12 2 9 10-9 10-9-10zM12 2 8 12l4 10 4-10zM3 12h18"/>',
    "sentinel": '<path d="m12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6z"/><path d="m12 6 3 6-3 6-3-6z"/>',
    "atlas": '<path d="M12 12c-3-7-10-7-10 0s7 7 10 0 10-7 10 0-7 7-10 0z"/><path d="M12 2v3m0 14v3"/>',
}


@lru_cache(maxsize=64)
def icon(name, color="#aebed9"):
    """Render an original vector at multiple sizes for native/DPI-scaled controls."""
    drawing = PATHS.get(name, PATHS["agents"])
    safe_color = QColor(color).name()
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{safe_color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        + drawing
        + "</svg>"
    )
    result = QIcon()
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    for size in (24, 48, 96):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        result.addPixmap(pixmap)
    return result


def text_label(text, name="muted"):
    label = QLabel(text)
    label.setObjectName(name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    return label


class ElidedLabel(QLabel):
    """Keep full text/accessibility/tooltip while painting paths within available space."""

    def __init__(self, text=""):
        super().__init__(text)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(text)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        painter.drawText(
            self.contentsRect(),
            self.alignment(),
            self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, self.width()),
        )


class Disclosure(QWidget):
    """Keyboard-operable progressive disclosure; hidden controls retain their state."""

    def __init__(self, title, content, expanded=False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.toggle = QToolButton()
        self.toggle.setObjectName("disclosure")
        self.toggle.setText(title)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolTip("Show or hide these options. Existing values are kept.")
        self.content = content
        layout.addWidget(self.toggle)
        layout.addWidget(content)
        self.toggle.toggled.connect(self.set_expanded)
        self.set_expanded(expanded)

    def set_expanded(self, expanded):
        self.content.setVisible(expanded)
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.toggle.setAccessibleDescription("Expanded" if expanded else "Collapsed")
        if self.toggle.isChecked() != expanded:
            self.toggle.setChecked(expanded)


class CommandPalette(QDialog):
    """Search only explicit application actions; typing never dispatches work."""

    def __init__(self, window, commands):
        super().__init__(window)
        self.commands = tuple(commands)
        self.setWindowTitle("Find a command")
        self.resize(580, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(text_label("Where do you want to go?", "sectionTitle"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search actions, for example: tests, agents, settings…")
        self.search.setAccessibleName("Search application commands")
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.setAccessibleName("Matching application commands")
        layout.addWidget(self.results)
        layout.addWidget(text_label("Enter to open • Esc to close • No model request runs from search"))
        self.search.textChanged.connect(self.filter)
        self.search.returnPressed.connect(self.execute)
        self.results.itemActivated.connect(self.execute)
        self.filter("")
        self.search.setFocus()

    def filter(self, query):
        self.results.clear()
        terms = query.casefold().split()
        for index, (title, hint, callback) in enumerate(self.commands):
            if all(term in (title + " " + hint).casefold() for term in terms):
                item = QListWidgetItem(title + "\n" + hint)
                item.setData(Qt.UserRole, index)
                self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def execute(self, *_):
        item = self.results.currentItem()
        if item is None:
            return
        callback = self.commands[item.data(Qt.UserRole)][2]
        self.accept()
        callback()


def navigation_button(title, symbol, callback, *, checkable=False):
    result = QPushButton(title)
    result.setObjectName("nav")
    result.setIcon(icon(symbol))
    result.setIconSize(QSize(19, 19))
    result.setCheckable(checkable)
    result.setCursor(Qt.PointingHandCursor)
    result.setAccessibleName(title)
    result.clicked.connect(callback)
    return result
