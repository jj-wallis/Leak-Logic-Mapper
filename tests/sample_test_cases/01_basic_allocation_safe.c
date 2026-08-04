/*
 * TEST CASE: This test demonstrates how the system handles basic allocation/deallocation wrapper functions.
 *
 * EXPECTED TAGS: [source_buffer()] AllocSource<void*>::Ret
 *                [cleanup_buffer()] FreeSink<void*>Arg{0}
 *                [target_function()] MemoryNeutral
 * 
 * VULNERABILITY: No vulnerabilities.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// Safe AllocSource
void* source_buffer(size_t size) {
    printf("[DEBUG] Allocating %zu bytes...\n", size);

    void * p = malloc(size);
    return p;
}

// Safe FreeSink
void cleanup_buffer(void* ptr) {
    printf("[DEBUG] Cleaning up buffer at %p\n", ptr);
    free(ptr);
}

// TARGET FUNCTION
void target_function() {

    void* my_data = source_buffer(1024);

    if (my_data == NULL) {
        return;
    }

    cleanup_buffer(my_data);
}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}