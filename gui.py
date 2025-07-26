# gui.py
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QTextEdit, QCheckBox, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QMessageBox
)
from converter import convert_file  # vår nya convert_file(path, metadata, toc)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Converter")
        self.resize(600, 400)

        # Central widget och layout
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 1) Filval
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Inputfil:"))
        self.fileLineEdit = QLineEdit()
        file_layout.addWidget(self.fileLineEdit)
        browse = QPushButton("Bläddra…")
        browse.clicked.connect(self.browse_file)
        file_layout.addWidget(browse)
        layout.addLayout(file_layout)

        # 2) Metadata-fält
        layout.addWidget(QLabel("Titel:"))
        self.titleLineEdit = QLineEdit()
        layout.addWidget(self.titleLineEdit)

        layout.addWidget(QLabel("Författare:"))
        self.authorLineEdit = QLineEdit()
        layout.addWidget(self.authorLineEdit)

        layout.addWidget(QLabel("Fotograf (om någon):"))
        self.photographerLineEdit = QLineEdit()
        layout.addWidget(self.photographerLineEdit)

        layout.addWidget(QLabel("ISBN:"))
        self.isbnLineEdit = QLineEdit()
        layout.addWidget(self.isbnLineEdit)

        layout.addWidget(QLabel("Kategorier (komma-separerade):"))
        self.categoriesLineEdit = QLineEdit()
        layout.addWidget(self.categoriesLineEdit)

        layout.addWidget(QLabel("Beskrivning:"))
        self.descriptionTextEdit = QTextEdit()
        layout.addWidget(self.descriptionTextEdit)

        # 3) Innehållsförteckning?
        self.tocCheckBox = QCheckBox("Inkludera innehållsförteckning (TOC)")
        self.tocCheckBox.setChecked(True)
        layout.addWidget(self.tocCheckBox)

        # 4) Konvertera-knapp
        convert_btn = QPushButton("Konvertera till EPUB")
        convert_btn.clicked.connect(self.on_convert)
        layout.addWidget(convert_btn)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Välj Word eller PDF",
            "", "Word-dokument (*.docx);;PDF-filer (*.pdf)"
        )
        if path:
            self.fileLineEdit.setText(path)

    def on_convert(self):
        path = self.fileLineEdit.text().strip()
        if not path:
            QMessageBox.warning(self, "Fel", "Du måste välja en indatafil.")
            return

        # Bygg upp metadata-dict:
        metadata = {
            'path': path,
            'title': self.titleLineEdit.text().strip(),
            'author': self.authorLineEdit.text().strip(),
            'photographer': self.photographerLineEdit.text().strip(),
            'ISBN': self.isbnLineEdit.text().strip(),
            'categories': [
                {'value': c.strip()}
                for c in self.categoriesLineEdit.text().split(',')
                if c.strip()
            ],
            'description': self.descriptionTextEdit.toPlainText().strip()
        }

        try:
            convert_file(metadata, self.tocCheckBox.isChecked())
            QMessageBox.information(self, "Klart!", "EPUB har skapats i mappen Books/")
        except Exception as e:
            QMessageBox.critical(self, "Misslyckades", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
