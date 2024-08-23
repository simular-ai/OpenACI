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

# def is_useful(element):
#     # Tags to explicitly ignore
#     ignore_tags = ['style', 'script', 'meta', 'link', 'head', 'title', 'noscript']

#     # Early return if the element is in the ignore list
#     if element.name in ignore_tags:
#         return False

#     # Interactive elements
#     interactive_tags = ['button', 'a', 'input', 'select', 'textarea', 'label']
    
#     # Elements with meaningful content
#     content_tags = ['h1', 'h2', 'h3', 'p', 'div', 'span', 'li']
    
#     # Check if the element is one of the interactive or content tags
#     if element.name not in interactive_tags and element.name not in content_tags:
#         return False
    
#     # Check for non-empty text or specific attributes
#     if not (element.get_text(strip=True) or element.has_attr('id') or element.has_attr('name') or element.has_attr('role')):
#         return False
    
#     # Check visibility (simplified)
#     style = element.get('style', '')
#     if 'display:none' in style or 'visibility:hidden' in style:
#         return False
    
#     # If it passes all checks, it's considered useful
#     return True

# def filter_useful_elements(soup):
#     return [element for element in soup.find_all() if is_useful(element)]

# def linearize_and_annotate_dom(soup):
#     # Headers for the linearized tree
#     linearized_dom_tree = ["idx\ttag\tid\tclass\tlabel\ttext"]

#     # Function to extract attributes and text content
#     def extract_info(node, idx):
#         tag = node.name or ""
#         node_id = node.get('id', '')
#         node_class = " ".join(node.get('class', []))
#         text = node.get_text(strip=True) if node.get_text(strip=True) else ""
#         label = node.get('aria-label', '')  

#         return "{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
#             idx, tag, node_id, node_class, label, text
#         )

#     # Traverse the useful elements and linearize
#     preserved_nodes = filter_useful_elements(soup)
#     for idx, node in enumerate(preserved_nodes):
#         linearized_dom_tree.append(extract_info(node, idx))

#     # Convert to string
#     linearized_dom_tree = "\n".join(linearized_dom_tree)
    
#     return preserved_nodes, linearized_dom_tree

from macos.UIElement import UIElement

def list_apps_in_directories(directories):
    apps = []
    for directory in directories:
        if os.path.exists(directory):
            directory_apps = [app for app in os.listdir(directory) if app.endswith(".app")]
            apps.extend(directory_apps)
    return apps

class GroundingAgent:
    def __init__(self, obs, top_app=None):
        self.page = obs['accessibility_tree']
        self.screenshot = obs['screenshot']
        self.active_apps = []
        self.top_app = top_app

        self.index_out_of_range_flag = False
        self.top_active_app = None
        self.execution_feedback = None

        self.nodes, self.linearized_accessibility_tree = self.linearize_and_annotate_tree(
            self.page, self.screenshot)


    def filter_useful_elements(self, soup):
        def is_useful(element):
            # Tags to explicitly ignore
            ignore_tags = ['style', 'script', 'meta', 'link', 'head', 'title', 'noscript']

            # Early return if the element is in the ignore list
            if element.name in ignore_tags:
                return False

            # Interactive elements
            interactive_tags = ['button', 'a', 'input', 'select', 'textarea', 'label']
            
            # Elements with meaningful content
            content_tags = ['h1', 'h2', 'h3', 'p', 'div', 'span', 'li']
            
            # Check if the element is one of the interactive or content tags
            if element.name not in interactive_tags and element.name not in content_tags:
                return False
            
            # Check for non-empty text or specific attributes
            if not (element.get_text(strip=True) or element.has_attr('id') or element.has_attr('name') or element.has_attr('role')):
                return False
            
            # Check visibility (simplified)
            style = element.get('style', '')
            if 'display:none' in style or 'visibility:hidden' in style:
                return False
            
            # If it passes all checks, it's considered useful
            return True
        return [element for element in soup.find_all() if is_useful(element)]
        

    # TODO: chunk and shorten this function
    def linearize_and_annotate_dom(self, soup, screenshot):
        # Headers for the linearized tree
        linearized_dom_tree = ["idx\ttag\tid\tclass\tlabel\ttext"]

        # Function to extract attributes and text content
        def extract_info(node, idx):
            tag = node.name or ""
            node_id = node.get('id', '')
            node_class = " ".join(node.get('class', []))
            text = node.get_text(strip=True) if node.get_text(strip=True) else ""
            label = node.get('aria-label', '')  

            return "{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                idx, tag, node_id, node_class, label, text
            )

        # Traverse the useful elements and linearize
        preserved_nodes = self.filter_useful_elements(soup)
        for idx, node in enumerate(preserved_nodes):
            linearized_dom_tree.append(extract_info(node, idx))

        # Convert to string
        linearized_dom_tree = "\n".join(linearized_dom_tree)
        
        return preserved_nodes, linearized_dom_tree

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
            return f"""import subprocess; subprocess.run(["open", "-a", "{app_name}"], check=True)"""
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
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2
        print(f'coordinates of node {node}, are {x}, {y}')

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks={num_clicks}, button="{click_type}")"""

    def double_click(self, element_id):
        '''Double click on the element
        Args:
            element: a short description of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks=2, button="left")"""

    def right_click(self, element_id):
        '''Right click on the element
        Args:
            element: a short description of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, button="right")"""

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
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.click({x}, {y}); pyautogui.typewrite("{text}")"""
        else:
            return f"""import pyautogui; pyautogui.click({x}, {y}); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("backspace"); pyautogui.typewrite("{text}")"""

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
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to type into the element
        if append:
            return f"""import pyautogui; pyautogui.click({x}, {y}); pyautogui.typewrite("{text}"); pyautogui.press("enter")"""
        else:
            return f"""import pyautogui; pyautogui.click({x}, {y}); pyautogui.hotkey("ctrl", "a", interval=1); pyautogui.press("delete"); pyautogui.typewrite("{text}"); pyautogui.press("enter")"""

    def drag_and_drop(self, element1_id, element2_id):
        '''Drag element1 and drop it on element2
        Args:
            element1: a short description of the element to drag
            element2: a short description of the element to drop on
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
