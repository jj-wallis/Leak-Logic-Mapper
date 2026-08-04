"""
Leak Logic Mapper: Exceptions
Author: Jacob Wallis

This module is used to define and custom exceptions to wrap anticipated errors.
"""

class CycleDependencyError(Exception):
    """
    Exception raised when a cyclic dependency is detected in the function call graph.
    (triggered if the codebase invloved recursive functions which out of scope in V1.0)
    """
    def __init__(self, stuck_functions: list):
        # The list of function names that could not be resolved
        self.stuck_functions = stuck_functions
        # Summary to be displayed to the user.
        self.message = f"Analysis halted: Cyclic dependency detected in {len(stuck_functions)} functions."
        super().__init__(self.message)

    def __str__(self):
        # Returns the list of functions not resolved
        return f"{self.message} Stuck nodes: {', '.join(self.stuck_functions)}"


class LLMError(Exception):
    """
    Exception raised when an API transaction fails.
    """
    def __init__(self, func_name: str, original_error: str):
        # The identity of the function being analyzed when the error occured
        self.func_name = func_name
        # Raw error string from the API.
        self.original_error = original_error

        # Optional containers for rescuing partial pipeline state
        self.partial_profiles = {}
        self.partial_order = []
        self.partial_payloads = {}
        
        # Summary to be displayed to the user.
        self.message = f"API Failure during analysis of '{func_name}': {original_error}"
        super().__init__(self.message)
