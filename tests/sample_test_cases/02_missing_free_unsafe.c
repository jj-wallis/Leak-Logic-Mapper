/*
 * TEST CASE: This test demonstrates how the system handles a pointer that is not freed.
 *
 * EXPECTED TAGS: [create_session()] AllocSource<void*>::Ret
 *                [end_session()] FreeSink<void*>::Arg{0}
 *                [target_function()] InternalLeak<void*>::<current_session>
 * 
 * VULNERABILITY: The programmer forgets to call end_session() before the program terminates.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// Safe AllocSource
void* create_session(size_t size) {
    printf("[DEBUG] Allocating %zu bytes...\n", size);

    return malloc(size);
}

// FreeSink
// Safe FreeSink that is never called
void end_session(void* session) {
    printf("[DEBUG] Cleaning up buffer at %p\n", session);

    free(session);
}

// THE TARGET FUNCTION
void target_function() {
    void* current_session = create_session(128);
}

// MAIN EXECUTION (The Entry Point)
int main() {
    target_function();
    return 0;
}
