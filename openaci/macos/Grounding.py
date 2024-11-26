from typing import Dict, List, Tuple
import os 
import subprocess
import logging
logger = logging.getLogger("openaci.agent")
import difflib
from Foundation import *
from AppKit import *
import torchvision 
import torch 
import base64 
import requests
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from typing import Dict, List, Tuple
import os
import subprocess
import logging
logger = logging.getLogger("openaci.agent")
import difflib


from openaci.macos.UIElement import UIElement
from openaci.macos.system import open_running_app

from AppKit import NSWorkspace, NSRunningApplication



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
    def __init__(self, top_app=None, top_app_only=True, ocr=True):
        self.active_apps = set()
        self.top_app = top_app
        self.top_app_only = (
            top_app_only  # Only include top app in the accessibility tree
        )
        self.ocr = ocr
        self.index_out_of_range_flag = False
        self.clipboard = ""
        self.top_active_app = None
        self.notes = []
        self.clipboard = ""

        # Directories to search for applications in MacOS
        directories_to_search = [
            "/System/Applications",
            "/Applications"
        ]
        self.all_apps = list_apps_in_directories(directories_to_search)

        # self.nodes, self.linearized_accessibility_tree = self.linearize_and_annotate_tree(
        #     self.input_tree, self.screenshot)
        # print(self.linearized_accessibility_tree)
    
    def get_current_applications(self, initial_obs):
        # Get the shared workspace instance
        workspace = NSWorkspace.sharedWorkspace()

        # Get a list of running applications
        running_apps = workspace.runningApplications()

        # Iterate through the list and print each application's name
        current_apps = []
        for app in running_apps:
            if app.activationPolicy() == 0:
                app_name = app.localizedName()
                current_apps.append(app_name)
        
        return current_apps
                
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
    
    def extract_elements_from_screenshot(self, screenshot) -> Dict:
        """Uses paddle-ocr to extract elements with text from the screenshot. The elements will be added to the linearized accessibility tree downstream"""

        # Convert screenshot to PIL image
        def send_image_to_ocr(screenshot) -> Dict:

            url = os.environ.get("OCR_SERVER_ADDRESS", "")
            if url == "":
                raise Exception("OCR SERVER ADDRESS NOT SET")
            encoded_screenshot = base64.b64encode(screenshot).decode("utf-8")
            data = {"img_bytes": encoded_screenshot}
            response = requests.post(url, json=data)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Request failed with status code {response.status_code}",
                    "results": [],
                }

        return send_image_to_ocr(screenshot)["results"]

    def add_ocr_elements(
        self, screenshot, linearized_accessibility_tree, preserved_nodes
    ):
        # Get the bounding boxes of the elements in the linearized accessibility tree
        tree_bboxes = []
        for node in preserved_nodes:
            coordinates: Tuple[int, int] = node['position']
            sizes: Tuple[int, int] = node['size']
            tree_bboxes.append(
                [
                    coordinates[0],
                    coordinates[1],
                    coordinates[0] + sizes[0],
                    coordinates[1] + sizes[1],
                ]
            )

        # Use OCR to found boxes that might be missing from the accessibility tree
        try:
            ocr_bboxes = self.extract_elements_from_screenshot(screenshot)
        except Exception as e:
            print(f"Error: {e}")
            ocr_bboxes = []
        else:
            # Check for intersection over union between the existing atree bounding boxes and the ocr bounding boxes, if ocr bounding boxes are new add them to the linearized accesibility tree
            if (
                len(ocr_bboxes) > 0
            ):  # Only check IOUs and add if there are any bounding boxes returned by the ocr module
                preserved_nodes_index = len(preserved_nodes)
                for ind, (i, content, box) in enumerate(ocr_bboxes):
                    # x1, y1, x2, y2 = int(box.get('left', 0)), int(box['top']), int(), int(box['bottom'])
                    (
                        x1,
                        y1,
                        x2,
                        y2,
                    ) = (
                        int(box.get("left", 0)),
                        int(box.get("top", 0)),
                        int(box.get("right", 0)),
                        int(box.get("bottom", 0)),
                    )
                    iou = (
                        torchvision.ops.box_iou(
                            torch.tensor(tree_bboxes), torch.tensor([[x1, y1, x2, y2]])
                        )
                        .numpy()
                        .flatten()
                    )

                    if max(iou) < 0.1:
                        # Add the element to the linearized accessibility tree
                        # TODO: ocr detected elements should be classified for their tag, currently set to push button for the agent to think they are interactable
                        linearized_accessibility_tree.append(
                            f"{preserved_nodes_index}\tAXButton\t\t{content}\t\t"
                        )

                        # add to preserved node with the component_ns prefix node.get("{{{:}}}screencoord".format(component_ns), "(-1, -1)"
                        node = {'position': (x1, y1), 
                                'size' : (x2 - x1, y2 - y1), 
                                'title': "", 
                                'text': content,
                                'role': "AXButton"}
                        
                        preserved_nodes.append(node)
                        preserved_nodes_index += 1

        return linearized_accessibility_tree, preserved_nodes

    # TODO: chunk and shorten this function
    def linearize_and_annotate_tree(self, obs, show_all=False):
        accessibility_tree = obs['accessibility_tree']
        screenshot = obs['screenshot']  
        self.top_app = NSWorkspace.sharedWorkspace().frontmostApplication().localizedName()
        tree = (UIElement(accessibility_tree.attribute('AXFocusedApplication')))
        exclude_roles = ["AXGroup", "AXLayoutArea", "AXLayoutItem", "AXUnknown"]
        preserved_nodes = self.preserve_nodes(tree, exclude_roles).copy()
        
        
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
        
         # Add OCR elements to the linearized accessibility tree to account for elements that are not in the accessibility tree
        if self.ocr:
            linearized_accessibility_tree, preserved_nodes = self.add_ocr_elements(
                screenshot, linearized_accessibility_tree, preserved_nodes
            )
        self.nodes = preserved_nodes.copy()
            
        # Convert to string
        linearized_accessibility_tree = "\n".join(
            linearized_accessibility_tree)
        
        return linearized_accessibility_tree

    def find_element(self, element_id):
        try:
            selected_element = self.nodes[int(element_id)]
        except:
            print("The index of the selected element was out of range.")
            selected_element = self.nodes[0]
            self.index_out_of_range_flag = True 
        return selected_element

    # TODO: this is still MACOS specific code
    # @agent_action
    # def open(self, app_or_file_name):
    #     '''Open an application
    #         Args:
    #             app_or_file_name:str, the name of the application or file to open 
    #     '''
    #     return f"import pyautogui; import time; pyautogui.hotkey('command', 'space', interval=1); pyautogui.typewrite({repr(app_or_file_name)}); pyautogui.press('enter'); time.sleep(2.);"
    @agent_action
    def open_app(self, app_name):
        '''Open an application
            Args:
                app_name:str, the name of the application to open from the list of available applications in the system: AVAILABLE_APPS
        '''
        # fuzzy match the app name
        closest_matches = difflib.get_close_matches(app_name + ".app", self.all_apps, n=1, cutoff=0.6) 
        if app_name in self.all_apps:
            print(f"{app_name} has been opened successfully.")
            return f"""import subprocess; subprocess.run(["open", "-a", "{app_name}"], check=True)"""
        elif open_running_app(app_name):
            print(f"{app_name} has been opened successfully.")
            return """WAIT"""
        else:
            self.execution_feedback = "There is no application " + app_name + " installed on the system. Please replan and avoid this action."
            print(self.execution_feedback)
            return """WAIT"""
    
    @agent_action
    def switch_applications(self, app_or_file_name):
        '''Open an application
            Args:
                app_or_file_name:str, the name of the application or file to open 
        '''
        return f"import pyautogui; pyautogui.hotkey('command', 'space', interval=1); pyautogui.typewrite({repr(app_or_file_name)}); pyautogui.press('enter')"

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
        coordinates: Tuple[int, int] = node['position']
        sizes: Tuple[int, int] = node['size']

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
            coordinates = node['position']
            sizes = node['size']

            # Calculate the center of the element
            x = coordinates[0] + sizes[0] // 2
            y = coordinates[1] + sizes[1] // 2

            # Start typing at the center of the element
            command = "import pyautogui; "
            command += f"pyautogui.click({x}, {y}); "

            if overwrite:
                command += (
                    f"pyautogui.hotkey('command', 'a', interval=1); pyautogui.press('backspace'); "
                )

            command += f"pyautogui.write({repr(text)}); "

            if enter:
                command += "pyautogui.press('enter'); "
        else:
            # If no element is found, start typing at the current cursor location
            command = "import pyautogui; "

            if overwrite:
                command += (
                    f"pyautogui.hotkey('command', 'a', interval=1); pyautogui.press('backspace'); "
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
        coordinates1 = node1['position']
        sizes1 = node1['size']

        coordinates2 = node2['position']
        sizes2 = node2['size']

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
        coordinates = node['position']
        sizes = node['size']

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
            keys:List the keys to press in combination in a list format (e.g. ['command', 'c'])
        """
        # add quotes around the keys
        keys = [f"'{key}'" for key in keys]
        return f"import pyautogui; pyautogui.hotkey({', '.join(keys)}, interval=1)"

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
