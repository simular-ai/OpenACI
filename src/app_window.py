"""Load OpenAI api key from environment variable or ini config
sample ini config: api_key.ini
[openai]
APIKEY = xxx
"""

import os
import sys
from configparser import ConfigParser
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QTextBrowser,
)
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtCore import Qt, QSize
import requests
import vision

api_key = os.environ.get("OPENAI_API_KEY")
if api_key is None:
    try:
        config = ConfigParser()
        config.read(os.path.join(os.getcwd(), "api_key.ini"))
        api_key = config.get("openai", "APIKEY")
    except:
        print("No OpenAI api key found!")
        exit()

DOWNLOADED_IMG = "downloaded_img"

class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()

        self.reset()

    def reset(self):
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setText("\nDrop Image Here\n")
        self.setWordWrap(True)
        self.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #aaa
            }
            """
        )

    def show_image(self, image):
        try:
            image = image.scaled(
                QSize(self.width(), self.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            super().setPixmap(image)
        except Exception as ex:
            print(ex)


class DisplayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.window_width, self.window_height = 480, 240
        self.setMinimumSize(self.window_width, self.window_height)
        # self.setWindowIcon(QIcon(os.path.join(os.getcwd(), 'llama.png')))
        self.setWindowTitle("OpenAGI by Simular")
        self.setStyleSheet(
            """
            QWidget {
                font-size: 15px;               
            }
            """
        )

        self.reader = QTextBrowser()
        layout = QVBoxLayout()
        layout.addWidget(self.reader)
        self.setLayout(layout)

    def display(self, text, color="blue"):
        # Text color must be changed before setting text
        self.reader.setTextColor(QColor(color))
        self.reader.setText(text)


class AppWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.query = ""
        self.image_path = ""

        self.window_width, self.window_height = 720, 360
        self.setMinimumSize(self.window_width, self.window_height)
        self.setBaseSize(self.window_width, self.window_height)
        # self.setWindowIcon(QIcon(os.path.join(os.getcwd(), 'llama.png')))
        self.setWindowTitle("OpenAGI by Simular")
        self.setStyleSheet(
            """
            QWidget {
                font-size: 15px;               
            }
            """
        )
        self.editor = QLineEdit()
        self.editor.setPlaceholderText("How can I help?")
        self.editor.returnPressed.connect(self.confirmed)
        self.confirm_button = QPushButton(self, text="run")
        self.confirm_button.clicked.connect(self.confirmed)
        self.image_viewer = ImageLabel()
        self.reply = DisplayWindow()

        self.setAcceptDrops(True)

        line_layout = QHBoxLayout()
        line_layout.addWidget(self.editor)
        line_layout.addWidget(self.confirm_button)
        main_layout = QVBoxLayout()
        main_layout.addLayout(line_layout)
        main_layout.addWidget(self.image_viewer)
        self.setLayout(main_layout)

    def confirmed(self):
        self.query = self.editor.text()
        if self.query and self.image_path:
            response = vision.ask_gpt(self.query, api_key, self.image_path)
            if "choices" in response:
                answer = response["choices"][0]["message"]["content"]
                self.reply.display(answer)
                self.reply.show()
                self.reply.activateWindow()
            else:
                self.reply.display(f"{response}", "orange")
                self.reply.show()
                self.reply.activateWindow()
        else:
            msg = QMessageBox()
            msg.setWindowTitle(self.windowTitle())
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Drop me an image, and type your query")
            msg.exec()

    def set_image(self, image):
        self.image_viewer.show_image(image)

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasImage:
            event.setDropAction(Qt.DropAction.CopyAction)
            # Take first image
            file_url = event.mimeData().urls()[0]
            if file_url.isLocalFile():
                file_path = file_url.toLocalFile()
                image = QPixmap(file_path)
            else:
                download_img = requests.get(file_url.url())
                if download_img.ok and download_img.headers.get(
                    "Content-Type", ""
                ).startswith("image"):
                    with open(DOWNLOADED_IMG, "wb") as image_file:
                        image_file.write(download_img.content)
                    file_path = os.path.join(os.getcwd(), DOWNLOADED_IMG)
                    image = QPixmap(DOWNLOADED_IMG)
                else:
                    msg = QMessageBox()
                    msg.setWindowTitle(self.windowTitle())
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setText("Not an image url")
                    msg.exec()
                    file_path = None
                    image = None

            print(file_path)
            # Make sure it is purely an image
            if image is None or image.isNull():
                print("pixmap is null")
                self.image_viewer.reset()
                self.image_path = ""
                event.ignore()
            else:
                self.set_image(image)
                self.image_path = file_path
                event.accept()
        else:
            self.image_viewer.reset()
            self.image_path = ""
            event.ignore()


def main():
    """Entry point for the program.

    It gets a query from user, sends it to the vision module for processing,
    and displays the response received from the vision module.
    """
    app = QApplication([])

    # qss_style = open(os.path.join(os.getcwd(), "style.qss"), "r")
    # app.setStyleSheet(qss_style.read())

    # Launch app window
    app_window = AppWindow()
    app_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
