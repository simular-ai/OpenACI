from Foundation import *
from AppKit import *
import difflib
from AppKit import NSWorkspace, NSRunningApplication, NSApplicationActivateIgnoringOtherApps
from openaci.macos import web
from openaci.macos.UIElement import get_content_from_app, get_menu_items_from_app, press_menu_item


def get_closest_app(app_name):
    '''Get the running application that is closest to the given app name
    Args:
        app_name:str, the name of the application to find
    Returns:
        NSRunningApplication: The running application that is closest to the given app name
    '''
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    running_app_names = [app.localizedName() for app in running_apps if app.activationPolicy() == 0]
    closest_app = difflib.get_close_matches(app_name, running_app_names, n=1, cutoff=0.6)
    if closest_app:
        matched_app = closest_app[0]
        # Find and activate the running app
        for app in running_apps:
            if app.localizedName() == matched_app:
                return app
            
    return None

def open_running_app(app_name):
    '''Open an application
        Args:
            app_name:str, the name of the application to open from the list of available applications in the system
    '''
    # Get current running applications
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    running_app_names = [app.localizedName() for app in running_apps if app.activationPolicy() == 0]

    # First check if app is already running
    closest_running = difflib.get_close_matches(app_name, running_app_names, n=1, cutoff=0.6)
    if closest_running:
        matched_app = closest_running[0]
        # Find and activate the running app
        for app in running_apps:
            if app.localizedName() == matched_app:
                app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                print(f"Switched to running application: {matched_app}")
                return "WAIT"

    # If not running, try to launch from installed apps
    closest_installed = difflib.get_close_matches(app_name + ".app", self.all_apps, n=1, cutoff=0.6)
    if closest_installed:
        matched_app = closest_installed[0].replace(".app", "")
        print(f"Opening application: {matched_app}")
        return f"""import subprocess; subprocess.run(["open", "-a", "{matched_app}"], check=True)"""
    
    execution_feedback = f"Could not find application '{app_name}' in running or installed applications"
    print(execution_feedback)
    return "WAIT"


def open_url_in_chrome(url, reuse_tab=False, background=False):
    """Open a URL in Chrome browser
    Args:
        url (str): The URL to open
        reuse_tab (bool): Whether to reuse the current tab, default is False
        background (bool): Whether to open the URL in the background, default is False
    """
    import subprocess
    
    # Ensure URL has proper scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    try:
        # Open URL in Chrome
        subprocess.run([
            'open',
            '-a',
            'Google Chrome',
            url
        ], check=True)
        print(f"Opened {url} in Chrome")
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to open {url} in Chrome")
        return False
    

def fetch_content_from_app(app_name):
    """Get the accessibility tree for Chrome browser
    Returns:
        UIElement: The root element of Chrome's accessibility tree
    """
    closest_app = get_closest_app(app_name)
    if not closest_app:
        print(f"Could not find application '{app_name}'")
        return None
    
    return get_content_from_app(closest_app)
    
import time

def close_tab_in_chrome():
    """Close the current tab in Chrome"""
    # get menu items from current app.
    current_app = NSWorkspace.sharedWorkspace().frontmostApplication()
    # get menu items from accessibility tree
    return press_menu_item(current_app, "Close Tab")
    

def fetch_content_from_url(url, 
                           where="Chrome", 
                           reuse_tab=False, 
                           background=False, 
                           wait_time=2,
                           retry=3,
                           close_tab_when_done=True):
    """Get the accessibility tree for a given URL
    Args:
        url (str): The URL to fetch content from
        where (str): The application to fetch content from, default is Chrome
        wait_time (int): The time to wait for the page to load, default is 2 seconds
        background (bool): Whether to fetch content in the background, default is False
        reuse_tab (bool): Whether to reuse the current tab, default is False
        retry (int): The number of times to retry fetching content, default is 3
    """
    open_url_in_chrome(url, reuse_tab=reuse_tab, background=background)
    target_domain = web.get_domain(url)
    target_url = url
    for _ in range(retry):
        # wait longer for each retry exponentially
        time.sleep(wait_time * (2 ** _))
        content = fetch_content_from_app(where)
        if not content:
            continue

        url = content.get('url', None)
        if not url:
            continue
        
        domain = web.get_domain(url)

        if close_tab_when_done and domain == target_domain:
            print(target_url, url, "closing tab with domain match")
            close_tab_in_chrome()
        
        if content:
            return content
        
    return None