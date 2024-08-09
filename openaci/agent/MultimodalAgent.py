# Author: Saaket Agashe
# Date: 2021-09-15
# License: Apache 2.0

from agent.MultimodalEngine import LMMEngineOpenAI, LMMEngineAzureOpenAI
import base64
import re 

# TODO: Import only if module exists, else ignore
# from llava.constants import (
#     IMAGE_TOKEN_INDEX,
#     DEFAULT_IMAGE_TOKEN,
#     DEFAULT_IM_START_TOKEN,
#     DEFAULT_IM_END_TOKEN,
#     IMAGE_PLACEHOLDER,
# )

class LMMAgent:
    def __init__(self, engine_params=None, system_prompt=None, engine=None):
        if engine is None:
            if engine_params is not None:
                engine_type = engine_params.get('engine_type')
                if engine_type == 'openai':
                    self.engine = LMMEngineOpenAI(**engine_params)
                elif engine_type == 'azure':
                    self.engine = LMMEngineAzureOpenAI(**engine_params)
                else:
                    raise ValueError("engine_type must be either 'openai' or 'azure'")
            else:
                raise ValueError("engine_params must be provided")
        else:
            self.engine = engine

        self.messages = []  # Empty messages

        if system_prompt:
            self.add_system_prompt(system_prompt)
        else:
            self.add_system_prompt("You are a helpful assistant.")
    
    def encode_image(self, image_content):
        # if image_content is a path to an image file, check type of the image_content to verify
        if isinstance(image_content, str):
            with open(image_content, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        else:
            return base64.b64encode(image_content).decode('utf-8')
    
    def reset(self,):
        self.messages = [{"role": "system", "content": [{"type": "text", "text": self.system_prompt}]}]

    def add_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        if len(self.messages) > 0:
            self.messages[0] = {"role": "system", "content": [{"type": "text", "text": self.system_prompt}]}
        else:
            self.messages.append({"role": "system", "content": [{"type": "text", "text": self.system_prompt}]})

    
    def remove_message_at(self, index):
        '''Remove a message at a given index'''
        if index < len(self.messages):
            self.messages.pop(index)

    def add_message(self, text_content, image_content=None, role=None):
        '''Add a new message to the list of messages'''
        # For API-style inference from OpenAI and AzureOpenAI 
        if isinstance(self.engine, (LMMEngineOpenAI, LMMEngineAzureOpenAI)):
            # infer role from previous message
            if self.messages[-1]["role"] == "system":
                role = "user"
            elif self.messages[-1]["role"] == "user":
                role = "assistant"
            elif self.messages[-1]["role"] == "assistant":
                role = "user"

            message = {"role": role, "content": [{"type": "text", "text": text_content}]}
            if image_content:
                base64_image = self.encode_image(image_content)
                message["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}})

            self.messages.append(message)
    
    def get_response(self, user_message=None, image=None, messages=None, temperature=0., max_new_tokens=None, **kwargs):
        '''Generate the next response based on previous messages'''
        if messages is None:
            messages = self.messages
        if user_message:
            messages.append({"role": "user", "content": [{"type": "text", "text": user_message}]})
            
        return self.engine.generate(messages, temperature=temperature, max_new_tokens=max_new_tokens, **kwargs)

