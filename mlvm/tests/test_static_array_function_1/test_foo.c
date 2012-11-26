#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include "foo.h"

const int N = 10;

int test_foo(){
    int i, n;
    float A[N];
    float B[N];
    float C[N];

    for (i=0; i<N; ++i){
        A[i] = rand() % N;
        B[i] = rand() % N;
    }

    n = foo(A, B, C, N);

    for (i=0; i<N; ++i){
        float expect = (A[i] + B[i]) * 3.14;
        float relerr = fabs(expect - C[i]) / expect;
        if (relerr > 1e-5){
            return 0;
        }
    }
    return 1;
}


int test_foo2(){
    int i, n;
    double A[N];
    double B[N];
    double C[N];

    for (i=0; i<N; ++i){
        A[i] = rand() % N;
        B[i] = rand() % N;
    }

    n = foo2(A, B, C, N);

    for (i=0; i<N; ++i){
        double expect = (A[i] + B[i]) * 3.14;
        double relerr = fabs(expect - C[i]) / expect;
        if (relerr > 1e-5){
            return 0;
        }
    }
    return 1;
}


int main(){
    printf("test_foo()...");
    if (!test_foo()){
        puts("error");
        return 1;
    } else {
        puts("ok");
    }

    printf("test_foo2()...");
    if (!test_foo2()){
        puts("error");
        return 1;
    } else {
        puts("ok");
    }
    return 0;
}