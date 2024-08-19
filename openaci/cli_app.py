import os 
import datetime 
import base64
import io
import pyautogui
import platform 
import logging
import sys
import time 

if platform.system() == 'Darwin':
    from macos.UIElement import UIElement
    from Foundation import *
    from AppKit import *
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
elif platform.system() == 'Linux':
    from ubuntu.UIElement import UIElement

from agent.UIAgent import IDBasedGroundingUIAgent

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

platform_os = platform.system() 

def main():
    # Examples.
    while True:
        query = input("Query: ")
        engine_params = {
            "engine_type": "openai",
            "model": "gpt-4o",
        }
        agent = IDBasedGroundingUIAgent(
            engine_params,
            platform=platform_os,
            max_tokens=1500,
            top_p=0.9,
            temperature=0.5,
            action_space="pyautogui",
            observation_type="atree",
            max_trajectory_length=3,
            a11y_tree_max_tokens=10000,
            enable_reflection=True,
        )
        agent.reset()
        agent.run(instruction=query)
        
        # Ask user if they want to provide another query
        response = input("Would you like to provide another query? (y/n): ")
        if response.lower() != "y":
            break


if __name__ == '__main__':
    main()
