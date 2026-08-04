/*
 * TEST CASE: This case tests an orphaned return, the return pointer from the allocating call process is not stored.
 *
 * EXPECTED TAGS: [process()] AllocSource<Node*>::Ret
 *                [target_function()] InternalLeak<Node*>::OrphanedReturn
 * 
 * VULNERABILITY: Orphaned return.
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
struct Node {
    int data;
};

// DEPENDENCY FUNCTIONS
// AllocSource
struct Node* process(struct Node* incoming) {
    struct Node* a = incoming; 

    a = malloc(sizeof(struct Node)); 
    return a; 
}

// THE TARGET FUNCTION
// Call process but do not store the returned pointer.
void target_function() {
    struct Node* myNode = malloc(sizeof(struct Node));
    printf("[DEBUG] Allocating %zu bytes at %p...\n", sizeof(struct Node), myNode);
    
    process(myNode); 
    
    printf("[DEBUG] Cleaning up buffer at %p\n", myNode);
    free(myNode);
}

// MAIN EXECUTION (The Entry Point)
int main() {
    target_function();
    return 0;
}