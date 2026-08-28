from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt
import pandas as pd

from custom_titlebar import CustomTitleBar, CUSTOM_TITLEBAR  # adjust to your actual filename

class SongSearchDialog(QDialog):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.setObjectName("SongSearchDialog")
        self.setWindowTitle("Add Banned Song")
        self.df = df
        self.selected_row_index = None
        self.resize(750, 500)

        if CUSTOM_TITLEBAR:
            self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            if parent is not None:
                self.setStyleSheet(parent.styleSheet())
                

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if CUSTOM_TITLEBAR:
            self._titlebar = CustomTitleBar(self)
            self._titlebar._min_btn.hide()
            self._titlebar._max_btn.hide()
            if parent is not None and hasattr(parent, '_titlebar'):
                current_pixmap = parent._titlebar._icon_lbl.pixmap()
                if current_pixmap is not None:
                    self._titlebar.update_icon(current_pixmap)
            outer_layout.addWidget(self._titlebar)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setObjectName("titleBarSeparator")
        outer_layout.addWidget(separator)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 8, 12, 12)
        outer_layout.addWidget(content)

        content_layout.addWidget(QLabel("Search for a song:"))
        content_layout.addSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type song name or artist...")
        self.search_box.textChanged.connect(self.update_results)
        content_layout.addWidget(self.search_box)
        content_layout.addSpacing(8)
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self.accept_selection)
        content_layout.addWidget(self.results_list)

        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.accept_selection)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.confirm_button)
        button_layout.setContentsMargins(0, 12, 0, 0)
        content_layout.addLayout(button_layout)

        self.update_results()

    def update_results(self):
        query = self.search_box.text().strip().lower()
        self.results_list.clear()

        if not query:
            display_df = self.df
        else:
            mask = (
                self.df['songName'].astype(str).str.lower().str.contains(query, na=False)
                | self.df['ContributingArtists'].astype(str).str.lower().str.contains(query, na=False)
            )
            display_df = self.df[mask].head(10)

        display_df = display_df.sort_values(by='songName', key=lambda col: col.str.lower())

        for idx, row in display_df.iterrows():
            extreme_str = "| (Extreme)" if row.get('extreme', False) else ""
            alt_val = None
            if row.get('alternate', '') not in [None, '', '-', 'extreme', 'Extreme', 'EXTREME']:
                alt_val = row.get('alternate', '')
            alt_str = f"| ({alt_val})" if not pd.isna(alt_val) and str(alt_val).strip() != '' else ""
            item_text = f"{row['songName']} - {row['ContributingArtists']} {alt_str}{extreme_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.results_list.addItem(item)

    def on_selection_changed(self):
        selected_items = self.results_list.selectedItems()
        self.confirm_button.setEnabled(len(selected_items) > 0)

    def accept_selection(self):
        selected_items = self.results_list.selectedItems()
        if selected_items:
            self.selected_row_index = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.accept()

    def get_selected_row_index(self):
        return self.selected_row_index