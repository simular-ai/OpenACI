from openaci.agent.UIAgent import IDBasedGroundingUIAgent
from openaci.macos.UIElement import UIElement
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




def run(instruction: str):
    engine_params = {
        "engine_type": "openai",
        "model": "gpt-4o",
    }

    agent = IDBasedGroundingUIAgent(
        engine_params,
        platform="macos",
        max_tokens=1500,
        top_p=0.9,
        temperature=0.5,
        action_space="pyautogui",
        observation_type="AXTree",
        max_trajectory_length=3,
        a11y_tree_max_tokens=10000,
        enable_reflection=True,
    )
    agent.reset()
    obs = {}
    for _ in range(15):
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

        info, code = agent.predict(instruction=instruction, obs=obs)
        
        print(info)
        print(code)

        if 'done' in code[0].lower() or 'fail' in code[0].lower():
            break 

        if 'wait' in code[0].lower():
            import time 
            time.sleep(5)
            continue

        else:
            exec(code[0])

def main():
    # Examples.
    while True:
        query = input("Query: ")
        run(query)
        break 


if __name__ == '__main__':
    main()
