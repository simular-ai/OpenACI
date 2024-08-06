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

    def systemWideElement():
        ref = AXUIElementCreateSystemWide()
        return UIElement(ref)

    def __repr__(self):
        return "UIElement%s" % (self.ref)


if __name__ == "__main__":
    # Examples.
    elem = UIElement.systemWideElement()
    print(elem)
    print(elem.attribute('AXFocusedApplication'))
    print(elem.getAttributeNames())
    elem = (UIElement(elem.attribute('AXFocusedApplication')))
    print(elem.getAttributeNames())
