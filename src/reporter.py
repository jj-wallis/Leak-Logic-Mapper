"""
Leak Logic Mapper: Reporter
Author: Jacob Wallis

Formats a final report to the user and prints it to the terminal.
A summary of leaks detected is included aswell as individual analysis for each function.
The full debug log will show the AST data and LLM claim for each function.
"""

import json    

def _print_debug_log(ast_entry: dict, llm_entry: dict) -> None:
    """
    Prints AST and LLM entries to the terminal for each function analysed.
    To be used whilst debugging, should not be printed to the end user.
    """
    print("\n>> Code:")
    print(ast_entry.get("code")+"\n")
    
    print("\n>> AST INTERFACE (Deterministic Boundaries):")
    function_boundaries = {key: value for key, value in ast_entry.items() if key != "code"}
    print(json.dumps(function_boundaries, indent=2)+"\n")

    print("\n>> LLM SEMANTIC PAYLOAD:")
    print("Sources:", json.dumps(llm_entry.get("sources", []), indent=2)+"\n")
    print("Sinks:", json.dumps(llm_entry.get("sinks", []), indent=2)+"\n")
    print("PassThroughs:", json.dumps(llm_entry.get("passthroughs", []), indent=2)+"\n")
    print("ReferenceLosses:", json.dumps(llm_entry.get("reference_losses", []), indent=2)+"\n")



def print_vulnerability_summary(final_profiles: dict[str, dict]) -> None:
    """
    Scans the final memory profiles and reports a summary of memory leaks detcted.
    """
    print(f"\n" + "="*50)
    print("VULNERABILITY SUMMARY")
    print("="*50)
    
    total_leaks = 0
    
    for func_name, profile in final_profiles.items():
        tags = profile.get("tags", [])
        
        # Filter only the tags that indicate a leak
        leak_tags = [tag for tag in tags if "Leak" in tag]
        
        if leak_tags:
            total_leaks += len(leak_tags)
            print(f"\n[!] LEAK DETECTED: Function '{func_name}'")
            for leak in leak_tags:
                print(f"    -> {leak}")

    if total_leaks == 0:
        print("\n>> No memory leaks detected across the call graph.")
    else:
        print(f"\n>> {total_leaks} leak(s) require attention.")


def print_report(execution_order: list[str], ast_data: dict[str, dict], final_profiles: dict[str, dict], raw_llm_json: dict[str, dict], debug_mode: bool) -> None:
    """
    Print the functional summary, return type and tag associated with each function in the system.
    """
    print("\n=== DETAILED FUNCTION ANALYSIS ===")
    for func_name in execution_order:
        print(f"\n" + "="*50)
        print(f" FUNCTION: {func_name}")
        print("="*50)

        if (debug_mode):
            _print_debug_log(ast_entry=ast_data[func_name], llm_entry=raw_llm_json[func_name])

        print("\n>> MEMORY PROFILE:")
        print(json.dumps(final_profiles[func_name], indent=2))

    print_vulnerability_summary(final_profiles)
            
    print("\n" + "="*50)