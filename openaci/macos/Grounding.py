from typing import Dict, List, Tuple
import logging
logger = logging.getLogger("openaci.agent")

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

class UIElement(object):
    def __init__(self, ref=None):
        self.ref = ref

    def getAttributeNames(self):
        error_code, attributeNames = AXUIElementCopyAttributeNames(
            self.ref, None)
        return list(attributeNames)

    def attribute(self, key: str):
        error, value = AXUIElementCopyAttributeValue(self.ref, key, None)
        return value

    def children(self):
        return self.attribute('AXChildren')

    def systemWideElement():
        ref = AXUIElementCreateSystemWide()
        return UIElement(ref)

    def __repr__(self):
        return "UIElement%s" % (self.ref)

class GroundingAgent:
    def __init__(self, obs, top_app=None):
        self.input_tree = obs['accessibility_tree']
        self.screenshot = obs['screenshot']
        self.active_apps = []
        self.top_app = top_app

        self.index_out_of_range_flag = False
        self.top_active_app = None

        self.nodes, self.linearized_accessibility_tree = self.linearize_and_annotate_tree(
            self.input_tree, self.screenshot)

    def get_coordinates(self, position):
        pos_parts = position.__repr__().split().copy()
        # Find the parts containing 'x:' and 'y:'
        for part in pos_parts:
            if part.startswith('x:'):
                x_part = part
            if part.startswith('y:'):
                y_part = part
        # Extract the numerical values after 'x:' and 'y:'
        x = float(x_part.split(':')[1])
        y = float(y_part.split(':')[1])
        return x, y

    def get_sizes(self, size):
        size_parts = size.__repr__().split().copy()

        # Find the parts containing 'Width:' and 'Height:'
        for part in size_parts:
            if part.startswith('w:'):
                width_part = part
            if part.startswith('h:'):
                height_part = part

        # Extract the numerical values after 'Width:' and 'Height:'
        w = float(width_part.split(':')[1])
        h = float(height_part.split(':')[1])
        return w, h

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
                            preserved_nodes.append(element)
            
            children = element.children()
            if children:
                for child_ref in children:
                    child_element = UIElement(child_ref)
                    traverse_and_preserve(child_element)

        # Start traversing from the given element
        traverse_and_preserve(tree)

        # Sanity Check
        for node in preserved_nodes:
            assert node.attribute('AXPosition') is not None

        return preserved_nodes

    # TODO: chunk and shorten this function
    def linearize_and_annotate_tree(self, accessibility_tree, screenshot, platform="macos", tag=False):
        tree = (UIElement(accessibility_tree.attribute('AXFocusedApplication')))
        preserved_nodes = self.preserve_nodes(tree).copy()
        
        linearized_accessibility_tree = [
            "id\trole\ttitle\ttext"]

        for idx, node in enumerate(preserved_nodes):
            title = node.attribute('AXTitle')
            text = node.attribute('AXDescription') or node.attribute('AXValue')
            role = node.attribute('AXRole')
            linearized_accessibility_tree.append(
                "{:}\t{:}\t{:}\t{:}".format(
                    idx,
                    role,
                    title,
                    text,
                )
            )

        tree_bboxes = []
        for node in preserved_nodes:
            coordinates = self.get_coordinates(node.attribute('AXPosition'))
            sizes = self.get_sizes(node.attribute('AXSize'))

            tree_bboxes.append([coordinates[0], coordinates[1], coordinates[0] + sizes[0], coordinates[1] + sizes[1]])

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


    def click(self, element_id, num_clicks=1, click_type="left"):
        '''Click on the element
        Args:
            element: a short description of the element to click on
            num_clicks: the number of clicks to perform
            click_type: the type of click to perform (left, right)
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = self.get_coordinates(node.attribute('AXPosition'))
        sizes: Tuple[int, int] = self.get_sizes(node.attribute('AXSize'))

        # Calculate the center of the element
        x = coordinates[0] + sizes[0] // 2
        y = coordinates[1] + sizes[1] // 2

        # Return pyautoguicode to click on the element
        return f"""import pyautogui; pyautogui.click({x}, {y}, clicks={num_clicks}, button="{click_type}")"""

    def double_click(self, element_id):
        '''Double click on the element
        Args:
            element: a short description of the element to click on
        '''
        node = self.find_element(element_id)
        coordinates: Tuple[int, int] = self.get_coordinates(node.attribute('AXPosition'))
        sizes: Tuple[int, int] = self.get_sizes(node.attribute('AXSize'))

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
        coordinates: Tuple[int, int] = self.get_coordinates(node.attribute('AXPosition'))
        sizes: Tuple[int, int] = self.get_sizes(node.attribute('AXSize'))

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
        coordinates: Tuple[int, int] = self.get_coordinates(node.attribute('AXPosition'))
        sizes: Tuple[int, int] = self.get_sizes(node.attribute('AXSize'))

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
        coordinates: Tuple[int, int] = self.get_coordinates(node.attribute('AXPosition'))
        sizes: Tuple[int, int] = self.get_sizes(node.attribute('AXSize'))

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
        coordinates1: Tuple[int, int] = self.get_coordinates(node1.attribute('AXPosition'))
        sizes1: Tuple[int, int] = self.get_sizes(node2.attribute('AXSize'))

        coordinates2: Tuple[int, int] = self.get_coordinates(node2.attribute('AXPosition'))
        sizes2: Tuple[int, int] = self.get_sizes(node2.attribute('AXSize'))
        
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
