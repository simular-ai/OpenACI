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

    # TODO: chunk and shorten this function
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

    # TODO: this is still MACOS specific code
    def open_app(self, app_name):
        '''Open an application
            Args:
                app_name:str, the name of the application to open from the following list of available applications in the system: AVAILABLE_APPS
        '''
        # fuzzy match the app name
        # closest_matches = difflib.get_close_matches(app_name + ".app", self.all_apps, n=1, cutoff=0.6) 
        if app_name in self.all_apps:
            print(f"{app_name} has been opened successfully.")
            return f"""import subprocess; subprocess.Popen(["{app_name}"])"""
        else:
            self.execution_feedback = "There is no application " + app_name + " installed on the system. Please replan and avoid this action."
            print(self.execution_feedback)
            return """WAIT"""

    def click(self, element_id, num_clicks=1, click_type="left"):
        '''Click on the element
        Args:
            element: a short description of the element to click on
            num_clicks: the number of clicks to perform
            click_type: the type of click to perform (left, right)
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
        sizes: Tuple[int, int] = node.component.getSize()

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}, clicks={num_clicks}, button="{click_type}")"""

    def double_click(self, element_id):
        '''Double click on the element
        Args:
            element: a short description of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
        sizes: Tuple[int, int] = node.component.getSize()

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}, clicks=2, button="left")"""

    def right_click(self, element_id):
        '''Right click on the element
        Args:
            element: a short description of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node.component.getPosition(pyatspi.XY_SCREEN)
        sizes: Tuple[int, int] = node.component.getSize()

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}, button="right")"""

    def click_at_coordinates(self, x, y, num_clicks, click_type="left"):
        '''Click on the element at the specified coordinates. Only use if the required element does not exist in the accessibility tree.
        Args:
            x: the x-coordinate of the element to click on
            y: the y-coordinate of the element to click on
            num_clicks: the number of clicks to perform
            click_type: the type of click to perform (left, right)
        '''
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks={num_clicks}, button="{click_type}")"""

    def switch_applications(self, app_name):
        '''Switch to a different application
        Args:
            app_name: the name of the application to switch to from the provided list of applications
        '''
        return self.app_setup_code.replace('APP_NAME', app_name)

    def make_full_screen(self, app_name):
        '''Make the application full screen
        Args:
            app_name: the name of the application to make full screen
        '''
        return self.app_setup_code.replace('APP_NAME', app_name)

    def type(self, element_id, text, append: bool = True):
        '''Type text into the element
        Args:
            element: a short description of the element to type into
            text: the text to type into the element
        '''
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

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}); pyautogui.typewrite("{text}")"""
        else:
            return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("delete"); pyautogui.typewrite("{text}")"""

    def type_and_enter(self, element_id, text, append: bool = True):
        '''Type text into the element
        Args:
            element: a short description of the element to type into
            text: the text to type into the element
        '''
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

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}); pyautogui.typewrite("{text}"); pyautogui.press("enter")"""
        else:
            return f"""import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.click({x}, {y}); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("delete"); pyautogui.typewrite("{text}"); pyautogui.press("enter")"""

    def drag_and_drop(self, element1_id, element2_id):
        '''Drag element1 and drop it on element2
        Args:
            element1: a short description of the element to drag
            element2: a short description of the element to drop on
        '''
        node1 = self.find_element(element1_id)
        node2 = self.find_element(element2_id)
        coordinates1: Tuple[int, int] = node1.component.getPosition(pyatspi.XY_SCREEN)
        sizes1: Tuple[int, int] = node1.component.getSize()

        coordinates2: Tuple[int, int] = node2.component.getPosition(pyatspi.XY_SCREEN)
        sizes2: Tuple[int, int] = node2.component.getSize()
        
        # Calculate the center of the element
        x1 = coordinates1[0] + sizes1[0] // 2
        y1 = coordinates1[1] + sizes1[1] // 2

        x2 = coordinates2[0] + sizes2[0] // 2
        y2 = coordinates2[1] + sizes2[1] // 2

        # Return pyautoguicode to drag and drop the elements
        return f"import pyautogui; pyautogui.moveTo({x1}, {y1}); pyautogui.dragTo({x2}, {y2})"

    def scroll(self, clicks):
        '''Scroll the element in the specified direction
        Args:
            clicks: the number of clicks to scroll can be positive or negative
        '''
        return f"import pyautogui; pyautogui.scroll({clicks})"

    def hotkey(self, keys):
        '''Press a hotkey combination
        Args:
            keys: the keys to press in combination in a list format (e.g. ['command', 'c'])
        '''
        # add quotes around the keys
        keys = [f"'{key}'" for key in keys]

        return f"import pyautogui; pyautogui.hotkey({', '.join(keys)}, interval=1)"

    def wait(self, time):
        return """WAIT"""

    def done(self):
        return """DONE"""
