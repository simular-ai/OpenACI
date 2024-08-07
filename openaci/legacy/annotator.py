import pyautogui
import os
from PIL import Image, ImageTk
from tkinter import Tk, Canvas, mainloop, NW
from tkinter.simpledialog import askstring
from datetime import datetime


class AnnotationTool:

    def __init__(self, image_path):
        # Load the image from the provided path
        self.image = Image.open(image_path)
        self.original_image = self.image.copy()
        self.image_width, self.image_height = self.image.size
        print("original image size", self.image.size)
        print("screen size", pyautogui.size())
        screen_width, screen_height = pyautogui.size()
        aspect_ratio = min(screen_width / self.image.width,
                           screen_height / (self.image.height * 1.05))
        self.aspect_ratio = aspect_ratio
        canvas_width, canvas_height = int(
            self.image.width * aspect_ratio), int(self.image.height *
                                                  aspect_ratio)

        self.image = self.image.resize((canvas_width, canvas_height))
        self.image_width, self.image_height = self.image.size

        # Create a tkinter window
        self.root = Tk()
        self.root.title("Image Annotation")
        self.root.attributes("-fullscreen", True)  # Set to fullscreen mode

        # Set the window size to match the screen resolution
        self.root.geometry(f"{screen_width}x{screen_height}")

        # Create a canvas to display the image
        self.canvas = Canvas(self.root,
                             width=self.image_width,
                             height=self.image_height)
        self.canvas.pack()

        # Convert the image to a tkinter-compatible format and display it on the canvas
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor=NW, image=self.tk_image)

        # Initialize annotation variables
        self.start_x, self.start_y = None, None
        self.end_x, self.end_y = None, None

        # Bind mouse events to corresponding functions
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        # Bind the "Escape" key press event to close the window
        self.root.bind("<Escape>", self.on_escape_key_press)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_mouse_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.canvas.delete(
            "rectangle")  # Remove the previous rectangle, if any
        self.canvas.create_rectangle(self.start_x,
                                     self.start_y,
                                     self.end_x,
                                     self.end_y,
                                     outline="red",
                                     width=2,
                                     tags="rectangle")

    def on_button_release(self, event):
        # Prompt for the label and save the annotation
        label = askstring("Annotation Label",
                          "Enter the label for this annotation:")
        if label:
            self.annotation_label = label
            self.save_annotation()

    def save_annotation(self):
        # Create a directory using the provided label if it doesn't exist
        if self.annotation_label:
            directory_name = os.path.join('../icons', self.annotation_label)
            if not os.path.exists(directory_name):
                os.makedirs(directory_name)

            # Get the current datetime
            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # Crop the image based on the annotated region
            cropped_image = self.original_image.crop(
                (self.start_x / self.aspect_ratio,
                 self.start_y / self.aspect_ratio,
                 self.end_x / self.aspect_ratio,
                 self.end_y / self.aspect_ratio))

            # Save the cropped image to a PNG file using the current datetime as the filename
            filename = os.path.join(directory_name, f"{current_datetime}.png")
            cropped_image.save(filename)
            print(f"Cropped image saved as: {filename}")

    def on_escape_key_press(self, event):
        # Close the tkinter window when "Escape" key is pressed
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def annotate_screenshot():
    # Take a screenshot
    screenshot = pyautogui.screenshot()

    w, h = pyautogui.size()
    print(w, h)

    # Save the screenshot as a temporary image file
    screenshot_path = "screenshot.png"
    screenshot.save(screenshot_path)

    AnnotationTool(screenshot_path).run()


if __name__ == "__main__":
    annotate_screenshot()
