/*
 * TEST CASE: This test case shows that the system should highlight a potential flaw determining that the allocation may not on certain run time conditions.
 *
 * EXPECTED TAGS: [target_function()] CondInternalLeak<char*>::<data>
 * 
 * VULNERABILITY: The allocation and free are dependent on random runtime return conditions.
 * 
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
int globalReturnsTrueOrFalse() 
{
    return (rand() % 2);
}

// THE TARGET FUNCTION
void target_function() {
    char * data;
    data = NULL;

    data = (char *)malloc(100*sizeof(char));
    printf("[DEBUG] Allocated heap buffer at %p\n", data);
    if (data == NULL) {exit(-1);}
    
    strcpy(data, "A String");
    printf("%s\n",data);

    if(globalReturnsTrueOrFalse())
    {
        
    }
    else
    {
        printf("[DEBUG] Cleaning up buffer at %p\n", data);
        free(data);
    }
}

// MAIN EXECUTION
int main() {
    srand(time(NULL));

    target_function();
    return 0;
}
