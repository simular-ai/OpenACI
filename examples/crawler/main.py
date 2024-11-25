from openaci.macos.Grounding import GroundingAgent
import openaci.macos.system as system
import openaci.macos.web as web
import time
import json
import os

def crawl(main_url, root_dir=None, browser="Chrome"):
    # get domain from url in general way
    domain = web.get_domain(main_url)
    print('domain', domain)
    content = system.fetch_content_from_url(main_url, where=browser, wait_time=2, retry=3)

    # pretty print content
    # print(json.dumps(content, indent=4))

    # get all the links from content and open them in chrome
    # do not open the same link twice
    # do not open links that are not in the same domain
    # create a directory to save the json content
    visited_links = []
    # default goes to home directory downloads folder
    root_dir = root_dir or os.path.expanduser("~/Downloads/simular/")
    root_dir = f"{root_dir}/{domain}"
    os.makedirs(root_dir, exist_ok=True)

    def get_file_path(link):
        # handle / inside the link and remove https://
        link = link.replace('/', '_').replace('https://', '')
        return f"{root_dir}/{link}.json"
    
    # save json content to a file
    def save_json_content(content, link):
        with open(get_file_path(link), "w") as f:
            # pretty print json
            json.dump(content, f, indent=4)

    def load_json_content(link):
        with open(get_file_path(link), "r") as f:
            return json.load(f)
        return None

    save_json_content(content, main_url)

    # breadth first search visit all the links
    queue = []

    def add_to_queue(links):
        for link in links:
            # skip if link is already visited
            if link in visited_links:
                continue
            # skip if link is not in the same domain
            print(web.get_domain(link), domain)
            if web.get_domain(link) != domain:
                continue
            queue.append(link)
    
    try:
        add_to_queue([x['url'] for x in content['links'] if x['url']])
    except Exception as e:
        print(f"Error adding to queue: {e}")

    print(content['links'])
    print(f"Queue size: {len(queue)}")
        
    while queue:
        link = queue.pop(0)
        print(f"Visiting {link}")

        visited_links.append(link)
        # skip if file already exists
        if os.path.exists(get_file_path(link)):
            # load the json content
            content = load_json_content(link)
        else:
            content = system.fetch_content_from_url(link, where=browser, wait_time=2)
            save_json_content(content, link)

        try:
            add_to_queue([x['url'] for x in content['links'] if x['url']])
        except Exception as e:
            print(f"Error adding to queue: {e}")

if __name__ == "__main__":
    crawl("smarthistory.org")