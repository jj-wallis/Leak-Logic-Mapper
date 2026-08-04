# Leak Logic Mapper

Leak Logic Mapper is a deterministic Static Memory Analyser for C code. It leverages Large Language Models to perform semantic extraction, track pointer lifecycles and identify potential memory leaks.


## Prerequisites
- **Python:** Version 3.8 or higher.
- **Ollama (Optional):** installed and running in the background if you plan to execute the model locally. Ollama can be installed from https://ollama.com/download


## Installation and Setup

**Clone or download the repository, then navigate to the project directory:**

    cd Leak_Logic_Mapper

**Create and activate a virtual environment**

    python -m venv .venv

On macOS/Linux:

    source .venv/bin/activate

On Windows:

    .\.venv\Scripts\activate

**Install the required dependencies:**

    pip install -r requirements.txt


## Configuration

This application sources its runtime configuration from a .env file. Copy the provided .env.example to .env to set your parameters.

You can choose between two backends for LLM inference: API or Local.
By default Leak Logic Mapper is set to use the API backend.
To verify this, open the .env file and ensure the following is set:

    LLM_BACKEND=api

**API Backend Setup:**

Leak Logic Mapper interfaces with the OpenAI API standard. As well as the AzureOpenAI platform.
Open your .env file and set:

    OPENAI_API_KEY=your_api_key_here

Please select a model of choice by setting:

    OPENAI_API_MODEL=your_target_model

*(gpt-4o is the recommended choice)* 

If you are using an OpenAI-Compatible provider set:

    OPENAI_BASE_URL=your_url_here

If you are using Azure OpenAI set:

    OPENAI_ENDPOINT=your_endpoint_here

*Note: If you are not using Azure, ensure the OPENAI_ENDPOINT line in the .env file is commented out.*

**Local Backend Setup:**

To run the analysis locally without external network calls, use Ollama.
Ensure the Ollama background service is running, then Pull your desired model:

    ollama pull your_model_here

Open your .env file and set:

    LLM_BACKEND=local
    LOCAL_MODEL=your_model_here


*Note: local Models must enforce outputs in a JSON format.*


## Usage

Run the application by pointing it to a specific .c file:

    python main.py [OPTIONS] [FILEPATH]

Run Leak Logic Mapper with the -h option to see a list of available options.

**Examples using Sample Test Cases**

A suite of sample C files is included in the tests/sample_test_cases/ directory to help you verify the tool is working correctly.

To test the tool with a sample test case run:

    python main.py tests/sample_test_cases/01_malloc_free_safe.c


## For Your Information

You may want to alter the level of concurrency, when running local models, dependant on your hardware specifications, or when using a provider with low request per minute constraints. To change the number of maximum threads set:


    MAX_WORKERS=...