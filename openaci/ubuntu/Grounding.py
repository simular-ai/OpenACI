import ctypes
import os
import platform
import shlex
import subprocess, signal
from lxml.etree import _Element

import pyatspi
from typing import Any, Optional
from typing import List, Dict, Tuple
from pyatspi import Accessible, StateType, STATE_SHOWING
from pyatspi import Action as ATAction
from pyatspi import Component, Document
from pyatspi import Text as ATText
from pyatspi import Value as ATValue

platform_name: str = platform.system()
import logging
logger = logging.getLogger("openaci.agent")

from ubuntu.UIElement import UIElement

def agent_action(func):
    func.is_agent_action = True
    return func

def list_apps_in_directories(directories):
    apps = []
    for directory in directories:
        if os.path.exists(directory):
            directory_apps = [app.replace('.desktop', '') for app in os.listdir(directory) if app.endswith(".desktop")]
            apps.extend(directory_apps)
    return apps

class GroundingAgent:
    def __init__(self, obs, top_app=None):
        self.input_tree = obs['accessibility_tree']
        self.screenshot = obs['screenshot']
        self.active_apps = []
        self.top_app = top_app

        self.index_out_of_range_flag = False
        self.top_active_app = None
        self.execution_feedback = None

        # Directories to search for applications in MacOS
        directories_to_search = [
            "/usr/share/applications/",
        ]
        self.all_apps = list_apps_in_directories(directories_to_search)

        self.nodes, self.linearized_accessibility_tree = self.linearize_and_annotate_tree(
            self.input_tree, self.screenshot)


    def preserve_nodes(self, tree, exclude_roles=None):
        if exclude_roles is None:
            exclude_roles = set()
        
        preserved_nodes = []

        # Inner function to recursively traverse the accessibility tree
        def traverse_and_preserve(element):
            role = element.node.getRoleName()

            if role not in exclude_roles:
                # TODO: get coordinate values directly from interface
                if element.component:
                    position = element.component.getPosition(pyatspi.XY_SCREEN)
                    size = element.component.getSize()
                    if position and size:                        
                            # Extract the numerical values after 'x:' and 'y:'
                            x = position[0]
                            y = position[1]

                            # Extract the numerical values after 'Width:' and 'Height:'
                            w = size[0]
                            h = size[1]
            
                            if x >= 0 and y >= 0 and w > 0 and h > 0:
                                preserved_nodes.append(element)
            
            children = element.children()
            if children:
                for child_ref in children:
                    child_element = UIElement(child_ref)
                    traverse_and_preserve(child_element)

        # Start traversing from the given element
        traverse_and_preserve(tree)

        return preserved_nodes

    def linearize_and_annotate_tree(self, accessibility_tree, screenshot, platform="macos", tag=False):
        tree = accessibility_tree
        preserved_nodes = self.preserve_nodes(tree, exclude_roles=['panel', 'window', 'filler', 'separator']).copy()
        
        linearized_accessibility_tree = [
            "id\trole\tname\ttext"]

        for idx, node in enumerate(preserved_nodes):
            name = node.attributes.get('name', '')
            text = node.text
            role = node.role
            linearized_accessibility_tree.append(
                "{:}\t{:}\t{:}\t{:}".format(
                    idx,
                    role,
                    name,
                    text,
                )
            )

        # Convert to string
        linearized_accessibility_tree = "\n".join(
            linearized_accessibility_tree)
        print(linearized_accessibility_tree)
        return preserved_nodes, linearized_accessibility_tree

    def find_element(self, element_id):
        try:
            selected_element = self.nodes[int(element_id)]
        except:
            print("The index of the selected element was out of range.")
            selected_element = self.nodes[0]
            self.index_out_of_range_flag = True 
        return selected_element
    
    @agent_action
    def click(
        self,
        element_id: int,
        num_clicks: int = 1,
        button_type: str = "left",
        hold_keys: List = [],
    ):
        """Click on the element
        Args:
            element_id:int, ID of the element to click on
            num_clicks:int, number of times to click the element
            button_type:str, which mouse button to press can be "left", "middle", or "right"
            hold_keys:List, list of keys to hold while clicking
        """
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
        sizes: Tuple[int, int] = node.component.getSize()

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        command = "import pyautogui; "

        # TODO: specified duration?
        for k in hold_keys:
            command += f"pyautogui.keyDown({repr(k)}); "
        command += f"""import pyautogui; pyautogui.click({x}, {y}, clicks={num_clicks}, button={repr(button_type)}); """
        for k in hold_keys:
            command += f"pyautogui.keyUp({repr(k)}); "
        # Return pyautoguicode to click on the element
        return command

    @agent_action
    def switch_applications(self, app_code):
        """Switch to a different application that is already open
        Args:
            app_code:str the code name of the application to switch to from the provided list of open applications
        """
        return self.app_setup_code.replace("APP_NAME", app_code)

    @agent_action
    def type(
        self,
        element_id: int = None,
        text: str = '',
        overwrite: bool = False,
        enter: bool = False,
    ):
        """Type text into the element
        Args:
            element_id:int ID of the element to type into. If not provided, typing will start at the current cursor location.
            text:str the text to type
            overwrite:bool Assign it to True if the text should overwrite the existing text, otherwise assign it to False. Using this argument clears all text in an element.
            enter:bool Assign it to True if the enter key should be pressed after typing the text, otherwise assign it to False.
        """
        try:
            # Use the provided element_id or default to None
            node = self.find_element(element_id) if element_id is not None else None
        except:
            node = None

        if node is not None:
            # If a node is found, retrieve its coordinates and size
            coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
            sizes: Tuple[int, int] = node.component.getSize()

            # Calculate the center of the element
            x = coordinates[0] + sizes[0] // 2
            y = coordinates[1] + sizes[1] // 2

            # Start typing at the center of the element
            command = "import pyautogui; "
            command += f"pyautogui.click({x}, {y}); "

            if overwrite:
                command += (
                    f"pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); "
                )

            command += f"pyautogui.write({repr(text)}); "

            if enter:
                command += "pyautogui.press('enter'); "
        else:
            # If no element is found, start typing at the current cursor location
            command = "import pyautogui; "

            if overwrite:
                command += (
                    f"pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); "
                )

            command += f"pyautogui.write({repr(text)}); "

            if enter:
                command += "pyautogui.press('enter'); "

        return command

    @agent_action
    def save_to_knowledge(self, text: List[str]):
        """Save facts, elements, texts, etc. to a long-term knowledge bank for reuse during this task. Can be used for copy-pasting text, saving elements, etc.
        Args:
            text:List[str] the text to save to the knowledge
        """
        self.notes.extend(text)
        return """WAIT"""

    @agent_action
    def drag_and_drop(self, drag_from_id: int, drop_on_id: int, hold_keys: List = []):
        """Drag element1 and drop it on element2.
        Args:
            drag_from_id:int ID of element to drag
            drop_on_id:int ID of element to drop on
            hold_keys:List list of keys to hold while dragging
        """
        node1 = self.find_element(drag_from_id)
        node2 = self.find_element(drop_on_id)
        coordinates1: Tuple[int, int] = node1.component.getPosition(pyatspi.XY_SCREEN)
        sizes1: Tuple[int, int] = node1.component.getSize()

        coordinates2: Tuple[int, int] = node2.component.getPosition(pyatspi.XY_SCREEN)
        sizes2: Tuple[int, int] = node2.component.getSize()

        # Calculate the center of the element
        x1 = coordinates1[0] + sizes1[0] // 2
        y1 = coordinates1[1] + sizes1[1] // 2

        x2 = coordinates2[0] + sizes2[0] // 2
        y2 = coordinates2[1] + sizes2[1] // 2

        command = "import pyautogui; "

        command += f"pyautogui.moveTo({x1}, {y1}); "
        # TODO: specified duration?
        for k in hold_keys:
            command += f"pyautogui.keyDown({repr(k)}); "
        command += f"pyautogui.dragTo({x2}, {y2}, duration=1.); pyautogui.mouseUp(); "
        for k in hold_keys:
            command += f"pyautogui.keyUp({repr(k)}); "

        # Return pyautoguicode to drag and drop the elements

        return command

    @agent_action
    def scroll(self, element_id: int, clicks: int):
        """Scroll the element in the specified direction
        Args:
            element_id:int ID of the element to scroll in
            clicks:int the number of clicks to scroll can be positive (up) or negative (down).
        """
        try:
            node = self.find_element(element_id)
        except:
            node = self.find_element(0)
        # print(node.attrib)
        coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
        sizes: Tuple[int, int] = node.component.getSize()

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2
        return (
            f"import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.scroll({clicks})"
        )

    @agent_action
    def hotkey(self, keys: List):
        """Press a hotkey combination
        Args:
            keys:List the keys to press in combination in a list format (e.g. ['ctrl', 'c'])
        """
        # add quotes around the keys
        keys = [f"'{key}'" for key in keys]
        return f"import pyautogui; pyautogui.hotkey({', '.join(keys)})"

    @agent_action
    def hold_and_press(self, hold_keys: List, press_keys: List):
        """Hold a list of keys and press a list of keys
        Args:
            hold_keys:List, list of keys to hold
            press_keys:List, list of keys to press in a sequence
        """

        press_keys_str = "[" + ", ".join([f"'{key}'" for key in press_keys]) + "]"
        command = "import pyautogui; "
        for k in hold_keys:
            command += f"pyautogui.keyDown({repr(k)}); "
        command += f"pyautogui.press({press_keys_str}); "
        for k in hold_keys:
            command += f"pyautogui.keyUp({repr(k)}); "

        return command

    @agent_action
    def wait(self, time: float):
        """Wait for a specified amount of time
        Args:
            time:float the amount of time to wait in seconds
        """
        return f"""import time; time.sleep({time})"""

    @agent_action
    def done(self):
        """End the current task with a success"""
        return """DONE"""

    @agent_action
    def fail(self):
        """End the current task with a failure"""
        return """FAIL"""

