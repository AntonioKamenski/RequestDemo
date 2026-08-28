from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtCore import Qt

class SeparatorDelegate(QStyledItemDelegate):
    def __init__(self, color):
        self.color = QColor(color)
        super().__init__()
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        painter.save()
        pen = QPen(self.color)
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidth(1)
        painter.setPen(pen)

        y = option.rect.bottom() - 1
        painter.drawLine(option.rect.left(), y, option.rect.right(), y)

        painter.restore()
    def setColor(self, color):
        self.color = QColor(color)

class BorderDelegate(QStyledItemDelegate):
    def __init__(self, color):
        super().__init__()
        self.color = QColor(color)
    
    def setColor(self, color):
        self.color = QColor(color)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        painter.save()

        pen = QPen(self.color)
        pen.setWidth(1)
        painter.setPen(pen)

        rect = option.rect
        model = index.model()

        row = index.row()
        col = index.column()

        last_col = model.columnCount() - 1

        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        painter.drawLine(rect.topRight(), rect.bottomRight())

        if col == 0:
            painter.drawLine(rect.topLeft(), rect.bottomLeft())

        if row == 0:
            painter.drawLine(rect.topLeft(), rect.topRight())

        painter.restore()