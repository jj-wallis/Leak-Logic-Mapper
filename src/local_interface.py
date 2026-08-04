"""
Leak Logic Mapper: Local Interface
Author: Jacob Wallis | Student ID: 22513465

This module interfaces with locally hosted models (currently configure with Ollama),
providing an offline source of inference generation for the 
core orchestrator without relying on external network calls.
"""

import json
import os
import threading
from pathlib import Path
import urllib.request
import urllib.error
from openai import OpenAI
from src.exceptions import LLMError
from src.utils import sanitize_llm_json

# Fetch from environment
MODEL = os.getenv("LOCAL_MODEL")

# Get the local Ollama port 11434 is a safe default
LOCAL_PORT = os.getenv("LOCAL_PORT", "11434")

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


def _verify_model_availability(target_model: str) -> None:
    """
    Queries the local Ollama instance to confirm the required model is available.
    """
    try:
        # Send a request to Ollama's local tags endpoint
        req = urllib.request.Request(f"http://localhost:{LOCAL_PORT}/api/tags")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            available_models = [model["name"] for model in data.get("models", [])]
            
            # Check if the exact name or the ':latest' appended version is in the list
            match_found = target_model in available_models or f"{target_model}:latest" in available_models
            
            if not match_found:
                raise ValueError(f"MISSING MODEL: '{target_model}' was not found locally.\n[*] Please open a terminal and run: ollama pull {target_model}")
                
    except urllib.error.URLError as e:
        raise ValueError(
            "Failed to reach the local Ollama instance.\n"
            "[*] Please ensure Ollama is installed and the background service is running on the LOCAL_PORT specified in the .env file."
        ) from e


def _initialise_client() -> OpenAI:
    """
    Initializes the OpenAI client pointed at the local Ollama server.
    """
    print("[*] Verifying Local Environment...")
    _verify_model_availability(MODEL)

    print("[*] Model selected:", MODEL)
    return OpenAI(
        base_url=f'http://localhost:{LOCAL_PORT}/v1',
        api_key='ollama' 
    )


# Initialise to none when this nodule is imported
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
    Sinks the C code into the local GPU via Ollama.
    """
    # Construct the prompt payload
    full_prompt = f"Target Function: {func_name}\n\nCode:\n{func_code}\n\n"
    
    # Inject the memory profiles of child functions if they exist
    if child_context:
         full_prompt += f"Child Function Memory Profiles:\n{json.dumps(child_context, indent=2)}"

    try:
        # Get the JSON prediction from the model
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1,
            response_format={ "type": "json_object" } # Forces the model to respect the JSON schema
        )

        raw_json_string = response.choices[0].message.content
        parsed_json = json.loads(raw_json_string)

        # Replace any NULL values with the "none" as to adhere to the JSON schema
        return sanitize_llm_json(parsed_json)

    except json.JSONDecodeError as e:
        # Local models occasionally hallucinate bad JSON syntax
        raise LLMError(func_name, f"Local model returned invalid JSON: {e}")
    except Exception as e:
        raise LLMError(func_name, str(e))