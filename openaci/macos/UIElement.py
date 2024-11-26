import json
from Foundation import *
from AppKit import *

from ApplicationServices import (
    AXIsProcessTrusted,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    AXUIElementPerformAction,
    CFEqual,
)

from ApplicationServices import (
    AXUIElementCopyAttributeNames,
    AXUIElementCopyAttributeValue,
)

import logging
logger = logging.getLogger("openaci.agent")

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

    def performAction(self, action):
        AXUIElementPerformAction(self.ref, action)

    def systemWideElement():
        ref = AXUIElementCreateSystemWide()
        return UIElement(ref)

    def __repr__(self):
        return "UIElement%s" % (self.ref)

def traverse_tree(element, level=0, max_depth=10):
    """Traverse and print detailed information for each node in the accessibility tree
    Args:
        element: UIElement to start from
        level: Current indentation level
        max_depth: Maximum depth to traverse
    """
    if level >= max_depth:
        return
        
    try:
        # Get all attributes for the current element
        attribute_names = element.getAttributeNames()
        indent = "  " * level
        
        # Print basic info
        print(f"\n{indent}Level {level} Node:")
        print(f"{indent}{'='*20}")
        
        # Print each available attribute and its value
        for attr_name in attribute_names:
            try:
                value = element.attribute(attr_name)
                # Handle different types of values
                if value is None:
                    continue

                if isinstance(value, (str, int, float, bool)):
                    print(f"{indent}{attr_name}: {value}")
                elif isinstance(value, (list, tuple)):
                    print(f"{indent}{attr_name}: {len(value)} items")
                else:
                    # print(f"{indent}{attr_name}: {type(value)}")
                    pass
            except Exception as e:
                print(f"{indent}{attr_name}: Error getting value - {str(e)}")
        
        # Recursively process children
        children = element.children()
        if children:
            print(f"\n{indent}Children ({len(children)}):")
            for child_ref in children:
                child = UIElement(child_ref)
                traverse_tree(child, level + 1, max_depth)
                
    except Exception as e:
        print(f"{indent}Error processing node at level {level}: {e}")

from bs4 import BeautifulSoup
import html

def accessibility_to_soup(element, level=0, max_depth=20):
    """Convert accessibility tree to HTML-like structure for BeautifulSoup parsing
    Args:
        element: UIElement to start from
        level: Current depth level
        max_depth: Maximum depth to traverse
    Returns:
        BeautifulSoup: Parsed HTML-like structure
    """
    if level >= max_depth or element is None:
        return ""
        
    try:
        # Get element properties
        role = element.attribute('AXRole') or 'unknown'
        title = element.attribute('AXTitle')
        value = element.attribute('AXValue')
        description = element.attribute('AXDescription')
        value = element.attribute('AXValue')
        url_obj = element.attribute('AXURL')
        url = url_obj.absoluteString() if url_obj else str(url_obj)
        frame = element.attribute('AXFrame')

        # Convert role to HTML-friendly tag
        match role:
            case 'AXLink':
                role = 'a'
            case 'AXButton':
                role = 'button'
            case 'AXHeading':
                role = 'h1'
            case 'AXTextField':
                role = 'input'
            case 'AXGroup':
                role = 'div'
            case 'AXStaticText':
                role = 'span'
            case _:  # default case
                role = role.lower().removeprefix('ax')
        
        # Start building HTML-like structure
        html_parts = []
        html_parts.append(f'<{role}')
        
        # Add attributes
        if title:
            html_parts.append(f' title="{html.escape(str(title))}"')
        if url:
            html_parts.append(f' href="{html.escape(str(url))}"')

        if description:
            html_parts.append(f' description="{html.escape(str(description))}"')

        if frame:
            # Convert AXValueRef (CGRect) to string and parse dimensions
            frame_str = str(frame)
            # Parse the frame string which looks like:
            # {x:19.000000 y:168.000000 w:1441.000000 h:737.000000}
            try:
                import re
                dimensions = re.findall(r'[xywh]:(\d+\.?\d*)', frame_str)
                if len(dimensions) == 4:
                    x, y, w, h = map(float, dimensions)
                    html_parts.append(f' width="{w}"')
                    html_parts.append(f' height="{h}"')
                    # html_parts.append(f' x="{x}"')
                    # html_parts.append(f' y="{y}"')
            except:
                pass
        if value:
            html_parts.append(f' value="{html.escape(str(value))}"')
            
        html_parts.append('>')
        
        # Add value as content if it exists
        if value and isinstance(value, str):
            html_parts.append(html.escape(value))
            
        # Process children
        children = element.children()
        if children:
            for child_ref in children:
                if child_ref is not None:
                    child = UIElement(child_ref)
                    child_html = accessibility_to_soup(child, level + 1, max_depth)
                    html_parts.append(child_html)
                    
        # Close tag
        html_parts.append(f'</{role.lower()}>')
        
        return ''.join(html_parts)
        
    except Exception as e:
        logger.error(f"Error converting to soup at level {level}: {e}")
        return ""
    
