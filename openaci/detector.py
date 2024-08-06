import pyautogui as pag
import subprocess
import os
import glob
from typing import List
import time
import pyperclip

IS_RETINA = False
CONCEPT_ICON_PREFIX = "../icons/"

concepts = {'chrome'}


def get_icon_images_by_name(name: str) -> List[str]:
    return glob.glob(os.path.join(CONCEPT_ICON_PREFIX, name, '*.png'))


def detect_icon(icon_image_paths, confidence=0.9):
    for impath in icon_image_paths:
        # TODO: this requires OpenCV.
        # position = pag.locateCenterOnScreen(impath, confidence=confidence)
        position = pag.locateCenterOnScreen(impath)
        if position is not None:
            return position

    return None


def detect_concept(concept: str, confidence=0.9):
    """Detect the location of a concept."""
    if subprocess.call("system_profiler SPDisplaysDataType | grep -i 'retina'",
                       shell=True) == 0:
        print("Retina screen detected.")
        IS_RETINA = True

    try:
        icon_images = get_icon_images_by_name(concept)
        print(icon_images)
        position = detect_icon(icon_images, confidence=confidence)
        if position is None:
            print(f'{concept} not found on screen.')
            return None
        else:
            x = position[0]
            y = position[1]
            if IS_RETINA:
                x /= 2
                y /= 2
            print(f"detected {concept} at {x},{y}")
            return x, y
    except OSError as e:
        raise Exception(e)


if __name__ == "__main__":
    x, y = detect_concept("chrome")
    pag.moveTo(x, y, duration=1)
