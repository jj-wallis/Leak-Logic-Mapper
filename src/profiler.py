"""
Leak Logic Mapper: Profiler
Author: Jacob Wallis | Student ID: 22513465

This module takes a claim made by the LLM and checks it against dertemistic
data from the AST to validate claims. The module will return a formal tag 
for a function which defines the affect this funciton has on the wider programs memory.

[Generate profiles runs within a thread called by the orchestrator, no global states should be modified
within this function.]
"""


from src.utils import build_ast_maps, normalise_parameters
from src.validators import ROUTING_MATRIX, MEMORY_REGISTRY
from src.constants import Schema
from dataclasses import dataclass

@dataclass
class PointerFlow:
    """
    Returned from the evaluate boundaries function.
    """
    exit_type: str
    src_idx: int | None
    dst_idx: int | None


def _evaluate_boundaries(llm_item: dict, param_map: dict, rets_map: list) -> PointerFlow:
    """
    Evaluates a source, sink, or passthrough to determine its exit type.
    Maps its entry/exit variables to their parameter indices.
    Validates that the parameter entry and exit portals are valid. 
    """
    # Base conditions
    exit_type = Schema.NONE
    src_idx = None
    dst_idx = None

    # Process entry variable for sinks, passthroughs and overwites
    tracked_pointer = llm_item.get("tracked_pointer", Schema.NONE)
    if tracked_pointer != Schema.NONE:
        # Pass the raw string into the normaliser and discard the returned type 
        _, norm_tracked_pointer = normalise_parameters(str(tracked_pointer))
        # Check the entry variable against the AST
        if norm_tracked_pointer in param_map:
            # Get index of entry variable
            src_idx = param_map[norm_tracked_pointer]["index"]

    # Process exit portal and destination index 
    exit_portal = llm_item.get("exit_portal", Schema.NONE)

    # Discard if the llm did not provide an exit portal or last known alias
    if exit_portal == Schema.NONE:
        exit_type = Schema.NONE

    # Check if the exit portal was a return statement and it the ret map is populated
    elif exit_portal == Schema.RETURN and len(rets_map) > 0:
        exit_type = Schema.RETURN

    # Exit portal will be an out parameter
    else:
        # Pass the raw string into the normaliser and discard the returned type 
        _, norm_exit_portal = normalise_parameters(str(exit_portal))

        # Check the out parameter against the AST.
        if norm_exit_portal in param_map:
            exit_type = Schema.OUT_PARAM
            # Get index of out_parameter
            dst_idx = param_map[norm_exit_portal]["index"]
            
    return PointerFlow(exit_type=exit_type, src_idx=src_idx, dst_idx=dst_idx)


def generate_profile(func_name: str, llm_payload: dict, ast_payload: dict, dynamic_memory_funcs: dict) -> dict:
    """
    Evaluates tags for a function by sequentially analysing its sources, sinks and passthroughs.
    Organises the pass of the LLM claim through a route of validating functions checked against
    AST dertemistic boundaries.
    """

    # Build maps by normalising parameters and extracting return statements
    param_map, rets_map = build_ast_maps(ast_payload)

    # Build sets of functions confirmed to be memory allocators or deallocators
    dynamic_allocs = dynamic_memory_funcs.get("allocators", set())
    combined_allocs = dynamic_allocs | MEMORY_REGISTRY["allocators"]

    dynamic_deallocs = dynamic_memory_funcs.get("deallocators", set())
    combined_deallocs = dynamic_deallocs | MEMORY_REGISTRY["deallocators"]
    
    # Unified context for validators
    validation_context = {
        "param_map": param_map, 
        "rets_map": rets_map, 
        "known_allocators": combined_allocs,
        "known_deallocators": combined_deallocs,
        "func_code": ast_payload["code"],
        # Provided so source-based validators can check if a locally allocated pointer is freed in the same function
        "sinks": llm_payload.get("sinks", [])
    }
    
    # Holds resolved tags
    generated_tags = []

    # Map each JSON array to a lambda that generates its specific ROUTING_MATRIX coordinate
    routing_definitons = [
        (Schema.SOURCE, lambda llm_claim, exit_type: (Schema.SOURCE, llm_claim.get("immediate_assignment", Schema.NONE), exit_type)),
        (Schema.SINK, lambda llm_claim, exit_type: (Schema.SINK)),
        (Schema.PASSTHROUGH, lambda llm_claim, exit_type: (Schema.PASSTHROUGH, exit_type)),
        (Schema.REFERENCELOSS, lambda llm_claim, exit_type: (Schema.REFERENCELOSS))
    ]

    # Run a single unified processing loop
    for route_category, build_route_key in routing_definitons:
        
        # Process every source, sink and passthrough in the llm_payload
        for llm_claim in llm_payload.get(route_category, []):
            # Extract exit type, srcIdx and dstIdx
            pointer_flow = _evaluate_boundaries(llm_claim, param_map, rets_map)
            
            # Dynamically build the routing coordinate using the lambda
            route_key = build_route_key(llm_claim, pointer_flow.exit_type)
            route = ROUTING_MATRIX.get(route_key)
            
            # Check validators to map behaviour
            if route and all(validator(llm_claim, validation_context) for validator in route.validators):
                # Build the tag
                prefix = ""
                if llm_claim.get("is_conditional"):
                    prefix = "Cond"

                # If an unconditional source is passed into a conditional sink
                elif route_key == (Schema.SOURCE, Schema.LOCAL, Schema.NONE):
                    linked_sinks = [sink for sink in validation_context["sinks"] if sink.get("linked_allocation_statement") == llm_claim.get("allocation_statement")]
                    if linked_sinks and all(sink.get("is_conditional") for sink in linked_sinks):
                        # Prefix the cond tag
                        prefix = "Cond"
                
                # Get the variable name for the tag
                var_type = llm_claim.get("variable_type", Schema.NONE)
                var_type = var_type.replace(" ", "").strip()

                # Get the last known alias to be used for the leak tag
                alias_trace = llm_claim.get("alias_trace", [])
                # If it has aliases, grab the last one. Otherwise, unknown
                if alias_trace:
                    last_alias = alias_trace[-1]
                else:
                    last_alias = "unknown"
                
                tag = route.template.format(
                    prefix=prefix, 
                    var_type=var_type,
                    srcIdx=pointer_flow.src_idx,
                    dstIdx=pointer_flow.dst_idx,
                    var_name=last_alias
                )
                generated_tags.append(tag)

    # If the function passed through the entire LLM payload and AST validation
    # without triggering a single tag:
    if not generated_tags:
        generated_tags.append("MemoryNeutral")

    return {
        "return_type": ast_payload.get("return_type", ""),
        "functional_description": llm_payload.get("functional_description", ""),
        "tags": generated_tags,
    }