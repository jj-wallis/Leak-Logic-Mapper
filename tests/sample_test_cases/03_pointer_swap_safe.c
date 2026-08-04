/*
 * TEST CASE: This test case demonstrates a function that takes two pointers and swaps them.
 *
 * EXPECTED TAGS: [simple_swap()] PassThrough<int**>::Arg{0}ToArg{1}
 *                                PassThrough<int**>::Arg{1}ToArg{0}
 * 
 * VULNERABILITY: No Vulnerabilities
 */

#include <stdlib.h>
#include <stdio.h>

// DATA STRUCTURES
// N/A

// DEPENDENCY FUNCTIONS
// Swaps the memory addresses held by two pointers.
void simple_swap(int** a, int** b) {
    int* temp = *a;
    *a = *b;
    *b = temp;
}

// THE TARGET FUNCTION
void target_function() {
    int* x = malloc(sizeof(int));
    *x = 100;
    printf("[DEBUG] Allocating %zu bytes at %p [x = %d]\n", sizeof(int), x, *x);
    int* y = malloc(sizeof(int));
    *y = 200;
    printf("[DEBUG] Allocating %zu bytes at %p [y = %d]\n", sizeof(int), y, *y);

    if (x == NULL || y == NULL) return;

    simple_swap(&x, &y);

    printf("[DEBUG] Cleaning up buffer at %p [x = %d]\n", x, *x);
    free(x);
    printf("[DEBUG] Cleaning up buffer at %p [y = %d]\n", y, *y);
    free(y);
}

// MAIN EXECUTION
int main() {
    target_function();
    return 0;
}