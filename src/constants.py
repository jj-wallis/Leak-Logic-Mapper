"""
Leak Logic Mapper: Reporter
Author: Jacob Wallis

This module defines constants that are pulled by multiple files.
"""

class Schema:
    """
    Direct mapping to the JSON schema.
    """
    SOURCE = "sources"
    SINK = "sinks"
    PASSTHROUGH = "passthroughs"
    REFERENCELOSS = "reference_losses"
    LOCAL = "local_variable"
    RETURN = "return_statement"
    OUT_PARAM = "out_parameter"
    NONE = "none"