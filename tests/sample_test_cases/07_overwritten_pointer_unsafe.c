/*
 * TEST CASE: This test case stores the returned pointer from process but overwrites myNode in the act of doing so.
 *
 * EXPECTED TAGS: [process()] AllocSource<Node*>::Ret
 *                [target_function()] InternalLeak<Node*>::<myNode>
 * 
 * VULNERABILITY: Overwritten pointer in target_function()
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
struct Node {
    int data;
};

// DEPENDENCY FUNCTIONS
struct Node* process(struct Node* incoming) {
    struct Node* a = incoming; 
    a = malloc(sizeof(struct Node)); 
    return a; 
}

// THE TARGET FUNCTION
// Overwrite our original pointer with the returned pointer.
void target_function() {
    struct Node* myNode = malloc(sizeof(struct Node));
    printf("[DEBUG] Allocating %zu bytes at %p...\n", sizeof(struct Node), myNode);
    
    myNode = process(myNode); 
    
    printf("[DEBUG] Cleaning up buffer at %p\n", myNode);
    free(myNode);

}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}