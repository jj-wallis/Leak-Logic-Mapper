/*
 * TEST CASE: This test houses a free statement within a conditional block.
 *
 * EXPECTED TAGS: [target_function()]: CondInternalLeak<int*>::<buffer>
 * 
 * VULNERABILITY: Depending on the execution path, the memory may leak.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// N/A

// THE TARGET FUNCTION
void target_function(int cleanup_flag) {
    int* buffer = malloc(1024 * sizeof(int));
    if (buffer == NULL) return;

    printf("[DEBUG] Allocated 4096 bytes at %p...\n", (void*)buffer);

    if (cleanup_flag == 1) {
        free(buffer);
    } 
    
    else {
        
    }
    
}

// MAIN EXECUTION
int main() {
    
    target_function(1);

    target_function(0);

    return 0;
}