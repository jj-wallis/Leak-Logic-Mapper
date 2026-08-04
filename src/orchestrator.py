"""
Leak Logic Mapper: Orchestrator
Author: Jacob Wallis

This module manages the execution flow the the system.
It orders functions for analysis in order of bottom up execution,
passes target functions and child context to the LLM and 
hands off an LLM claim to generate a formal analysis tag.

[Maximum worker threads and a choice between a local LLM or an API
can be set in the .env file].
"""

import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import time
from dotenv import load_dotenv
from src.profiler import generate_profile
from src.exceptions import CycleDependencyError

# Load the environment variables
load_dotenv()

# Read the configuration (defaults to 'local' if not set)
ACTIVE_BACKEND = os.getenv("LLM_BACKEND", "local").lower()
# Dynamically assign the function based on the config
if ACTIVE_BACKEND == "api":
    from src.api_interface import query_llm_memory_analyser, setup_client
elif ACTIVE_BACKEND == "local":
    from src.local_interface import query_llm_memory_analyser, setup_client
else:
    raise ValueError(f"Unknown LLM_BACKEND: {ACTIVE_BACKEND}")

# The number of threads that can execute in parallel, defaults to 1
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 1))

def _analyse_function_worker(func_name: str, func_data: dict, child_context: dict, stop_event: threading.Event) -> tuple[dict,dict]:
    """
    Thread to send a single function's data to the LLM analyzer to source a semantic memory profile.
    """
    # If a sibling thread has raised an LLMError, do not send another request to the LLM.
    if stop_event.is_set():
        return {}, {}

    print(f"[*] Thread started for: {func_name}...")

    start_time = time.perf_counter()

    # The thread will wait here until the LLM returns the JSON object or fails.
    llm_inference_payload = query_llm_memory_analyser(
        func_name, 
        func_data["code"], 
        child_context,
        stop_event
    )

    end_time = time.perf_counter()
    duration = end_time - start_time

    print(f"[+] LLM response recieved for '{func_name}' (Took {duration:.2f}s)")

    # Initialise a dictionary to hold known allocators and deallocators used for validation
    dynamic_memory_funcs = {
        "allocators": set(),
        "deallocators": set()
    }

    # Update known allocators and deallocators
    if child_context:
        for child_func_name, child_profile in child_context.items():
            child_tags = child_profile.get("tags", [])
            
            # If the child function's profile proved it returns an allocation
            if any("AllocSource" in tag for tag in child_tags):
                dynamic_memory_funcs["allocators"].add(child_func_name)
                
            # If the child function's profile proved it sinks a pointer
            if any("FreeSink" in tag for tag in child_tags):
                dynamic_memory_funcs["deallocators"].add(child_func_name)

    memory_profile = generate_profile(
        func_name, 
        llm_inference_payload, 
        func_data,
        dynamic_memory_funcs 
    )
    
    # Acts as the return for the 'as_completed' loop in the main orchestrator logic.
    return memory_profile, llm_inference_payload


def run_analysis_pipeline(ast_data: dict) -> tuple[dict, list]:
    """
    The main orchestrator, performs bottom-up analysis dynamically.
    """
    # Initialise backend
    setup_client()

    print("[*] Initialising topological sort")

    # Dictionary to store analysed profiles
    memory_profiles = {}
    # Final order in which profiles were analysed
    analysis_order = []   
    # Signal to abort threads if an API error was raised   
    stop_event = threading.Event()

    # Unprocessed LLM returns, used for debug output
    inference_payloads = {}

    # Tracks how many children a function is waiting on before it can be analysed
    pending_dependencies = {node: 0 for node in ast_data}
    # Maps a child function to all the parents that call it
    parent_map = {node: [] for node in ast_data}

    # Build the directional links of the call graph
    for parent, data in ast_data.items():
        for child in data["children"]:
            # Safety check to only depend on user-defined functions
            if child in ast_data: 
                pending_dependencies[parent] += 1
                parent_map[child].append(parent)

    # Identify the absolute leaf nodes (zero dependencies) to start the pipeline
    ready_queue = [node for node, count in pending_dependencies.items() if count == 0]

    # Initialize the executor exactly
    with ThreadPoolExecutor(MAX_WORKERS) as executor:
        # This dictionary maps a specific background thread to the name of the function it is analysing
        running_tasks = {}

        # Iterates through the intial list of leaf nodes
        for func_name in ready_queue:
            # Get raw C code and parameter data for this function
            func_data = ast_data[func_name]

            # Absolute leaf nodes have no children
            child_context = {}
            
            # Assign this funciton to the next available thread
            future = executor.submit(_analyse_function_worker, func_name, func_data, child_context, stop_event)
            # Map the future to track the function name
            running_tasks[future] = func_name

        print(f"[*] Pipeline initiated with {len(running_tasks)} leaf functions...")

        # Keep running as long as there is at least one active thread and there has not been an error
        while running_tasks and not stop_event.is_set():
            
            # Pause the main thread, returns threads as they complete execution
            done, _ = concurrent.futures.wait(
                running_tasks.keys(),
                return_when=concurrent.futures.FIRST_COMPLETED
            )

            # Process futures that have been completed
            for future in done:
                # Remove from tracking map and get the name
                target_name = running_tasks.pop(future)
                
                try:
                    # Source the completed memory profile
                    memory_profile, llm_inference_payload = future.result()
                    
                    # If another thread has thrown an API error halt execution
                    if stop_event.is_set(): 
                        continue

                    # Save the completed memory profile
                    memory_profiles[target_name] = memory_profile

                    # Used for debug output
                    inference_payloads[target_name] = llm_inference_payload

                    # Log the order of completion
                    analysis_order.append(target_name)
                    print(f"[+] Analysis complete: {target_name}")

                    # Check if this completion unblocks any parent functions
                    for parent in parent_map[target_name]:
                        pending_dependencies[parent] -= 1
                        
                        # If the parent has all child dependencies met, queue it immediately
                        if pending_dependencies[parent] == 0:
                            # Get the function data for the parent node
                            p_data = ast_data[parent]
                            # Organise context from the memory profiles of the child nodes
                            child_context = {
                                child: memory_profiles[child] 
                                for child in p_data["children"] 
                                if child in memory_profiles
                            }
                            
                            # Sink the newly unblocked parent into the executor
                            new_future = executor.submit(_analyse_function_worker, parent, p_data, child_context, stop_event)
                            running_tasks[new_future] = parent

                # Halt execution and store profiles that were successfully analysed
                except Exception as exc:
                    print(f"\n[!] FATAL ERROR: {target_name} failed. Halting Execution...")
                    stop_event.set()
                    executor.shutdown(wait=False, cancel_futures=True)

                    # Bind the partial state to the exception object itself
                    exc.partial_profiles = memory_profiles
                    exc.partial_order = analysis_order
                    exc.partial_payloads = inference_payloads

                    # Store the exception to raise after the pool is closed, then break
                    caught_fatal_error = exc 
                    break

                
                except KeyboardInterrupt:
                    print("\n[!] User aborted. Cancelling active threads...")
                    stop_event.set()
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise

    # Cycle Detection
    if not stop_event.is_set() and len(memory_profiles) < len(ast_data):
        stuck_functions = [name for name in ast_data if name not in memory_profiles]
        raise CycleDependencyError(stuck_functions)
    
    # Raise the error now that the thread pool is safely and fully shut down 
    if stop_event.is_set() and 'caught_fatal_error' in locals():
        raise caught_fatal_error

    return memory_profiles, analysis_order, inference_payloads