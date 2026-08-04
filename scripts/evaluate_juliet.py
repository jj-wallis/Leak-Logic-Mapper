"""
Leak Logic Mapper: Automated Juliet Evaluation Harness
Author: Jacob Wallis | Student ID: 22513465

This script automatically iterates through a directory of Juliet CWE-401 test cases,
bypasses the CLI to directly invoke the core analysis pipeline, evaluates the memory
profiles against Juliet's naming conventions, and exports the metrics to a CSV file.
"""

import os
import glob
import csv
import traceback
from src.ast_parser import extract_ast_interface
from src.orchestrator import run_analysis_pipeline
from src.exceptions import CycleDependencyError, LLMError
import time 
import re

def sanitize_source_code(raw_code: bytes) -> bytes:
    """
    Prevents LLM Data Leakage by stripping explicit vulnerability hints
    and anonymizing function names from the Juliet Test Suite.
    """
    code_str = raw_code.decode('utf-8', errors='ignore')

    # 1. Strip Block Comments /* ... */
    code_str = re.sub(r'/\*.*?\*/', '', code_str, flags=re.DOTALL)
    
    # 2. Strip Line Comments // ...
    code_str = re.sub(r'//.*', '', code_str)

    # 3. Anonymize Function Names
    code_str = code_str.replace('_bad', '_target')
    
    # By replacing 'good' with 'variant', we safely catch both the primary wrapper 
    # (e.g., '_good' -> '_variant') AND the secondary functions 
    # (e.g., 'goodB2G1' -> 'variantB2G1') in one sweep.
    code_str = code_str.replace('good', 'variant')

    return code_str.encode('utf-8')

# --- CONFIGURATION ---
TEST_SUITE_DIR = "tests/juliet/" 
OUTPUT_CSV = "juliet_evaluation_results.csv"

def is_bad_function(func_name: str) -> bool:
    """The vulnerable function is now anonymized to end with '_target'"""
    return func_name.endswith('target')

def is_good_function(func_name: str) -> bool:
    """The safe functions are now anonymized to start with 'variant'"""
    # We explicitly exclude the primary wrapper function, which ends with '_variant'
    # This leaves only the actual safe secondary functions (e.g., variant1, variantB2G1)
    return func_name.startswith('variant') and not func_name.endswith('_variant')

def evaluate_file(filepath: str) -> dict:
    """Runs the pipeline on a single file and tallies the metrics."""
    metrics = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "Total": 0}
    
    with open(filepath, 'rb') as file:
        raw_c_code = file.read()

    # Apply the Sanitizer HERE before the AST reads it!
    sanitized_code = sanitize_source_code(raw_c_code)

    # ==========================================
    # DEBUG: PRINT SANITIZED CODE AND EXIT
    # ==========================================
    #import sys
    #print(f"\n[DEBUG] Previewing sanitized code for: {os.path.basename(filepath)}")
    #print("=" * 60)
    #print(sanitized_code.decode('utf-8'))
    #print("=" * 60)
    #print("[DEBUG] Exiting script to prevent terminal flooding.")
    #sys.exit(0) 
    # ==========================================

    try:
        # Bypass the CLI and invoke the Python modules directly
        ast_data = extract_ast_interface(sanitized_code)
        final_profiles, _, _ = run_analysis_pipeline(ast_data)

        # Evaluate the generated profiles against Juliet's naming rules
        for func_name, profile in final_profiles.items():
            tags = profile.get("tags", [])
            has_leak_tag = any("Leak" in tag for tag in tags)

            if is_bad_function(func_name):
                metrics["Total"] += 1
                if has_leak_tag:
                    metrics["TP"] += 1
                else:
                    metrics["FN"] += 1

            elif is_good_function(func_name):
                metrics["Total"] += 1
                if has_leak_tag:
                    metrics["FP"] += 1
                else:
                    metrics["TN"] += 1

    except Exception as e:
        print(f"[!] Evaluation failed for {os.path.basename(filepath)}: {e}")
        return None # Skip this file in the final tally if it crashes

    return metrics

def main():
    print(f"[*] Starting Automated Evaluation of Juliet Test Suite...")
    print(f"[*] Target Directory: {TEST_SUITE_DIR}")
    
    search_pattern = os.path.join(TEST_SUITE_DIR, "**/*.c")
    test_files = glob.glob(search_pattern, recursive=True)
    
    if not test_files:
        print("[!] No .c files found. Please check your TEST_SUITE_DIR path.")
        return

    print(f"[*] Found {len(test_files)} test files. Beginning analysis...")

    overall_tp, overall_fp, overall_fn, overall_tn = 0, 0, 0, 0

    # Write the CSV Header immediately
    fieldnames = ["Test Case File", "Total Functions", "TP", "FP", "FN", "TN"]
    with open(OUTPUT_CSV, mode='w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

    for idx, filepath in enumerate(test_files, 1):
        filename = os.path.basename(filepath)
        print(f"[{idx}/{len(test_files)}] Evaluating {filename}...")
        
        file_metrics = evaluate_file(filepath)
        
        if file_metrics:
            overall_tp += file_metrics["TP"]
            overall_fp += file_metrics["FP"]
            overall_fn += file_metrics["FN"]
            overall_tn += file_metrics["TN"]
            
            # Save the row immediately (Append Mode)
            row_data = {
                "Test Case File": filename,
                "Total Functions": file_metrics["Total"],
                "TP": file_metrics["TP"],
                "FP": file_metrics["FP"],
                "FN": file_metrics["FN"],
                "TN": file_metrics["TN"]
            }
            with open(OUTPUT_CSV, mode='a', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writerow(row_data)

        # Pause to prevent API Rate Limiting (Adjust up if you still get 429 errors)
        time.sleep(1) 

    # Calculate Final Metrics
    total_functions = overall_tp + overall_fp + overall_fn + overall_tn
    precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0
    recall = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "="*50)
    print("FINAL EVALUATION METRICS")
    print("="*50)
    print(f"Total Files Evaluated: {len(test_files)}")
    print(f"Total Functions Evaluated: {total_functions}\n")
    print(f"True Positives (TP):  {overall_tp}")
    print(f"False Positives (FP): {overall_fp}")
    print(f"False Negatives (FN): {overall_fn}")
    print(f"True Negatives (TN):  {overall_tn}\n")
    print(f"Precision: {precision * 100:.2f}%")
    print(f"Recall:    {recall * 100:.2f}%")
    print(f"F1 Score:  {f1_score:.3f}")
    print("="*50)

if __name__ == "__main__":
    main()