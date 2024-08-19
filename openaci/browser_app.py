import os 
import datetime 
import base64
import io
import pyautogui
import platform 
import logging
import sys
import time 

from playwright.sync_api import sync_playwright
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

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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

def filter_useful_elements(soup):
    return [element for element in soup.find_all() if is_useful(element)]

def linearize_and_annotate_dom(soup):
    # Headers for the linearized tree
    linearized_dom_tree = ["idx\ttag\tid\tclass\ttext"]

    # Function to extract attributes and text content
    def extract_info(node, idx):
        tag = node.name or ""
        node_id = node.get('id', '')
        node_class = " ".join(node.get('class', []))
        text = node.get_text(strip=True) if node.get_text(strip=True) else ""

        return "{:}\t{:}\t{:}\t{:}\t{:}".format(
            idx, tag, node_id, node_class, text
        )

    # Traverse the useful elements and linearize
    preserved_nodes = filter_useful_elements(soup)
    for idx, node in enumerate(preserved_nodes):
        linearized_dom_tree.append(extract_info(node, idx))

    # Convert to string
    linearized_dom_tree = "\n".join(linearized_dom_tree)
    
    return preserved_nodes, linearized_dom_tree

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os

def main():
    def run(playwright):
        # Define the path for the user data directory where the browser state will be saved
        user_data_dir = os.path.join(os.getcwd(), "user_data")
        
        # Launch the browser with the persistent context
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir, 
            headless=False
        )
        
        page = browser.new_page()
        page.goto("https://www.google.com")
        
        # Retrieve the DOM tree
        dom_tree = page.content()
        
        # Parse the DOM with BeautifulSoup
        soup = BeautifulSoup(dom_tree, 'lxml')
        
        # Linearize and annotate the DOM tree
        preserved_nodes, linearized_dom_tree = linearize_and_annotate_dom(soup)
        print(linearized_dom_tree)
        
        input("Press Enter to close the browser...")
        browser.close()

    with sync_playwright() as playwright:
        run(playwright)

if __name__ == "__main__":
    main()

    # while True:
    #     query = input("Query: ")
    #     engine_params = {
    #         "engine_type": "openai",
    #         "model": "gpt-4o",
    #     }
    #     agent = IDBasedGroundingUIAgent(
    #         engine_params,
    #         platform="browser",
    #         max_tokens=1500,
    #         top_p=0.9,
    #         temperature=0.5,
    #         action_space="pyautogui",
    #         observation_type="atree",
    #         max_trajectory_length=3,
    #         a11y_tree_max_tokens=10000,
    #         enable_reflection=True,
    #     )
    #     agent.reset()
    #     agent.run(instruction=query)
        
    #     # Ask user if they want to provide another query
    #     response = input("Would you like to provide another query? (y/n): ")
    #     if response.lower() != "y":
    #         break

# if __name__ == '__main__':
#     main()
