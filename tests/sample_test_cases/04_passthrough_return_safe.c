/*
 * TEST CASE: This test demonstrates that the system can keep track of a pointer that is passed through and safely utilised then aliased by a child function.
 *
 * EXPECTED TAGS: [activate_session()] PassThrough<SessionData*>::Arg{0}ToRet
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
// Safe PassThrough
struct SessionData* activate_session(struct SessionData* session) {
    if (session != NULL) {
        session->is_active = 1;
    }
    return session; 
}

// THE TARGET FUNCTION
void target_function() {
    
    struct SessionData* my_session = malloc(sizeof(struct SessionData));
    printf("[DEBUG] Allocating %zu bytes at %p...\n", sizeof(struct SessionData), my_session);
    
    struct SessionData* active_session = activate_session(my_session);
    
    printf("[DEBUG] Cleaning up buffer at %p\n", my_session);
    free(active_session);
}

// MAIN EXECUTION (The Entry Point)
int main() {
    target_function();
    return 0;
}