"""
Leak Logic Mapper: Validators
Author: Jacob Wallis

This module defines a series of validator functions which describe rules 
that constrict and filter out LLM hallucinations.
Rules for a claim are listed in a ROUTING MATRIX where the type of operation,
how the pointer associated with that operation came into the function and
how that pointer leaves correspond with a list of rules.
"""

from dataclasses import dataclass
from typing import Callable, List
from src.utils import normalise_parameters, normalise_return_statements
from src.constants import Schema

# Global Registry of known allocators and deallocators
MEMORY_REGISTRY = {
    "allocators": {"malloc", "calloc", "realloc","wcsdup","strdup"},
    "deallocators": {"free"}
}

# --- THE VALIDATORS ---
# Verify internal control flow
def require_allocator(llm_data: dict, validation_data: dict) -> bool:
    """
    Discard if the allocating function in the allocation statement
    has not already been validated.
    """
    statement = llm_data.get("allocation_statement", Schema.NONE)
    if statement == Schema.NONE: return False
    return any(alloc in statement for alloc in validation_data.get("known_allocators"))

def require_deallocator(llm_data: dict, validation_data: dict) -> bool:
    """
    Discard if the deallocating function in the freeing statement
    has not already been validated.
    """
    statement = llm_data.get("free_statement", Schema.NONE)
    if statement == Schema.NONE: return False
    return any(dealloc in statement for dealloc in validation_data.get("known_deallocators"))

def exit_alias_in_returns(llm_data: dict, validation_data: dict) -> bool:
    """
    Checks if the exit_alias exists in the AST return map.
    """
    alias = llm_data.get("exit_alias", Schema.NONE)
    if alias == Schema.NONE: return False
    norm_alias = normalise_return_statements(alias)
    return any(norm_alias in ret for ret in validation_data["rets_map"])

def is_immediate_return(llm_data: dict, validation_data: dict) -> bool:
    """
    Applies a bi-directional check for if the normalised allocation matches an AST return.
    """
    statement = llm_data.get("allocation_statement", Schema.NONE)
    if statement == Schema.NONE: return False 
    
    norm_statement = normalise_return_statements(str(statement))
    return any((norm_statement in ret) or (ret in norm_statement) for ret in validation_data["rets_map"])

def is_source_allocation_statement_in_code(llm_data: dict, validation_data: dict) -> bool:
    """
    Checks if the exact allocation statement claimed by the LLM actually exists within the target function's deterministic boundaries.
    """
    code = validation_data.get("func_code", "")
    
    statement = llm_data.get("allocation_statement", Schema.NONE)
    
    if statement == Schema.NONE: return False 

    # Prevents the check from failing if the allocation statement includes the assignment
    if "=" in statement:
        statement = statement.split("=")[-1] # Takes everything after the last '='
        
    # Strip all whitespace to prevent LLM formatting hallucinations from failing the check
    normalised_code = "".join(code.split())
    normalised_statement = "".join(statement.split())
    
    return normalised_statement in normalised_code

def tracked_pointer_is_not_equal_to_exit_portal(llm_data: dict, validation_data: dict) -> bool:
    """
    Checks that a pointer is not passed back to the same argument in which it entered.
    """
    tracked_pointer = llm_data.get("tracked_pointer", Schema.NONE)
    exit_portal = llm_data.get("exit_portal", Schema.NONE)
    
    if tracked_pointer == Schema.NONE or exit_portal == Schema.NONE: return False 
    
    _, clean_entry = normalise_parameters(str(tracked_pointer))
    _, clean_exit = normalise_parameters(str(exit_portal))
    return clean_entry != clean_exit

def is_not_freed(llm_data: dict, validation_data: dict) -> bool:
    """
    Checks if an allocated pointer lacks a guaranteed free.
    """
    allocation_statement = llm_data.get("allocation_statement", Schema.NONE)
    if allocation_statement == Schema.NONE: return True

    # it is a guaranteed leak. Even if a free() exists later, it's freeing NULL/garbage.
    if llm_data.get("is_reference_lost", False):
        return True
    
    # Check if there is an associating sink for a locally allocated source
    sinks = validation_data.get("sinks", [])
    linked_sinks = [sink for sink in sinks if sink.get("linked_allocation_statement") == allocation_statement]
    if not linked_sinks: return True

    # If one sink is unconditional, the memory is safely handled on the main path.
    has_unconditional_sink = any(not sink.get("is_conditional", False) for sink in linked_sinks)
    if has_unconditional_sink: return False

    # Conditional Leak.
    return True

