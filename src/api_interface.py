"""
Leak Logic Mapper: Api Interface
Author: Jacob Wallis

This module interfaces with an API, the LLM can be specified in the .env file.
This module establishes a connection with external providers (currently configured to 
Google Gemini), to act as a remote inference engine for the core orchestrator.
"""

import json
import os
import random
import threading
from pathlib import Path
from dotenv import load_dotenv
from src.exceptions import LLMError

import openai
from openai import AzureOpenAI, OpenAI

# Fetch from environment
MODEL = os.getenv("OPENAI_API_MODEL", "")
HTTP_TIMEOUT_MS = int(os.getenv("HTTP_TIMEOUT_MS", 60000))

# Backoff and Retry
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))
BASE_DELAY = int(os.getenv("BASE_DELAY", 3))

# Get path relative to this file
CURRENT_DIR = Path(__file__).parent
PROMPT_FILE = CURRENT_DIR / "system_instruction.md"

# Get the prompt from the system_instruction.md file
try:
    SYSTEM_INSTRUCTION = PROMPT_FILE.read_text(encoding="utf-8").strip()
    
    # Check if the file exists but has no actual content
    if not SYSTEM_INSTRUCTION:
        raise ValueError(f"Prompt file at {PROMPT_FILE} is empty.")
        
except FileNotFoundError:
    raise ValueError(f"Could not find prompt file at {PROMPT_FILE}")


def _initialise_client() -> AzureOpenAI | OpenAI:
    """
    Safely sources environment variables and initializes the Azure API client.
    """
    print("[*] Verifying Local Environment...")
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    endpoint = os.getenv("OPENAI_ENDPOINT") # used for Azure
    base_url = os.getenv("OPENAI_BASE_URL") # Used for Standard OpenAI
    api_version = os.getenv("OPENAI_API_VERSION", "2024-02-01")
    
    if not api_key:
        raise ValueError("'OPENAI_API_KEY' is missing.")
        
    # Timeout in seconds
    timeout_seconds = HTTP_TIMEOUT_MS / 1000.0
    
    print(f"[*] Model selected: {MODEL}")
    
    # If the user provided an Azure endpoint, use Azure
    if endpoint:
        print("[*] Using Azure OpenAI client...")
        return AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            timeout=timeout_seconds
        )
    # Otherwise, use the standard OpenAI client
    else:
        print("[*] Using Standard OpenAI client...")
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds
        )


# Initialise to none to mitigate import side effects
client = None

def setup_client():
    """
    Called explicitly by the orchestrator to initialize the client.
    """
    global client
    client = _initialise_client()


# Called by the orchestrator when a function is put into the analysis ready queue
def query_llm_memory_analyser(func_name: str, func_code: str, child_context: dict, stop_event: threading.Event) -> dict:
    """
    Sinks the C code and child context into the LLM API, forcing a structured JSON return.
    """
    # Construct the prompt payload
    full_prompt = f"Target Function: {func_name}\n\nCode:\n{func_code}\n\n"
    
    # Inject the memory profiles of dependencies if they exist
    if child_context:
         full_prompt += f"Child Function Memory Profiles:\n{json.dumps(child_context, indent=2)}"

    for attempt in range(MAX_RETRIES):
        try:
            # OpenAI formatting for chat completions
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": full_prompt}
                ],
                response_format={"type": "json_object"}, # Forces the model to respect the JSON schema
                temperature=0.0 # Kept at 0.0 for deterministic extraction
            )
            
            # Extract the string response and parse it
            result_text = response.choices[0].message.content
            return json.loads(result_text)

        # Catch HTTP status errors from OpenAI, like timeouts or rate limits
        except openai.APIStatusError as e:
            if e.status_code in [429, 502, 503, 504]:
                if attempt < MAX_RETRIES - 1:
                    sleep_time = (BASE_DELAY ** attempt) + random.uniform(0, 1)
                    print(f"[-] Timeout/Rate Limit on {func_name}. Retrying in {sleep_time:.2f}s...")
                    
                    stopped = stop_event.wait(timeout=sleep_time)
                    if stopped:
                        return {}
                    continue
            
            # If it's a different API error or we ran out of retries
            raise LLMError(func_name, str(e))
            
        except Exception as e:
            # Catchall 
            raise LLMError(func_name, str(e))