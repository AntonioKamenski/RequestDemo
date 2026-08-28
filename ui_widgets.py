from PyQt6.QtWidgets import QListWidget, QTreeWidget


class ClearSelectionTreeWidget(QTreeWidget):
    def focusOutEvent(self, event):
        self.clearSelection()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)


class ClearSelectionListWidget(QListWidget):
    def focusOutEvent(self, event):
        self.clearSelection()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)