def is_mutating_argument(llm_data: dict, validation_data: dict) -> bool:
    """
    Validates that the pointer being acted upon was passed in as an argument, rather than being a purely internal local variable.
    """
    raw_entry = str(llm_data.get("tracked_pointer", Schema.NONE))
    if raw_entry == Schema.NONE: return False
    
    _, clean_entry = normalise_parameters(str(raw_entry))
    return clean_entry in validation_data.get("param_map", {})


@dataclass
class TagRoute: 
    template: str                   # Tag template
    validators: List[Callable]      # List of rules that must pass to ensure a tag is appended

ROUTING_MATRIX = {
    # --- AllocSources ---
    # FORMAT: ("Source", "immediate_assignment_type", "exit_type")
    (Schema.SOURCE, Schema.LOCAL, Schema.RETURN): TagRoute(
        template="{prefix}AllocSource<{var_type}>::Ret",
        validators=[require_allocator, exit_alias_in_returns]
    ),
    (Schema.SOURCE, Schema.LOCAL, Schema.OUT_PARAM): TagRoute(
        template="{prefix}AllocSource<{var_type}>::Arg{{{dstIdx}}}",
        validators=[require_allocator]
    ),
    (Schema.SOURCE, Schema.RETURN, Schema.RETURN): TagRoute(
        template="{prefix}AllocSource<{var_type}>::Ret",
        validators=[require_allocator, is_immediate_return]
    ),
    (Schema.SOURCE, Schema.OUT_PARAM, Schema.OUT_PARAM): TagRoute(
        template="{prefix}AllocSource<{var_type}>::Arg{{{dstIdx}}}",
        validators=[require_allocator]
    ),

    # --- InternalLeak --- 
    # FORMAT: ("Source", "immediate_assignment_type", "exit_type")
    (Schema.SOURCE, Schema.LOCAL, Schema.NONE): TagRoute(
        template="{prefix}InternalLeak<{var_type}>::<{var_name}>",
        validators=[require_allocator, is_not_freed]
    ),
    (Schema.SOURCE, Schema.OUT_PARAM, Schema.NONE): TagRoute(
        template="{prefix}InternalLeak<{var_type}>::<{var_name}>",
        validators=[require_allocator, is_not_freed]
    ),
    (Schema.SOURCE, Schema.NONE, Schema.NONE): TagRoute(
        template="{prefix}InternalLeak<{var_type}>::OrphanedReturn",
        validators=[require_allocator, is_source_allocation_statement_in_code]
    ),

    # --- Sinks ---
    # FORMAT: ("Sink")
    (Schema.SINK): TagRoute (
        template="{prefix}FreeSink<{var_type}>::Arg{{{srcIdx}}}",
        validators=[require_deallocator, is_mutating_argument]
    ),
    
    # --- Passthroughs ---
    # FORMAT: ("Passthrough", "exit_type")
    (Schema.PASSTHROUGH, Schema.RETURN): TagRoute (
        template="{prefix}PassThrough<{var_type}>::Arg{{{srcIdx}}}ToRet",
        validators=[tracked_pointer_is_not_equal_to_exit_portal]
    ),
    (Schema.PASSTHROUGH, Schema.OUT_PARAM): TagRoute (
        template="{prefix}PassThrough<{var_type}>::Arg{{{srcIdx}}}ToArg{{{dstIdx}}}",
        validators=[tracked_pointer_is_not_equal_to_exit_portal]
    ),

    # --- Reference Losses ---
    # FORMAT: ("ReferenceLoss")
    (Schema.REFERENCELOSS): TagRoute (
        template="{prefix}ReferenceLoss<{var_type}>::Arg{{{srcIdx}}}",
        validators=[is_mutating_argument]
    ),
}