def get_web_area(element, level=0, max_depth=10):
    """Find the AXWebArea element in the accessibility tree
    Args:
        element: UIElement to start from
        level: Current depth level
        max_depth: Maximum depth to search
    Returns:
        UIElement: The AXWebArea element or None
    """
    if level >= max_depth or element is None:
        return None
        
    try:
        # Check if current element is WebArea
        role = element.attribute('AXRole')
        if role == 'AXWebArea':
            return element
            
        # Search children
        children = element.children()
        if children:
            for child_ref in children:
                if child_ref is not None:
                    child = UIElement(child_ref)
                    web_area = get_web_area(child, level + 1, max_depth)
                    if web_area:
                        return web_area
        return None
        
    except Exception as e:
        logger.error(f"Error finding WebArea at level {level}: {e}")
        return None
    

def extract_page_content(web_area):
    """Extract structured content from web area
    Args:
        web_area: UIElement of AXWebArea
    Returns:
        dict: Structured page content
    """
    if not web_area:
        return None
        
    try:
        # Get basic page info
        title = web_area.attribute('AXTitle')
        url_obj = web_area.attribute('AXURL')
        url = url_obj.absoluteString() if url_obj else str(url_obj)
        
        # Convert to soup for easier parsing
        html_structure = accessibility_to_soup(web_area)
        soup = BeautifulSoup(html_structure, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract images and their context
        images = []
        for img_elem in soup.find_all(['image', 'img']):
            image_url = img_elem.get('href', '')  # href attribute
            width = img_elem.get('width', '')
            height = img_elem.get('height', '')
            description = img_elem.get('alt', '')
            
            # Get image context (nearby text)
            context = [description]
            # Check previous sibling
            prev_elem = img_elem.find_previous_sibling()
            if prev_elem and prev_elem.string:
                context.append(prev_elem.get_text(strip=True))
            # Check next sibling
            next_elem = img_elem.find_next_sibling()
            if next_elem and next_elem.string:
                context.append(next_elem.get_text(strip=True))
            # Check parent's text
            if img_elem.parent and img_elem.parent.string:
                context.append(img_elem.parent.get_text(strip=True))
            
            if image_url:  # Only add if URL exists
                images.append({
                    'imageurl': image_url,
                    'imagecontext': ' '.join(context),
                    'width': width
                })
        # Extract links with deduplication
        links_dict = {}  # Use dict to handle duplicates
        for link in soup.find_all('a'):
            link_url = link.get('href', '')
            link_text = link.get_text(strip=True)
            link_title = link.get('title', '')
            link_description = link.get('description', '')

            textarray = [link_text, link_title, link_description]
            textarray = [text for text in textarray if text]
            # deduplicate
            textarray = list(dict.fromkeys(textarray))

            if link_url:  # Only process if URL exists
                if link_url in links_dict:
                    # If URL exists, append new text if it's different
                    for text in textarray:
                        if text and text not in links_dict[link_url]['text']:
                            links_dict[link_url]['text'].append(text)
                else:
                    # New URL, create new entry with text as list
                    links_dict[link_url] = {
                        'url': link_url,
                        'text': textarray
                    }
        
        # Convert links dictionary to list
        links = [
            {
                'url': url,
                'text': ' | '.join(filter(None, info['text']))  # Join texts with separator
            }
            for url, info in links_dict.items()
        ]

        # Create page dictionary
        page_content = {
            'page_id': str(hash(title)),  # Generate unique ID
            'url': url,
            'title': title,
            'text_content': text_content,
            'images': images,
            'links': links
        }
        
        return page_content
        
    except Exception as e:
        print(f"Error extracting page content: {e}")
        logger.error(f"Error extracting page content: {e}")
        return None
    
def get_title_to_element_map(element, level=0, max_depth=10):
    """Linearize elements from the accessibility tree"""
    # depth first search and put title as key and element as value
    # do not include over max_depth

    elements = {}
    role = UIElement(element).attribute('AXRole')
    title = UIElement(element).attribute('AXTitle')
    print(role, title)

    def traverse(element, level):
        if level >= max_depth:
            return
        
        ui_element = UIElement(element) 
        title = ui_element.attribute('AXTitle')
        role = ui_element.attribute('AXRole')
        print(title, role)
        if role == 'AXMenuItem':
            elements[title] = ui_element
        children = ui_element.children()
        if children:
            for child in children:
                traverse(child, level + 1)
        
    traverse(element, level)

    return elements

def get_menu_items_from_app(app):
    """Get menu items from the accessibility tree of an app"""
    # Get the AXUIElement for Chrome
    pid = app.processIdentifier()
    ax_app = AXUIElementCreateApplication(pid)
    element = UIElement(ax_app)
    # traverse element to get menu items
    children = element.children()
    menuBarElement = None
    for childref in children:
        child = UIElement(childref)
        print(child.attribute('AXRole'))
        if child.attribute('AXRole') == 'AXMenuBar':
            menuBarElement = childref

    print(menuBarElement)

    if not menuBarElement:
        return None
    
    menuItems = get_title_to_element_map(menuBarElement)

    return menuItems

def press_menu_item(app, name):
    """Press a menu item"""
    # Get the AXUIElement for Chrome
    pid = app.processIdentifier()
    ax_app = AXUIElementCreateApplication(pid)
    element = UIElement(ax_app)
    # traverse element to get menu items
    children = element.children()
    menuBarElement = None
    for childref in children:
        child = UIElement(childref)
        if child.attribute('AXRole') == 'AXMenuBar':
            menuBarElement = childref

    if not menuBarElement:
        print("No menu bar element found")
        return False
    
    max_depth = 5
    target_element = None

    def traverse(element, level):
        nonlocal target_element

        if level >= max_depth or target_element:
            return
        
        ui_element = UIElement(element) 
        title = ui_element.attribute('AXTitle')
        role = ui_element.attribute('AXRole')
        if role == 'AXMenuItem':
            if title == name:
                print(f"Found menu item {name}")
                target_element = ui_element
                return
            
        children = ui_element.children()
        if children:
            for child in children:
                traverse(child, level + 1)

    traverse(menuBarElement, 0)

    if target_element:
        target_element.performAction('AXPress')
        print(f"Pressed menu item {name}")

        return True
    else:
        print(f"Menu item {name} not found")
        return False
    
def get_content_from_app(app):
    try:
        # Get the AXUIElement for Chrome
        pid = app.processIdentifier()
        ax_app = AXUIElementCreateApplication(pid)
        element = UIElement(ax_app)
        
        # Get the main window
        windows = element.children()
        if not windows:
            print("No Chrome windows found")
            return None
            
        # Get the accessibility tree for the main window
        main_window = UIElement(windows[0])
        web_area = get_web_area(main_window)
        
        page_content = extract_page_content(web_area)
        # print(json.dumps(page_content, indent=4))
        
        return page_content
    
    except Exception as e:
        print(f"Error getting Chrome accessibility tree: {e}")
        return None

def print_accessibility_tree(self, element, level=0, max_depth=5):
    """Print the accessibility tree structure
    Args:
        element: UIElement to start from
        level: Current indentation level
        max_depth: Maximum depth to traverse
    """
    if level >= max_depth:
        return
        
    try:
        role = element.attribute('AXRole')
        title = element.attribute('AXTitle')
        print("  " * level + f"{role}: {title}")
        
        children = element.children()
        if children:
            for child_ref in children:
                child = UIElement(child_ref)
                self.print_accessibility_tree(child, level + 1, max_depth)
                
    except Exception as e:
        print(f"Error at level {level}: {e}")

if __name__ == "__main__":
    # Examples.
    elem = UIElement.systemWideElement()
    print(elem)
    print(elem.attribute('AXFocusedApplication'))
    print(elem.getAttributeNames())
    elem = (UIElement(elem.attribute('AXFocusedApplication')))
    print(elem.getAttributeNames())
