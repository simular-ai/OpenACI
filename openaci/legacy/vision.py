from openai import OpenAI
import pyautogui
import os
import sys
import base64
import requests
import subprocess

# Path to your image
TEMP_SCREENSHOT_PATH = "temp.png"

def encode_image(image_path):
    """Encodes the image from the specified path into a base64 string.

    Parameters:
    - image_path (str): The path to the image file.

    Returns:
    - encoded_image (str): The base64 encoded image string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def take_screenshot(image_path=TEMP_SCREENSHOT_PATH):
    """Takes a screenshot of the screen and saves it as a downscaled image.

    Args:
        image_path (str, optional): The path where the downscaled screenshot image will be saved.
            Defaults to TEMP_SCREENSHOT_PATH.

    Returns:
        tuple: A tuple containing the downscaled image and the size of the original screen.

    """
    screenshot = pyautogui.screenshot()
    scale = 4
    downsampled_image = screenshot.resize(
        (screenshot.width // scale, screenshot.height // scale))

    print(downsampled_image)
    screen_size = screenshot.size
    print(screen_size)

    # Save the screenshot as "temp.jpg" in the current directory
    downsampled_image.save(image_path)
    return downsampled_image, screen_size

def is_retina():
    """Check if the screen is retina."""
    if sys.platform != 'win32':
        return subprocess.call("system_profiler SPDisplaysDataType | grep 'Retina'", shell= True) == 0
    else:
        return False

def crop_image(image, xmin, ymin, xmax, ymax):
    """Crop an image based on given bounding box coordinates.

    Args:
        image (PIL.Image.Image): The input image to be cropped.
        xmin (float): The normalized minimum x-coordinate of the bounding box.
        ymin (float): The normalized minimum y-coordinate of the bounding box.
        xmax (float): The normalized maximum x-coordinate of the bounding box.
        ymax (float): The normalized maximum y-coordinate of the bounding box.

    Returns:
        PIL.Image.Image: The cropped image.

    Note: The coordinates should be normalized between 0 and 1, where (0, 0) represents the top left corner
    of the image and (1, 1) represents the bottom right corner of the image.
    """
    # Get the width and height of the image
    width, height = image.size

    # Calculate the pixel coordinates
    xmin_pixel = int(xmin * width)
    ymin_pixel = int(ymin * height)
    xmax_pixel = int(xmax * width)
    ymax_pixel = int(ymax * height)

    # Crop the image
    cropped_image = image.crop((xmin_pixel, ymin_pixel, xmax_pixel, ymax_pixel))
    return cropped_image

def move_to_block(x, y, xmin, ymin, xmax, ymax):
    """Moves the mouse cursor to a specific location on the screen and shrink the area.

    Parameters:
    x (float): The x-coordinate of the target location, relative to the minimum and maximum x-values provided.
    y (float): The y-coordinate of the target location, relative to the minimum and maximum y-values provided.
    xmin (float): The minimum x-value of the bounding box.
    ymin (float): The minimum y-value of the bounding box.
    xmax (float): The maximum x-value of the bounding box.
    ymax (float): The maximum y-value of the bounding box.

    Returns:
    (float, float, float, float): A tuple representing the coordinates for cropping the image. The tuple contains the
    minimum x-value, minimum y-value, maximum x-value, and maximum y-value for cropping.

    Example:
    crop_xmin, crop_ymin, crop_xmax, crop_ymax = move_to_block(0.3, 0.8, 0, 0, 1, 1)
    # The mouse cursor will move to the (0.3, 0.8) location on the screen.
    # The returned cropping coordinates will be 1/4 area of (0, 0, 1, 1).
    """
    x = xmin + (xmax - xmin) * x
    y = ymin + (ymax - ymin) * y
    xcenter = (xmin + xmax) / 2.0
    ycenter = (ymin + ymax) / 2.0
    crop_xmin, crop_ymin, crop_xmax, crop_ymax = 0, 0, 1, 1
    if x < xcenter:
        crop_xmax = 0.5
    else:
        crop_xmin = 0.5

    if y < ycenter:
        crop_ymax = 0.5
    else:
        crop_ymin = 0.5

    print(f"moving mouse to ({x}, {y})")
    pyautogui.moveTo(x, y, 1, pyautogui.easeOutQuad)
    return crop_xmin, crop_ymin, crop_xmax, crop_ymax

def ask(concept: str, api_key: str):
    """Find a concept on the screen and move the mouse to click it.
    
    Takes a concept as input and performs sequential localization on a screenshot to determine the location of the concept
    on the screen.

    Parameters:
        concept (str): The concept to be localized on the screen.
    """
    image_path = TEMP_SCREENSHOT_PATH
    screen, screen_size = take_screenshot(image_path=image_path)
    width, height = screen_size
    if is_retina():
        width /= 2
        height /= 2
    screen_xmin = 0
    screen_ymin = 0
    screen_xmax = width
    screen_ymax = height

    for _ in range(3):
        # Sequential localization.
        query = f"Where is `{concept}`? Share the x_min, y_min, x_max, y_max in 0-1 normalized space. Only return the numbers, nothing else."
        response = ask_gpt(query, api_key, image_path=image_path)
        if 'choices' not in response:
            # Stop.
            return response
        message = response['choices'][0]['message']
        role = message['role']
        content = message['content']
        try:
            xmin, ymin, xmax, ymax = tuple(map(float, content.split(',')))
            x = (xmin+xmax) / 2.0
            y = (ymin+ymax) / 2.0
            crop_xmin, crop_ymin, crop_xmax, crop_ymax = move_to_block(x, y, screen_xmin, screen_ymin, screen_xmax, screen_ymax)

            # Refine the bbox.
            screen = crop_image(screen, crop_xmin, crop_ymin, crop_xmax, crop_ymax)
            screen.save(image_path)
            new_xmin = screen_xmin + crop_xmin * (screen_xmax - screen_xmin)
            new_xmax = screen_xmin + crop_xmax * (screen_xmax - screen_xmin)
            new_ymin = screen_ymin + crop_ymin * (screen_ymax - screen_ymin)
            new_ymax = screen_ymin + crop_ymax * (screen_ymax - screen_ymin)
            screen_xmin, screen_xmax, screen_ymin, screen_ymax = new_xmin, new_xmax, new_ymin, new_ymax
        except:
            print(f"Failed: {content}")
    
    if screen_xmin !=0 and screen_ymin != 0:
        pyautogui.click()
        return f"Clicked ({x}, {y})"
    else:
        return content

def ask_gpt(query: str, api_key: str, image_path=TEMP_SCREENSHOT_PATH):
    """Use GPT-4 Vision API to ask a question based on an image.

    Parameters:
        query (str): The question/query to ask based on the image.
        image_path (str, optional): The path to the image file to be analyzed. Defaults to TEMP_SCREENSHOT_PATH.

    Returns:
        str: The generated response/answer from the GPT-4 Vision API.

    Raises:
        None

    Examples:
        >>> ask_gpt("What is this object?", "{your_openai_api_key}", "image.png")
        "This object is a cat."
    """

    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model":
        "gpt-4-vision-preview",
        "messages": [{
            "role":
            "user",
            "content": [
                {
                    "type": "text",
                    "text": query
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }],
        "max_tokens":
        300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions",
                             headers=headers,
                             json=payload)

    # TODO potential RequestsJSONDecodeError
    return response.json()


