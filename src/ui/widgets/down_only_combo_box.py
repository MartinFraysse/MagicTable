from PySide6.QtWidgets import QComboBox, QListView


class DownOnlyComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        view = QListView(self)
        view.setFrameShape(QListView.Box)
        view.setFrameShadow(QListView.Plain)

        self.setView(view)
