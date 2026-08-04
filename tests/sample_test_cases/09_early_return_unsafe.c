/*
 * TEST CASE: This test houses an early return within a conditional block, exiting the function without performing proper cleanup.
 *
 * EXPECTED TAGS: [target_function()]: CondInternalLeak<int*>::<buffer>
 * 
 * VULNERABILITY: The function allocates memory but returns early on an error path without freeing the buffer.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// N/A

// THE TARGET FUNCTION
void target_function(int error_flag) {
    int* buffer = malloc(1024 * sizeof(int));
    if (buffer == NULL) return;

    printf("[DEBUG] Allocated buffer at %p\n", (void*)buffer);

    if (error_flag == 1) {
        return; 
    }

    free(buffer);
}

// MAIN EXECUTION
int main() {
    target_function(0);

    target_function(1);

    return 0;
}