from typing import Dict, List, Tuple
import os 
import subprocess
import logging
logger = logging.getLogger("openaci.agent")
import difflib
from Foundation import *
from AppKit import *

from ApplicationServices import (
    AXIsProcessTrusted,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    CFEqual,
)

from ApplicationServices import (
    AXIsProcessTrusted,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeNames,
    AXUIElementCopyAttributeValue,
    AXValueGetType,
    AXValueGetValue,
    kAXValueCGPointType,
    kAXValueCGSizeType,
)


from openaci.macos.UIElement import UIElement


def agent_action(func):
    func.is_agent_action = True
    return func

def list_apps_in_directories(directories):
    apps = []
    for directory in directories:
        if os.path.exists(directory):
            directory_apps = [app for app in os.listdir(directory) if app.endswith(".app")]
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
            "/System/Applications",
            "/Applications"
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
            role = element.attribute('AXRole')

            if role not in exclude_roles:
                # TODO: get coordinate values directly from interface
                position = element.attribute('AXPosition')
                size = element.attribute('AXSize')
                if position and size:
                        pos_parts = position.__repr__().split().copy()
                        # Find the parts containing 'x:' and 'y:'
                        x_part = next(part for part in pos_parts if part.startswith('x:'))
                        y_part = next(part for part in pos_parts if part.startswith('y:'))
                        
                        # Extract the numerical values after 'x:' and 'y:'
                        x = float(x_part.split(':')[1])
                        y = float(y_part.split(':')[1])

                        size_parts = size.__repr__().split().copy()
                        # Find the parts containing 'Width:' and 'Height:'
                        width_part = next(part for part in size_parts if part.startswith('w:'))
                        height_part = next(part for part in size_parts if part.startswith('h:'))

                        # Extract the numerical values after 'Width:' and 'Height:'
                        w = float(width_part.split(':')[1])
                        h = float(height_part.split(':')[1])
        
                        if x >= 0 and y >= 0 and w > 0 and h > 0:
                            preserved_nodes.append({'position': (x, y), 
                                                    'size' : (w, h), 
                                                    'title': str(element.attribute('AXTitle')), 
                                                    'text': str(element.attribute('AXDescription')) or str(element.attribute('AXValue')),
                                                    'role': str(element.attribute('AXRole'))})
            
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
        tree = (UIElement(accessibility_tree.attribute('AXFocusedApplication')))
        preserved_nodes = self.preserve_nodes(tree).copy()
        
        linearized_accessibility_tree = [
            "id\trole\ttitle\ttext"]

        for idx, node in enumerate(preserved_nodes):
            title = node['title']
            text = node['text']
            role = node['role']
            linearized_accessibility_tree.append(
                "{:}\t{:}\t{:}\t{:}".format(
                    idx,
                    role,
                    title,
                    text,
                )
            )

        # Convert to string
        linearized_accessibility_tree = "\n".join(
            linearized_accessibility_tree)
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
    @agent_action
    def open_app(self, app_name):
        '''Open an application
            Args:
                app_name:str, the name of the application to open from the list of available applications in the system: AVAILABLE_APPS
        '''
        # fuzzy match the app name
        # closest_matches = difflib.get_close_matches(app_name + ".app", self.all_apps, n=1, cutoff=0.6) 
        if app_name in self.all_apps:
            print(f"{app_name} has been opened successfully.")
            return f"""import subprocess; subprocess.run(["open", "-a", "{app_name}"], check=True)"""
        else:
            self.execution_feedback = "There is no application " + app_name + " installed on the system. Please replan and avoid this action."
            print(self.execution_feedback)
            return """WAIT"""

    @agent_action
    def click(self, element_id:int):
        '''Click on the element
        Args:
            element_id:int, ID of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2
        print(f'coordinates of node {node}, are {x}, {y}')

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks=1, button="left")"""

    @agent_action
    def double_click(self, element_id:int):
        '''Double click on the element
        Args:
            element_id:int, ID of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks=2, button="left")"""

    @agent_action
    def right_click(self, element_id:int):
        '''Right click on the element
        Args:
            element_id:int, ID of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, button="right")"""

    @agent_action
    def click_at_coordinates(self, x:int, y:int, num_clicks:int, click_type:str="left"):
        '''Click on the element at the specified coordinates. Only use if the required element does not exist in the accessibility tree.
        Args:
            x:int the x-coordinate of the element to click on
            y:int the y-coordinate of the element to click on
            num_clicks:int the number of clicks to perform
            click_type:str the type of click to perform ("left", "right")
        '''
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks={num_clicks}, button="{click_type}")"""

    @agent_action
    def type(self, element_id:int, text:str, append: bool = True):
        '''Type text into the element
        Args:
            element_id:int, ID of the element to click on
            text:str the text to type into the element
        '''
        try:
            node = self.find_element(element_id)
        except:
            node = self.find_element(0)
        # print(node.attrib)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.click({x}, {y}); time.sleep(0.5); pyautogui.typewrite('''{text}''')"""
        else:
            return f"""import pyautogui; pyautogui.click({x}, {y}); time.sleep(0.5); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("backspace"); pyautogui.typewrite('''{text}''')"""

    @agent_action
    def type_and_enter(self, element_id:int, text:str, append: bool = True):
        '''Type text into the element
        Args:
            element_id:int, ID of the element to click on
            text:str the text to type into the element
        '''
        try:
            node = self.find_element(element_id)
        except:
            node = self.find_element(0)
        # print(node.attrib)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.click({x}, {y}); time.sleep(0.5); pyautogui.typewrite('''{text}'''); pyautogui.press("enter")"""
        else:
            return f"""import pyautogui; pyautogui.click({x}, {y}); time.sleep(0.5); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("delete"); pyautogui.typewrite('''{text}'''); pyautogui.press("enter")"""

    @agent_action
    def drag_and_drop(self, element1_id:int, element2_id:int):
        '''Drag element1 and drop it on element2
        Args:
            element1_id: ID of the element to click on of the element to drag
            element2_id: ID of the element to click on of the element to drop on
        '''
        node1 = self.find_element(element1_id)
        node2 = self.find_element(element2_id)
        coordinates1: Tuple[int, int] = node1['position']
        sizes1: Tuple[int, int] = node1['size']

        coordinates2: Tuple[int, int] = node2['position']
        sizes2: Tuple[int, int] = node2['size']
        
        # Calculate the center of the element
        x1 = coordinates1[0] + sizes1[0] // 2
        y1 = coordinates1[1] + sizes1[1] // 2

        x2 = coordinates2[0] + sizes2[0] // 2
        y2 = coordinates2[1] + sizes2[1] // 2

        # Return pyautoguicode to drag and drop the elements
        return f"import pyautogui; pyautogui.moveTo({x1}, {y1}); pyautogui.dragTo({x2}, {y2})"

    @agent_action
    def scroll_in_element(self, element_id:int,clicks:int):
        '''Scroll the element in the specified direction
        Args:
            element_id: ID of the element to scroll in
            clicks: the number of clicks to scroll can be positive or negative
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to scroll the element
        return f"import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.scroll({clicks})"

    @agent_action
    def hotkey(self, keys:List[str]):
        '''Press a hotkey combination
        Args:
            keys:List[str] the keys to press in combination in a list format (e.g. ['command', 'c'])
        '''
        # add quotes around the keys
        keys = [f"'{key}'" for key in keys]

        return f"import pyautogui; pyautogui.hotkey({', '.join(keys)}, interval=1)"

    @agent_action
    def wait(self, time:float):
        '''Wait for the specified amount of time
        Args:
            time:float the amount of time to wait in seconds
        '''
        return f"""import time; time.sleep({time})"""

    @agent_action
    def done(self):
        '''Indicate that the task is complete'''
        return """DONE"""
