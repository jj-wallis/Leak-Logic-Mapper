/*
 * TEST CASE: This test takes a pointer to a pointer and overwrites it with a new memory allocation, causing the original reference to be overwritten and lost.
 *
 * EXPECTED TAGS: [child_function()]: ReferenceLoss<int*>::Arg{0}
 *                                    AllocSource<int*>::Arg{0}
 *                [target_function]: InternalLeak<int*>::<buffer>
 * 
 * VULNERABILITY: There is a missing free in the buffer_reset function, the reference to the original buffer is lost without being freed when it is set to NULL, causing a memory leak.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// Unsafe AllocSource
void buffer_reset(int** ptr_to_buffer) {
    *ptr_to_buffer = NULL;
    *ptr_to_buffer = (int*)malloc(2048 * sizeof(int));
}

// THE TARGET FUNCTION
void target_function() {
    int* buffer = (int*)malloc(1024 * sizeof(int));
    if (buffer == NULL) return;
    
    printf("[DEBUG] Allocated buffer at %p...\n", (void*)buffer);
    buffer[0] = 42;

    buffer_reset(&buffer);
    
    if (buffer == NULL) return; 

    printf("[INFO] Cleaning up buffer...\n");
    free(buffer);
}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}