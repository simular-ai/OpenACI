from Foundation import *
from AppKit import *
import os 

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

import logging
logger = logging.getLogger("openaci.agent")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import playwright


# TODO: this implementation needs to be adjusted to better support playwright-style browser automation
class UIElement(object):

    def __init__(self, page:str):
        self.page = page

    def systemWideElement(url:str):
        user_data_dir = os.path.join(os.getcwd(), "user_data")
        
        # Launch the browser with the persistent context
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir, 
            headless=False
        )
        page = browser.new_page()
        if page:
            page.goto(url)
        else:
            raise Exception("Must specify URL")
            
        # Retrieve the DOM tree
        dom_tree = page.content()
        
        # Parse the DOM with BeautifulSoup
        soup = BeautifulSoup(dom_tree, 'lxml')

        return UIElement(soup) 

    def __repr__(self):
        return "UIElement%s" % (self.ref)




