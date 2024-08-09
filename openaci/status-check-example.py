import os
import subprocess
from macos.Grounding import GroundingAgent

from agent.UIAgent import IDBasedGroundingUIAgent
from macos.UIElement import UIElement
import logging

from Foundation import *
from AppKit import *
import sys 
from ApplicationServices import (
    AXIsProcessTrusted,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    CFEqual,
)

from ApplicationServices import (
    AXUIElementCopyAttributeNames,
    AXUIElementCopyAttributeValue,
)
import os 
import datetime 
import base64
import io
import pyautogui

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

file_handler = logging.FileHandler(
    os.path.join("logs", "normal-{:}.log".format(datetime_str)), encoding="utf-8"
)
debug_handler = logging.FileHandler(
    os.path.join("logs", "debug-{:}.log".format(datetime_str)), encoding="utf-8"
)
stdout_handler = logging.StreamHandler(sys.stdout)
sdebug_handler = logging.FileHandler(
    os.path.join("logs", "sdebug-{:}.log".format(datetime_str)), encoding="utf-8"
)

file_handler.setLevel(logging.INFO)
debug_handler.setLevel(logging.DEBUG)
stdout_handler.setLevel(logging.INFO)
sdebug_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s"
)
file_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
sdebug_handler.setFormatter(formatter)

stdout_handler.addFilter(logging.Filter("desktopenv"))
sdebug_handler.addFilter(logging.Filter("desktopenv"))

logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(stdout_handler)
logger.addHandler(sdebug_handler)

def is_app_running(app_name):
    """
    Check if an application is currently running.
    
    :param app_name: Name of the application to check.
    :return: True if the application is running, False otherwise.
    """
    try:
        # Normalize app_name to remove the .app extension and any spaces
        normalized_app_name = app_name.replace(".app", "").replace(" ", "\ ")
        # Use pgrep to check if the application is running
        result = subprocess.run(["pgrep", "-f", normalized_app_name], stdout=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking status of {app_name}: {e}")
        return False

def get_installed_apps(apps_directory="/Applications"):
    """
    Get a list of installed applications in the specified directory, along with their running status.
    
    :param apps_directory: Directory where applications are installed.
    :return: List of tuples with application names and their running status (True/False).
    """
    try:
        apps = [(app, is_app_running(app)) for app in os.listdir(apps_directory) if app.endswith(".app")]
        return apps
    except Exception as e:
        print(f"Error accessing {apps_directory}: {e}")
        return []

# Example usage
if __name__ == "__main__":
    installed_apps = get_installed_apps()
    print("Installed Applications and their status:")
    for app, is_running in installed_apps:
        status = "Running" if is_running else "Not Running"
        print(f"{app}: {status}")

    obs = {}
    obs['accessibility_tree'] = UIElement.systemWideElement()

    # Get screen shot using pyautogui.
    # Take a screenshot
    screenshot = pyautogui.screenshot()

    # Save the screenshot to a BytesIO object
    buffered = io.BytesIO()
    screenshot.save(buffered, format="PNG")

    # Get the byte value of the screenshot
    screenshot_bytes = buffered.getvalue()
    # Convert to base64 string.
    obs['screenshot'] = screenshot_bytes
    grounding_agent = GroundingAgent(obs)

    grounding_agent.open_app("Safari")