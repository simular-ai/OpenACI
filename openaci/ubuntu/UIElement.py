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


class UIElement(object):
    def __init__(self, node:Accessible):
        self.node: Accessible = node 

    def getAttributeNames(self):
        attributes = self.node.getAttributes()

    @staticmethod
    def systemWideElement():
        desktop = pyatspi.Registry.getDesktop(0)
        for app in desktop:
            for window in app:
                if window.getState().contains(pyatspi.STATE_ACTIVE):
                    active_node = app
        return UIElement(active_node)
    
    @property
    def states(self):
        state_names = []
        states: List[StateType] = self.node.getState().get_states()
        for st in states:
            state_name: str = StateType._enum_lookup[st]
            state_names.append(state_name)
        return state_names

    @property 
    def attributes(self):
        try:
            attributes: List[str] = self.node.getAttributes()
            attribute_dict = {}
            for attrbt in attributes:
                attribute_name: str
                attribute_value: str
                attribute_name, attribute_value = attrbt.split(":", maxsplit=1)
                attribute_dict[attribute_name] = attribute_value
            return attribute_dict
        except NotImplementedError:
            return None
        
    @property
    def component(self):
        try:
            component: Component = self.node.queryComponent()
            return component
        except NotImplementedError:
            return None
    
    @property
    def value(self):
        try:
            value: ATValue = self.node.queryValue()
            return value 
        except NotImplementedError:
            return None 
    
    @property
    def text(self):
        try:
            action: ATAction = self.node.queryAction()
            text: str = text_obj.getText(0, text_obj.characterCount)
            text = text.replace("\ufffc", "").replace("\ufffd", "")
            return text
        except NotImplementedError:
            return ''


    def children(self):
        '''Return list of children of the current node'''
        return list(self.node)

    def __repr__(self):
        return "UIElement%s" % (self.node)

def traverse_and_print(node):
    print(node.attributes)
    print(node.node.getRoleName())
    for child in node.children():
        traverse_and_print(UIElement(child))
        

if __name__ == "__main__":
    # Examples.
    desktop = pyatspi.Registry.getDesktop(0)
    
    for app in desktop:
        for window in app:
            if window.getState().contains(pyatspi.STATE_ACTIVE):
                active_node = UIElement(window)

    traverse_and_print(active_node)


