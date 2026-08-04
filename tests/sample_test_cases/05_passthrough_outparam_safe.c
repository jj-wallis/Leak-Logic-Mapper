/*
 * TEST CASE: This test demonstrates that the system can keep track of a pointer that is aliased via out parameters.
 *
 * EXPECTED TAGS: [transfer_session_reference()] PassThrough<SessionData*>::Arg{0}ToArg{1}
 *                [target_function()] MemoryNeutral
 * 
 * VULNERABILITY: No vulnerabilities.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
struct SessionData {
    int session_id;
    int is_active;
};

// DEPENDENCY FUNCTIONS
// Safe Passthrough
void transfer_session_reference(struct SessionData* src, struct SessionData** dest) {
    if (src != NULL && dest != NULL) {
        *dest = src;
    }
}

// THE TARGET FUNCTION
void target_function() {

    struct SessionData* original_session = malloc(sizeof(struct SessionData));
    printf("[DEBUG] Allocating %zu bytes at %p...\n", sizeof(struct SessionData), original_session);

    struct SessionData* retrieved_session = NULL;
    
    transfer_session_reference(original_session, &retrieved_session);
    
    printf("[DEBUG] Cleaning up buffer at %p\n", retrieved_session);
    free(retrieved_session);
}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}
