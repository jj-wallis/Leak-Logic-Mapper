/*
 * TEST CASE: This test case expects that the system will not recognise alloca as a heap allocation source.
 *
 * EXPECTED TAGS: There is no tag that encapsulates this behaviour in Leak Logic Mapper v1.0
 * 
 * VULNERABILITY: The function allocates memory on the stack using alloca and returns the pointer. The memory is instantly corrupted upon return.
 */

#include <stdlib.h>
#include <stdio.h>
#include <alloca.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// N/A

// THE TARGET FUNCTION
// Dynamic allocation on the stack
int* target_function() {
    int* buffer = (int*)alloca(1024 * sizeof(int));
    
    printf("[DEBUG] Allocated buffer at %p...\n", (void*)buffer);

    buffer[0] = 42;

    return buffer; 
}

// MAIN EXECUTION
// Accessing this is undefined behavior, the stack frame is gone.
int main() {
    int* ptr = target_function();
    
    printf("Accessing memory: %d\n", ptr[0]);

    return 0;
}