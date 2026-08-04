/*
 * TEST CASE: This test case demonstrates that the will bubble up tags for wrapper functions

 * EXPECTED TAGS: [layer_3_cleanup()] FreeSink<int*>::<data>
 *                [layer_2_pass()] FreeSink<int*>::<data>
 *                [layer_1_pass()] FreeSink<int*>::<data>
 *                [target_function()] MemoryNeutral
 *
 * VULNERABILITY: No Vulnerabilities.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// Layer 3 The actual FreeSink
void layer_3_cleanup(int* data) {
    printf("[INFO] Layer 3: Cleaning up buffer at %p...\n", (void*)data);
    free(data);
}

// FreeSink Wrapper
void layer_2_pass(int* data) {
    printf("[DEBUG] Layer 2: Passing pointer down...\n");
    layer_3_cleanup(data);
}

// FreeSink Wrapper
void layer_1_pass(int* data) {
    printf("[DEBUG] Layer 1: Passing pointer down...\n");
    layer_2_pass(data);
}

// TARGET FUNCTION
void target_function() {
    int* buffer = (int*)malloc(1024 * sizeof(int));
    if (buffer == NULL) return;
    
    printf("[DEBUG] Allocated buffer at %p...\n", (void*)buffer);
    buffer[0] = 42;
    
    layer_1_pass(buffer);
}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}