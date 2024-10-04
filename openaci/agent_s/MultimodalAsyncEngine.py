# Author: Saaket Agashe
# Date: 2021-09-15
# License: Apache 2.0

import os
import backoff
import openai
from openai import (
    APIConnectionError,
    APIError,
    RateLimitError,
    AsyncOpenAI,
    AsyncAzureOpenAI
)
import requests
from PIL import Image
from io import BytesIO


def image_parser(args):
    out = args.image_file.split(args.sep)
    return out


def load_image(image_file):
    if image_file.startswith("http") or image_file.startswith("https"):
        response = requests.get(image_file)
        image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        image = Image.open(image_file).convert("RGB")
    return image


def load_images(image_files):
    out = []
    for image_file in image_files:
        image = load_image(image_file)
        out.append(image)
    return out

class LMMEngine:
    pass

class LMMEngineAsyncOpenAI(LMMEngine):
    def __init__(self, api_key=None, model=None, rate_limit=-1, **kwargs):
        assert model is not None, "model must be provided"
        self.model = model

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("An API Key needs to be provided in either the api_key parameter or as an environment variable named OPENAI_API_KEY")
        
        self.api_key = api_key
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit

        self.llm_client = AsyncOpenAI(api_key=self.api_key)

    @backoff.on_exception(backoff.expo, (APIConnectionError, APIError, RateLimitError), max_time=60)
    async def generate(self, messages, temperature=0., max_new_tokens=None, **kwargs):
        '''Generate the next message based on previous messages'''
        response = await self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens if max_new_tokens else 4096,
            temperature=temperature,
            **kwargs,
        )
        if response.choices:
            return response.choices[0].message.content
        else:
            return ValueError("No choices returned from the API")


# TODO: Fix async op
class LMMEngineAsyncAzureOpenAI(LMMEngine):
    def __init__(self, api_key=None, azure_endpoint=None, model=None, api_version=None, rate_limit=-1, **kwargs):
        assert model is not None, "model must be provided"
        self.model = model

        assert api_version is not None, "api_version must be provided"
        self.api_version = api_version

        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("An API Key needs to be provided in either the api_key parameter or as an environment variable named AZURE_OPENAI_API_KEY")
        
        self.api_key = api_key

        azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_API_BASE")
        if azure_endpoint is None:
            raise ValueError("An Azure API endpoint needs to be provided in either the azure_endpoint parameter or as an environment variable named AZURE_OPENAI_API_BASE")
        
        self.azure_endpoint = azure_endpoint
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit

        self.llm_client = AsyncAzureOpenAI(azure_endpoint=self.azure_endpoint, api_key=self.api_key, api_version=self.api_version)
        self.cost = 0.

    @backoff.on_exception(backoff.expo, (APIConnectionError, APIError, RateLimitError), max_tries=10)
    async def generate(self, messages, temperature=0., max_new_tokens=None, **kwargs):
        '''Generate the next message based on previous messages'''
        completion = self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens if max_new_tokens else 4096,
            temperature=temperature,
            **kwargs,
        )
        total_tokens = completion.usage.total_tokens
        self.cost +=  0.02 * ((total_tokens+500) / 1000)
        return completion.choices[0].message.content
    
