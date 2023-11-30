"""Load OpenAI api key from environment variable or ini config
sample ini config: api_key.ini
[openai]
APIKEY = xxx
"""

import os
import sys
from configparser import ConfigParser
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtGui import QIcon
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


class AppWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.query = ""

        self.window_width, self.window_height = 720, 60
        self.setMinimumSize(self.window_width, self.window_height)
        self.setBaseSize(self.window_width, self.window_height)
        # self.setWindowIcon(QIcon(os.path.join(os.getcwd(), 'llama.png')))
        self.setWindowTitle("OpenAGI by Simular")
        self.setStyleSheet("""
            QWidget {
                font-size: 15px;               
            }
        """)
        self.editor = QLineEdit()
        self.editor.setPlaceholderText("What app do you want to open?")
        self.editor.returnPressed.connect(self.confirmed)
        self.confirm_button = QPushButton(self, text="run")
        self.confirm_button.clicked.connect(self.confirmed)

        layout = QHBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

    def confirmed(self):
        self.query = self.editor.text()
        response = vision.ask(self.query, api_key)
        if "choices" in response:
            message = response["choices"][0]["message"]
            role = message["role"]
            content = message["content"]
            self.editor.setText(f"\n{role}: {content}")
        else:
            self.editor.setText(response)


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
