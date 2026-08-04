"""
Leak Logic Mapper: Utils
Author: Jacob Wallis | Student ID: 22513465

This module defines and houses utility functions used when validating LLM claims
against AST data.
As well as classes used for CLI options.
"""

import re
import sys
from typing import Tuple, Dict, List
from src.constants import Schema

class DualLogger:
    """
    Catches all print() statements and sends them to both terminal and a file.
    """
    def __init__(self, log_filepath):
        self.terminal = sys.stdout  # Save the original standard output
        self.log_file = open(log_filepath, "w", encoding="utf-8") # Open the log file

    def write(self, message):
        self.terminal.write(message)   # Print to the screen
        self.log_file.write(message)   # Write to the file

    def flush(self):
        # Clear buffers
        self.terminal.flush()
        self.log_file.flush()


# Pre-compiles the pattern to strip simple type-casts like '(void*)', requiring text afterward to prevent deleting valid variables.
POINTER_CAST_REGEX = re.compile(r'^\(\s*[a-zA-Z_][\w\s\*]*\)\s*(.*)')
RETURN_KEYWORD_REGEX = re.compile(r'^return\s+')


def normalise_return_statements(raw_ret: str) -> str:
    """
    Strips redundant wrapping parentheses and basic type-casts from a return expression string.
    """
    # Start cleanup to strip away to the core expression.
    clean_ret = raw_ret.strip()
    # Strip trailing semicolons (common in LLM output)
    clean_ret = clean_ret.rstrip(';')
    # Strip leading 'return' keyword safely
    clean_ret = RETURN_KEYWORD_REGEX.sub('', clean_ret).strip()
    
    # Strip wrapping parentheses
    while clean_ret.startswith('(') and clean_ret.endswith(')'):
        depth = 0
        # Assumes the outer parentheses are a matching pair until proven otherwise.
        is_wrapping_pair = True
        
        # Check if the outer parentheses actually belong to each other
        for char in clean_ret[:-1]:
            if char == '(': depth += 1
            elif char == ')': depth -= 1
            
            # If depth hits 0 before the end, the first '(' and last ')' don't match.
            if depth == 0: 
                is_wrapping_pair = False
                break
                
        if is_wrapping_pair:
            # Slices off the first and last characters (the parentheses) and strips any inner padding.
            clean_ret = clean_ret[1:-1].strip()
        else:
            # Core expression reached
            break 

    # Strip basic type casts
    cast_match = POINTER_CAST_REGEX.match(clean_ret)
    if cast_match:
        clean_ret = cast_match.group(1).strip()

    # Dense normalization for strict pattern matching
    return re.sub(r'\s+', '', clean_ret)


def normalise_parameters(raw_text: str) -> tuple[str, str]:
    """
    Cleans C pointer syntax to isolate a base variable name and its type.
    Handles full declarations ('void ** p'), pointer variables ('*p'), 
    or split AST data.
    """
    # Count stars natively
    pointer_depth = raw_text.count('*')
    
    # Strip stars to get pure text
    clean_text = raw_text.replace('*', '').strip()
    words = clean_text.split()
    
    # Safety check for empty strings
    if not words:
        return "", ""
        
    # The variable name is always the last word
    param_name = words[-1]
    
    # Assume all preceding words make up the base type.
    derived_base = " ".join(words[:-1])
        
    # Reconstruct the type (If derived_base is empty, it just leaves the stars)
    full_type = f"{derived_base}{'*' * pointer_depth}".strip()
    
    return full_type, param_name


def build_ast_maps(ast_payload: dict) -> Tuple[Dict[str, Dict], List[str]]:
    """Pre-computes parameter lookups and normalised returns."""
    
    param_map = {}
    for param in ast_payload.get("params", []):
        
        # Sink the single raw string into the normaliser to split the type and the base name.
        full_type, clean_name = normalise_parameters(param["raw_text"])
        
        # If the split was succesfull, add it to the param map
        if clean_name:
            param_map[clean_name] = {"index": param["index"], "type": full_type}

    # Remove the literal keyword 'return' and type casts from the return statement
    rets_map = [normalise_return_statements(ret) for ret in ast_payload.get("rets", [])]
    
    return param_map, rets_map


def sanitize_llm_json(data):
    """
    Recursively replaces all Python None values with the string 'none'.
    This is called for local models whihc struggle to adhere to JSON.
    """
    if isinstance(data, dict):
        return {key: sanitize_llm_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_llm_json(i) for i in data]
    elif data is None:
        return Schema.NONE
    return data