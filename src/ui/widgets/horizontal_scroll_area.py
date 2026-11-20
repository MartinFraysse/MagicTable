from PySide6.QtWidgets import QScrollArea


class HorizontalScrollArea(QScrollArea):
    def wheelEvent(self, event):
        # Molette verticale → scroll horizontal
        delta = event.angleDelta().y()

        if delta != 0:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - delta)

        event.accept()
