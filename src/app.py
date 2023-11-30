"""Load OpenAI api key from environment variable or ini config
sample ini config: api_key.ini
[openai]
APIKEY = xxx
"""

import os
from configparser import ConfigParser
import vision
import pyautogui

api_key = os.environ.get('OPENAI_API_KEY')
if api_key is None:
    try:
        config = ConfigParser()
        config.read(os.path.join(os.getcwd(), 'api_key.ini'))
        api_key = config.get('openai', 'APIKEY')
    except:
        print('No OpenAI api key found!')
        exit()


def run(query: str):
    """Run query."""
    if query.startswith("type"):
        # Keyboard.
        pyautogui.write(query[len("type "):])
    else:
        # Mouse.
        response = vision.ask(query, api_key)
        if 'choices' in response:
            message = response['choices'][0]['message']
            role = message['role']
            content = message['content']
            print(f'\n{role}: {content}')
        else:
            print(response)


def main():
    """Entry point for the program.

    It continuously prompts the user for a query, sends it to the vision module for processing,
    and displays the response received from the vision module.
    """

    while True:
        query = input("Query: ")
        run(query)


if __name__ == '__main__':
    main()
