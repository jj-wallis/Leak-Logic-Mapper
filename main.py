"""
Leak Logic Mapper: Application Entry Point
Author: Jacob Wallis

Sources arguments from the command line, runs a C code snippet through
the AST extractor, passes the data to the local LLM interface, and outputs 
the vulnerability report to the console.
"""

import argparse
import os
import sys
import traceback

sys.dont_write_bytecode = True

from src.orchestrator import run_analysis_pipeline
from src.ast_parser import extract_ast_interface
from src.exceptions import CycleDependencyError, LLMError
from src.reporter import print_report
from src.utils import DualLogger
from datetime import datetime


class CLIParser(argparse.ArgumentParser):
    """
    Custom CLIparser to override error handling
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.add_argument("filepath", type=str, help="The path to the .c file you want to analyse.")
        self.add_argument("-l", action="store_true", help="Log the terminal output to the logs directory.")
        self.add_argument("-d", action="store_true", help="Print debug information. Including the AST parsed function boundaries and the LLM query responses.")
    
    # Triggers when no arguments are given
    def error(self, message):
        print(f"usage: {self.usage}")
        #print(f"main.py: error: {message}") # Commented out to suppress the error message
        print("Try 'python main.py --help' for more information.")
        sys.exit(1)


def main():
    try:
        # Initialize argument parser
        parser = CLIParser(
            usage="python main.py [OPTIONS] [FILEPATH]" 
        )

        args = parser.parse_args()

        # Check file paths
        if not os.path.exists(args.filepath):
            print(f"[!] PATH ERROR: The path '{args.filepath}' does not exist.")
            sys.exit(1)
            
        if os.path.isdir(args.filepath):
            print(f"[!] PATH ERROR: '{args.filepath}' is a directory. Please specify a .c file.")
            sys.exit(1)

        # Read the target .c file into bytes
        print(f"[*] Reading target file: {args.filepath}")
        with open(args.filepath, 'rb') as file:
            target_c_code = file.read()

        # Duplicate output to a log file if the -l was specified
        if args.l:
            os.makedirs("logs", exist_ok=True) 
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.basename(args.filepath)
            log_name = f"logs/{base_name}_{timestamp}.log"
            sys.stdout = DualLogger(log_name)
            print(f"[*] Logging enabled. Output is being saved to '{log_name}'")

        debug_mode = True if args.d else False

        print("\n=== STAGE 1: FUNCTION BOUNDARY ANALYSIS ===")
        
        # Extract determinstic data used to validate llm claims
        ast_data = extract_ast_interface(target_c_code)

        print("\n=== STAGE 2: LLM SEMANTIC EXTRACTION ===")
        
        # Run bottom up analysis on all functions in the codebase
        final_profiles, execution_order, raw_llm_json = run_analysis_pipeline(ast_data)

        print("\n=== PIPELINE COMPLETE ===")
        print("\n[+] Topological Analysis Order (Bottom-Up):")
        print(" -> ".join(execution_order))

        # Print a debug report to the user
        print_report(execution_order, ast_data, final_profiles, raw_llm_json, debug_mode)

    except CycleDependencyError as e:
        # CycleDependencyError was raised (the codebase invloved recursive functions which out of scope in V1.0)
        print(f"\n[!] PIPELINE HALTED: {e}")
        print("[*] Please check the following functions for recursion:")
        for func in e.stuck_functions:
            print(f"  - {func}")
            
        sys.exit(1)

    except LLMError as e:  
        print(f"\n[!] SERVICE ERROR: {e}")
              
        # Check for functions that were analysed before the error
        if hasattr(e, 'partial_order') and len(e.partial_order) > 0:
            # Feed the rescued data into the existing report generator
            print_report(e.partial_order, ast_data, e.partial_profiles, e.partial_payloads, debug_mode)

            print("\n=== RESCUED PARTIAL ANALYSIS ===")
            print(f"[*] Successfully analyzed {len(e.partial_order)} functions before failure.")
        else:
            print("[*] No functions were successfully analyzed before the failure.")

        sys.exit(1)

    except ValueError as e:
        print(f"\n[!] CONFIGURATION ERROR: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n[!] PIPELINE HALTED: Manual cancellation by user.")
        sys.exit(130)

    except Exception as e:
        # A catch-all for any errors
        print(f"[!] CRITICAL ERROR: An unexpected issue occurred: {e}")

        #traceback.print_exception(e) # Commented out so user errors are not cluttered

        sys.exit(1)


if __name__ == "__main__":
   main()