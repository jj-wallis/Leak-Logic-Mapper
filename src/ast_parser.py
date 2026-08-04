"""
Leak Logic Mapper: AST Parser
Author: Jacob Wallis

This module uses tree-sitter-c to extract function indentities
and determistic entry and exit boundaries of a functon.
Entry and exit boundaries are listed as in/ out parameters and return statements.
"""

import tree_sitter_c 
from tree_sitter import Language, Parser, Query, QueryCursor

# Wraps the C grammar rules into a usable Language object for the parser.
C_LANGUAGE = Language(tree_sitter_c.language())

# AST QUERIES
# Tree-sitter will source matches from both patterns one for regular functions and another for functions returning pointers
FUNC_QUERY = """
(function_definition
  type: (_) @return_type
  declarator: (function_declarator 
    declarator: (identifier) @function_name
  ) @function_signature
) @function_body

(function_definition
  type: (_) @return_type
  declarator: (pointer_declarator 
    declarator: (function_declarator 
      declarator: (identifier) @function_name
    )
  ) @function_signature
) @function_body
"""  

PARAMS_QUERY = "(parameter_declaration) @parameter" # Tag parameter (type + name)
CHILD_QUERY = "(call_expression function: (identifier) @child_name)" # Sub function
RET_QUERY = "(return_statement (_) @ret_statement)" # The node that immediately follows the return keyword


def _extract_parameters(signature_node, c_code_bytes: bytes, params_query: Query) -> list[dict]:
    """
    Isolates full parameter strings from a function signature.
    """
    params_list = []

    # Search within the function signature
    for param_match in list(QueryCursor(params_query).matches(signature_node)): 
        # Discard metadata
        p_captures = param_match[1]
        
        # Check for the @parameter tag
        if "parameter" not in p_captures: 
            continue 
            
        # Get the node representing the parameter
        param_node = p_captures["parameter"][0]
        # Slice out the string
        raw_param_string = c_code_bytes[param_node.start_byte:param_node.end_byte].decode('utf8').strip()
        
        params_list.append({
            "raw_text": raw_param_string, 
            "index": len(params_list)
        })
        
    return params_list


def _extract_children(body_node, c_code_bytes: bytes, child_query: Query) -> list[str]:
    """
    Sources the child function calls.
    """
    children_names = [] 
    
    # Search within the body node
    for child_match in list(QueryCursor(child_query).matches(body_node)):
        # Discard metadata
        child_captures = child_match[1] 

        # Ensure @child_name tag was successfully bound
        if child_captures.get("child_name"):
            child_node = child_captures["child_name"][0]
            child_name_str = c_code_bytes[child_node.start_byte:child_node.end_byte].decode('utf8') 
            children_names.append(child_name_str)
            
    # Remove duplicate entries
    return list(set(children_names))


def _extract_ast_returns(body_node, c_code_bytes: bytes, ret_query: Query) -> list[str]:
    """
    Sources the full syntactic line of all return statements.
    """
    rets = []
    
    # Search within the body node
    for match in list(QueryCursor(ret_query).matches(body_node)):

        # Discard metadata
        captures = match[1]

        # Ensure @ret_statement tag was successfully bound
        if "ret_statement" in captures:
            ret_node = captures["ret_statement"][0]
            raw_ret = c_code_bytes[ret_node.start_byte:ret_node.end_byte].decode('utf8').strip()
            rets.append(raw_ret)
            
    return list(set(rets))


def extract_ast_interface(c_code_bytes: bytes) -> dict: 
    """
    The master function that maps the Input/Output boundaries of a C file.
    """
    print("[*] Extracting deterministic AST Interface...")

    # Initialize a new Tree-sitter parser strictly configured for C.
    parser = Parser(C_LANGUAGE) 
    # Feed the raw C bytes into the engine, generate a complete AST.
    tree = parser.parse(c_code_bytes) 
    # Initialize an empty dictionary for final data.
    ast_data = {} 

    # Take S-expression strings and compile them into executable Query objects.
    func_query = Query(C_LANGUAGE, FUNC_QUERY)
    params_query = Query(C_LANGUAGE, PARAMS_QUERY) 
    child_query = Query(C_LANGUAGE, CHILD_QUERY)
    ret_query = Query(C_LANGUAGE, RET_QUERY)

    # Create a QueryCursor to run 'func_query' against, wrapping in list() forces an immediate source of all matches in the file
    function_matches = list(QueryCursor(func_query).matches(tree.root_node))

    # Loop through every function that tree-sitter found
    for match in function_matches: 
        # Throw away metadata, index [1] contains all @tags
        captures = match[1] 
        
        # Use the dictionary's .get() method to safely source the lists of nodes associated with each tag.
        type_nodes = captures.get("return_type", []) 
        signature_nodes = captures.get("function_signature", []) 
        body_nodes = captures.get("function_body", []) 
        name_nodes = captures.get("function_name", []) 
        
        # Safety check: If any of these components are missing, the AST is likely malformed.
        if not type_nodes or not signature_nodes or not body_nodes or not name_nodes: 
            continue
            
        # Unwrap lists to get the actual AST node object.
        type_node = type_nodes[0]
        signature_node = signature_nodes[0]
        body_node = body_nodes[0]
        name_node = name_nodes[0]
        
        # Slice the raw byte-string and decode it back into standard UTF-8 text.
        func_name = c_code_bytes[name_node.start_byte:name_node.end_byte].decode('utf8') 

        # Strip out spaces between type and * symbol for a normalised return type
        gap_start = type_node.end_byte
        gap_end = name_node.start_byte 
        pointers = c_code_bytes[gap_start:gap_end].decode('utf8').replace(' ', '').replace('\n', '') 
        base_return_type = c_code_bytes[type_node.start_byte:type_node.end_byte].decode('utf8').strip() 
        return_type = f"{base_return_type}{pointers}"

        # Slice the main body of the function
        raw_code = c_code_bytes[type_node.start_byte:body_node.end_byte].decode('utf8')
            
        if func_name not in ast_data:
            ast_data[func_name] = {
                "return_type": return_type,
                "params": _extract_parameters(signature_node, c_code_bytes, params_query),
                "children": _extract_children(body_node, c_code_bytes, child_query),
                "rets": _extract_ast_returns(body_node, c_code_bytes, ret_query),
                "code": raw_code
            }

    # Remove any children that are not user-defined functions (i.e standard library calls)
    defined_functions = set(ast_data.keys())
    for func in ast_data: 
        valid_children = [] 
        for child in ast_data[func]["children"]:
            if child in defined_functions:
                valid_children.append(child)
        ast_data[func]["children"] = valid_children
            
    return ast_data