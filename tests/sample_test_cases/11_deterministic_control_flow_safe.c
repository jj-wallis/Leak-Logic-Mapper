/*
 * TEST CASE: This case tests the systems ability to use contextual clues to understand control flow.
 *
 * EXPECTED TAGS: [target_function()] MemoryNeutral
 * 
 * VULNERABILITY: No vulnerabilities.
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
static int staticReturnsTrue()
{
    return 1;
}

static int staticReturnsFalse()
{
    return 0;
}

// THE TARGET FUNCTION
void target_function() {
    char * data;
    data = NULL;
    if(staticReturnsTrue())
    {
        data = (char *)malloc(100*sizeof(char));
        if (data == NULL) {exit(-1);}

        printf("[DEBUG] Allocated buffer at %p\n", data);

        strcpy(data, "A String");
        printf("%s\n", data);
    }
    if(staticReturnsFalse())
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
    target_function();
    return 0;
}